# Tom Clancy's Rainbow Six 3 (Xbox) — static recompilation

Ubisoft's *Tom Clancy's Rainbow Six 3* (Xbox, 2004) recompiled into a native
program for Windows, macOS and Linux (including SteamOS and the Steam Deck).
You bring your own copy of the game, and it is built from that copy on your
computer. This repository and its releases contain no game code or data.

- [Play](#play): download, point it at your disc, play.
- [Build it yourself](#build-it-yourself): for developers working on the port,
  and for [Xbox Live](#playing-on-xbox-live), which needs a build of your own.

# Play

## What you need

- Rainbow Six 3: a disc image (`.iso` or `.xiso`), a folder with the disc's
  files in it, or a copy made to run from a console's hard disk. Other
  releases are refused (see [Releases of the game](#releases-of-the-game)).
- 64-bit Windows 10 or 11, a Mac with Apple Silicon (macOS 13 or later), or
  x86-64 Linux, SteamOS included, with Vulkan drivers.
- About 500 MB of space, plus room for the game's files if you give it a disc
  image (an image is unpacked once; a folder is used where it is), and about
  1 GB for the game's own cache.

Nothing else needs installing: the download carries everything it builds the
game with.

## Download and start

Download the file for your system from the
[latest release](https://github.com/phobos665/Rainbow-six-three-recomp/releases/latest):

| System | File | Start |
| --- | --- | --- |
| Windows | `rs3-<version>-windows-x86_64.zip` | Unzip it and run `rs3.exe` |
| macOS | `rs3-<version>-macos-arm64.tar.xz` | Unpack it, then see [macOS](#macos) below |
| Linux, SteamOS | `rs3-<version>-linux-x86_64.tar.xz` | Unpack it and run `./rs3` |

The first time it starts, it asks for your copy of the game: choose **Disc
image...** or **Folder...**, or paste a path. It then builds the game, which
takes several minutes (longer on a Steam Deck), and opens the settings. Press
**Play**. After that it opens straight to the settings.

**Windows** may say it protected your PC, because the release is not signed:
choose More info, then Run anyway.

### macOS

Move `Rainbow Six 3.app` to Applications. It is not signed with an Apple
Developer ID, so before opening it the first time, open Terminal and run

```sh
xattr -dr com.apple.quarantine "/Applications/Rainbow Six 3.app"
```

That clears the flag macOS puts on everything downloaded, from the app and the
tools it builds the game with. Then open it.

### Steam Deck and SteamOS

Unpack the release in desktop mode and run `rs3` once to build the game. To
play from Game Mode, add `rs3` to Steam (Add a Non-Steam Game) and give the
shortcut `icon.png` from the release folder as its icon.

## What works

Played on macOS (Apple Silicon) from boot through the intro movies, the menus
over their Bink backgrounds, the briefings and into the levels, at 60 fps with
sound.

- **60 fps.** The game asks for 30, but it is timed by Unreal's delta time, so
  it runs at 60. Its Bink movies are paced by the clock, so they play at their
  own 30 fps.
- **Night and thermal vision, bloom**, drawn as the console draws them.
- **Sound.** The game makes about 800 sound streams in a session, one per
  sound, and all of them are heard.
- **Xbox Live (Insignia)** signs in and plays online, from a build of your own
  with a backup of your own console: see [Playing on Xbox
  Live](#playing-on-xbox-live).

Known issues:

- The game's own widescreen mode has not been checked yet.

## Controls

Controllers work as an Xbox pad, and the keyboard plays as controller 1.
Change the bindings in the launcher's Input tab.

While playing:

| Key | |
| --- | --- |
| F9 | Show or hide the frame rate |
| F10 | Change the frame cap |
| F11 | Save a screenshot and a capture of the frame, for bug reports |
| Alt+Enter | Switch between fullscreen and a window |

## Where things are kept

The built game, its saves and the logs are in one folder per user:

| | |
| --- | --- |
| Windows | `%LOCALAPPDATA%\xboxrecomp\builds\55530013\` |
| macOS | `~/Library/Application Support/xboxrecomp/builds/55530013/` |
| Linux | `~/.local/share/xboxrecomp/builds/55530013/` |

In it, `game/UDATA/` holds your saves, `build.log` is the build's log and
`rs3_recomp.log` the game's. Your own disc or folder is never written to.

The settings and controls are kept apart from the build:

| | Settings | Controls |
| --- | --- | --- |
| Windows | `%APPDATA%\xboxrecomp\titles\55530013.conf` | `%APPDATA%\xboxrecomp\input_bindings.json` |
| macOS | `~/Library/Application Support/xboxrecomp/titles/55530013.conf` | `~/Library/Application Support/xboxrecomp/input_bindings.json` |
| Linux | `~/.config/xboxrecomp/titles/55530013.conf` | `~/.config/xboxrecomp/input_bindings.json` |

## Updating

Download the new release and start it. It sees that the game was built by an
older release and offers **Build again**, with your disc remembered. Saves and
settings carry over.

## Problems

- The disc is refused: it is not one of the releases below. Please open an
  issue with the title, region and SHA-1 the message shows.
- The build fails: open an issue and attach `build.log` (see [Where things
  are kept](#where-things-are-kept)).
- A black window and nothing else: attach `rs3_recomp.log` from the same
  folder.
- A rendering bug in one place: press F11 there, and attach the `.bmp` and
  `.d3dcap` files it writes beside the game.

## Releases of the game

The game is recognised by the SHA-1 of its `default.xbe`:

| Copy | `default.xbe` SHA-1 |
| --- | --- |
| Disc | `a232aa535391d53ea01ace0df17f801ee03c57f6` |
| Hard-drive copy | `7aea9715ad1a42d83796f9e106fd6e6a75ae9635` |

Any other is refused.

# Build it yourself

For working on the port, and for Xbox Live. This builds the game by hand, from
a clone, against the
[DirectXbox-Recomp](https://github.com/phobos665/DirectXbox-Recomp) toolkit:
the game's own code (title ID `0x55530013`, XDK 5659, Unreal Engine 2) is
lifted to C from the XBE and runs natively, and Direct3D 8 and DirectSound
are replaced at the API boundary.

## Layout

```
Rainbow-six-three-recomp/
  CMakeLists.txt          the project; pulls in ../DirectXbox-Recomp
  src/main.c              entry point, game folder lookup (from the toolkit's template)
  src/recomp_manual.c     the title's own overrides, each with its reason
  src/recomp/gen/         lifted code (generated, not committed)
  config/seeds/           functions the disassembler cannot find on its own
  release/rs3.json        the recipe the release workflow builds from
  scripts/build.py        everything, from your files to build/play (build.sh, build.bat run it)
  scripts/doctor.py       checks the game files and the console backup
  scripts/recompile.sh    runs the toolkit's lift pipeline for this game
  scripts/disc_xbe.py     the disc's default.xbe from a hard-drive copy's
  scripts/release_lift.py the lift a release runs on the player's machine
  game/                   your game files (not committed)
```

## Building

You need the toolkit's `main` checked out beside this repository, at
`../DirectXbox-Recomp`. Point `XBOXRECOMP_DIR` elsewhere to use another checkout,
both for `scripts/recompile.sh` and for CMake (`-DXBOXRECOMP_DIR=...`).

The toolkit's own requirements apply: see its `docs/GETTING_STARTED.md`
(on macOS: Homebrew CMake and Ninja, the LunarG Vulkan SDK, a Python with
`capstone` in the toolkit's `.venv`).

1. **Game files.** Extract the disc into `game/`, so that `game/default.xbe`
   exists. A copy made to run from a console's hard disk will do.
2. **Build.**

   ```bash
   python3 scripts/build.py      # Windows: scripts\build.bat
   ```

   It checks your files (`scripts/doctor.py`), builds the toolkit's XDK
   symbol tool and makes the game's XDK symbols, lifts the game (about six
   minutes, most of it disassembly) and builds it into `build/play`. With a
   console backup in `xboxbackup/` it builds the online updater too
   ([docs/xbox-live.md](docs/xbox-live.md)). Run it again after changing
   anything: it redoes only what is missing (`--relift` lifts again).

By hand, the same steps: the XDK symbols with the toolkit's
`tools.xdk_symbols` (`--cli` its `XbSymbolDatabaseCLI`), which writes
`game/default_xdk_symbols.json` (without it nothing is replaced by name, and
the game runs with no picture and no sound); `scripts/recompile.sh`; then

```bash
cmake -S . -B build/Release -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build/Release --target rs3_recomp --parallel
```

On Windows the toolkit's launcher is built too (`rs3_launcher`).

## Running a build of your own

```bash
build/play/rs3_recomp
```

The settings file is as in [Where things are kept](#where-things-are-kept),
and these environment variables are particular to this game:

| Variable | Default | |
|---|---|---|
| `RECOMP_TITLE_INTERVAL` | 0 | 1 holds the game to the console's 30 fps |
| `RECOMP_RS3_MOVIE_PACE` | 1 | 0 steps Bink movies once a frame (2x speed at 60) |
| `RECOMP_RS3_MOVIE_LOG` | 0 | 1 logs movie frames against the clock |
| `RECOMP_VA_64K` | 1 | regions on 64 KB boundaries (Unreal's pooled allocator needs it) |
| `RECOMP_ETHERNET_LINK` | 0 | 0 reports no cable, so XNet does not wait on DHCP at start-up |

**Saves and cache.** The game keeps its saves on the Xbox's E: drive, which
the runtime maps to the game folder: in a build of your own they are written
into `game/UDATA`. It also fills its Z: cache partition (about 1 GB a run)
under the save folder. Test runs belong on a copy of `game/` without `UDATA`
(`RECOMP_GAME_DIR`) and with `RECOMP_SAVE_DIR` set to a fresh folder.

## Playing on Xbox Live

Rainbow Six 3 can sign in to [Insignia](https://insignia.live/), the free
revival of the original Xbox Live, and play online with people on real
consoles. This has been checked on macOS, from a build of your own; the
release download does not do it.

Insignia only lets in consoles it knows, so the game signs in as **your own
Xbox**. You give it a backup of that console; the build does everything else.

### What you need

- An original Xbox you own that can run homebrew (softmodded or chipped),
  with the EvoX dashboard and FTP access.
- A free account at [insignia.live](https://insignia.live/).
- This game built as above, with its files in `game/`.

### 1. Sign the Xbox up (once, on the console)

1. If your modded BIOS blocks Xbox Live, run Insignia's **xblunblock** first.
2. Run the **Insignia Setup Assistant** and register the console.
3. Sign in once from the dashboard's **Xbox Live** section, so your gamertag
   is on the console.

### 2. Back up the Xbox (after step 1)

1. In EvoX, choose **Backup eeprom**. It writes `eeprom.bin`, `hddinfo.txt`
   and `disk.bin`.
2. Connect to the Xbox over FTP and copy those three files, and the whole
   **C:** drive (about 100 MB).
3. Put them in this repository like this:

   ```text
   xboxbackup/
     eeprom.bin
     hddinfo.txt
     disk.bin
     C/            everything from the Xbox's C: drive
   ```

These files are your console's identity. **Never share them.** Git ignores
`xboxbackup/`.

### 3. Check and build

```bash
python3 scripts/doctor.py     # should end with "Xbox Live: ready."
python3 scripts/build.py      # Windows: scripts\build.bat
```

### 4. Install the game's update (once)

Insignia needs title update 0x501. The game fetches it itself:

1. Start `build/play/rs3_recomp`.
2. On the main menu choose **Xbox Live** and sign in.
3. At "A required update is available", choose **OK**.
4. The updater opens: choose **Yes**. When it says "Xbox Live is updating
   your system", it closes and the game starts again.
5. Quit the game and run `python3 scripts/build.py` again. This builds the
   updated game.

### 5. Play

Start `build/play/rs3_recomp`. It opens the updated game by itself. Choose
**Xbox Live** and sign in: your gamertag appears on the main menu, and you
can join games and use Friends.

Something not working? See the table in
[docs/xbox-live.md](docs/xbox-live.md#troubleshooting), which also explains
what the build does.

## What is specific to this game

All in `src/recomp_manual.c` and `config/`:

- **64 KB regions and no network cable**, set before `main` unless the
  variable is already set (see the table above).
- **Bink pacing.** `sub_002BC000` (BinkDoFrame, BinkNextFrame,
  BinkCopyToBuffer into the locked back buffer) is wrapped so it runs only
  when the movie's next frame is due by the clock; between those the last
  frame is shown again.
- **Seeds:** thread routines and indirect-call targets seen at run time,
  among them the XNet timer callback (`0x003AC22A`) and the Bink blitters.

## Making a release

Pushing a version tag (`git tag v1.0 && git push origin v1.0`) runs
`.github/workflows/release.yml`, which builds the Windows, macOS and Linux
downloads from `release/rs3.json` and attaches them to the tag's GitHub
release. No game files are involved. How the downloads work is in the
toolkit's
[self-build-release.md](https://github.com/phobos665/DirectXbox-Recomp/blob/main/docs/technical/self-build-release.md).
