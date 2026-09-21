# scoring — machine doc

| Key | Value |
|---|---|
| Module | `scoring` |
| Version | 19.0.1.0.0 |
| Depends | `base` |
| Models | 7 (3 concrete, 4 abstract) |
| Hosts in this checkout | 1 (`res.partner`; `credit.profile` lives in agromarin and is not counted here) |
| Tests | `tests/test_scorecard.py` |

Every figure here is derived by `factcheck.sh` from the tree; a mismatch is a red, not a
note. `MODEL_MAP.md` holds the models, their fields and the hook contract.

## Hosts

A host inherits `mixin.scored` and ships a `scorecard` record. In this checkout:

- `res.partner` — `partner_scoring`, line `partner.score.line`, scale `partner.tier`

The credit host (`credit.profile`, `account_credit`) and the bridges live in `agromarin` and
are outside this harness's tree.

## Tests

- `test_scorecard.py` — every dimension code resolves to a hook on its host; every offered
  `res_model` is a concrete `mixin.scored`; a dimension band may start below zero and may not
  overlap; one active scorecard per model and company.
