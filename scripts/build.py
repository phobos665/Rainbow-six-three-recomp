#!/usr/bin/env python3
"""From your files to a folder you can play from: build/play.

  game/        the disc's files (README.md)
  xboxbackup/  your console's backup, for Xbox Live (docs/xbox-live.md):
               eeprom.bin, hddinfo.txt, disk.bin, and its C: drive in C/

    python3 scripts/build.py            build what is missing
    python3 scripts/build.py --relift   lift everything again (after a toolkit change)

(scripts/build.sh and scripts\\build.bat run this.) It checks the files
(scripts/doctor.py), makes the XDK symbols, lifts and builds the disc's game,
and with a backup the online updater too. Once the game has installed title
update 0x501 (Xbox Live, "A required update is available"), run it again: it
builds the update's game, which the disc's then starts by itself.

  XBOXRECOMP_DIR  the toolkit (default: ../xboxrecomp beside this repo)
  RECOMP_HDD_DIR  the E: drive, if not hdd_dir in the settings, else game/
"""
import argparse
import filecmp
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "scripts"))
import disc_xbe  # noqa: E402
import doctor    # noqa: E402

TITLE = "55530013"
WINDOWS = os.name == "nt"
EXE = ".exe" if WINDOWS else ""


def step(what: str) -> None:
    print(f"\n== {what}", flush=True)


def run(cmd, cwd=None, quiet=False) -> None:
    cmd = [str(c) for c in cmd]
    r = subprocess.run(cmd, cwd=cwd, stdout=subprocess.DEVNULL if quiet else None)
    if r.returncode != 0:
        sys.exit(f"\nFailed ({r.returncode}): {' '.join(cmd)}")


def settings_file() -> Path:
    """The game's per-user settings, where the toolkit reads them."""
    home = Path.home()
    if platform.system() == "Darwin":
        base = home / "Library" / "Application Support"
    elif WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA", home))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share"))
    return base / "xboxrecomp" / "titles" / f"{TITLE}.conf"


def setting(key: str):
    conf = settings_file()
    if not conf.is_file():
        return None
    value = None
    for line in conf.read_text().splitlines():
        if line.lstrip().startswith("#"):
            continue
        k, _, v = line.partition("=")
        if k.strip() == key:
            value = v.strip()
    return value


def set_setting(key: str, value: str, why: str) -> None:
    conf = settings_file()
    lines = conf.read_text().splitlines() if conf.is_file() else []
    out, done = [], False
    for line in lines:
        if not line.lstrip().startswith("#") and line.partition("=")[0].strip() == key:
            if line.partition("=")[2].strip() != value:
                print(f"{key} = {value} in {conf} (was: {line.strip()}); {why}")
            line, done = f"{key} = {value}", True
        out.append(line)
    if not done:
        out.append(f"{key} = {value}")
        print(f"{key} = {value} in {conf}; {why}")
    conf.parent.mkdir(parents=True, exist_ok=True)
    conf.write_text("\n".join(out) + "\n")


def find_exe(build_dir: Path, name: str) -> Path:
    """A single-configuration build puts it at the top, Visual Studio under Release/."""
    for p in (build_dir / f"{name}{EXE}", build_dir / "Release" / f"{name}{EXE}"):
        if p.is_file():
            return p
    sys.exit(f"\n{name}{EXE} was not built in {build_dir}")


def copy_if_changed(src: Path, dst: Path) -> None:
    if not dst.is_file() or not filecmp.cmp(src, dst, shallow=False):
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def sync_tree(src: Path, dst: Path, skip=()) -> None:
    """dst becomes a copy of src (links followed), copying only what changed."""
    dst.mkdir(parents=True, exist_ok=True)
    wanted = set()
    for root, dirs, files in os.walk(src, followlinks=True):
        rel = Path(root).relative_to(src)
        for f in files:
            if rel == Path(".") and f in skip:
                continue
            s, d = Path(root) / f, dst / rel / f
            wanted.add(d)
            if not d.is_file() or s.stat().st_size != d.stat().st_size or \
                    int(s.stat().st_mtime) != int(d.stat().st_mtime):
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s, d)
    for root, dirs, files in os.walk(dst, topdown=False):
        for f in files:
            p = Path(root) / f
            if p not in wanted and not (Path(root) == dst and f in skip):
                p.unlink()
        if Path(root) != dst and not any(Path(root).iterdir()):
            Path(root).rmdir()


