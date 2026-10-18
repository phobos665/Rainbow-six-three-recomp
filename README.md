# Tom Clancy's Rainbow Six 3 (Xbox) — static recompilation

A native build of Ubisoft's *Tom Clancy's Rainbow Six 3* (Xbox, 2004; title ID
`0x55530013`, XDK 5659, Unreal Engine 2) made with the
[xboxrecomp](https://github.com/phobos665/xboxrecomp) toolkit. The game's own
code is lifted to C from the XBE and runs natively; Direct3D 8 and
DirectSound are replaced at the API boundary.

**No game code or data is in this repository.** You need the files from a
copy of the disc you own.

## Current State

Runs on macOS (Apple Silicon) from boot through the intro movies, the menus
over their Bink backgrounds, the briefings and into the levels, at 60 fps with
sound.

- **60 fps.** The title asks D3D for 30 (`TWO_OR_IMMEDIATE`), but its game is
  timed by Unreal's delta time, so it runs at 60. Its Bink movies, which it
  stepped once a frame, are paced by the clock instead, so they play at their
  own 30 fps. `RECOMP_TITLE_INTERVAL=1` holds the game to the console's 30.
- **Night and thermal vision, bloom.** The post-process chain (screen copy,
  bright pass with depth in alpha, eight-level blur, additive composite) is
  drawn as the console draws it.
- **Sound.** The game makes about 800 DirectSound streams in a session, one
  per sound; all of them are heard (toolkit `f00c870`).
- **Xbox Live (Insignia).** Signs in and plays online, with title update
  0x501 installed by the recompiled dashboard updater. It needs your own
  console's identity backup; the steps are in
  [docs/xbox-live.md](docs/xbox-live.md).

Known issues:

- Not yet checked: the game's own widescreen mode. No `recomp_title_widescreen`
  is declared, so the toolkit treats it as native 16:9.

## Layout

```
Rainbow-six-three-recomp/
  CMakeLists.txt          the project; pulls in ../xboxrecomp
  src/main.c              entry point, game folder lookup (from the toolkit's template)
  src/recomp_manual.c     the title's own overrides, each with its reason
  src/recomp/gen/         lifted code (generated, not committed)
  config/seeds/           functions the disassembler cannot find on its own
  scripts/recompile.sh    runs the toolkit's lift pipeline for this game
  game/                   your game files (not committed)
```

## Building

You need the toolkit checked out beside this repository, at
`../xboxrecomp`, at a commit that has the fixes this game needs. Until those
are on the toolkit's `main`, that is its `title/rs3-split` branch (`main`
plus the DirectSound stream pool and per-project seeds). Point
`XBOXRECOMP_DIR` elsewhere to use another checkout, both for
`scripts/recompile.sh` and for CMake (`-DXBOXRECOMP_DIR=...`).

The toolkit's own requirements apply: see its `docs/GETTING_STARTED.md`
(on macOS: Homebrew CMake and Ninja, the LunarG Vulkan SDK, a Python with
`capstone` in the toolkit's `.venv`).

1. **Game files.** Extract the disc into `game/`, so that `game/default.xbe`
   exists.
2. **XDK symbols.** Build the toolkit's `third_party/XbSymbolDatabase` CLI
   (`cmake --build ... --target XbSymbolDatabaseCLI`), then from the toolkit:

   ```bash
   .venv/bin/python -m tools.xdk_symbols ../Rainbow-six-three-recomp/game/default.xbe \
       --cli <path to XbSymbolDatabaseCLI>
   ```

   That writes `game/default_xdk_symbols.json`. Without it nothing is
   replaced by name, and the game runs with no picture and no sound.
3. **Lift.** `scripts/recompile.sh` (about six minutes, most of it
   disassembly).
4. **Build.**

   ```bash
   cmake -S . -B build/Release -G Ninja -DCMAKE_BUILD_TYPE=Release
   cmake --build build/Release --target rs3_recomp --parallel
   ```

   On Windows the toolkit's launcher is built too (`rs3_launcher`).

## Running

```bash
build/Release/rs3_recomp
```

Settings live in the per-user settings file the toolkit writes
(`~/Library/Application Support/xboxrecomp/titles/55530013.conf` on macOS), or
as environment variables:

| Variable | Default | |
|---|---|---|
| `RECOMP_TITLE_INTERVAL` | 0 | 1 holds the game to the console's 30 fps |
| `RECOMP_RS3_MOVIE_PACE` | 1 | 0 steps Bink movies once a frame (2x speed at 60) |
| `RECOMP_RS3_MOVIE_LOG` | 0 | 1 logs movie frames against the clock |
| `RECOMP_VA_64K` | 1 | regions on 64 KB boundaries (Unreal's pooled allocator needs it) |
| `RECOMP_ETHERNET_LINK` | 0 | 0 reports no cable, so XNet does not wait on DHCP at start-up |

F9 shows the frame rate, F10 steps the frame cap, F11 saves a capture of the
frame on screen.

**Saves and cache.** The game keeps its saves on the Xbox's E: drive, which
the runtime maps to the game folder: they are written into `game/UDATA`. It
also fills its Z: cache partition (about 1 GB a run) under the save folder.
Test runs belong on a copy of `game/` without `UDATA` (`RECOMP_GAME_DIR`)
and with `RECOMP_SAVE_DIR` set to a fresh folder.

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
