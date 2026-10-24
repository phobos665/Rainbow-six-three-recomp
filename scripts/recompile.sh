#!/bin/bash
# Lift Rainbow Six 3 from the game's own XBE into src/recomp/gen/, with the
# xboxrecomp pipeline. Run from anywhere; extra arguments go to
# scripts/recompile.py (--from disasm after a seed is added, --from lift
# after a recomp_manual.c override is added).
#
#   XBOXRECOMP_DIR  the toolkit (default: ../DirectXbox-Recomp beside this repo)
#   PYTHON          a Python with the toolkit's requirements (capstone)
set -eu
HERE="$(cd "$(dirname "$0")/.." && pwd)"
TOOLKIT="${XBOXRECOMP_DIR:-$HERE/../DirectXbox-Recomp}"
PY="${PYTHON:-$TOOLKIT/.venv/bin/python}"
[ -x "$PY" ] || PY=python3
XBE="$HERE/game/default.xbe"
[ -f "$XBE" ] || { echo "no $XBE: put the game's files in game/ (README.md)" >&2; exit 1; }
cd "$TOOLKIT"
if [ ! -f "$HERE/game/default_xdk_symbols.json" ]; then
    echo "game/default_xdk_symbols.json is missing: without it nothing is replaced"
    echo "by name (no rendering, no sound). Make it with tools.xdk_symbols; README.md."
    exit 1
fi
# --tu501 <xbe>: title update 0x501 instead of the disc, from the XBE the
# online updater installed (E:\TDATA\55530013\$u\default.xbe), into
# src/recomp/gen_tu501 with its own seeds; build with -DRS3_TU501=ON.
if [ "${1:-}" = "--tu501" ]; then
    SRC="${2:?--tu501 needs the default.xbe of the update}"
    case "$SRC" in /*) ;; *) SRC="$OLDPWD/$SRC" ;; esac   # relative to where it was run
    shift 2
    W="$HERE/build/pipeline_tu501"
    mkdir -p "$W/xbe"
    cp "$SRC" "$W/xbe/default.xbe"
    if [ ! -f "$W/xbe/default_xdk_symbols.json" ]; then
        echo "make $W/xbe/default_xdk_symbols.json with tools.xdk_symbols first (README.md)" >&2
        exit 1
    fi
    exec "$PY" scripts/recompile.py "$W/xbe/default.xbe" --work-dir "$W" \
        --gen-dir "$HERE/src/recomp/gen_tu501" --manual "$HERE/src/recomp_manual_tu501.c" \
        --seeds "$HERE/config/seeds/55530013_tu501.json" "$@"
fi
# Lift the disc's default.xbe, with a hard-drive copy's patches undone
# (scripts/disc_xbe.py), and keep it as the online updater's disc overlay,
# build/disc_overlay. The game's own files stay as they are.
"$PY" "$HERE/scripts/disc_xbe.py" "$HERE/game" "$HERE/build/pipeline/xbe" "$HERE/build/disc_overlay"
XBE="$HERE/build/pipeline/xbe/default.xbe"
exec "$PY" scripts/recompile.py "$XBE" --work-dir "$HERE/build/pipeline" \
    --project "$HERE" "$@"