def install(src: Path, dst_dir: Path) -> None:
    """An executable into the play folder, with any DLLs beside it."""
    copy_if_changed(src, dst_dir / src.name)
    if WINDOWS:
        for dll in src.parent.glob("*.dll"):
            copy_if_changed(dll, dst_dir / dll.name)


class Builder:
    def __init__(self, toolkit: Path, relift: bool):
        self.toolkit = toolkit
        self.relift = relift
        self.build = HERE / "build"
        self.generator = ["-G", "Ninja"] if shutil.which("ninja") else []
        self.py = None
        self.cli = None

    # ---- tools ---------------------------------------------------------

    def python(self) -> None:
        step("The toolkit's Python")
        venv = self.toolkit / ".venv"
        py = venv / ("Scripts/python.exe" if WINDOWS else "bin/python")
        if not py.is_file():
            run([sys.executable, "-m", "venv", venv])
        if subprocess.run([str(py), "-c", "import capstone"],
                          stderr=subprocess.DEVNULL).returncode != 0:
            run([py, "-m", "pip", "install", "--quiet", "capstone"])
        self.py = py

    def symbols(self, xbe: Path) -> None:
        """Its XDK symbols, beside it."""
        if xbe.with_name(xbe.stem + "_xdk_symbols.json").is_file():
            return
        if self.cli is None:
            out = self.build / "xbsdb"
            try:
                self.cli = find_exe(out / "projects" / "cli", "XbSymbolDatabaseCLI")
            except SystemExit:
                step("XbSymbolDatabase (names the XDK functions)")
                self.configure(self.toolkit / "third_party" / "XbSymbolDatabase", out, toolkit=False)
                run(["cmake", "--build", out, "--target", "XbSymbolDatabaseCLI",
                     "--config", "Release"], quiet=True)
                self.cli = find_exe(out / "projects" / "cli", "XbSymbolDatabaseCLI")
        run([self.py, "-m", "tools.xdk_symbols", xbe, "--cli", self.cli], cwd=self.toolkit)

    def configure(self, src: Path, out: Path, *extra, toolkit=True) -> None:
        args = [f"-DXBOXRECOMP_DIR={self.toolkit}"] if toolkit else []
        if (out / "CMakeCache.txt").is_file():
            # Again, so a folder configured against another toolkit follows this one.
            run(["cmake", "-S", src, "-B", out, *args, *extra], quiet=True)
        else:
            run(["cmake", "-S", src, "-B", out, *self.generator,
                 "-DCMAKE_BUILD_TYPE=Release", *args, *extra])

    def compile(self, src: Path, out: Path, target: str, *extra) -> Path:
        self.configure(src, out, *extra)
        run(["cmake", "--build", out, "--target", target, "--config", "Release", "--parallel"])
        return find_exe(out, target)

    def lift(self, xbe: Path, work: Path, *args) -> None:
        run([self.py, "scripts/recompile.py", xbe, "--work-dir", work, *args], cwd=self.toolkit)

    # ---- the three programs ---------------------------------------------

    def disc_game(self) -> Path:
        step("The disc's game")
        game = HERE / "game"
        self.symbols(game / "default.xbe")
        # The disc's default.xbe, with a hard-drive copy's patches undone,
        # for the lift and as the updater's disc overlay (scripts/disc_xbe.py).
        xbe_dir = self.build / "pipeline" / "xbe"
        if disc_xbe.main([game, xbe_dir, self.build / "disc_overlay"]) != 0:
            sys.exit(1)
        if self.relift or not (HERE / "src/recomp/gen/recomp_dispatch.c").is_file():
            self.lift(xbe_dir / "default.xbe", self.build / "pipeline", "--project", HERE)
        return self.compile(HERE, self.build / "Release", "rs3_recomp")

    def updater(self) -> Path:
        step("The online updater (the dashboard's update.xbe, from your C: drive)")
        work = self.build / "pipeline_updater"
        xbe = work / "xbe" / "default.xbe"
        copy_if_changed(HERE / "xboxbackup/C/xodash/update.xbe", xbe)
        self.symbols(xbe)
        project = self.toolkit / "titles" / "xodash-update"
        if self.relift or not (project / "src/recomp/gen/recomp_dispatch.c").is_file():
            self.lift(xbe, work, "--project", project)
        return self.compile(project, self.build / "updater", "xodash_update_recomp")

    def update_game(self, installed: Path) -> Path:
        step(f"Title update 0x501 (installed in {installed.parents[3]})")
        work = self.build / "pipeline_tu501"
        xbe = work / "xbe" / "default.xbe"
        if not xbe.is_file() or not filecmp.cmp(installed, xbe, shallow=False):
            copy_if_changed(installed, xbe)
            xbe.with_name("default_xdk_symbols.json").unlink(missing_ok=True)
        self.symbols(xbe)
        if self.relift or not (HERE / "src/recomp/gen_tu501/recomp_dispatch.c").is_file():
            self.lift(xbe, work, "--gen-dir", HERE / "src/recomp/gen_tu501",
                      "--manual", HERE / "src/recomp_manual_tu501.c",
                      "--seeds", HERE / f"config/seeds/{TITLE}_tu501.json")
        return self.compile(HERE, self.build / "Release-tu501", "rs3_tu501_recomp",
                            "-DRS3_TU501=ON")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--relift", action="store_true", help="lift everything again")
    args = ap.parse_args()
    toolkit = Path(os.environ.get("XBOXRECOMP_DIR", HERE.parent / "xboxrecomp")).resolve()
    if not (toolkit / "scripts" / "recompile.py").is_file():
        sys.exit(f"The toolkit is not at {toolkit}: check it out there, or set XBOXRECOMP_DIR.")
    for tool in ("cmake",):
        if not shutil.which(tool):
            sys.exit(f"{tool} is not installed (the toolkit's docs/GETTING_STARTED.md).")

    step("Checking your files")
    if doctor.main([HERE]) != 0:
        return 1
    backup = HERE / "xboxbackup"
    live = (backup / "eeprom.bin").is_file() and (backup / "C/xodash/update.xbe").is_file()

    b = Builder(toolkit, args.relift)
    b.python()
    disc = b.disc_game()
    updater = b.updater() if live else None

    # Title update 0x501, once the updater has installed it on the E: drive.
    e_drive = Path(os.environ.get("RECOMP_HDD_DIR") or setting("hdd_dir") or HERE / "game")
    installed = e_drive / "TDATA" / TITLE / "$u" / "default.xbe"
    update = b.update_game(installed) if installed.is_file() else None

    step("build/play")
    # The executables side by side, so each finds the next by itself: the
    # disc's game hands over to the update's when it is installed, and
    # launches the updater from updater/, whose game folder is your C: drive
    # with the updater as its default.xbe. disc_overlay/ is the disc's
    # default.xbe, which the updater checks before patching it. The game and
    # the backup are found two folders up (game/, xboxbackup/).
    play = b.build / "play"
    install(disc, play)
    if update:
        install(update, play)
    sync_tree(b.build / "disc_overlay", play / "disc_overlay")
    if updater:
        install(updater, play / "updater")
        sync_tree(backup / "C", play / "updater" / "game", skip=("default.xbe",))
        copy_if_changed(backup / "C/xodash/update.xbe", play / "updater/game/default.xbe")

    if live:
        step("Settings")
        set_setting("syslink", "nat",
                    "the game reaches Xbox Live through it. Set it back to play System Link.")

    step("Done")
    print(f"Play: {play / disc.name}")
    if live and not update:
        print("Xbox Live: choose Xbox Live in the game and accept the update; then run\n"
              "this again to build the update's game.")
    elif not live:
        print("Xbox Live: needs your console's backup (python3 scripts/doctor.py).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
