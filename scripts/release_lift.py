#!/usr/bin/env python3
"""The lift a self-building release runs (release/rs3.json; the toolkit's
docs/technical/self-build-release.md), in place of the toolkit's own.

    release_lift.py <folder holding the player's default.xbe>
    release_lift.py --tu501 <folder holding the installed update's default.xbe>

The disc's default.xbe from the player's (scripts/disc_xbe.py: a hard-drive
copy's patches undone), its XDK functions named with the release's own
XbSymbolDatabase, then the pipeline into src/recomp/gen, as
scripts/recompile.sh does at a desk. The release's builder runs this with its
Python, from its copy of this repository, with the release's pipeline linked
in as xboxrecomp/.

--tu501 lifts title update 0x501 once the dashboard's updater has installed
it (release/rs3.json's title_update; the builder's title-update): into
src/recomp/gen_tu501 with src/recomp_manual_tu501.c and the update's seeds,
as scripts/build.py does, built with RS3_TU501=ON.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "scripts"))
import disc_xbe  # noqa: E402


def run(cmd, cwd):
    cmd = [str(c) for c in cmd]
    print("$ " + " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=cwd)
    if r.returncode:
        sys.exit(f"failed ({r.returncode}): {cmd[0]}")


def lift_update(src: Path, toolkit: Path) -> int:
    xbe = src / "default.xbe"
    cli = toolkit.resolve().parent / "bin" / "XbSymbolDatabaseCLI"
    run([sys.executable, "-m", "tools.xdk_symbols", xbe, "--cli", cli,
         "--out", xbe.with_name("default_xdk_symbols.json")], cwd=toolkit)
    run([sys.executable, toolkit / "scripts" / "recompile.py", xbe,
         "--work-dir", src.parent / "rs3_tu501" / "out", "--project", HERE,
         "--gen-dir", HERE / "src/recomp/gen_tu501",
         "--manual", HERE / "src/recomp_manual_tu501.c",
         "--seeds", HERE / "config/seeds/55530013_tu501.json"], cwd=toolkit)
    return 0


def main() -> int:
    args = sys.argv[1:]
    update = args[:1] == ["--tu501"]
    if update:
        args = args[1:]
    if len(args) != 1:
        print("usage: release_lift.py [--tu501] <folder holding the XBE>", file=sys.stderr)
        return 2
    src = Path(args[0]).resolve()
    toolkit = HERE / "xboxrecomp"
    if not (toolkit / "scripts" / "recompile.py").is_file():
        sys.exit(f"no pipeline at {toolkit}: this runs inside a release's build")
    if update:
        return lift_update(src, toolkit)
    work = src.parent / "rs3"
    xbe = work / "xbe" / "default.xbe"
    if disc_xbe.main([src, xbe.parent]) != 0:
        return 1
    # The patches undone move no function, so the names apply to either.
    cli = toolkit.resolve().parent / "bin" / "XbSymbolDatabaseCLI"
    run([sys.executable, "-m", "tools.xdk_symbols", xbe, "--cli", cli,
         "--out", xbe.with_name("default_xdk_symbols.json")], cwd=toolkit)
    run([sys.executable, toolkit / "scripts" / "recompile.py", xbe,
         "--work-dir", work / "out", "--project", HERE], cwd=toolkit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
