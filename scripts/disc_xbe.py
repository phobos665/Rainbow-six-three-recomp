#!/usr/bin/env python3
"""Rainbow Six 3's default.xbe as the disc has it.

A copy of the game made to run from a console's hard drive usually carries
three patches in default.xbe, and the patcher keeps the original beside it as
default.bak:

  certificate, allowed media   DVD only -> any media (runs from the HDD)
  0x000A05FA                   jge -> jmp (XapiInitProcess's DVD check passes)
  0x0038C6FD                   test al,1; jnz -> four nops

The third is a Live block: the logon (0x0038C6D6) asks for the Ethernet link
and, with the branch gone, always fails with XONLINE_E_LOGON_NO_NETWORK_
CONNECTION (0x80151000), so the game says it cannot connect to Xbox Live
without sending a packet. Scene copies did this so a modified console stayed
off Microsoft's service. The DVD check needs no patch here: the runtime
answers it as the drive does.

Those are the only differences, so undoing all three gives back the disc's
file byte for byte, whether or not default.bak is still there. This writes it
twice:

  <out dir>/default.xbe       for the pipeline to lift, with the analysis and
                              symbol files the pipeline reads beside it
  <overlay dir>/default.xbe   the disc overlay (disc_overlay): the online
                              updater checks D:\\default.xbe against the disc's
                              before it patches it

The game's own files are not touched; the runtime still loads
game/default.xbe, whose code it never runs.

    disc_xbe.py <game dir> <out dir> [<overlay dir>]
"""
import hashlib
import shutil
import struct
import sys
from pathlib import Path

# SHA-1 of the disc's default.xbe (NTSC/PAL, the one update 0x501 patches).
DISC_SHA1 = "a232aa535391d53ea01ace0df17f801ee03c57f6"
TITLE_ID = 0x55530013

MEDIA_DISC = 0x00000002                     # XBEIMAGE_MEDIA_TYPE_DVD_X2
# (virtual address, as the disc has it, as a hard-drive copy has it)
CODE_PATCHES = [
    (0x000A05FA, bytes.fromhex("7d"), bytes.fromhex("eb")),
    (0x0038C6FD, bytes.fromhex("a801750c"), bytes.fromhex("90909090")),
]


def file_offset(xbe: bytes, va: int) -> int:
    base = struct.unpack_from("<I", xbe, 0x104)[0]
    count = struct.unpack_from("<I", xbe, 0x11C)[0]
    headers = struct.unpack_from("<I", xbe, 0x120)[0] - base
    for i in range(count):
        vaddr, vsize, raw, rsize = struct.unpack_from("<IIII", xbe, headers + i * 56 + 4)
        if vaddr <= va < vaddr + min(vsize, rsize):
            return raw + (va - vaddr)
    raise ValueError(f"0x{va:08X} is in no section")


def certificate(xbe: bytes) -> int:
    base = struct.unpack_from("<I", xbe, 0x104)[0]
    return struct.unpack_from("<I", xbe, 0x118)[0] - base


def restore(xbe: bytearray) -> list:
    """Undo the hard-drive patches in place; returns what was undone."""
    undone = []
    media = certificate(xbe) + 0x9C
    if struct.unpack_from("<I", xbe, media)[0] != MEDIA_DISC:
        struct.pack_into("<I", xbe, media, MEDIA_DISC)
        undone.append("allowed media")
    for va, disc, hdd in CODE_PATCHES:
        off = file_offset(xbe, va)
        if bytes(xbe[off:off + len(hdd)]) == hdd:
            xbe[off:off + len(disc)] = disc
            undone.append(f"0x{va:08X}")
    return undone


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else [str(a) for a in argv]
    if len(argv) not in (2, 3):
        print(__doc__.strip().splitlines()[-1].strip(), file=sys.stderr)
        return 2
    game, out = Path(argv[0]), Path(argv[1])
    overlay = Path(argv[2]) if len(argv) == 3 else None

    xbe = bytearray((game / "default.xbe").read_bytes())
    if struct.unpack_from("<I", xbe, certificate(xbe) + 8)[0] != TITLE_ID:
        print("game/default.xbe is not Rainbow Six 3's", file=sys.stderr)
        return 1
    undone = restore(xbe)
    if undone:
        print("default.xbe is a hard-drive copy's: lifting the disc's, with "
              + ", ".join(undone) + " undone")
    sha1 = hashlib.sha1(xbe).hexdigest()
    if sha1 != DISC_SHA1:
        # Another release, or patched some other way: lift it, but the online
        # updater will refuse it as the disc's.
        print(f"default.xbe (restored) is not the disc's file this was made for "
              f"(SHA-1 {sha1}): lifting it as it is; the online update may not "
              "install", file=sys.stderr)

    out.mkdir(parents=True, exist_ok=True)
    (out / "default.xbe").write_bytes(xbe)
    for name in ("default_analysis.json", "default_xdk_symbols.json"):
        if (game / name).exists():
            shutil.copyfile(game / name, out / name)

    if overlay is not None:
        overlay.mkdir(parents=True, exist_ok=True)
        (overlay / "default.xbe").write_bytes(xbe)
        print(f"disc overlay: {overlay} (disc_overlay)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
