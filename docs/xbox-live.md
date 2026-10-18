# Playing Rainbow Six 3 on Xbox Live (Insignia)

The recompiled Rainbow Six 3 can sign in to [Insignia](https://insignia.live/),
the revived Xbox Live, and play online. Insignia requires title update 0x501,
which the game downloads and installs itself the first time, as a console
does.

You supply two things: the game's files, and a backup of your own console.
`scripts/build.sh` does the rest. Checked on macOS; Windows and Linux are not
yet tried.

## 1. What you need

- **The game's files** in `game/` (README). A copy made to run from a
  console's hard disk will do: the build undoes its patches (below).
- **Your console, signed up with Insignia.** Sign it up on the real console
  first; the toolkit's guide (`docs/xbox-live-guide.md` in `xboxrecomp`,
  Steps 1 and 2) says how, and how to make the backup.
- **Its backup**, in `xboxbackup/` in this repository (kept out of git):

  | File | What it is |
  | --- | --- |
  | `eeprom.bin` | the console's EEPROM (256 bytes) |
  | `hddinfo.txt` | its hard disk's key and serial |
  | `disk.bin` | its accounts (the first 512 KB of the disk) |
  | `C/` | its whole C: drive (about 100 MB): the dashboard's online updater, `C/xodash/update.xbe`, installs the title update |

  **These identify your console: never share them**, or the logs and packet
  captures made with them.

`scripts/doctor.py` checks all of this and says what each missing file costs.

## 2. Build

```bash
scripts/build.sh
```

It checks the files, makes the XDK symbols, lifts and builds the game and
the online updater, and puts them together in `build/play`. It also sets
`syslink = nat` in the game's settings (`55530013.conf`), which is how the
game reaches the internet. Set it back to play System Link.

## 3. Get the update

Start `build/play/rs3_recomp`. Choose **Xbox Live** and sign in. At "A
required update is available" choose **OK**. The updater starts; choose
**Yes**. It signs in, downloads update 0x501 (about 9 MB) and installs it
into `game/TDATA/55530013/$u`. When it says "Xbox Live is updating your
system" it closes and starts the game again.

Then quit the game and build the update's game:

```bash
scripts/build.sh
```

This time it finds the update and builds `build/play/rs3_tu501_recomp`.

## 4. Play online

Start `build/play/rs3_recomp` as before. With the update installed it starts
`rs3_tu501_recomp` in its place, as a console starts the updated game.
Choose **Xbox Live** and sign in. The main menu then shows your gamertag;
Friends and joining games online work.

## What the build does for a hard-drive copy

A copy made to run from a console's hard disk differs from the disc in three
patches to `default.xbe`: the media it may run from, the disc check, and a
block on Xbox Live (the logon's cable check is patched out, so the game says
it cannot connect without sending anything). `scripts/disc_xbe.py` undoes
all three. That gives back the disc's file, which is what is lifted, and
what the updater is shown as `D:\default.xbe` (`build/play/disc_overlay`):
the update is a patch against it, checked by hash. Your game files are not
changed.

The disc check reads the disc's security sectors, which a copy of its files
has not got; on a console the drive has checked them before the game starts,
so the recompiled game answers it as passed.

Such copies also leave out `downloader.xbe`, which the update patches. The
updater skips it (`[UPDATE] d:\downloader.xbe is not on this disc ...` in the
log) and installs the rest.

## Things to know

- **The Downloader** (Xbox Live menu) launches the game's content downloader,
  which is not recompiled: the game closes. Map packs are not needed to play.
- **Saves** are on the E: drive, `game/` (or `hdd_dir`); the update's game
  uses the same ones.
- **The cache.** The game fills its cache partition (about 1 GB) under the
  save folder.
- **Another computer.** Copy the repository's `game/` (with its `TDATA`, which
  holds the update) and `xboxbackup/`, and run `scripts/build.sh` there.

## Troubleshooting

The toolkit guide's table covers the general cases. For this game:

| Symptom | Cause | What to do |
| --- | --- | --- |
| "Cannot connect to Xbox Live" at once | the hard-drive copy's Live block in a lift made before `disc_xbe.py` | `scripts/build.sh --relift` |
| "There was not enough memory to create the asynchronous logon task" | a lift without seed `0x00397E0D` | `scripts/build.sh --relift` |
| the game closes on OK at "required update" | no updater in `build/play/updater` | `xboxbackup/C/xodash/update.xbe` missing: `scripts/doctor.py` |
| "A required update is available" again after the update | `rs3_tu501_recomp` not built yet | `scripts/build.sh` again |
| the game goes back to the dashboard at start | an old lift of the disc's file without the disc-check override | `scripts/build.sh --relift` |

## By hand

`scripts/build.sh` runs these; each can be run on its own.

- `scripts/recompile.sh`: lifts the disc's `default.xbe` into
  `src/recomp/gen` and writes `build/disc_overlay`.
- `scripts/recompile.sh --tu501 <$u/default.xbe>`: lifts the update into
  `src/recomp/gen_tu501`, with its own seeds
  (`config/seeds/55530013_tu501.json`) and overrides
  (`src/recomp_manual_tu501.c`); it wants that XBE's XDK symbols beside its
  copy in `build/pipeline_tu501/xbe/`. Build with `-DRS3_TU501=ON`.
- `rs3_tu501_recomp` reads its executable from
  `E:\TDATA\55530013\$u\default.xbe` (`hdd_dir`, else `game/`), or
  `RECOMP_TU501_XBE`.
- The settings that join the programs (`updater`, `title_update_exe`, `disc_overlay`, `hdd_dir`, `launch_map`) are in the
  toolkit guide, Step 5b.
