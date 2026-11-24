# ClamCove

ClamCove is a fork of [ClamAV](https://github.com/Cisco-Talos/clamav), the
open source antivirus engine. It enhances ClamAV for two reasons:

- **Performance and scale.** Signatures that cannot match a file are skipped
  sooner, and large RAR archives no longer hold their whole decompression
  window in memory, so one server screens more files, and more at once, within
  a fixed memory limit.
- **RAR without the unRAR licence.** ClamAV reads RAR archives with RARLAB's
  unRAR code, whose licence is not an open source licence and restricts how the
  code may be used. ClamCove reads RAR through
  [libarchive](https://github.com/libarchive/libarchive) (BSD-2-Clause)
  instead, with no unRAR code at all, so it can be shipped wherever that
  licence is not acceptable.

ClamCove is versioned on ClamAV's version:
`<clamav major>.<minor>.<patch>.<clamcove release>`, the OpenResty convention,
so ClamCove 1.5.4.4 is ClamAV 1.5.4 plus ClamCove release 4.

Each release publishes three container images, for linux/amd64 and linux/arm64,
built from the release tarball, with their digests in the release notes. The
drop-in and runtime images are built on `debian:trixie-slim`; the updater image
carries only what `freshclam` loads, copied from it with the Debian package
records and copyright files. All read their configuration from `/etc/clamav`
and their signatures from `/var/lib/clamav`.

| Image | Contents | Tags |
| --- | --- | --- |
| Drop-in | Everything a ClamAV build installs: every program, library, header and document | `ghcr.io/mkhanal/clamcove:1.5.4.4`, and `1.5.4`, `1.5`, `1`, `latest` |
| Runtime | Only `clamd` and `clamdscan`, the libraries they load (without debug symbols) and the CVD certificates, for running `clamd` as a service with signatures kept current from outside it; user and group `clamav` are 1000:1000 | `ghcr.io/mkhanal/clamcove:1.5.4.4-runtime`, and `1.5.4-runtime`, `1.5-runtime`, `1-runtime`, `runtime` |
| Updater | Only `freshclam`, the libraries it loads and the certificates it verifies with, on an empty base: no shell or other program. Runs `freshclam --daemon` by default; any other arguments, such as `--stdout`, run one update and exit. User and group `clamav` are 1000:1000, so it shares a signature folder with the runtime image | `ghcr.io/mkhanal/clamcove-updater:1.5.4.4`, and `1.5.4`, `1.5`, `1`, `latest` |

Each floating tag moves to the newest ClamCove release on its line.

Every image carries `/usr/share/doc/clamcove/SOURCES`, naming its complete
corresponding source: the release tarball, and
`clamcove-<version>-debian-sources.tar`, a separate asset of the same release
holding the Debian source package of every Debian package in the images, at
the exact version each carries (listed in its `SOURCES.txt`). Running ClamCove
needs neither; download them when you need that source.

ClamCove is a drop-in replacement for ClamAV: the same commands, configuration
files, libraries, install paths and signature database. Its aim is to get every
change it makes accepted into ClamAV, so that it shrinks back to ClamAV.

## Differences from ClamAV

| Difference | ClamAV 1.5.4 | ClamCove | Upstream status |
| --- | --- | --- | --- |
| PCRE container check | PCRE subsignatures are evaluated whatever the container | PCRE subsignatures whose container cannot match are skipped | [Cisco-Talos/clamav#1886](https://github.com/Cisco-Talos/clamav/pull/1886), open |
| 7z folder checked against `MaxScanSize` | A solid 7z folder is decoded into memory whatever `MaxScanSize` is, so a small 7z can hold gigabytes until `MaxScanTime` ends the scan | The folder is checked against the scan size still available before it is decoded; a file in a folder that is too large is skipped and raises `Heuristics.Limits.Exceeded.MaxScanSize` under `AlertExceedsMax` ([#54](https://github.com/mkhanal/clamcove/pull/54)) | [Cisco-Talos/clamav#1932](https://github.com/Cisco-Talos/clamav/pull/1932), open |
| gzip, bzip2, xz and xar output checked against `MaxScanSize` | Each chunk is written to the temporary file before the total is checked, so the chunk that crosses the limit stays in the file, the scan size does not advance, and a ZIP of N gzip files writes about N times the limit | The total with the chunk added is checked before the chunk is written; the data up to the limit is written, counted and scanned ([#56](https://github.com/mkhanal/clamcove/pull/56)) | [Cisco-Talos/clamav#1933](https://github.com/Cisco-Talos/clamav/pull/1933), open |
| OpenSSL 3 digest handles | Every hash creates a library context and fetches its digest again, which costs hundreds of microseconds per scanned object and leaks a context per hash where a FIPS policy withholds MD5 | Each digest is fetched once into a shared context and reused; hash values are unchanged, a zip of 10,000 small files scans 1.4 times faster with the official databases ([#59](https://github.com/mkhanal/clamcove/pull/59)) | Merged upstream in [Cisco-Talos/clamav#1774](https://github.com/Cisco-Talos/clamav/pull/1774) (ClamAV main, after 1.5.4), backported |
| Database added during clamd's initial load | The database directory state is recorded after the initial load, so a database written while it runs is taken as already loaded and `SelfCheck` does not reload it | The state is recorded before the initial load, as `reload_db` does, so the next `SelfCheck` loads it ([#65](https://github.com/mkhanal/clamcove/issues/65)) | Not yet offered |
| RAR read through libarchive | RAR read by RARLAB unRAR code | RAR read through libarchive, on by default and turned off with `-DENABLE_UNRAR=OFF` ([#7](https://github.com/mkhanal/clamcove/pull/7)) | Not yet offered |
| No RARLAB code | `libclamunrar/` and `COPYING.unrar` are in the source | ClamCove carries no RARLAB code: no unRAR source or licence file in the source tree, a release or an image ([#34](https://github.com/mkhanal/clamcove/issues/34)) | ClamCove only, never offered |
| Large RAR windows on disk | A RAR decompression window (up to 4 GiB) is anonymous memory, so concurrent scans of large archives can exhaust a memory limit | A window above 64 MiB is a mapping of an unnamed 0600 file in the temporary directory (`TemporaryDirectory`, `--tempdir`) that the kernel can write to disk and that disappears with the process; needs window size × concurrent scans of free disk, falls back to memory when the file cannot be made, always memory on Windows; an entry whose window cannot be had is not extracted and raises `Heuristics.Limits.Exceeded.RARSpace` and `Heuristics.Incomplete.RAR` ([#26](https://github.com/mkhanal/clamcove/issues/26), [#45](https://github.com/mkhanal/clamcove/issues/45)) | Not yet offered |
| Alert on an incomplete RAR | A RAR that cannot be fully scanned reports clean | Opt-in `AlertIncompleteRAR` / `--alert-incomplete-rar` raises `Heuristics.Incomplete.RAR` ([#11](https://github.com/mkhanal/clamcove/pull/11)) | Not yet offered |
| RAR 1.5, RAR 2.0 and RAR 2.6 archives | Extracted by RARLAB unRAR code | RAR 2.0 and 2.6 are extracted by a decoder ported from [rardecode](https://github.com/nwaples/rardecode) (BSD-2-Clause) ([#16](https://github.com/mkhanal/clamcove/pull/16)). RAR 1.5 is not extracted, and ClamCove alerts on it when the option above is on ([#7](https://github.com/mkhanal/clamcove/pull/7)) | Not yet offered |
| Version output | `ClamAV 1.5.4/...` | `ClamAV 1.5.4/... (ClamCove <version>)`, ClamAV's version first and unchanged ([#13](https://github.com/mkhanal/clamcove/pull/13)) | ClamCove only, never offered |
| freshclam User-Agent | `ClamAV/1.5.4 (OS: ...)` | Unchanged | None needed |

Every functional difference, with measured gains and losses, limits and risks, parity evidence and how to reproduce them: [docs/DIFFERENCES.md](docs/DIFFERENCES.md).

## Release patches

Every release ships its changes to the official ClamAV source as patches, next to the complete source tarball. Each patch is
the net diff of one change: it contains what the release contains and nothing a later commit removed, so no patch carries code
that is not in the release. A patch records a deleted file without its text, so no patch carries the code of a file the release
does not contain (the RARLAB unRAR source is deleted this way). Apply the patches in file name order to the official
`clamav-<version>` source with `apply-patch.sh <patch>`, attached to the release, which removes the deleted files and applies the rest
with `git apply --binary -p1`; the result is exactly the release tree without `.github` (CI and release inputs).
Changes that edit the same lines cannot be split and come as one patch whose title names them; the last patch holds the tests,
test inputs, fuzz targets, RAR parity tooling and README of all the changes. ClamCove contains no RARLAB unRAR
code. `.github/dist/split-changes.sh` writes the patches and `.github/dist/check-patches.sh` verifies them on every pull request
and push to a release branch; the ownership of commits by change is `.github/clamcove-changes.txt`. The release workflow fails if the
source tarball, any patch or any layer of the image holds a RARLAB file (`.github/dist/check-no-rarlab.sh`).

## Cutting a release

The source carries its own release number: `CLAMCOVE_RELEASE` in `CMakeLists.txt`, which with the project version gives the
version in `clamscan --version`. To cut `clamcove-<version>.<n>`, first set `CLAMCOVE_RELEASE` to `<n>` and update the version
in `README.md` and `NOTICE`, merge that to the release branch, then tag the merge commit. `.github/dist/check-version.sh` fails
a pull request or push when those three disagree, and fails the release workflow, before anything is built, when the tag names
another version than the tagged source.

ClamCove is based on ClamAV by Cisco Systems, Inc. ClamAV is a trademark of
Cisco. ClamCove is not affiliated with or endorsed by Cisco or the ClamAV
project. ClamCove is licensed under the GNU General Public License, version 2
(see [COPYING](COPYING)). See [NOTICE](NOTICE) for the full statement.

The rest of this file is ClamAV's own README.

# ClamAV

<p align="center">
  <img width="250" height="250" src="https://raw.githubusercontent.com/Cisco-Talos/clamav/main/logo.png" alt='Maeve, the ClamAV mascot'>
</p>

<p align="center">
  ClamAV® is an open source antivirus engine for detecting trojans, viruses,
  malware & other malicious threats.
</p>

<p align="center">
  <a href="https://github.com/Cisco-Talos/clamav/actions"><img src="https://github.com/Cisco-Talos/clamav/workflows/CMake%20Build/badge.svg" height="18"></a>
  <a href="https://discord.gg/6vNAqWnVgw"><img src="https://img.shields.io/discord/636023333074370595.svg?logo=discord" height="18"/></a>
  <a href="https://twitter.com/clamav"><img src="https://abs.twimg.com/favicons/twitter.ico" width="18" height="18"></a>
</p>

## Documentation & FAQ

ClamAV documentation is hosted at [docs.clamav.net](https://docs.clamav.net/).
The source archive for each release also includes a copy of the documentation
for [offline](docs/html/index.html) reading.

You can contribute to the documentation by submitting improvements to
[Cisco-Talos/clamav-documentation](https://github.com/Cisco-Talos/clamav-documentation)

## ClamAV News

For information about the features in this and prior releases, read
[the news](NEWS.md).

Catch up on the latest about ClamAV by reading our
[blog](http://blog.clamav.net) and follow us on Twitter `@clamav`.

## ClamAV Signatures

Anyone can learn to read and write ClamAV signatures. To get started, see our
[signature writing manual](https://docs.clamav.net/manual/Signatures.html).

## Installation Instructions

### Using Docker

ClamAV can be run using Docker. For details, visit to the online manual under
["Docker"](https://docs.clamav.net/manual/Installing/Docker.html) and check out
our images on [Docker Hub](https://hub.docker.com/r/clamav/clamav).

### Using a Package Manager

For help installing from a package manager, refer to the online manual under
["Packages"](https://docs.clamav.net/manual/Installing/Packages.html).

### Using an Installer

The following install packages are available for download from
[clamav.net/downloads](https://www.clamav.net/downloads):

- Linux - Debian and RPM packages for x86_64 and i686. *New in v0.104.*
- macOS - PKG installer for x86_64 and arm64 (universal). *New in v0.104.*
- Windows - MSI installers and portable ZIP packages for win32 and x64.

To learn how to use these packages, refer to the online manual under
["Installing"](https://docs.clamav.net/manual/Installing.html#installing-with-an-installer).

### Build from Source

For step-by-step instructions, refer to the online manual:
- [Unix/Linux/Mac](https://docs.clamav.net/manual/Installing/Installing-from-source-Unix.html)
- [Windows](https://docs.clamav.net/manual/Installing/Installing-from-source-Windows.html)

The source archive for each release includes a copy of the documentation for
[offline](docs/html/UserManual.html) reading.

A reference with all of the available build options can be found in the
[INSTALL.md](INSTALL.md) file.

You can find additional advice for developers in the online manual under
["For Developers"](https://docs.clamav.net/manual/Development.html).

### Upgrading from a previous version

Visit [the FAQ](https://docs.clamav.net/faq/faq-upgrade.html) for tips on how
to upgrade from a previous version.

## Join the ClamAV Community

The best way to get in touch with the ClamAV community is to join our
[mailing lists](https://docs.clamav.net/faq/faq-ml.html).

You can also join the community on our
[ClamAV Discord chat server](https://discord.gg/6vNAqWnVgw).

## Want to make a contribution?

The ClamAV development team welcomes
[code contributions](https://github.com/Cisco-Talos/clamav),
improvements to
[our documentation](https://github.com/Cisco-Talos/clamav-documentation),
and also [bug reports](https://github.com/Cisco-Talos/clamav/issues).

ClamCove changes follow [CONTRIBUTING.md](CONTRIBUTING.md): every pull request
is a clean series of logical commits.

Thanks for joining us!

## Licensing

ClamAV is licensed for public/open source use under the GNU General Public
License, Version 2 (GPLv2).

See `COPYING.txt` for a copy of the license.

### 3rd Party Code

ClamAV contains a number of components that include code copied in part or in
whole from 3rd party projects and whose code is not owned by Cisco and which
are licensed differently than ClamAV. These include:

- Yara: Apache 2.0 license
  - Yara has since switched to the BSD 3-Clause License;
    Our source is out-of-date and needs to be updated.
- 7z / lzma: public domain
- libclamav's NSIS/NulSoft parser includes:
  - zlib: permissive free software license
  - bzip2 / libbzip2: BSD-like license
- OpenBSD's libc/regex: BSD license
- file: BSD license
- str.c: Contains BSD licensed modified-implementations of strtol(), stroul()
  functions, Copyright (c) 1990 The Regents of the University of California.
- pngcheck (png.c): MIT/X11-style license
- getopt.c: MIT license
- Curl: license inspired by MIT/X, but not identical
- libmspack: LGPL license
- libarchive (libclamarchive), reads RAR archives: BSD-2-Clause license
- rardecode (RAR 2.0 and 2.6 decoder, ported into libarchive): BSD-2-Clause license

See the `COPYING` directory for a copy of the 3rd party project licenses.

## Acknowledgements

Credit for contributions to each release can be found in the [News](NEWS.md).

ClamAV is brought to you by
[the ClamAV Team](https://www.clamav.net/about.html#credits)
