# ClamCove 1.5.4.2 compared with ClamAV 1.5.4

What differs functionally between ClamCove 1.5.4.2 (tag `clamcove-1.5.4.2`) and ClamAV 1.5.4, for someone choosing between them. ClamCove is ClamAV 1.5.4 plus the changes listed here; the signature databases, configuration files, commands, library names and install paths are the same. Every number below was measured on 2026-11-16 on one machine (arm64 only; nothing was measured on x86-64) and can be reproduced with the commands in [How to reproduce](#how-to-reproduce).
The scan size rows under Differences (a solid 7z folder; gzip, bzip2, xz and xar output) are changes of ClamCove 1.5.4.3 and were not part of the measurements, which were made on 1.5.4.2.


## In short

| | ClamCove against ClamAV |
| --- | --- |
| Scan time of zip-based files of 9 MB with images (docx, zip, nested zip) | 4.6 to 9.8 times faster, same verdicts |
| Scan time of RAR4 and RAR5 of 9 MB, solid or not | 8 to 14 % faster, same verdicts |
| Scan time of a PDF of 9 MB | Equal (0.32 s and 0.34 s) |
| RAR5 entry whose window is above 64 MiB, one scan with room to spare | About 1.6 to 2.1 times slower (7.7 s against 4.7 s for 800 MiB of zeros under a 1 GiB dictionary), because the window is a file |
| The same entry under a memory limit (2.5 GiB, three or four concurrent scans through `clamd`) | All scans complete, `clamd` adds 0.4 to 0.55 GiB; ClamAV's `clamd` is OOM-killed and every scan on it is lost (2.2 to 3.0 GiB added) |
| RAR5 block that spans two volumes of one file | Scanned in full (10 of 10 markers); ClamAV scans none of it (0 of 10) |
| Disk | Needs the window size of free temporary space per concurrent scan of such an entry |
| RAR 1.5, and damaged archives where ClamAV decodes more | ClamAV scans more; ClamCove does not extract RAR 1.5 |
| RAR code and licence | No RARLAB code, source or licence in the source, packages, tarball or image |

## Measurement setup

| | |
| --- | --- |
| Host | Apple M2 Max, 12 cores, 64 GB, macOS 26.5 |
| Container runtime | Docker Engine 29.9.3 (Docker Desktop), Linux VM with kernel 7.0.14-linuxkit, aarch64, 12 vCPU, 17.5 GiB memory, 1 GiB swap, cgroup v2, overlayfs; no CPU limit on any container, and no swap for a container with a memory limit (`--memory-swap` equal to `--memory`) |
| Compiler | GCC 14.2.0 and rustc 1.99.1 (`rust:1.99.1-trixie`, pinned by digest in `tools/rar-parity/Dockerfile`), CMake from Debian trixie, Release build; runtime image `debian:trixie-slim` |
| ClamAV | `clamav-1.5.4.tar.gz`, sha256 `1af1117a228f1b5bc7fa91a0dabc37848a99e7d25188e9be8043332ce721dfd3` |
| ClamCove | `clamcove-1.5.4.2.tar.gz` of the release, sha256 `79b74c37dce4ed9c42b2ad142baee8da771a2a79d45437c3f03aae011f4f2bf0` |
| Build | Both from the same Dockerfile and CMake flags, no extra option (ClamAV with `-j2`, ClamCove with `-j4`); the ClamCove image is built from the release tarball, not pulled (the published image is linux/amd64 only) |
| Signatures | The official databases of the `clamav/clamav-debian:1.5.4` image, digest `sha256:cce3e1a43ae2bb40e11335c52c0e1e98273b12fa3d587e617f63a6907cc4b70b`: main 63, daily 28165, bytecode 339 |
| `clamd` | `MaxThreads 4`, `DisableCache yes`, default limits, one `clamd` per build in its own container, `TemporaryDirectory` on the container's overlay filesystem |
| Host load | No other ClamAV measurement ran during the timed runs. The Mac and the Docker VM were not otherwise idle: other containers were up but idle, other processes ran on the Mac (load average about 8 at the start), and the spread of the runs shows it |
| Previous numbers | [Cisco-Talos/clamav#1886](https://github.com/Cisco-Talos/clamav/pull/1886) measured the PCRE change on Docker 29.7.2, kernel 7.0, 12 vCPU and 7.7 GiB; its docx figures (4.6 s and 0.57 s) agree with those below; its nested zip is a different sample |

Time is the wall time of `clamdscan` against a running `clamd`, after one warm-up scan: the median of the runs, with the minimum and maximum in brackets. Memory is what `clamd` added to its own resident set during a scan (anonymous pages, sampled every 10 ms), on top of about 0.95 GiB with the databases loaded (966 MiB ClamAV, 964 MiB ClamCove).

## Performance

### Scan time of 9 MB files

The files are made by `tools/differences/make-corpus.py` and `make-rar.sh`: a docx with three images (9.3 MB), a plain zip (9.5 MB), a zip nested three deep (8.4 MB), a PDF of three images (9.0 MB), and RAR4 and RAR5 archives of the same 30 binary and 30 text files (8.5 to 8.7 MB), non-solid and solid. All scan clean in both builds. Two passes in the order ClamAV, ClamCove, ClamCove, ClamAV of seven runs each; the RAR rows are 27 runs each (three passes of nine, interleaved) because their runs vary more.

| file | ClamAV 1.5.4 | ClamCove 1.5.4.2 | ratio | memory added, ClamAV / ClamCove | verdict |
|---|---|---|---|---|---|
| doc9.docx | 4.68 s (4.57-5.16) | 0.59 s (0.50-0.81) | 7.94x | 12 / 12 MiB | OK |
| nested9.zip | 12.71 s (12.26-13.97) | 1.29 s (1.16-1.56) | 9.82x | 15 / 15 MiB | OK |
| plain9.zip | 5.85 s (5.26-6.30) | 1.27 s (1.11-1.46) | 4.62x | 10 / 10 MiB | OK |
| pdf9.pdf | 0.32 s (0.28-0.45) | 0.34 s (0.29-0.37) | 0.96x | 9 / 9 MiB | OK |
| rar4.rar | 1.40 s (1.25-4.08) n=27 | 1.25 s (1.16-1.81) n=27 | 1.13x | 9 / 11 MiB | OK |
| rar5.rar | 1.42 s (1.29-4.34) n=27 | 1.30 s (1.15-1.64) n=27 | 1.10x | 8 / 8 MiB | OK |
| rar4-solid.rar | 1.51 s (1.25-2.80) n=27 | 1.32 s (1.15-1.56) n=27 | 1.14x | 8 / 8 MiB | OK |
| rar5-solid.rar | 1.46 s (1.33-1.73) n=27 | 1.36 s (1.23-1.47) n=27 | 1.08x | 9 / 9 MiB | OK |

The zip-based gain is the PCRE change: 400 mail-only signatures of `main.cvd` and 368 zip-only ones of `daily.cvd` no longer run their regular expressions over every zip-based file ([Cisco-Talos/clamav#1886](https://github.com/Cisco-Talos/clamav/pull/1886) has the analysis and its own timings, 4.5 s to 0.57 s for a 9.4 MB docx). The gain grows with file size and nesting and is absent for a file that is not a zip, such as the PDF. A zip inside an email (`.eml`) gets none, by design: there the mail-only signatures apply.

### Many small objects

The cost of fetching a digest per hash is per scanned object, so it shows on archives of many small members. Same machine and build as above, Apple M2 Max and the Docker Linux VM, ClamCove 1.5.4.3 before and with [Cisco-Talos/clamav#1774](https://github.com/Cisco-Talos/clamav/pull/1774) backported ([#59](https://github.com/mkhanal/clamcove/pull/59)), median of 5 to 7 alternating runs, `MaxFiles` 100000; verdicts identical on all 24 samples. `clamscan` with a one-signature database isolates the per-object cost, `clamd` has the official databases loaded.

| file | mode | before | after | ratio |
|---|---|---|---|---|
| zip of 10,000 small files | `clamscan`, one signature | 5.33 s | 0.29 s | 18.2x |
| zip nested three deep, 500 members per level | `clamscan`, one signature | 1.07 s | 0.07 s | 15.3x |
| zip of 10,000 small files | `clamd`, official databases | 56.1 s | 38.9 s | 1.44x |
| zip nested three deep, 500 members per level | `clamd`, official databases | 10.5 s | 7.27 s | 1.45x |
| xlsx with 400 sheets | `clamd`, official databases | 3.38 s | 2.65 s | 1.27x |
| docx, plain zip, nested zip and PDF of 9 MB | `clamd`, official databases | 0.30 to 1.20 s | 0.30 to 1.15 s | 1.00 to 1.11x |

### Large RAR5 window under a memory limit

An RAR5 archive of 800 MiB of zeros with a 1 GiB dictionary (34 KB, solid, `rar` 7.23, `-ma5 -s -m3 -md1g`), `MaxFileSize`, `MaxScanSize` and `StreamMaxLength` 4000M, `MaxScanTime` 0, a signature database of one marker, in a container with `--memory` and the same `--memory-swap`. `clamd` rows: `clamdscan` of the same file N times at once. Peak anonymous memory is of the whole `clamd`; the page cache (the window file) is reclaimable and not counted, which is why `memory.peak` reads the limit.

| Setup | ClamAV 1.5.4 | ClamCove 1.5.4.2 |
| --- | --- | --- |
| `clamscan`, 6 GiB, five runs | 4.9 s (4.5-7.3), OK | 9.7 s (7.8-11.4), OK |
| `clamscan`, 900 MiB | OOM-killed | OK, 9.9 s |
| `clamd`, 2560 MiB, 1 scan | OK, 4.7 s, 949 MiB anonymous | OK, 7.7 s, 151 MiB |
| `clamd`, 2560 MiB, 2 concurrent | OK, 6.5 s, 1928 MiB | OK, 13.3 s, 324 MiB |
| `clamd`, 2560 MiB, 3 concurrent | `clamd` OOM-killed, all 3 scans lost (2549 MiB) | OK, 11.6 s, 426 MiB |
| `clamd`, 2560 MiB, 4 concurrent | `clamd` OOM-killed, all 4 scans lost (2273 MiB) | OK, 16.7 s, 550 MiB |
| `clamd`, 3072 MiB, 4 concurrent | `clamd` OOM-killed, all 4 scans lost (3048 MiB) | OK, 16.7 s, 408 MiB |

ClamAV's anonymous memory here is about 0.93 GiB per scan and does not depend on the declared dictionary (a 2 GiB and a 4 GiB dictionary gave the same in an earlier run), so the kernel can only kill. ClamCove's window is a file the kernel can write out, which is the gain; the price is the time to write and read it (about 1.6 to 2.1 times) and 1 GiB of temporary disk per concurrent scan. One OOM kill ends `clamd`, so every scan in flight on that daemon fails, not just the large one.

A service that embeds `clamd` under a 2816 MiB container limit, with the same kind of archive (RAR5, solid, `-md1g`, 25 KB expanding to 600 MB), measured the same way: two concurrent screenings peaked at 1225 MiB non-reclaimable with the window in a file against 2416 MiB with it in anonymous memory; a 60 KB archive expanding to 1.5 GB peaked at 1545 MiB against 2787 MiB, where `clamd` was then killed. Those runs compare ClamCove with its own earlier behaviour, not with ClamAV.

### What to expect

- Gain: zip-based uploads (Office files, zips) with the official databases, in proportion to size; a service holding a `clamd` thread per upload frees it sooner.
- Gain: archives of many small objects (a zip of thousands of files, a large xlsx), in proportion to the number of objects; a few large files gain nothing.
- Gain: large RAR5 windows stop being a way to kill `clamd` under a memory limit.
- Gain: RAR4 and RAR5 of ordinary size scan 8 to 14 % faster; a volume-spanning RAR5 block is scanned.
- Loss: an entry that needs a window above 64 MiB is slower, as above. Windows of 64 MiB and below are anonymous memory as in ClamAV and cost the same.
- Loss: RAR 1.5 is not scanned, and some damaged archives are scanned less (see Limits and risks).
- No change: a PDF, `clamd`'s idle memory, and the memory added by any file of ordinary size.

## Differences

One line each; the detail is in the linked issues and pull requests.

| Area | ClamAV 1.5.4 | ClamCove 1.5.4.2 | Detail |
| --- | --- | --- | --- |
| PCRE subsignatures of a logical signature with a `Container` constraint | Evaluated whatever the container | Skipped when the layer being scanned is not that container; verdicts unchanged | [Cisco-Talos/clamav#1886](https://github.com/Cisco-Talos/clamav/pull/1886) |
| A solid 7z folder | Decoded whole into memory before `MaxScanSize` is checked against it, so a small 7z can hold gigabytes until `MaxScanTime` ends the scan | Checked against the scan size still available before it is decoded; a file in a folder that is too large is skipped and raises `Heuristics.Limits.Exceeded.MaxScanSize` under `AlertExceedsMax` | [#54](https://github.com/mkhanal/clamcove/pull/54), [Cisco-Talos/clamav#1932](https://github.com/Cisco-Talos/clamav/pull/1932) |
| gzip, bzip2, xz and xar output against `MaxScanSize` | A chunk is written to the temporary file before the total is checked, so the chunk that crosses the limit stays in the file, is not counted, and each further compressed entry in the archive writes the remaining scan size again | The total with the chunk added is checked before the chunk is written; the data up to the limit is written, counted and scanned | [#56](https://github.com/mkhanal/clamcove/pull/56), [Cisco-Talos/clamav#1933](https://github.com/Cisco-Talos/clamav/pull/1933) |
| OpenSSL 3 digest handles | Every MD5, SHA-1 and SHA-256 hash creates a library context and fetches its digest again, which costs hundreds of microseconds per scanned object and leaks a context per hash where a FIPS policy withholds MD5 | Each digest is fetched once into a shared context and reused; hash values and the FIPS bypass are unchanged | [#59](https://github.com/mkhanal/clamcove/pull/59), [Cisco-Talos/clamav#1774](https://github.com/Cisco-Talos/clamav/pull/1774) |
| Database added during clamd's initial load | The database directory state is recorded after the initial load, so a database written while it runs is taken as already loaded and `SelfCheck` does not reload it | The state is recorded before the initial load, as on reload; the next `SelfCheck` loads it | [#65](https://github.com/mkhanal/clamcove/issues/65) |
| RAR reader | RARLAB unRAR code in `libclamunrar/`, under the unRAR licence | libarchive 3.8.11 (BSD-2-Clause), vendored as `libclamarchive/`, behind the same `libclamunrar_iface` interface; no RARLAB code in source, patches, tarball or image | [#1](https://github.com/mkhanal/clamcove/issues/1), [#7](https://github.com/mkhanal/clamcove/pull/7), [#34](https://github.com/mkhanal/clamcove/issues/34) |
| RAR 3.x (unpack version 29) and RAR5: solid, SFX stub, filters, volumes, encryption detection | Extracted | Extracted, compared on 226 archives (parity below) | [#6](https://github.com/mkhanal/clamcove/pull/6) |
| RAR 2.0 and 2.6 | Extracted | Extracted by a decoder ported from [rardecode](https://github.com/nwaples/rardecode) (BSD-2-Clause) | [#16](https://github.com/mkhanal/clamcove/pull/16) |
| RAR 1.5 | Extracted | Not extracted; alert only with `AlertIncompleteRAR` | [#51](https://github.com/mkhanal/clamcove/issues/51) |
| RAR5 block that spans two volumes of one file | Decoding stops at the end of the first piece; the entry is not scanned at all | Decoded in full and scanned | [#37](https://github.com/mkhanal/clamcove/pull/37) |
| RAR entry checksum (CRC32, BLAKE2sp) | A mismatch is logged and the data is scanned | Same; the archive also counts as incomplete for `AlertIncompleteRAR` | [#7](https://github.com/mkhanal/clamcove/pull/7) |
| Decompression window above 64 MiB | Anonymous memory | An unnamed 0600 file in `TemporaryDirectory` (`--tempdir`) mapped shared, so the kernel can write it to disk; memory when the file cannot be made and always on Windows | [#26](https://github.com/mkhanal/clamcove/issues/26), [#28](https://github.com/mkhanal/clamcove/pull/28) |
| Largest RAR5 window | Scanned up to the 4 GiB tested; larger dictionaries are recorded in #51 | 4 GiB on 64-bit, 1 GiB on 32-bit; an entry needing more is declined (`Declared dictionary size is not supported`) | [#45](https://github.com/mkhanal/clamcove/issues/45), [#47](https://github.com/mkhanal/clamcove/pull/47) |
| Skipped entries of a solid RAR | Goes on to later entries | Decoding a skipped entry is bounded by the scan size still available and by the scan time; when used up the archive is not read further | [#33](https://github.com/mkhanal/clamcove/issues/33), [#51](https://github.com/mkhanal/clamcove/issues/51) |
| Alert `Heuristics.Incomplete.RAR` | None; an archive that cannot be fully scanned is clean | Opt-in: `AlertIncompleteRAR` (clamd.conf), `--alert-incomplete-rar` (clamscan), `CL_SCAN_HEURISTIC_INCOMPLETE_RAR` (0x4000, libclamav) | [#8](https://github.com/mkhanal/clamcove/issues/8), [#11](https://github.com/mkhanal/clamcove/pull/11) |
| Alert `Heuristics.Limits.Exceeded.RARSpace` | None | Under `AlertExceedsMax` / `--alert-exceeds-max`: a RAR entry that cannot be extracted for lack of memory or disk | [#45](https://github.com/mkhanal/clamcove/issues/45), [#49](https://github.com/mkhanal/clamcove/pull/49) |
| Damaged data in an entry | Keeps decoding past some damage (an invalid Huffman prefix code, a damaged PPMd entry), as recorded in #51 | Stops at the damage and scans what was decoded | [#51](https://github.com/mkhanal/clamcove/issues/51) |
| `libclamav` and RAR | `dlopen`s `libclamunrar_iface` at run time; scans without RAR when it is missing | Links `libclamunrar_iface` (`NEEDED`); a missing library stops the program from starting | [#51](https://github.com/mkhanal/clamcove/issues/51) |
| Installed libraries | `libclamunrar.so*` (373 KB) and `libclamunrar_iface.so*` (69 KB) | `libclamunrar_iface.so*` only (368 KB), which exports two more private symbols (`unrar_set_skip_limits`, `unrar_set_temp_dir`); `/opt/clamav` is 134 MiB in both | |
| Licence files in `share/doc/ClamAV` | None | `COPYING.libarchive`, `COPYING.rardecode` | [#34](https://github.com/mkhanal/clamcove/issues/34) |
| Version output (`clamscan -V`, the `VERSION` command of `clamd`) | `ClamAV 1.5.4/28165/<date>` | `ClamAV 1.5.4/28165/<date> (ClamCove 1.5.4.2)`; anything that parses the line must allow the suffix | [#13](https://github.com/mkhanal/clamcove/pull/13) |
| Names of packages and documents | `clamav` | CPack, `.deb` and `.rpm` packages are `clamcove` (providing, conflicting with and replacing `clamav`); man page headers and Windows file resources say ClamCove; library sonames and install paths are unchanged | [#12](https://github.com/mkhanal/clamcove/issues/12) |
| freshclam | `User-Agent: ClamAV/1.5.4 (OS: ...)`, official signature databases | Same | |
| Configuration and signatures | `clamd.conf`, `freshclam.conf`, official databases | Same files and databases; two options added (`AlertIncompleteRAR`, `--alert-incomplete-rar`) | |
| Release artefacts | Cisco's tarball, packages and images | The source tarball, the net patches against ClamAV 1.5.4, and a linux/amd64 image `ghcr.io/mkhanal/clamcove`; no other binaries | [README](../README.md#release-patches) |
| Platforms built and tested in CI | Not compared | Linux x86-64 and arm64, macOS arm64, Windows x64; 32-bit is not built | `.github/workflows/cmake.yml` |

## Limits and risks

Each item is a place where ClamCove can scan less than ClamAV, or needs something ClamAV does not. Open items are tracked in [#51](https://github.com/mkhanal/clamcove/issues/51).

| Item | What happens | What to do |
| --- | --- | --- |
| Largest file and entry | Both builds cap `MaxFileSize` at 2 GiB - 1 (libclamav lowers a larger value and warns); a file or RAR entry above the limit is not scanned in either build and alerts only under `AlertExceedsMax`, as `Heuristics.Limits.Exceeded.*`. `MaxScanSize` and `MaxScanTime` end a scan in both with the same verdicts | Same in both; nothing to change |
| RAR5 window above 1 GiB | Scanned: ClamCove allocates a window of up to 4 GiB on 64-bit, so disk (or memory) for that much is needed per concurrent scan of such an entry | Size the temporary directory (below) |
| RAR5 window above 4 GiB (dictionary larger than RAR 6 writes) | The entry is not scanned (`Declared dictionary size is not supported`); `Heuristics.Limits.Exceeded.RARSpace` under `AlertExceedsMax`, and `Heuristics.Incomplete.RAR` under `AlertIncompleteRAR`. Otherwise the archive is reported clean | Turn the alerts on where the input is untrusted |
| 32-bit | The window stops at 1 GiB | Use 64-bit |
| Temporary disk | A window above 64 MiB reserves its whole size in the temporary directory when it is created (`posix_fallocate` on Linux and the BSDs, `F_PREALLOCATE` on macOS), so free space of window size times concurrent scans of such entries is needed up front. Where the file cannot be made (no space, no permission) the window falls back to anonymous memory; when that fails too the entry is declined (`RARSpace`) | Put `TemporaryDirectory` on a disk with that space, not on tmpfs |
| `TemporaryDirectory` on tmpfs | The window file lives in RAM, so the memory saving is lost, and the reservation counts against a container's memory limit | As above |
| Windows | Windows are always memory: a 4 GiB window is 4 GiB of RAM | Lower `MaxFileSize`, or scan RAR on Linux |
| macOS | The window file is preallocated in full; where preallocation fails, zeros are written through the file | |
| Solid RAR whose window cannot be had | Later entries continue the stream of the entry that failed, so they are not scanned either; the verdict is clean unless `AlertExceedsMax` or `AlertIncompleteRAR` is set | Turn the alerts on |
| Solid RAR skip budget | Skipped entries are decoded within the scan size and scan time still available; past that the later entries are not scanned (clean unless `AlertExceedsMax`) where ClamAV goes on | |
| Damaged archives | Where ClamAV extracts more (an invalid Huffman prefix code, a damaged PPMd entry; about 2 MB more of a second solid entry in a test), ClamCove scans less | `AlertIncompleteRAR` reports it |
| RAR 1.5 | Not extracted, so its content is not scanned; reported only under `AlertIncompleteRAR` | Turn the alert on |
| Missing volume | Neither build can scan a continuation that is a missing file; both leave the archive unscanned (ClamCove alerts under `AlertIncompleteRAR`) | |
| Packaging | `libclamav` needs `libclamunrar_iface` to start; RAR cannot be a separate optional package | Ship the library with `libclamav` |
| Parsers of the version line | `ClamAV 1.5.4/<db>/<date> (ClamCove 1.5.4.2)` has a suffix | Allow it |
| Maturity | A 226-archive parity set, a libFuzzer target and 56 RAR tests back it, but it has no field history of its own; ClamAV's unRAR has years of it | Compare on your own archives, with `AlertIncompleteRAR` on |
| Licence | GPL-2.0, as ClamAV; libarchive and rardecode are BSD-2-Clause and their texts are installed | |

## Upstream status

| Change | Upstream | Status |
| --- | --- | --- |
| PCRE container check | [Cisco-Talos/clamav#1886](https://github.com/Cisco-Talos/clamav/pull/1886) (with the report [#1885](https://github.com/Cisco-Talos/clamav/issues/1885)) | Open |
| A solid 7z folder checked against `MaxScanSize` | [Cisco-Talos/clamav#1932](https://github.com/Cisco-Talos/clamav/pull/1932) | Open |
| gzip, bzip2, xz and xar output checked against `MaxScanSize` | [Cisco-Talos/clamav#1933](https://github.com/Cisco-Talos/clamav/pull/1933) | Open |
| OpenSSL 3 digest handles cached | [Cisco-Talos/clamav#1774](https://github.com/Cisco-Talos/clamav/pull/1774) | Merged upstream in Cisco-Talos/clamav#1774 (ClamAV main, after 1.5.4), backported |
| Fuzz target for the unRAR interface (also drives the libarchive backend) | [Cisco-Talos/clamav#1929](https://github.com/Cisco-Talos/clamav/pull/1929) | Open |
| clamd initial-load state recorded before the load | None yet | Not yet offered |
| RAR through libarchive and everything RAR-specific above | None ([#14](https://github.com/mkhanal/clamcove/issues/14)) | Not offered |
| Name, version suffix, release patches, CI | None | ClamCove only, never offered |

## Memory and disk

- **Idle `clamd`**: about 0.95 GiB with the official databases in both builds. `/opt/clamav` is 134 MiB in both.
- **Ordinary archives** (the 9 MB files above): `clamd` adds 8 to 15 MiB in both builds.
- **RAR window up to 64 MiB**: anonymous memory, as in ClamAV. The window of an entry is the data the entry writes (twice that where a filter can run), capped at the dictionary it declares and at what the scan limits allow, so a header that declares 1 GiB for a small entry does not allocate it.
- **RAR window above 64 MiB**: a file in `TemporaryDirectory` (`clamd.conf`) or `--tempdir` (`clamscan`), unnamed with mode 0600 and closed on exec, mapped shared, with its whole size reserved when it is made. It is released when the scan ends or the process dies. Free space needed is the window size, up to 4 GiB on 64-bit, times the concurrent scans of such entries; in the test above 1 GiB each.
- **Page cache**: the window file is reclaimable page cache, so a cgroup's `memory.peak` reads its limit during such a scan while anonymous memory stays small. Judge by anonymous memory, not by `memory.peak`.
- **Under a memory limit**: see the table above. The limit now decides how fast a scan runs, not whether `clamd` survives.
- **With concurrent scans**: each scan of such an entry has its own window, so disk, not memory, scales with `MaxThreads` for such entries.
- **Disk writes**: a window above 64 MiB is written to the temporary directory (up to the window size per entry); on flash that is wear, on a network filesystem it is latency. Use a local disk.

## Parity evidence

- **RAR parity set**: `tools/rar-parity` scans 226 archives with both builds and compares the verdicts. Run on the two builds of this document: with default options all 226 rows give the same verdict and the same number of alerts in both builds (153 alert, 73 clean), and every row matches its expected outcome. With `--alert-incomplete-rar` on ClamCove, detections are unchanged and 61 more rows alert, each with `Heuristics.Incomplete.RAR` and no row is clean in ClamCove where ClamAV alerted. The rows come from libarchive's own RAR tests (122), RARLAB `rar` 6.24 (66), archives derived from them by nesting, truncation and corruption (32), four written at scan time, and two of ClamAV's. Without the option, the rows where both builds report clean are archives no build can fully scan (a lone volume of a set, a damaged header) or that hold nothing; the option makes ClamCove alert on 61 of them.
- **RAR tests**: 56 tests in `unit_tests/clamscan/rar_test.py` cover extraction against what unRAR extracts, RAR 2.50 archives in every method, solid and not, volumes, damaged data, limits, encryption and the windows above.
- **Fuzzing**: a libFuzzer target on the RAR interface ([Cisco-Talos/clamav#1929](https://github.com/Cisco-Talos/clamav/pull/1929)) with eleven regression inputs replayed in CI.
- **CI on the tagged commit**: the [checks of the commit](https://github.com/mkhanal/clamcove/commit/3c45b0af155ca0540806f7f4b5132867da15bcdd) all passed: CMake Build (Linux x86-64 and arm64, macOS arm64, Windows x64), RAR backend, CodeQL, clang-format and Release.
- **Release gate**: the release fails if the source tarball, any patch or any image layer holds a RARLAB file (`.github/dist/check-no-rarlab.sh`), if the patches do not rebuild the release tree from the ClamAV source, or if the image lacks `libclamunrar_iface` or has `libclamunrar`.
- **Limits**: the parity set holds 12 limit rows (`MaxFileSize`, `MaxScanSize`, `MaxScanTime`), and both builds give the same verdicts on them.
- **Known open differences**: [#51](https://github.com/mkhanal/clamcove/issues/51): RAR 1.5, damaged data, the solid skip budget, a solid archive whose window cannot be had, dictionaries above 4 GiB, and the packaging link. Each is listed under Limits and risks.

### RAR5 block spanning two volumes

A 2,102,100 byte entry of filler with a 13-byte marker every 200,000 bytes (ten markers), whose single compressed block is cut in two pieces under two headers in one file (a volume set concatenated into one file), scanned with `clamscan --debug --leave-temps --max-filesize=4000M --max-scansize=4000M --allmatch` and a ten-marker `.ndb`:

| Archive | ClamAV 1.5.4 | ClamCove 1.5.4.2 |
| --- | --- | --- |
| Block in two pieces | Decodes 600,002 bytes, then `Volume open error`; 312 B scanned, 0 of 10 markers | 2,102,100 bytes, 4.01 MiB scanned, 10 of 10 markers |
| Same content, one piece (control) | 10 of 10 | 10 of 10 |
| `vol_c.rar` (318 B, a review reproducer) | Leaves 606,443 bytes unscanned, 318 B scanned | 2,102,100 bytes, 4.01 MiB scanned |

If the continuation is a genuinely missing file, neither build can scan it. The archives were written by a local RAR5 encoder that is not in the repository; the committed test is `test_block_spanning_two_volumes_is_decoded_in_full` in `unit_tests/clamscan/rar_test.py`.

## How to reproduce

Docker is the only requirement besides `python3` and `gh` (or `curl`). Everything runs in containers; nothing is installed on the host. Run from a checkout of the `clamcove-1.5.4.2` tag.

```sh
# 1. The two builds, from the two tarballs, with one Dockerfile
curl -fsSLO https://www.clamav.net/downloads/production/clamav-1.5.4.tar.gz
echo "1af1117a228f1b5bc7fa91a0dabc37848a99e7d25188e9be8043332ce721dfd3  clamav-1.5.4.tar.gz" | shasum -a 256 -c
gh release download clamcove-1.5.4.2 -R mkhanal/clamcove -p clamcove-1.5.4.2.tar.gz
echo "79b74c37dce4ed9c42b2ad142baee8da771a2a79d45437c3f03aae011f4f2bf0  clamcove-1.5.4.2.tar.gz" | shasum -a 256 -c
mkdir official cove
tar -xzf clamav-1.5.4.tar.gz -C official --strip-components=1
tar -xzf clamcove-1.5.4.2.tar.gz -C cove --strip-components=1
docker build -f tools/rar-parity/Dockerfile -t clamav-official-1.5.4 official
docker build -f tools/rar-parity/Dockerfile -t clamcove-1.5.4.2 cove

# 2. The official databases (main 63, daily 28165, bytecode 339 at the time of measurement; newer ones change timings a little)
mkdir db && docker create --name db-source clamav/clamav-debian:1.5.4 \
  && docker cp db-source:/var/lib/clamav/. db/ && docker rm db-source

# 3. The corpus: stdlib Python for the docx, zips and PDF; RARLAB rar (fetched from rarlab.com, never committed) for the RAR files
python3 -I tools/differences/make-corpus.py corpus
tools/differences/make-rar.sh rar-6.24 rar-7.23 corpus      # directories holding the rar binary of each release

# 4. Scan time and memory of the 9 MB files, one build at a time (RUNS=7 is the default)
for image in clamav-official-1.5.4 clamcove-1.5.4.2; do tools/differences/run-bench.sh $image db corpus; done

# 5. The large dictionary archive under a memory limit
for image in clamav-official-1.5.4 clamcove-1.5.4.2; do
  tools/differences/memory-cap-clamscan.sh $image "$PWD/corpus/rar" dict1g-800m.rar 900m
  tools/differences/memory-cap-clamd.sh $image "$PWD/corpus/rar" dict1g-800m.rar 2560m 4
done

# 6. Parity of the RAR test set (about 15 minutes), then again with the alert on for ClamCove
python3 tools/rar-parity/compare.py --a docker:clamav-official-1.5.4 --b docker:clamcove-1.5.4.2
python3 tools/rar-parity/compare.py --a docker:clamav-official-1.5.4 --b docker:clamcove-1.5.4.2 \
  --b-extra-options="--alert-incomplete-rar=yes"
```

`run-bench.sh` prints one JSON line per file with the median, minimum and maximum time and the memory `clamd` added; the tables above are the medians of the passes, run in the order ClamAV, ClamCove, ClamCove, ClamAV. The large-dictionary scripts print the verdicts, the peak anonymous and file memory of the cgroup, `memory.peak`, the OOM kills and the wall time; run each of them five times for a median. The version, library and installed-file claims are read with `clamscan -V`, `readelf -d` and `nm -D` on `/opt/clamav/lib` of each image, and by comparing `find /opt/clamav` between them.

The block that spans two volumes needs an RAR5 writer for a layout `rar` never produces. The archives of that table came from a small local encoder that stays out of the repository; the repository's test of the same behaviour is `test_block_spanning_two_volumes_is_decoded_in_full`.

Not measured: x86-64, Windows and macOS timings (only the Windows and macOS behaviour in the code is described), 32-bit, a network filesystem or tmpfs for the temporary directory, and RAR 1.5 and damaged-archive behaviour beyond the parity set.
