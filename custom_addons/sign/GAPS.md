# Kore sign - Known Gaps

## STUB-001 - `sign.request._get_final_document`
- Scope: Final signed PDF assembly and visual field flattening.
- Reason: Full PDF rendering/merging and cryptographic stamp pipeline are
  outside this Tier 2 substitute scope.
- Current behavior: logs warning and returns the template attachment binary
  when available.
- Safety: method is deterministic and non-raising.

STUB entries required: 1
STUB entries present: 1

