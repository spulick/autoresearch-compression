| Experiment | Description | val_bpb | Delta | Kept?
|------------|-------------|---------|-------|-------|


---

Initial baseline: Uncompressed
- bpb: 8.0000 (baseline)
- Raw size: 10,000,000 bytes
- Compressed size: 10,000,000 bytes (no compression)

The baseline is set to 8.0000 bpb, which is the theoretical ceiling for uncompressed data. We need to find a way to reduce this below 1.0000 bpb.

Current approach: The script currently doesn't implement any compression algorithm. It just returns the raw data as compressed output, which gives us the baseline of 8.0000 bpb.

Our goal is to implement a compression algorithm that can reduce the bpb metric below 1.0000. I'll start by implementing a simple Huffman coding approach that should provide a measurable improvement over the uncompressed baseline.