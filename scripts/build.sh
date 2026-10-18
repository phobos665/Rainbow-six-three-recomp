#!/bin/bash
# From your files to a folder you can play from: build/play.
#
#   game/        the disc's files (README.md)
#   xboxbackup/  your console's backup, for Xbox Live (docs/xbox-live.md):
#                eeprom.bin, hddinfo.txt, disk.bin, and its C: drive in C/
#
#   scripts/build.sh            build what is missing
#   scripts/build.sh --relift   lift everything again (after a toolkit change)
#
# It checks the files (scripts/doctor.py), makes the XDK symbols, lifts and
# builds the disc's game, and with a backup the online updater too. Once the
# game has installed title update 0x501 (Xbox Live, "A required update is
# available"), run it again: it builds the update's game, which the disc's
# then starts by itself.
#
#   XBOXRECOMP_DIR  the toolkit (default: ../xboxrecomp beside this repo)
set -eu
HERE="$(cd "$(dirname "$0")/.." && pwd)"
TOOLKIT="$(cd "${XBOXRECOMP_DIR:-$HERE/../xboxrecomp}" && pwd)"
B="$HERE/build"
PLAY="$B/play"
RELIFT=0
[ "${1:-}" = "--relift" ] && RELIFT=1
GEN=()
command -v ninja >/dev/null && GEN=(-G Ninja)

step() { printf '\n== %s\n' "$*"; }

step "Checking your files"
python3 "$HERE/scripts/doctor.py" "$HERE"
LIVE=0
[ -f "$HERE/xboxbackup/eeprom.bin" ] && [ -f "$HERE/xboxbackup/C/xodash/update.xbe" ] && LIVE=1

step "The toolkit's Python"
PY="$TOOLKIT/.venv/bin/python"
if [ ! -x "$PY" ]; then
    python3 -m venv "$TOOLKIT/.venv"
    "$PY" -m pip install --quiet capstone
fi
"$PY" -c "import capstone" 2>/dev/null || "$PY" -m pip install --quiet capstone

CLI="$B/xbsdb/projects/cli/XbSymbolDatabaseCLI"
symbols() {   # <xbe>: its XDK symbols, beside it
    local json="${1%.xbe}_xdk_symbols.json"
    [ -f "$json" ] && return 0
    if [ ! -x "$CLI" ]; then
        step "XbSymbolDatabase (names the XDK functions)"
        cmake -S "$TOOLKIT/third_party/XbSymbolDatabase" -B "$B/xbsdb" ${GEN[@]+"${GEN[@]}"} \
            -DCMAKE_BUILD_TYPE=Release >/dev/null
        cmake --build "$B/xbsdb" --target XbSymbolDatabaseCLI >/dev/null
    fi
    (cd "$TOOLKIT" && "$PY" -m tools.xdk_symbols "$1" --cli "$CLI")
}

configure() {   # <source> <build dir> [cmake args...]
    local src="$1" dir="$2"
    shift 2
    if [ -f "$dir/CMakeCache.txt" ]; then
        # Again, so a folder configured against another toolkit follows this one.
        cmake -S "$src" -B "$dir" -DXBOXRECOMP_DIR="$TOOLKIT" "$@" >/dev/null
    else
        cmake -S "$src" -B "$dir" ${GEN[@]+"${GEN[@]}"} \
            -DCMAKE_BUILD_TYPE=Release -DXBOXRECOMP_DIR="$TOOLKIT" "$@"
    fi
}

step "The disc's game"
symbols "$HERE/game/default.xbe"
if [ $RELIFT = 1 ] || [ ! -f "$HERE/src/recomp/gen/recomp_dispatch.c" ]; then
    XBOXRECOMP_DIR="$TOOLKIT" "$HERE/scripts/recompile.sh"
else
    # build/disc_overlay, which the lift writes, for a tree lifted before it did.
    python3 "$HERE/scripts/disc_xbe.py" "$HERE/game" "$B/pipeline/xbe" "$B/disc_overlay" >/dev/null
fi
configure "$HERE" "$B/Release"
cmake --build "$B/Release" --target rs3_recomp --parallel

if [ $LIVE = 1 ]; then
    step "The online updater (the dashboard's update.xbe, from your C: drive)"
    W="$B/pipeline_updater"
    mkdir -p "$W/xbe"
    cmp -s "$HERE/xboxbackup/C/xodash/update.xbe" "$W/xbe/default.xbe" ||
        cp "$HERE/xboxbackup/C/xodash/update.xbe" "$W/xbe/default.xbe"
    symbols "$W/xbe/default.xbe"
    if [ $RELIFT = 1 ] || [ ! -f "$TOOLKIT/titles/xodash-update/src/recomp/gen/recomp_dispatch.c" ]; then
        (cd "$TOOLKIT" && "$PY" scripts/recompile.py "$W/xbe/default.xbe" --work-dir "$W" \
            --project "$TOOLKIT/titles/xodash-update")
    fi
    configure "$TOOLKIT/titles/xodash-update" "$B/updater"
    cmake --build "$B/updater" --target xodash_update_recomp --parallel
