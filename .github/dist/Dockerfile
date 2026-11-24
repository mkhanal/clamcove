FROM rust:1.99.1-trixie@sha256:09027f873d45b8ecd1dc86f1fa13b7a62b875c961f017a0e331267b350430137 AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake libbz2-dev libcurl4-openssl-dev libjson-c-dev libncurses-dev libpcre2-dev \
    libssl-dev libxml2-dev pkg-config zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*
COPY . /src
RUN cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr \
    -DAPP_CONFIG_DIRECTORY=/etc/clamav -DDATABASE_DIRECTORY=/var/lib/clamav \
    -DENABLE_TESTS=OFF -DENABLE_EXAMPLES=OFF -DENABLE_MAN_PAGES=OFF \
    -DENABLE_MILTER=OFF -DENABLE_CLAMONACC=OFF -DENABLE_SYSTEMD=OFF \
 && cmake --build /build --parallel "$(nproc)" && DESTDIR=/out cmake --install /build
RUN mkdir /runtime /updater && cd /out \
 && cp -a --parents usr/sbin/clamd usr/bin/clamdscan etc/clamav/certs /runtime/ \
 && find usr/lib -name 'lib*.so*' ! -name 'libfreshclam.so*' -exec cp -a --parents {} /runtime/ \; \
 && cp -a --parents usr/bin/freshclam etc/clamav/certs /updater/ \
 && find usr/lib \( -name 'libclamav.so*' -o -name 'libclammspack.so*' -o -name 'libclamunrar_iface.so*' -o -name 'libfreshclam.so*' \) -exec cp -a --parents {} /updater/ \; \
 && find /runtime /updater -type f \( -name 'lib*.so*' -o -path '*bin/*' \) -exec strip --strip-unneeded {} +
ARG CLAMCOVE_REV
RUN test -n "$CLAMCOVE_REV" \
 && printf '%s\n' \
    "Complete corresponding source of this image, at https://github.com/mkhanal/clamcove/releases/tag/clamcove-$CLAMCOVE_REV:" \
    "- clamcove-$CLAMCOVE_REV.tar.gz: ClamCove $CLAMCOVE_REV." \
    "- clamcove-$CLAMCOVE_REV-debian-sources.tar: the Debian source package of every Debian package in this image," \
    "  at the version its dpkg records in /var/lib/dpkg name." > /SOURCES

FROM debian:trixie-slim@sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2 AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libbz2-1.0 libjson-c5 libpcre2-8-0 libssl3t64 libxml2 zlib1g \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1000 clamav \
    && useradd --system --uid 1000 --gid clamav --home-dir /var/lib/clamav --shell /usr/sbin/nologin clamav \
    && mkdir -p /var/lib/clamav /var/log/clamav && chown clamav:clamav /var/lib/clamav /var/log/clamav
COPY --from=build /runtime/ /
COPY --from=build /SOURCES /usr/share/doc/clamcove/SOURCES
RUN ldconfig
LABEL org.opencontainers.image.title="ClamCove runtime" \
      org.opencontainers.image.description="clamd and clamdscan of ClamCove, ClamAV with RAR read through libarchive; no RARLAB unRAR code. Not affiliated with or endorsed by Cisco or the ClamAV project." \
      org.opencontainers.image.licenses="GPL-2.0-only" \
      org.opencontainers.image.source="https://github.com/mkhanal/clamcove"
CMD ["clamd", "--version"]

FROM debian:trixie-slim@sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2 AS updater-root
RUN apt-get update && apt-get install -y --no-install-recommends \
    libbz2-1.0 libcurl4t64 libjson-c5 libpcre2-8-0 libssl3t64 libxml2 zlib1g ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /updater/ /
