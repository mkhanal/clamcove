#!/usr/bin/env bash
# usage: debian-sources.sh <packages file, source=version per line> <output .tar>
# Downloads the Debian source package of every line, at exactly that version: from the Debian release the images are
# built on, or from snapshot.debian.org once the mirror has moved past that version. Writes them with the packages file (SOURCES.txt) into one tar. Fails when any source cannot be downloaded.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
packages=$1 out=$2
base=$(sed -n 's/^FROM \(debian:trixie-slim@sha256:[0-9a-f]*\) AS runtime$/\1/p' "$here/Dockerfile")
[ -n "$base" ] || { echo "cannot read the Debian base image from the Dockerfile"; exit 1; }
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
mkdir "$work/sources"
sort -u "$packages" > "$work/sources/SOURCES.txt"
docker run --rm -v "$work/sources:/sources" -w /sources -e OWNER="$(id -u):$(id -g)" "$base" bash -euo pipefail -c '
  sed -i "s/^Types: deb$/Types: deb deb-src/" /etc/apt/sources.list.d/debian.sources
  apt-get update -qq
  apt-get install -y -qq --no-install-recommends curl jq ca-certificates > /dev/null
  from_snapshot() {
    curl -fsS "https://snapshot.debian.org/mr/package/$1/$2/srcfiles?fileinfo=1" \
      | jq -r ".fileinfo | to_entries[] | \"\(.key) \(.value[0].name)\"" > files
    while read -r hash name; do curl -fsS -o "$name" "https://snapshot.debian.org/file/$hash"; done < files
    rm files
  }
  while IFS== read -r src version; do
    apt-get source --download-only -qq "$src=$version" > /dev/null 2>&1 || from_snapshot "$src" "$version"
    [ -f "${src}_${version#*:}.dsc" ] || { echo "no source package for $src $version"; exit 1; }
  done < SOURCES.txt
  chown -R "$OWNER" /sources'
tar -C "$work/sources" -cf "$out" .
echo "$(wc -l < "$work/sources/SOURCES.txt" | tr -d ' ') Debian source packages, $(du -h "$out" | cut -f1): $out"
