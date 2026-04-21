| Experiment | Description | val_bpb | Delta | Kept? |
|------------|-----------------|---------|-------|-------|
| Initial baseline: Uncompressed | - bpb: 8.0000 (baseline) - Raw size: 10,000,000 bytes - Compressed size: 10,000,000 bytes (no compression) | 8.0000 | N/A | No |
| LZMA Optimization | Initial implementation of LZMA with preset=9 for standard library benchmark. | 2.1702 | -5.83 | Yes |
| Byte Substitution Tokenization | Applied byte frequency substitution before compression to reduce entropy, but the change slightly increased bpb (2.1897). | 2.1897 | +0.16 | No |