#!/usr/bin/env python3
"""Lift Rainbow Six 3 with Xbox Live as the disc has it.

A copy of the game made to run from a console's hard drive usually carries
three patches in default.xbe, and the patcher keeps the original beside it as
default.bak:

  certificate, allowed media   DVD only -> any media (runs from the HDD)
  0x000A05FA                   jge -> jmp (the media check passes)
  0x0038C6FD                   test al,1; jnz -> four nops

The third is a Live block: the logon (0x0038C6D6) asks for the Ethernet link
and, with the branch gone, always fails with XONLINE_E_LOGON_NO_NETWORK_
CONNECTION (0x80151000), so the game says it cannot connect to Xbox Live
without sending a packet. Scene copies did this so a modified console stayed
off Microsoft's service.

This writes a copy of the XBE for the pipeline to lift, with only that patch
undone, and the analysis and symbol files the pipeline reads beside it. The
game's own files are not touched; the runtime still loads game/default.xbe,
whose code it never runs. An XBE without the patch is copied as it is.

    live_unpatch.py <game dir> <out dir>
"""
import shutil
import struct
import sys
from pathlib import Path

LIVE_VA = 0x0038C6FD
PATCHED = bytes.fromhex("90909090")
ORIGINAL = bytes.fromhex("a801750c")     # test al, 1; jnz +0x0C


def file_offset(xbe: bytes, va: int) -> int:
    base = struct.unpack_from("<I", xbe, 0x104)[0]
    count = struct.unpack_from("<I", xbe, 0x11C)[0]
    headers = struct.unpack_from("<I", xbe, 0x120)[0] - base
    for i in range(count):
        vaddr, vsize, raw, rsize = struct.unpack_from("<IIII", xbe, headers + i * 56 + 4)
        if vaddr <= va < vaddr + min(vsize, rsize):
            return raw + (va - vaddr)
    raise ValueError(f"0x{va:08X} is in no section")


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.strip().splitlines()[-1].strip(), file=sys.stderr)
        return 2
    game, out = Path(sys.argv[1]), Path(sys.argv[2])
    xbe = bytearray((game / "default.xbe").read_bytes())
    off = file_offset(xbe, LIVE_VA)
    here = bytes(xbe[off:off + 4])
    out.mkdir(parents=True, exist_ok=True)

    if here == PATCHED:
        xbe[off:off + 4] = ORIGINAL
        print(f"default.xbe has the Xbox Live block at 0x{LIVE_VA:08X}: "
              "lifting a copy with it undone")
    elif here == ORIGINAL:
        print("default.xbe has no Xbox Live block: lifting it as it is")
    else:
        print(f"default.xbe has unexpected bytes at 0x{LIVE_VA:08X} "
              f"({here.hex(' ')}): lifting it as it is", file=sys.stderr)
    (out / "default.xbe").write_bytes(xbe)

    for name in ("default_analysis.json", "default_xdk_symbols.json"):
        if (game / name).exists():
            shutil.copyfile(game / name, out / name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
