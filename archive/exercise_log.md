# Compression Autoresearch — Experiment Log

## Setup

- **Repo**: `autoresearch-compression` on `master` branch
- **Corpus**: 1 GB `corpus/enwik9` (English Wikipedia XML), using first 10 MB
- **Constraints**: Pure Python + stdlib only, single file (`compress.py`), 5-minute time limit
- **Metric**: `val_bpb` — bits per byte, printed as `val_bpb: X.XXXX`
- **Correctness**: `assert recovered == raw` must pass

## Baseline

| Algorithm | bpb | Notes |
|-----------|-----|-------|
| Uncompressed | 8.0000 | Ceiling |
| LZMA preset=9 (raw) | **2.1702** | Starting point |
| gzip -6 | ~2.95 | Near-term target |
| zstd -3 | ~2.55 | Medium-term target |
| bzip2 | ~2.35 | Stretch target |
| xz / LZMA | ~2.10 | Hard stretch target |
| cmix / PAQ | ~1.20 | Near-limit for enwik9 |

---

## Experiment 1: BWT + MTF + RLE Pipeline

**Approach**: Burrows-Wheeler Transform on 64KB blocks, followed by Move-to-Front encoding and Run-Length Encoding, then LZMA compression.

**Rationale**: BWT groups similar bytes together, creating long runs that RLE compresses effectively, which in turn helps LZMA achieve better compression.

**Block size selection**: Tested sorting speed:
- 16KB: 0.04s per block
- 32KB: 0.21s per block
- 64KB: 2.34s per block → ~2 min total for 160 blocks
- 128KB: 26.79s per block → ~73 min total (too slow)

**Result**: **FAILED** — Process killed (OOM, exit code 137). Creating cyclic rotations as tuples for 64KB blocks consumed too much memory.

**Lesson**: BWT via full rotation sorting is memory-intensive. Need a more memory-efficient BWT implementation.

---

## Experiment 2: Multi-Step Delta + Freq Remap + RLE + LZMA

**Approach**: Per-block delta encoding (choosing best step per block), frequency remapping, RLE, then LZMA.

**Pipeline**:
1. Multi-step delta: per 4KB block, choose step (1,2,4,8,16,32,64) that produces most zero/small bytes
2. Frequency remapping: map most frequent bytes to 0,1,2,...
3. RLE: group consecutive identical bytes
4. LZMA preset=9

**Result**: **4.1212 bpb** — worse than baseline by **+1.95 bpb**

**Analysis**:
- RLE overhead (2 bytes per run) outweighed compression gains
- Frequency remapping is just a permutation — LZMA's adaptive model undoes it
- Multi-step delta destroyed LZMA's internal match patterns

**Lesson**: Per-byte frequency remapping doesn't help LZMA (it's adaptive). RLE adds overhead without long runs.

---

## Experiment 3: Delta + Freq Remap — Multiple Configurations

**Approach**: Tested 7 configurations in a single run:
- `delta+freq` (all 7 steps)
- `delta+freq (steps 1,4,16)`
- `freq only`
- `delta(1)+freq`
- `delta(4)+freq`
- `delta(16)+freq`
- `raw` (baseline)

**Results**:

| Configuration | bpb | Delta from baseline |
|---------------|-----|---------------------|
| delta(1)+freq | 2.5474 | +0.3772 |
| delta(4)+freq | 3.8526 | +1.6824 |
| delta(16)+freq | 5.9024 | +3.7322 |
| delta+freq (all steps) | 3.8893 | +1.7191 |
| delta+freq (1,4,16) | 3.6495 | +1.4793 |
| freq only | 2.1897 | +0.0195 |
| **raw (baseline)** | **2.1702** | **0.0000** |

**Key findings**:
- Delta encoding **always hurts** LZMA on raw text — it destroys the long-range repetitions LZMA's dictionary matching relies on
- Frequency remapping alone barely changes bpb (2.1897 vs 2.1702) — LZMA's adaptive model compensates
- Larger delta steps make things progressively worse

**Lesson**: Delta encoding is good for data with local similarity (numbers, images), but **bad for text** where LZMA already exploits repetition. The original baseline (raw + LZMA) was already near-optimal for this approach.

---

## Experiment 4: Byte Range Grouping (Irreversible)

**Approach**: Group all bytes by value range into 9 categories, compress as one stream.

**Groups**: ctrl(0-31), punct1(32-47), digit(48-57), punct2(58-64), upper(65-90), punct3(91-96), lower(97-122), punct4(123-128), high(128-255)

**Result**: **2.0934 bpb** (improvement!) but **irreversible** — can't reconstruct original from grouped data.

**Analysis**: Grouping by value range creates lower-entropy sections that compress better. However, the grouping loses positional information — you can't un-group without storing per-byte category tags (too much overhead).

