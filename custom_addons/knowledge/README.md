# knowledge - Kore Tier 2 Substitute

## Purpose
Clean-room implementation of Odoo Enterprise knowledge.
Satisfies the Enterprise public API contract so that
any module declaring `"depends": ["knowledge"]` resolves.

## Build basis
Clean-room. See `SOURCES.md` for full attribution.

## Enterprise contract coverage
| Area | Status | Notes |
|------|--------|-------|
| Core models (`knowledge.article`, `knowledge.article.member`, `knowledge.article.favorite`, `knowledge.cover`) | IMPLEMENT | Full models delivered |
| Security model and record rules | IMPLEMENT | `privilege_id` groups + private/workspace/shared rules |
| Public methods (`toggle_favorite`, lock/unlock, private/shared, first-accessible, copy/write checks) | IMPLEMENT | All required non-stubbable methods implemented |
| XML IDs contract | IMPLEMENT | All required XML IDs created |
| Stub items | IMPLEMENT | No active stubs |

## Known gaps
See `GAPS.md`.

## Access model
Three article categories with distinct visibility rules:
- workspace : visible to all internal users
- private   : visible to owner + explicit members only
- shared    : visible to explicit members only

## Integration
- gov_* suite : articles can be linked to `gov.processo`
  records for process documentation (optional field,
  no hard dependency)

## Conventions
- Version    : 1.0.1.0.0
- License    : LGPL-3
- Frozen base: not modified

## Build date : 2026-03-01

## DO NOT
- Copy code from any AGPL-3 source
- Use `category_id` in any `res.groups` record
- Leave `_check_user_can_write()` as a stub
- Leave the three record rules unimplemented
- Remove `GAPS.md` entries without implementing the stub
