#!/usr/bin/env bash
# usage: debian-packages.sh <docker image>
# Prints source=version for every Debian package installed in the image, from its dpkg records (var/lib/dpkg/status and
# var/lib/dpkg/status.d), read from the exported file system so no program of the image runs.
set -euo pipefail
image=$1
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
container=$(docker create "$image")
docker export "$container" | tar -x -C "$work" var/lib/dpkg 2> /dev/null || true
docker rm "$container" > /dev/null
records=()
[ -f "$work/var/lib/dpkg/status" ] && records+=("$work/var/lib/dpkg/status")
[ -d "$work/var/lib/dpkg/status.d" ] && records+=("$work"/var/lib/dpkg/status.d/*)
[ "${#records[@]}" -gt 0 ] || { echo "$image has no dpkg records"; exit 1; }
for record in "${records[@]}"; do cat "$record"; echo; done | awk '
  function flush() {
    if (pkg != "" && status == "install ok installed") {
      name = pkg; version = ver
      if (src != "") { name = src; if (match(src, / \(.*\)$/)) { name = substr(src, 1, RSTART - 1); version = substr(src, RSTART + 2, RLENGTH - 3) } }
      print name "=" version
    }
    pkg = ""; status = ""; src = ""; ver = ""
  }
  /^$/ { flush(); next }
  /^Package: / { pkg = substr($0, 10) }
  /^Status: / { status = substr($0, 9) }
  /^Source: / { src = substr($0, 9) }
  /^Version: / { ver = substr($0, 10) }
  END { flush() }' | sort -u