**Lesson**: Value-range grouping improves compression but is lossless only with heavy metadata. Not viable.

---

## Experiment 5: Byte Range Grouping with Block-Level Metadata

**Approach**: Per-block byte range grouping, each group compressed separately with LZMA. Metadata stores group lengths and compressed sizes.

**Result**: **2.6349 bpb** — worse than baseline.

**Analysis**: Per-group LZMA creates many small compressed streams with their own headers, adding overhead. The benefit of lower-entropy groups is outweighed by per-stream LZMA overhead.

**Lesson**: Many small LZMA streams hurt more than they help. One large stream is better.

---

## Experiment 6: Delta Encoding Variants + BWT

**Approach**: Tested delta encoding at various step sizes, plus block-level BWT + MTF + RLE.

### Delta Results:

| Step | bpb | Delta |
|------|-----|-------|
| 0 (raw) | 2.1702 | 0.0000 |
| 1 | 2.5214 | +0.3512 |
| 2 | 2.9652 | +0.7950 |
| 4 | 3.8006 | +1.6304 |
| 8 | 5.0336 | +2.8634 |
| 16 | 5.8448 | +3.6746 |
| 32 | 6.1625 | +3.9923 |

**Finding**: Delta encoding is **monotonically worse** for text compression. Each byte in text depends on its absolute value, not its difference from a neighbor. Delta encoding turns meaningful byte values into meaningless differences.

### BWT Results:

- **BWT + MTF + RLE**: **3.1011 bpb** — worse than baseline
- BWT took ~51 seconds for 160 blocks
- BWT inverse had a bug (off-by-one in loop range) that was fixed

**BWT Bug**: The inverse used `for i in range(n - 1, -1, -1)` instead of `for i in range(n)`. Fixed to forward iteration.

### Combined: BWT + MTF + RLE + Delta(1)

**Result**: Tested but not yet verified.

---

## Key Findings Summary

### What DOESN'T work:

1. **Delta encoding on raw text** — destroys LZMA's match patterns. Every step size tested was worse than raw.
2. **Frequency remapping** — LZMA is adaptive and compensates. Barely changes results.
3. **Per-group byte range grouping** — per-stream LZMA overhead outweighs entropy benefits.
4. **Full BWT via rotation sorting** — memory-intensive, crashed on 64KB blocks.
5. **RLE** — adds 2-byte overhead per run; without long runs, it's net negative.

### What DOES work (baseline):

1. **Raw bytes → LZMA preset=9** — **2.1702 bpb** — the current best result.
2. **Byte range grouping (single stream)** — 2.0934 bpb but **irreversible**.

### Research insights (from web research):

1. **Sub-1.5 bpb requires context mixing** (PPM/PAQ/cmix style) — predicting each byte from its context history with dozens of models. This is the technique cmix uses to achieve ~0.99 bpb on enwik9.
2. **Arithmetic coding** replaces fixed-bit overhead with entropy-optimal encoding — but pure Python arithmetic coding is ~50-100x slower than stdlib lzma.
3. **XML-aware transforms** — replacing frequent XML patterns (`<`, `>`, `class=`, `="`, etc.) with single-byte escapes could help, but must be reversible.
4. **The "bitstream as PRNG outputs" concept** — treating compressed data as a seed to a deterministic PRNG that generates a prior, with corrections encoding the residual. Essentially all good compressors do this implicitly.
5. **enwik9's entropy limit** is estimated at ~1.1-1.3 bpb. PAQ8F/cmix at ~1.29 bpb is near the theoretical limit.

### Why LZMA raw is so good:

- LZMA's internal PPMd literal model already does context mixing
- LZMA's dictionary matching finds long repeated patterns in XML
- No preprocessing overhead — LZMA adapts to the data
- Single large compression stream avoids per-block overhead

---

## Conclusion

After 6 experiments, **the baseline (LZMA preset=9 on raw bytes at 2.1702 bpb) remains the best result**. All attempts to improve it through preprocessing (delta encoding, frequency remapping, BWT, byte range grouping) either:

- Made compression worse (delta encoding, RLE overhead)
- Were irreversible (byte range grouping)
- Were too memory-intensive (full BWT)
- Barely changed results (frequency remapping)

To go below 2.0 bpb, the research points toward:
1. **Context mixing** — implementing a simplified PPMd-like predictor
2. **Arithmetic coding** — replacing LZMA's internal coder with a custom one
3. **XML-aware transforms** — reversible pattern escaping for frequent XML sequences
4. **Hybrid approaches** — combining LZMA with custom prediction models

The 5-minute time constraint makes context mixing impractical in pure Python, but it remains the most promising direction for future work.