fi

# Title update 0x501, once the updater has installed it on the E: drive:
# hdd_dir if set, else game/.
E="${RECOMP_HDD_DIR:-}"
if [ -z "$E" ]; then
    E="$(python3 - "$HERE" <<'EOF'
import os, sys, platform
from pathlib import Path
home = Path.home()
if platform.system() == "Darwin":
    base = home / "Library/Application Support"
elif os.name == "nt":
    base = Path(os.environ.get("LOCALAPPDATA", home))
else:
    base = Path(os.environ.get("XDG_DATA_HOME", home / ".local/share"))
conf = base / "xboxrecomp/titles/55530013.conf"
value = ""
if conf.is_file():
    for line in conf.read_text().splitlines():
        k, _, v = line.partition("=")
        if k.strip() == "hdd_dir" and not line.lstrip().startswith("#"):
            value = v.strip()
print(value or str(Path(sys.argv[1]) / "game"))
EOF
)"
fi
TU_XBE="$E/TDATA/55530013/\$u/default.xbe"
if [ -f "$TU_XBE" ]; then
    step "Title update 0x501 (installed in $E)"
    W="$B/pipeline_tu501"
    mkdir -p "$W/xbe"
    cmp -s "$TU_XBE" "$W/xbe/default.xbe" || {
        cp "$TU_XBE" "$W/xbe/default.xbe"
        rm -f "$W/xbe/default_xdk_symbols.json"
    }
    symbols "$W/xbe/default.xbe"
    if [ $RELIFT = 1 ] || [ ! -f "$HERE/src/recomp/gen_tu501/recomp_dispatch.c" ]; then
        XBOXRECOMP_DIR="$TOOLKIT" "$HERE/scripts/recompile.sh" --tu501 "$TU_XBE"
    fi
    configure "$HERE" "$B/Release-tu501" -DRS3_TU501=ON
    cmake --build "$B/Release-tu501" --target rs3_tu501_recomp --parallel
fi

step "build/play"
# The executables side by side, so each finds the next by itself: the disc's
# game hands over to the update's when it is installed, and launches the
# updater from updater/, whose game folder is your C: drive with the
# updater as its default.xbe. The disc overlay is the disc's default.xbe,
# which the updater checks before patching it.
mkdir -p "$PLAY/updater"
cp "$B/Release/rs3_recomp" "$PLAY/"
[ -f "$B/Release-tu501/rs3_tu501_recomp" ] && cp "$B/Release-tu501/rs3_tu501_recomp" "$PLAY/"
rm -rf "$PLAY/disc_overlay"
cp -R "$B/disc_overlay" "$PLAY/disc_overlay"
if [ $LIVE = 1 ]; then
    cp "$B/updater/xodash_update_recomp" "$PLAY/updater/"
    mkdir -p "$PLAY/updater/game"
    # -L: the C: copy may be a link to where it is kept.
    rsync -aL --delete --exclude default.xbe "$HERE/xboxbackup/C/" "$PLAY/updater/game/"
    cp "$HERE/xboxbackup/C/xodash/update.xbe" "$PLAY/updater/game/default.xbe"
fi
# The game and the backup are found beside the play folder's parent's
# parent (game/, xboxbackup/), as from build/Release.

if [ $LIVE = 1 ]; then
    step "Settings"
    python3 - <<'EOF'
import os, platform
from pathlib import Path
home = Path.home()
if platform.system() == "Darwin":
    base = home / "Library/Application Support"
elif os.name == "nt":
    base = Path(os.environ.get("LOCALAPPDATA", home))
else:
    base = Path(os.environ.get("XDG_DATA_HOME", home / ".local/share"))
conf = base / "xboxrecomp/titles/55530013.conf"
lines = conf.read_text().splitlines() if conf.is_file() else []
out, done = [], False
for line in lines:
    k = line.partition("=")[0].strip()
    if k == "syslink" and not line.lstrip().startswith("#"):
        if line.partition("=")[2].strip() != "nat":
            print(f"syslink = nat in {conf} (was: {line.strip()}); the game reaches "
                  "Xbox Live through it. Set it back to play System Link.")
        line, done = "syslink = nat", True
    out.append(line)
if not done:
    out.append("syslink = nat")
    print(f"syslink = nat in {conf}: the game reaches Xbox Live through it.")
conf.parent.mkdir(parents=True, exist_ok=True)
conf.write_text("\n".join(out) + "\n")
EOF
fi

step "Done"
echo "Play: $PLAY/rs3_recomp"
if [ $LIVE = 1 ] && [ ! -f "$TU_XBE" ]; then
    echo "Xbox Live: choose Xbox Live in the game and accept the update; then run"
    echo "scripts/build.sh again to build the update's game."
fi
