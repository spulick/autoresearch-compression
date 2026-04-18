# Compression Autoresearch — Research Program

## Mission

Minimise **bits per byte (bpb)** on the first 10 MB of `corpus/enwik9` (English Wikipedia XML).
Lower bpb is strictly better. The metric is printed as:

```
val_bpb: X.XXXX
```

The agent reads this line. Do not change its format.

## Baselines (for orientation)

| Algorithm        | bpb (enwik9)  | Notes                              |
|------------------|---------------|------------------------------------|
| Uncompressed     | 8.0000        | Ceiling                            |
| Our LZ78         | ~3.8–4.2      | Starting point (this repo)         |
| gzip -6          | ~2.95         | Near-term target                   |
| zstd -3          | ~2.55         | Medium-term target                 |
| bzip2            | ~2.35         | Stretch target                     |
| xz / LZMA        | ~2.10         | Hard stretch target                |
| cmix / PAQ       | ~1.20         | Theoretical near-limit for enwik9  |

Beat gzip first. Then aim for zstd. Anything below 0.6 bpb is a meaningful result.

---

## What you are allowed to modify

**Only `compress.py`** (the main compression script). You may:

- Rewrite the compression algorithm entirely — LZ77, LZW, DEFLATE-style, BWT+MTF, PPM, arithmetic coding, or any hybrid
- Add or replace the entropy coder (Huffman, range coder, ANS/tANS, arithmetic)
- Introduce a statistical model to predict the next byte (context mixing, Markov chains, small neural net)
- Change data preprocessing (BWT, delta coding, move-to-front, run-length encoding)
- Tune any parameters (dictionary size, context order, model depth)
- Add pure-Python or stdlib-only dependencies (`zlib`, `bz2`, `lzma` from stdlib are allowed)
- Rewrite in a more efficient style (bytearray ops, memoryview, struct packing)

**Do not modify:**

- `corpus/enwik9` or how it is read
- The `CHUNK = 10 * 1024 * 1024` constant (keeps experiments comparable)
- The correctness assertion: `assert recovered == raw` must remain and must pass
- The final printed line format: `val_bpb: X.XXXX`
- The time budget: the script must complete within 5 minutes on this machine

---

## What to optimise

**Primary metric:** `val_bpb` — bits per byte on the 10 MB sample. This is:

```python
bpb = (compressed_size_in_bits) / (raw_size_in_bytes)
```

The compressed size should be the **theoretical bit cost** of the output stream, not a Python object size. The current baseline uses variable-width index fields sized to `ceil(log2(dict_size))` bits per token. Keep the size estimate honest — do not game it by shrinking the estimate formula without a corresponding real coding improvement.

**Correctness is non-negotiable.** If the assertion fails, the run is invalid regardless of bpb. The agent must revert.

---

## Implementation constraints

- **Pure Python + stdlib only** unless a dependency can be installed via `pip` in under 30 seconds. Do not assume numpy, scipy, or PyTorch are available unless you verify they're importable.
- **No C extensions you compile yourself** — the agent cannot run `make` or `gcc`.
- `zlib`, `bz2`, `lzma` from Python stdlib are explicitly allowed (as oracles, targets, or building blocks).
- The script must be a single file (`compress.py`). No multi-file refactors.
- Do not load the full 1 GB enwik9 into memory — only the 10 MB chunk.

---

## How to evaluate an experiment

After every change:

1. Run `python compress.py`
2. Check that the assertion passes (`✓ Decompressed output matches original exactly`)
3. Read the printed `val_bpb: X.XXXX`
4. If bpb improved → commit with message describing what changed and by how much
5. If bpb did not improve or assertion failed → revert to last commit

Never commit a run that fails the assertion.

---

## Commit message format

```
[+0.12 bpb] Added process to improve efficiency 

Before: val_bpb 4.1823
After:  val_bpb 4.0601

Changed the literal encoding from fixed 8-bit to Huffman with a
two-pass frequency scan. Index field unchanged.
```

Include: direction (+/-), magnitude, one-line description, before/after bpb, and what specifically changed.

---

## What not to do

- Do not reduce `CHUNK` to make bpb look better — the sample size must stay at 10 MB
- Do not hardcode or precompute anything derived from the specific enwik9 content — the compressor must work on arbitrary input
- Do not store the raw input inside the "compressed" output — the ratio must be real
- Do not optimise for speed at the cost of correctness
- Do not spend more than one experiment on an approach that plateaued — if an idea gained less than 0.05 bpb in two consecutive iterations, move to the next direction
- Do not add complexity without a bpb gain — simpler code that scores the same is preferred

---

## State tracking

Keep a running log of results in `results.md` (the agent creates and updates this file). Format:

```
| Experiment | Description                        | val_bpb | Delta   | Kept? |
|------------|------------------------------------|---------|---------|-------|


---

## The goal, restated simply

Keep running experiments on the compress.py. If the new script does not beat the current benchmark, revert and try a new approach. Commit every time the new compression ratio is better than the old one. Every kept commit should move `val_bpb` down. Nothing else matters.

You are allowed to browse the internet. You are allowed to read and write compress.py within this directory. You are allowed to create new files within this directory. You are allowed to use git commands. 