#!/usr/bin/env python3
"""Check what you supplied: the game's files, and your console's backup.

    doctor.py [<repo>]

Says what each file is for, what is missing and what that costs. Nothing is
changed, and nothing from the backup is printed: it identifies your console.
Exits 1 only when the game itself cannot be built.

  game/                     the disc's files (a hard-drive copy will do)
  xboxbackup/eeprom.bin     the console's EEPROM          } Xbox Live
  xboxbackup/hddinfo.txt    its hard disk's key and serial }
  xboxbackup/disk.bin       its accounts (the disk's first 512 KB)
  xboxbackup/C/             its C: drive; C/xodash/update.xbe is the online
                            updater, which installs the title update
"""
import hashlib
import struct
import sys
from pathlib import Path

TITLE_ID = 0x55530013
UPDATER_TITLE_ID = 0xFFFE0000
# The 5960 dashboard's update.xbe, the updater this project is checked with.
UPDATER_SHA1 = "28e1634969edfd307c241979aef5aef1bdc6a5d4"


def title_id(xbe: Path):
    try:
        with xbe.open("rb") as f:
            head = f.read(0x1000)
        if head[:4] != b"XBEH":
            return None
        base = struct.unpack_from("<I", head, 0x104)[0]
        cert = struct.unpack_from("<I", head, 0x118)[0] - base
        with xbe.open("rb") as f:
            f.seek(cert + 8)
            return struct.unpack("<I", f.read(4))[0]
    except (OSError, struct.error):
        return None


def sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class Report:
    def __init__(self):
        self.fatal = False

    def ok(self, what):
        print(f"  ok       {what}")

    def missing(self, what, cost):
        print(f"  missing  {what}\n           {cost}")

    def problem(self, what, cost, fatal=False):
        print(f"  PROBLEM  {what}\n           {cost}")
        self.fatal |= fatal


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else [str(a) for a in argv]
    repo = Path(argv[0]) if argv else Path(__file__).resolve().parent.parent
    game, backup = repo / "game", repo / "xboxbackup"
    r = Report()

    print("The game (game/):")
    xbe = game / "default.xbe"
    if not xbe.is_file():
        r.problem("game/default.xbe", "copy the disc's files into game/ (README.md)", fatal=True)
    elif title_id(xbe) != TITLE_ID:
        r.problem("game/default.xbe is not Rainbow Six 3's", "check game/ holds this game", fatal=True)
    else:
        r.ok("default.xbe, Rainbow Six 3 (55530013)")
        if not (game / "default_xdk_symbols.json").is_file():
            print("           its XDK symbols will be made by scripts/build.py")

    print("Your console's backup (xboxbackup/), for Xbox Live:")
    live = True
    eeprom = backup / "eeprom.bin"
    if not eeprom.is_file():
        r.missing("eeprom.bin", "no Xbox Live: the console's identity (docs/xbox-live.md)")
        live = False
    elif eeprom.stat().st_size != 256:
        r.problem(f"eeprom.bin is {eeprom.stat().st_size} bytes, not 256",
                  "back it up again; Xbox Live will refuse this one")
        live = False
    else:
        r.ok("eeprom.bin")
    for name, cost in (("hddinfo.txt", "no Xbox Live: the hard disk's key and serial"),
                       ("disk.bin", "no Xbox Live: the console's accounts")):
        if (backup / name).is_file():
            r.ok(name)
        else:
            r.missing(name, cost)
            live = False

    print("Its C: drive (xboxbackup/C/), for the title update:")
    update = backup / "C" / "xodash" / "update.xbe"
    if not update.is_file():
        r.missing("C/xodash/update.xbe",
                  "no title update, and Xbox Live needs it: copy the console's whole C: "
                  "drive into xboxbackup/C (docs/xbox-live.md)")
        live = False
    elif title_id(update) != UPDATER_TITLE_ID:
        r.problem("C/xodash/update.xbe is not the dashboard's online updater",
                  "copy C:\\xodash again")
        live = False
    else:
        r.ok("C/xodash/update.xbe, the online updater")
        if sha1(update) != UPDATER_SHA1:
            print("           not the 5960 dashboard's, which this was checked with: "
                  "it may not work")
        for part in ("fonts", "xodash/media"):
            if not (backup / "C" / part).is_dir():
                r.missing(f"C/{part}", "the updater's screens need it: copy the whole C: drive")

    print()
    if r.fatal:
        print("The game cannot be built until the problems above are fixed.")
        return 1
    print("Xbox Live: ready." if live else
          "Xbox Live: not yet (above); the game builds and plays offline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