COPY --from=build /src/COPYING.txt /SOURCES /root-fs/usr/share/doc/clamcove/
COPY --from=build /src/COPYING/ /root-fs/usr/share/doc/clamcove/COPYING/
RUN <<'EOF'
set -eu
ldconfig
root=/root-fs
if ldd /usr/bin/freshclam | grep 'not found'; then exit 1; fi
triplet=$(basename "$(dirname "$(ldd /usr/bin/freshclam | awk '$1 ~ /^libc\.so/ {print $3}')")")
files=$( { echo /usr/bin/freshclam; ldd /usr/bin/freshclam | awk '$2 == "=>" && $3 ~ /^\// {print $3} $1 ~ /^\// {print $1}'; } | sort -u)
for f in $files; do mkdir -p "$root$(dirname "$f")"; cp -L "$f" "$root$f"; done
cp -a --parents /etc/clamav/certs "$root"
mkdir -p "$root/var/lib/dpkg/status.d" "$root/etc/ssl/certs" "$root/var/lib/clamav" "$root/tmp"
cp -L /etc/ssl/certs/ca-certificates.crt "$root/etc/ssl/certs/"
packages=ca-certificates
for f in $files; do
  case "$f" in /usr/bin/freshclam | */libclamav.so.* | */libclammspack.so.* | */libclamunrar_iface.so.* | */libfreshclam.so.*) continue ;; esac
  p=$( { dpkg -S "$f" || true; dpkg -S "$(realpath "$f")" || true; } 2> /dev/null | grep -v '^diversion ' | head -1 | cut -d: -f1)
  [ -n "$p" ] || { echo "no Debian package owns $f"; exit 1; }
  packages="$packages $p"
done
for p in $(printf '%s\n' $packages | sort -u); do
  dpkg-query -s "$p" > "$root/var/lib/dpkg/status.d/$p"
  mkdir -p "$root/usr/share/doc/$p"
  cp -L "/usr/share/doc/$p/copyright" "$root/usr/share/doc/$p/copyright"
done
printf 'root:x:0:0:root:/root:/usr/sbin/nologin\nclamav:x:1000:1000:clamav:/var/lib/clamav:/usr/sbin/nologin\n' > "$root/etc/passwd"
printf 'root:x:0:\nclamav:x:1000:\n' > "$root/etc/group"
printf 'DatabaseDirectory /var/lib/clamav\nDatabaseMirror database.clamav.net\nForeground yes\nLogTime yes\nChecks 12\n' > "$root/etc/clamav/freshclam.conf"
printf '/lib/%s\n/usr/lib/%s\n' "$triplet" "$triplet" > "$root/etc/ld.so.conf"
ldconfig -r "$root"
chown 1000:1000 "$root/var/lib/clamav"
chmod 1777 "$root/tmp"
EOF

FROM scratch AS updater
COPY --from=updater-root /root-fs/ /
USER 1000:1000
LABEL org.opencontainers.image.title="ClamCove updater" \
      org.opencontainers.image.description="freshclam of ClamCove alone, keeping a signature folder current for clamd running elsewhere. Not affiliated with or endorsed by Cisco or the ClamAV project." \
      org.opencontainers.image.licenses="GPL-2.0-only" \
      org.opencontainers.image.source="https://github.com/mkhanal/clamcove"
ENTRYPOINT ["freshclam"]
CMD ["--daemon"]

FROM debian:trixie-slim@sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2 AS dropin
RUN apt-get update && apt-get install -y --no-install-recommends \
    libbz2-1.0 libcurl4t64 libjson-c5 libncurses6 libpcre2-8-0 libssl3t64 libxml2 zlib1g ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --home-dir /var/lib/clamav --shell /usr/sbin/nologin clamav \
    && mkdir -p /var/lib/clamav /var/log/clamav && chown clamav:clamav /var/lib/clamav /var/log/clamav
COPY --from=build /out/ /
COPY --from=build /SOURCES /usr/share/doc/clamcove/SOURCES
RUN ldconfig
LABEL org.opencontainers.image.title="ClamCove" \
      org.opencontainers.image.description="ClamAV with RAR read through libarchive; no RARLAB unRAR code. Not affiliated with or endorsed by Cisco or the ClamAV project." \
      org.opencontainers.image.licenses="GPL-2.0-only" \
      org.opencontainers.image.source="https://github.com/mkhanal/clamcove"
CMD ["clamscan", "--version"]
