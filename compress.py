"""
Autoresearch compression — Experiment 1: LZMA (stdlib lzma) with tuned compression
Uses Python stdlib lzma which implements LZMA2 algorithm.
This is a strong baseline to beat from.
Usage: uv run compress.py
"""

import os
import sys
import lzma
import math

def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

CORPUS = "corpus/enwik9"
CHUNK = 10 * 1024 * 1024  # 10 MB sample

print(f"Reading {CHUNK // 1_000_000} MB sample from {CORPUS} ...")
with open(CORPUS, "rb") as f:
    raw = f.read(CHUNK)

print(f"Compressing {human(len(raw))} ...")

# Compress with lzma
# Preset levels: 0-9, where 9 is maximum compression
# FORM_RAW for raw stream (no header overhead)
compressed = lzma.compress(raw, preset=9)

print("Decompressing ...")
recovered = lzma.decompress(compressed)
assert recovered == raw, "MISMATCH: decompressed output differs from original!"
print("✓ Decompressed output matches original exactly.")

compressed_bytes = len(compressed)
bpb = (compressed_bytes * 8) / len(raw)

print()
print("=== Size report ===")
print(f"  Raw sample:        {human(len(raw))}  ({len(raw):,} bytes)")
print(f"  Compressed:        {human(compressed_bytes)}  ({compressed_bytes:,} bytes)")
print(f"  Compression ratio: {compressed_bytes/len(raw):.4f}  ({len(raw)/compressed_bytes:.2f}x)")
print(f"  Bits per byte:     {bpb:.4f}")
print(f"  Script size:       {human(os.path.getsize(__file__))}  ({os.path.getsize(__file__):,} bytes)")
print()

full_size = os.path.getsize(CORPUS)
projected = int(full_size * compressed_bytes / len(raw))
print(f"  Full enwik9 size:          {human(full_size)}")
print(f"  Projected compressed size: {human(projected)}  (extrapolated from sample ratio)")
