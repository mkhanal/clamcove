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

FROM debian:trixie-slim@sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libbz2-1.0 libcurl4t64 libjson-c5 libncurses6 libpcre2-8-0 libssl3t64 libxml2 zlib1g ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --home-dir /var/lib/clamav --shell /usr/sbin/nologin clamav \
    && mkdir -p /var/lib/clamav /var/log/clamav && chown clamav:clamav /var/lib/clamav /var/log/clamav
COPY --from=build /out/ /
RUN ldconfig
LABEL org.opencontainers.image.title="ClamCove" \
      org.opencontainers.image.description="ClamAV with RAR read through libarchive; no RARLAB unRAR code. Not affiliated with or endorsed by Cisco or the ClamAV project." \
      org.opencontainers.image.licenses="GPL-2.0-only" \
      org.opencontainers.image.source="https://github.com/mkhanal/clamcove"
CMD ["clamscan", "--version"]
