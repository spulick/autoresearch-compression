import os
import sys
from collections import defaultdict, Counter
from typing import List, Tuple

# Constants
CHUNK = 10 * 1024 * 1024  # 10 MB
CORPUS = 'corpus/enwik9'

# Helper function to get human readable size
def human(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f'{size:.1f} {unit}'
        size /= 1024
    return f'{size:.1f} TB'

# Read the 10MB chunk of enwik9
def read_chunk() -> bytes:
    with open(os.path.join(CORPUS), 'rb') as f:
        raw = f.read(CHUNK)
    return raw

# Statistical model to predict next byte
class BytePredictor:
    def __init__(self, context_size: int = 4):
        self.context_size = context_size
        self.context_counts = defaultdict(Counter)
        self.total_contexts = 0
        self.predictions = []

    def update(self, bytes: bytes) -> None:
        # Update context counts
        for i in range(len(bytes) - self.context_size):
            context = bytes[i:i + self.context_size]
            next_byte = bytes[i + self.context_size]
            self.context_counts[context][next_byte] += 1
            self.total_contexts += 1

    def predict_next_byte(self, bytes: bytes) -> int:
        # Find the most likely next byte
        if len(bytes) < self.context_size:
            return 0  # Default

        context = bytes[-self.context_size:]
        if context in self.context_counts:
            # Return the most frequent byte
            most_common = self.context_counts[context].most_common(1)[0]
            return most_common[0]
        return 0

# Huffman coding implementation
class HuffmanCoder:
    def __init__(self):
        self.codes = {}
        self.reverse_codes = {}

    def build_codes(self, frequencies: List[int]) -> None:
        # Build Huffman tree using a priority queue
        heap = [(freq, i) for i, freq in enumerate(frequencies) if freq > 0]
        heap.sort()

        while len(heap) > 1:
            freq1, idx1 = heap.pop(0)
            freq2, idx2 = heap.pop(0)
            new_freq = freq1 + freq2
            # Create a new node with combined frequency
            new_idx = len(self.codes)
            self.codes[new_idx] = (new_freq, [idx1, idx2])
            heap.append((new_freq, new_idx))
            heap.sort()

        # Extract codes from the tree
        self._build_codes_from_tree(heap[0][1], [])

    def _build_codes_from_tree(self, node_idx: int, current_code: str) -> None:
        if node_idx not in self.codes:
            return

        freq, children = self.codes[node_idx]
        if len(children) == 1:
            # Leaf node
            child_idx = children[0]
            self.codes[child_idx] = (freq, [])
            self.reverse_codes[current_code] = child_idx
            return

        # Internal node
        left_idx = children[0]
        right_idx = children[1]

        # Recursively build codes for left and right
        self._build_codes_from_tree(left_idx, current_code + '0')
        self._build_codes_from_tree(right_idx, current_code + '1')

    def encode(self, bytes: bytes) -> bytes:
        # Encode each byte using the Huffman code
        encoded_bits = []
        for byte in bytes:
            code = self.codes.get(byte, '0')  # Default to '0'
            encoded_bits.extend([int(bit) for bit in code])

        # Convert to bytes
        result = []
        for i in range(0, len(encoded_bits), 8):
            byte_value = 0
            for j in range(8):
                if i + j < len(encoded_bits):
                    byte_value = (byte_value << 1) | encoded_bits[i + j]
            result.append(byte_value)
        return bytes(result)

    def decode(self, bits: bytes) -> bytes:
        # Decode the bits back to bytes
        decoded_bytes = []
        current_code = ''

        for bit in bits:
            current_code += str(bit)
            if current_code in self.reverse_codes:
                byte = self.reverse_codes[current_code]
                decoded_bytes.append(byte)
                current_code = ''

        return bytes(decoded_bytes)

# Main compression function
def compress(raw: bytes) -> Tuple[bytes, float]:
    # Initialize predictors and coder
    predictor = BytePredictor(context_size=4)
    huffman = HuffmanCoder()

    # Build frequency table
    frequencies = [0] * 256
    for byte in raw:
        frequencies[byte] += 1

    # Build Huffman codes
    huffman.build_codes(frequencies)

    # Update predictor with raw data
    predictor.update(raw)

    # Compress using Huffman coding
    compressed_bytes = huffman.encode(raw)

    # Calculate bpb
    bpb = (len(compressed_bytes) * 8) / len(raw)

    return compressed_bytes, bpb

# Main execution
if __name__ == '__main__':
    # Read the 10MB chunk
    raw = read_chunk()

    # Compress the data
    compressed_bytes, bpb_final = compress(raw)

    # Verify correctness
    huffman = HuffmanCoder()
    huffman.build_codes([0] * 256)
    recovered = huffman.decode(compressed_bytes)

    assert recovered == raw, "Decompressed output does not match original"

    # Print results
    print()
    print("=== Size report ===")
    print(f"  Raw sample:        {human(len(raw))}  ({len(raw):,} bytes)")
    print(f"  Compressed:        {human(compressed_bytes)}  ({compressed_bytes:,} bytes)")
    print(f"  Compression ratio: {compressed_bytes/len(raw):.4f}  ({len(raw)/compressed_bytes:.2f}x)")
    print(f"  Bits per byte:     {bpb_final:.4f}")
    print(f"  vs baseline:       {bpb_final - 2.10:+.4f} bpb ({compressed_bytes - int(2.10 * len(raw) / 8):+,} bytes)")
    print(f"  Script size:       {human(os.path.getsize(__file__))}  ({os.path.getsize(__file__):,} bytes)")

    full_size = os.path.getsize(CORPUS)
    projected = int(full_size * compressed_bytes / len(raw))
    print(f"  Full enwik9 size:          {human(full_size)}")
    print(f"  Projected compressed size: {human(projected)}")