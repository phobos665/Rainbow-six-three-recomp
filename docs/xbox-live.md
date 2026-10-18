# Playing Rainbow Six 3 on Xbox Live (Insignia)

The recompiled Rainbow Six 3 can sign in to [Insignia](https://insignia.live/),
the revived Xbox Live, and play online. Insignia requires title update 0x501,
so there are two builds of the game: the disc's, which you start from, and
the update's, which you play online with.

The general steps (signing your console up, backing up its identity, the
network) are in the toolkit's guide, `docs/xbox-live-guide.md` in
`xboxrecomp`. This page is what Rainbow Six 3 adds. Checked on macOS; Windows
and Linux are not yet tried.

## Before you start

Do Steps 1 to 4 of the toolkit's guide:

1. Sign your real console up with Insignia.
2. Back up its EEPROM, HDD key and accounts (`eeprom.bin`, `hddinfo.txt`,
   `disk.bin`), and copy its C: drive.
3. Put the three backup files in `xboxbackup/` in this repository (already
   kept out of git). **They identify your console: never share them.**
4. Turn on the router: `syslink = nat` (or `RECOMP_SYSLINK=nat`).

Then build the toolkit's online updater (Step 5a of the guide), which installs
the update.

## 1. Build the disc's game

As in the README (`scripts/recompile.sh`, then CMake into `build/Release`).

If your copy was made to run from a console's hard disk, its `default.xbe`
stops Xbox Live: the logon's cable check is patched out, so the game says it
cannot connect without sending anything. `scripts/recompile.sh` lifts a copy
with that one patch undone (`scripts/live_unpatch.py`); your game files are
not changed.

## 2. Make the disc overlay

A hard-drive copy also differs from the disc in ways the update notices: its
`default.xbe` is patched (the disc's is kept as `default.bak`), and it leaves
out `downloader.xbe`, which the update patches. Make a folder, outside the
repository, holding:

| File | Where from |
| --- | --- |
| `default.xbe` | a copy of `game/default.bak` |
| `downloader.xbe` | your disc, if it has it; otherwise the updated `downloader.xbe` of update 0x501 (1,138,688 bytes, CRC32 `9CBA8622`), which the update accepts as already patched |

A disc ripped whole needs neither.

## 3. Get the update

Make a folder for the shared E: drive and copy the game's saves into it, so
the game keeps them:

```bash
mkdir -p ~/rs3-e
cp -R game/UDATA game/TDATA ~/rs3-e/
```

Run the disc's game with these settings (environment variables shown; each
also works as a setting in `55530013.conf`):

```bash
T=<path to xboxrecomp>
export RECOMP_SYSLINK=nat
export RECOMP_HDD_DIR=~/rs3-e
export RECOMP_DISC_OVERLAY=<the overlay folder>
export RECOMP_LAUNCH_MAP="update.xbe=$T/titles/xodash-update/build/Release/xodash_update_recomp|$PWD/game"
build/Release/rs3_recomp
```

In the game: **Xbox Live**, sign in, and at "A required update is available"
choose **OK**. The updater starts; choose **Yes**. It signs in, downloads
update 0x501 (about 9 MB) and installs it into
`~/rs3-e/TDATA/55530013/$u`. When it says "Xbox Live is updating your
system" and closes, the update is in place.

## 4. Build the update's game

The update's executable is now `~/rs3-e/TDATA/55530013/$u/default.xbe`.

1. Lift it. The first run stops and asks for its XDK symbols:

   ```bash
   scripts/recompile.sh --tu501 ~/rs3-e/TDATA/55530013/\$u/default.xbe
   ```

   Make them as for the disc (README, step 2), from the toolkit:

   ```bash
   .venv/bin/python -m tools.xdk_symbols ../Rainbow-six-three-recomp/build/pipeline_tu501/xbe/default.xbe \
       --cli <path to XbSymbolDatabaseCLI>
   ```

   and run `scripts/recompile.sh --tu501 ...` again. It writes
   `src/recomp/gen_tu501/` with its own seeds
   (`config/seeds/55530013_tu501.json`) and overrides
   (`src/recomp_manual_tu501.c`).

2. Build it, in its own folder:

   ```bash
   cmake -S . -B build/Release-tu501 -G Ninja -DCMAKE_BUILD_TYPE=Release -DRS3_TU501=ON
   cmake --build build/Release-tu501 --target rs3_tu501_recomp --parallel
   ```

## 5. Play online

```bash
RECOMP_SYSLINK=nat RECOMP_HDD_DIR=~/rs3-e build/Release-tu501/rs3_tu501_recomp
```

It reads its executable from `$RECOMP_HDD_DIR/TDATA/55530013/$u/default.xbe`
(or `RECOMP_TU501_XBE`), and the rest of the game from `game/`, as the
console reads the disc. Choose **Xbox Live** and sign in. The main menu then
shows your gamertag; Friends and joining games online work.

To have the disc's game hand over to it by itself, as the console does
after the update, add it to the launch map:

```bash
export RECOMP_LAUNCH_MAP="update.xbe=$T/titles/xodash-update/build/Release/xodash_update_recomp|$PWD/game;55530013=$PWD/build/Release-tu501/rs3_tu501_recomp|$PWD/game"
```

## Things to know

- **The Downloader** (Xbox Live menu) launches the game's content downloader,
  `downloader.xbe`, which is not recompiled: the game closes. Map packs are
  not needed to play.
- **Saves** live on the shared E: drive (`hdd_dir`) once it is set, not in
  `game/UDATA`.
- **The cache.** The game fills its cache partition (about 1 GB) under the
  save folder.

## Troubleshooting

The toolkit guide's table covers the general cases. For this game:

| Symptom | Cause | What to do |
| --- | --- | --- |
| "Cannot connect to Xbox Live" at once | the hard-drive copy's Live block | lift with `scripts/recompile.sh` (it undoes it) |
| "There was not enough memory to create the asynchronous logon task" | a lift without seed `0x00397E0D` | lift again from this branch's `config/seeds/55530013.json` |
| "A required update is available" again, in the update's game | the disc's game was started instead | run `rs3_tu501_recomp` |
| the update stops part-way | `default.xbe` or `downloader.xbe` in the overlay is not the expected file | section 2 |
| `rs3_tu501_recomp` cannot find its executable | the update is not installed where it looks | `RECOMP_HDD_DIR`, or `RECOMP_TU501_XBE=<path to $u/default.xbe>` |
