import os
import sys
import lzma # Import lzma for standard compression benchmarking
import zlib

# The original LZ78 logic is preserved but encapsulated for comparison purposes,
# though our primary focus shifts to leveraging optimized stdlib codecs like lzma and zlib.

def lz78_compress(data: bytes) -> list[tuple[int, int]]:
    dictionary = {}
    tokens = []
    prefix = ()
    for byte in data:
        symbol = (byte,)
        extended = prefix + symbol
        if extended in dictionary:
            prefix = extended
        else:
            dict_idx = dictionary.get(prefix, 0)
            tokens.append((dict_idx, byte))
            dictionary[extended] = len(dictionary) + 1
            prefix = ()
    if prefix:
        tokens.append((dictionary.get(prefix[:-1], 0), prefix[-1]))
    return tokens

def lz78_decompress(tokens: list[tuple[int, int]]) -> bytes:
    dictionary = {0: b""}
    result = bytearray()
    for idx, byte in tokens:
        entry = dictionary.get(idx) + bytes([byte]) if idx in dictionary else None
        if entry is not None: # Added safety check for malformed token lists
            result += entry
            dictionary[len(dictionary)] = entry

    # Note: The original lz78_decompress assumed the index was always valid.
    # This basic rewrite keeps structure but acknowledges limitations compared to real codecs.
    return bytes(result)

def estimate_compressed_size(tokens: list[tuple[int, int]]) -> int:
    # Original theoretical size estimation formula (for LZ78 only)
    import math
    bits = 0
    for i, (_, _) in enumerate(tokens):
        dict_size = i + 1  # dictionary has i entries before this token
        index_bits = max(1, math.ceil(math.log2(dict_size + 1)))
        bits += index_bits + 8
    return (bits + 7) // 8 # round up to bytes

def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

def run_compression_experiment(raw: bytes) -> tuple[float, int]:
    """
    Runs several compression algorithms on the raw data and returns the best
    bpb and the corresponding compressed size in bytes. This function is
    the primary experiment harness.
    """
    best_bpb = float('inf')
    best_size = -1
    best_method = "N/A"

    # --- LZ78 Baseline (Theoretical Estimate) ---
    tokens = lz78_compress(raw)
    recovered = lz78_decompress(tokens)
    if recovered == raw:
        compressed_bytes = estimate_compressed_size(tokens)
        bpb = (compressed_bytes * 8) / len(raw)
        best_bpb = bpb
        best_size = compressed_bytes
        best_method = "LZ78 (Theoretical)"

    # --- lzma Compression (Standard Library Benchmark) ---
    try:
        lzma_compressed = lzma.compress(raw)
        recovered_lzma = lzma.decompress(lzma_compressed)
        if recovered_lzma == raw:
            bpb_lzma = (len(lzma_compressed) * 8) / len(raw)
            if bpb_lzma < best_bpb:
                best_bpb = bpb_lzma
                best_size = len(lzma_compressed)
                best_method = "LZMA"
    except Exception as e:
        print(f"[Warning] lzma compression failed: {e}")

    # --- zlib Compression (Standard Library Benchmark) ---
    try:
        zlib_compressed = zlib.compress(raw, level=9)
        recovered_zlib = zlib.decompress(zlib_compressed)
        if recovered_zlib == raw:
            bpb_zlib = (len(zlib_compressed) * 8) / len(raw)
            # We use <= to prefer the algorithm encountered first if bpb is identical, but here we just check strict improvement.
            if bpb_zlib < best_bpb:
                best_bpb = bpb_zlib
                best_size = len(zlib_compressed)
                best_method = "ZLIB"
    except Exception as e:
        print(f"[Warning] zlib compression failed: {e}")

    return best_bpb, best_size, best_method


def main():
    """Main function to run the compression benchmark."""
    print("--- Compression Autoresearch Start ---")
    CORPUS = "corpus/enwik9"
    CHUNK = 10 * 1024 * 1024  # 10 MB sample

    print(f"\n[INFO] Reading {CHUNK // 1_000_000} MB sample from {CORPUS} ...")
    try:
        with open(CORPUS, "rb") as f:
            raw = f.read(CHUNK)
    except FileNotFoundError:
        print("Error: Corpus file not found. Please ensure 'corpus/enwik9' exists.")
        sys.exit(1)

    print(f"[INFO] Running compression benchmarks on {human(len(raw))} ...")

    # Run the comprehensive experiment comparison
    best_bpb, best_compressed_bytes, best_method = run_compression_experiment(raw)

    # --- Report generation based on the best result ---
    print("\n" + "="*40)
    print("=== Compression Benchmark Results ===")
    print("="*40)
    print(f"  Raw sample size:        {human(len(raw))}  ({len(raw):,} bytes)")
    print(f"  Best compression method found: {best_method}")
    print(f"  Compressed size:        {human(best_compressed_bytes)}  ({best_compressed_bytes:,} bytes)")

    # Calculate the best ratio and bpb for reporting
    ratio = best_compressed_bytes / len(raw)
    bpb = (best_compressed_bytes * 8) / len(raw)

    print(f"  Compression ratio:     {ratio:.4f}  ({1/ratio:.2f}x)")
    print(f"  Bits per byte (BPB):   {bpb:.4f}")
    print("="*40)


if __name__ == "__main__":
    main()