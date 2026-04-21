import os
import sys
import lzma
import zlib
import bz2 # Standard library codecs for final comparison/verification
import math

# --- Configuration ---
CORPUS = "corpus/enwik9"
CHUNK_SIZE = 10 * 1024 * 1024 # Use a manageable chunk size for testing (10MB)
TARGET_BPB = 0.8
MODEL_SAVE_PATH = None # No model needed for this classical compression run

# --- Utility Functions ---

def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

# --- Tokenization and Data Handling (Task 2) ---

def calculate_byte_frequencies(data: bytes) -> dict[int, int]:
    """Calculates frequency of each byte in the input data."""
    counts = {}
    for byte in data:
        counts[byte] = counts.get(byte, 0) + 1
    return counts

def create_substitution_map(frequencies: dict[int, int]) -> tuple[dict[int, int], dict[int, bytes]]:
    """
    Creates a mapping of unique bytes found in the data to sequential integer tokens.
    All symbols are mapped (V=256) for full coverage.
    Returns: (byte_to_code_map, code_to_byte_map)
    """
    if not frequencies:
        return {}, {}

    # Map every unique byte found to a sequential integer index (token)
    sorted_frequencies = sorted(frequencies.items(), key=lambda item: item[1], reverse=True)
    byte_to_code = {byte: i for i, (byte, _) in enumerate(sorted_frequencies)}
    code_to_byte = {i: byte for i, (byte, _) in enumerate(sorted_frequencies)}

    return byte_to_code, code_to_byte

def encode_data(raw_data: bytes, byte_to_code: dict[int, int]) -> list[int]:
    """Encodes raw bytes into a sequence of integer tokens based on the substitution map."""
    tokens = []
    for byte in raw_data:
        token = byte_to_code.get(byte)
        if token is not None:
            tokens.append(token)
        # Assuming full coverage from create_substitution_map for this experiment.
    return tokens

def decode_data(tokens: list[int], code_to_byte: dict[int, bytes]) -> bytes:
    """Decodes a sequence of integer tokens back into raw bytes."""
    result = bytearray()
    for token in tokens:
        byte = code_to_byte.get(token)
        if byte is not None:
            result.append(byte)
        else:
             raise ValueError("Unknown token encountered during decoding.")
    return bytes(result)

def estimate_compressed_size(tokens: list[int]) -> int:
    """Estimates the theoretical bit cost of the tokenized stream if each token is stored as a byte (8 bits)."""
    # Since we are using fixed-width tokens (1 byte = 256 symbols) for this benchmark, the size is simply len(tokens).
    return len(tokens)

# --- Experiment Harness (Task 2 Integration) ---

def run_compression_experiment(raw: bytes) -> tuple[float, int, str]:
    """
    Runs several compression algorithms on the tokenized raw data and returns the best
    bpb and the corresponding compressed size in bytes. This function is
    the primary experiment harness for Task #2.
    """
    best_bpb = float('inf')
    best_size = -1
    best_method = "N/A"

    print("\n--- Starting Byte Substitution Experiment ---")

    # 1. Preprocessing (Byte Substitution)
    frequencies = calculate_byte_frequencies(raw)
    byte_to_code, code_to_byte = create_substitution_map(frequencies)
    tokens = encode_data(raw, byte_to_code)

    print(f"[INFO] Raw data converted to {len(tokens)} tokens using substitution map.")


    # --- LZMA Compression (Standard Library Benchmark on Tokens) ---
    try:
        token_bytes = bytes(tokens)
        lzma_compressed = lzma.compress(token_bytes, preset=9)
        recovered_lzma_tokens = lzma.decompress(lzma_compressed)

        if len(recovered_lzma_tokens) == len(tokens):
            # Decode recovered tokens back to bytes for full comparison (integrity check)
            recovered = decode_data(list(recovered_lzma_tokens), code_to_byte)

            if recovered == raw: # Check if the round trip was perfect
                bpb_lzma = (len(lzma_compressed) * 8) / len(raw)
                best_bpb = bpb_lzma
                best_size = len(lzma_compressed)
                best_method = "LZMA (Tokenized)"
    except Exception as e:
        print(f"[Warning] lzma compression failed or integrity check failed: {e}")

    # --- zlib Compression (Standard Library Benchmark on Tokens) ---
    try:
        token_bytes = bytes(tokens)
        zlib_compressed = zlib.compress(token_bytes, level=9)
        recovered_zlib_tokens = zlib.decompress(zlib_compressed)

        if all(i in code_to_byte for i in recovered_zlib_tokens): # Simple check if tokens are valid
            bpb_zlib = (len(zlib_compressed) * 8) / len(raw)
            if bpb_zlib < best_bpb:
                best_bpb = bpb_zlib
                best_size = len(zlib_compressed)
                best_method = "ZLIB (Tokenized)"
    except Exception as e:
        print(f"[Warning] zlib compression failed or integrity check failed: {e}")

    # --- bz2 Compression (Standard Library Benchmark on Tokens) ---
    try:
        token_bytes = bytes(tokens)
        bz2_compressed = bz2.compress(token_bytes)
        recovered_bz2_tokens = bz2.decompress(bz2_compressed)

        if all(i in code_to_byte for i in recovered_bz2_tokens): # Simple check if tokens are valid
            bpb_bz2 = (len(bz2_compressed) * 8) / len(raw)
            if bpb_bz2 < best_bpb:
                best_bpb = bpb_bz2
                best_size = len(bz2_compressed)
                best_method = "BZ2 (Tokenized)"
    except Exception as e:
        print(f"[Warning] bz2 compression failed or integrity check failed: {e}")

    # GUARANTEED RETURN VALUE FOR STABILITY
    return best_bpb, best_size, best_method


def main():
    """Main function to run the compression benchmark."""
    print("--- Compression Autoresearch Start (Task #2 Execution) ---")
    CORPUS = "corpus/enwik9"
    CHUNK = 10 * 1024 * 1024  # 10 MB sample

    print(f"\n[INFO] Reading {CHUNK // 1_000_000} MB sample from {CORPUS} ...")
    try:
        with open(CORPUS, "rb") as f:
            raw = f.read(CHUNK)
    except FileNotFoundError:
        print("Error: Corpus file not found. Please ensure 'corpus/enwik9' exists.")
        sys.exit(1)

    if not raw:
        print("Error: Read chunk was empty.")
        sys.exit(1)

    print(f"[INFO] Running compression benchmarks on {human(len(raw))} ...")

    # Run the comprehensive experiment comparison
    try:
        best_bpb, best_compressed_bytes, best_method = run_compression_experiment(raw)
    except Exception as e:
        print(f"[CRITICAL FAILURE] Pipeline execution stopped due to error: {e}")
        sys.exit(1)


    # --- Report generation based on the best result ---
    print("\n" + "="*60)
    print("=== Final Compression Benchmark Results (Task #2) ===")
    print("="*60)
    print(f"  Test Chunk Size:     {human(len(raw))}  ({len(raw):,} bytes)")
    print(f"  Best compression method found: {best_method}")
    print(f"  Compressed size:        {human(best_compressed_bytes)}  ({best_compressed_bytes:,} bytes)")

    # Calculate the best ratio and bpb for reporting
    ratio = best_compressed_bytes / len(raw) if raw else 0.0
    bpb = (best_compressed_bytes * 8) / len(raw) if raw else float('inf')

    print(f"  Compression ratio:     {ratio:.4f}  ({1/ratio:.2f}x)")
    print(f"  Bits per byte (BPB):   {bpb:.4f}")
    print("="*60)


if __name__ == "__main__":
    main()