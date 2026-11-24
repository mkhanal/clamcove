#!/usr/bin/env bash
# usage: check-image.sh dropin|runtime|updater <docker image> <ClamCove version>
set -euo pipefail

kind=$1
image=$2
rev=$3
here=$(cd "$(dirname "$0")" && pwd)

in_image() { docker run --rm --entrypoint sh "$image" -c "$1"; }

"$here/check-no-rarlab.sh" image "$image"
container=$(docker create "$image")
notice=$(docker cp "$container:/usr/share/doc/clamcove/SOURCES" - | tar -xO)
docker rm "$container" > /dev/null
grep -qF "clamcove-$rev-debian-sources.tar" <<< "$notice" || { echo "the image does not say where its source is"; exit 1; }
if [ "$kind" != updater ]; then
  in_image 'test -z "$(find / -xdev -name "libclamunrar.so*")" && test -n "$(find / -xdev -name "libclamunrar_iface.so*")"'
  in_image 'test -f /etc/clamav/certs/clamav.crt' || { echo "the CVD certificates are not in /etc/clamav/certs"; exit 1; }
fi

expect_version() {
  local out
  out=$(docker run --rm --entrypoint sh "$image" -c ": > /tmp/empty.conf; $1 ${2:-} --version")
  echo "$out"
  case "$out" in "ClamAV "*"(ClamCove $rev)") ;; *) echo "$1 does not report ClamCove $rev"; exit 1 ;; esac
}

case "$kind" in
  dropin)
    expect_version clamscan
    docker run --rm --entrypoint clamconf "$image" | grep -x 'Checking configuration files in /etc/clamav' > /dev/null \
      || { echo "the programs do not read their configuration from /etc/clamav"; exit 1; }
    ;;
  runtime)
    expect_version clamd --config-file=/tmp/empty.conf
    expect_version clamdscan --config-file=/tmp/empty.conf
    in_image 'test "$(id -u clamav):$(id -g clamav)" = 1000:1000' \
      || { echo "the clamav user is not 1000:1000"; exit 1; }
    in_image 'for p in clamscan freshclam sigtool clambc clamconf clamdtop clamsubmit clamav-config; do
                if command -v "$p" > /dev/null; then echo "$p is in the runtime image"; exit 1; fi
              done
              found=$(find / -xdev \( -name "*.a" -o -name "clamav*.h" -o -name "libclamav.pc" -o -name "libfreshclam*" -o -name "libcurl*" \) -print)
              if [ -n "$found" ]; then echo "build files in the runtime image: $found"; exit 1; fi
              missing=$(ldd /usr/sbin/clamd /usr/bin/clamdscan | grep "not found" || true)
              if [ -n "$missing" ]; then echo "missing libraries: $missing"; exit 1; fi
'
    in_image 'set -e
              mkdir -p /tmp/db
              printf "ClamCove runtime check\n" > /tmp/sample
              printf "%s:%s:ClamCove.Runtime.Check\n" "$(md5sum /tmp/sample | cut -d" " -f1)" "$(stat -c %s /tmp/sample)" > /tmp/db/check.hdb
              printf "DatabaseDirectory /tmp/db\nLocalSocket /tmp/clamd.sock\nForeground yes\n" > /tmp/clamd.conf
              clamd --config-file=/tmp/clamd.conf &
              for _ in $(seq 100); do [ -S /tmp/clamd.sock ] && break; sleep 0.2; done
              out=$(clamdscan --config-file=/tmp/clamd.conf --no-summary /tmp/sample || true)
              echo "$out"
              case "$out" in *"ClamCove.Runtime.Check"*" FOUND"*) ;; *) echo "clamd did not find the check signature"; exit 1 ;; esac'
    ;;
  updater)
    out=$(docker run --rm "$image" --version)
    echo "$out"
    case "$out" in "ClamAV "*"(ClamCove $rev)") ;; *) echo "freshclam does not report ClamCove $rev"; exit 1 ;; esac
    [ "$(docker image inspect -f '{{.Config.User}}' "$image")" = 1000:1000 ] || { echo "the updater does not run as 1000:1000"; exit 1; }
    container=$(docker create "$image")
    files=$(docker export "$container" | tar -t)
    docker rm "$container" > /dev/null
    for f in usr/bin/freshclam etc/clamav/freshclam.conf etc/clamav/certs/clamav.crt etc/ssl/certs/ca-certificates.crt \
             etc/ld.so.cache var/lib/dpkg/status.d/libc6 var/lib/dpkg/status.d/libcurl4t64 usr/share/doc/libc6/copyright \
             usr/share/doc/clamcove/COPYING.txt; do
      grep -qx "$f" <<< "$files" || { echo "the updater image lacks $f"; exit 1; }
    done
    extra=$(grep -E '(^|/)(sh|bash|dash|busybox|apt|dpkg|clamd|clamscan|clamdscan|sigtool)$|libclamunrar\.so' <<< "$files" || true)
    [ -z "$extra" ] || { echo "the updater image carries more than freshclam: $extra"; exit 1; }
    out=$(docker run --rm --read-only --tmpfs /tmp --tmpfs /var/lib/clamav:uid=1000,gid=1000 "$image" --update-db=bytecode --stdout 2>&1)
    echo "$out"
    case "$out" in *"Database test passed"*"bytecode.cvd updated"*) ;; *) echo "the updater did not download, test and write bytecode.cvd"; exit 1 ;; esac
    ;;
  *)
    echo "usage: check-image.sh dropin|runtime|updater <docker image> <ClamCove version>"
    exit 2
    ;;
esac
echo "$kind image $image: checks pass"
