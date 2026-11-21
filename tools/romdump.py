#!/usr/bin/env python3
"""Dump a ROM through the ATmega128 RomReader firmware (USART1, 38400 8N1).

Example:
    python tools/romdump.py -p COM11 -t 2764 -o rom/HART/U45_CD8.bin
    python tools/romdump.py -p COM11 -t 129  -o rom/HART/U50_1.bin
    python tools/romdump.py -p COM11 -t 123  -o rom/HART/U5_82S123.bin

The board must run the firmware built for that chip (RomReader_<chip>.hex);
the script checks this before reading. The chip is read --reads times
(default 2). The file is written only when every read is identical and the
firmware reported no unstable address.
"""
import argparse
import hashlib
import os
import sys
import time

import serial

SIZES = {"2764": 8192, "129": 256, "123": 32}
ALIASES = {"2764": "2764", "82s129": "129", "129": "129", "82s126": "129",
           "126": "129", "82s123": "123", "123": "123"}
NAMES = {"2764": "2764", "129": "82S129", "123": "82S123"}   # firmware names


def wait_prompt(ser, timeout=3.0):
    """Read until the ']> ' prompt; return the text before it."""
    buf = b""
    end = time.time() + timeout
    while time.time() < end:
        chunk = ser.read(ser.in_waiting or 1)
        if chunk:
            buf += chunk
            end = time.time() + timeout
            if buf.endswith(b"]> "):
                return buf.decode("ascii", "replace")
    raise TimeoutError("no prompt from board. Check COM port, 38400 baud, "
                       "TX/RX wiring and that a RomReader_<chip>.hex is flashed.\n"
                       f"received: {buf[-200:]!r}")


def command(ser, line, timeout=3.0):
    ser.write(line.encode("ascii") + b"\r")
    return wait_prompt(ser, timeout)


def parse_ihex(text, size):
    data = bytearray(size)
    seen = [False] * size
    status = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#"):
            status.append(line)
            continue
        if not line.startswith(":"):
            continue
        rec = bytes.fromhex(line[1:])
        if sum(rec) & 0xFF:
            raise ValueError(f"bad checksum: {line}")
        n, addr, typ = rec[0], (rec[1] << 8) | rec[2], rec[3]
        if typ != 0:          # EOF record; status lines still follow
            continue
        for i in range(n):
            data[addr + i] = rec[4 + i]
            seen[addr + i] = True
    if not all(seen):
        raise ValueError(f"incomplete dump: {seen.count(False)} bytes missing")
    return bytes(data), status


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-p", "--port", required=True, help="FT232 port, e.g. COM11")
    ap.add_argument("-t", "--type", required=True, help="2764, 129 (82S129/82S126), 123 (82S123)")
    ap.add_argument("-o", "--out", required=True, help="output .bin")
    ap.add_argument("-n", "--reads", type=int, default=2, help="full reads to compare (default 2)")
    ap.add_argument("-b", "--baud", type=int, default=38400)
    ap.add_argument("--force", action="store_true", help="overwrite an existing file")
    args = ap.parse_args()

    kind = ALIASES.get(args.type.lower())
    if not kind:
        ap.error("type must be 2764, 129 or 123")
    size = SIZES[kind]
    if os.path.exists(args.out) and not args.force:
        ap.error(f"{args.out} exists, use --force")

    with serial.Serial(args.port, args.baud, timeout=0.1) as ser:
        ser.reset_input_buffer()
        # The firmware ignores an empty line (no new prompt), so sync with a
        # harmless command instead of a bare CR.
        ser.write(b"info\r")
        wait_prompt(ser)

        # The chip type is fixed in the firmware; refuse if the flashed one
        # does not match -t (the ZIF wiring is for one chip type).
        reply = command(ser, "info")
        flashed = next((n for n in NAMES.values() if f"{n} size=" in reply), None)
        if flashed != NAMES[kind]:
            sys.exit(f"board runs the {flashed or 'unknown'} firmware but -t is "
                     f"{NAMES[kind]}. Flash RomReader_{NAMES[kind]}.hex and wire the "
                     "ZIF for that chip first. Nothing read.")

        print(command(ser, "check").strip().rsplit("\n", 1)[0])

        dumps = []
        for i in range(args.reads):
            t0 = time.time()
            text = command(ser, "dump", timeout=5.0)
            data, status = parse_ihex(text, size)
            for s in status:
                print(f"  read {i + 1}: {s}")
            if any(s.startswith("# UNSTABLE") and s != "# UNSTABLE 0" for s in status):
                sys.exit("unstable bits: reseat the chip and check wires. Nothing written.")
            print(f"  read {i + 1}: {len(data)} bytes, {time.time() - t0:.1f} s, "
                  f"SHA-1 {hashlib.sha1(data).hexdigest()}")
            dumps.append(data)

    first = dumps[0]
    for i, d in enumerate(dumps[1:], start=2):
        if d != first:
            diff = [a for a in range(size) if d[a] != first[a]]
            sys.exit(f"read 1 and read {i} differ at {len(diff)} addresses "
                     f"(first 0x{diff[0]:04X}). Nothing written.")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "wb") as f:
        f.write(first)
    print(f"wrote {args.out}: {size} bytes, SHA-1 {hashlib.sha1(first).hexdigest()}, "
          f"{len(dumps)} reads match")


if __name__ == "__main__":
    main()
