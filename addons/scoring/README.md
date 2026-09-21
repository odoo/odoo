# scoring

The scoring engine every scored model stands on. A **scorecard** scores the records of one
model on **dimensions**; a dimension turns an observation into **points against a ceiling**;
the normalized total is `score` on the subject; a **scale** of bands classifies it. The
engine only evaluates -- which dimensions exist, what they weigh and where the bands lie is
data (`scorecard`, `scorecard.dimension`, `scorecard.dimension.band`).

Hosts today: `res.partner` (`partner_scoring`, tiers) and `credit.profile` (`account_credit`,
grades). Specializations add dimensions as records plus hooks: `agro_partner_scoring`,
`account_credit_partner_scoring`, `partner_relationship_credit`.

## The host contract

A host is a model that inherits `mixin.scored` and declares:

| What | Where |
|---|---|
| `_score_line_model = "<host>.score.line"` | a concrete `mixin.score.line` with `subject_id` (Many2one to the host, `ondelete="cascade"`) |
| `score_line_ids` | One2many to that line through `subject_id`; `score_line_count` if the form wants it |
| one `scorecard` record | `res_model` = the host, `company_id` empty for the shared one; `scorecard._for(model, company)` resolves the company's own first |
| `_score_classification_fields()` | the stored computes that derive from `score` through a scale (`tier_id`, `grade_proposed_id`); the refresh and the reclassification wave recompute them |
| `_score_trigger_fields()` | host fields whose write rescores; extend with `super()`, never assign a class tuple |
| `_score_company()` | the subject's company; the mixin reads `company_id` when the host has one |

A dimension of code `x` is answered on the host by, in this order of precedence:

| Hook | Kind | Returns |
|---|---|---|
| `_score_rows_x(dimension, ceiling)` | any | the rows themselves, when neither shape below fits (agro's `crop`, `size`) |
| `_score_observe_x(dimension)` | measure | a number, or `None` for "nothing to measure" |
| `_score_observe_x(dimension)` | catalog | the subject's attribute lines; the engine applies the catalog's ceiling and aggregation |
| `_score_ceiling_x(dimension)` | catalog | the ceiling, once per refresh wave; default `catalog_model._score_ceilings([])` |
| `_score_bands_x(dimension)` | measure | the bands, when they live outside `dimension.band_ids` (any `mixin.band` with `points`) |
| `_score_labels_x(keys)` | any | reader-language labels for the rows' `source_key`s |
| `_score_row_note(dimension, source_key, applied, applicable)` | any | the row's note |

A code is registered with `selection_add` on `scorecard.dimension.code`; the engine's own test
walks every dimension record and refuses one whose host answers no hook.

## The arithmetic

Catalog row: `points = value.score_value`, `max_points` = the attribute's ceiling,
`grouping_key = "<code>:<attribute>"`, `applied` by the attribute's aggregation mode.
Measured row: the observation is rounded to `dimension.precision`, banded (half-open,
`[min_value, max_value)`, the last band open at `max_value = 0`, the first one below zero when
`_band_allow_negative` says so), `points = band.points / 100 × dimension.weight`,
`max_points = dimension.weight`, `grouping_key = "<code>"`.

`score = Σ applied points / Σ max_points over distinct applicable groups × 100`, clamped. The
denominator counts each group once, however many rows it has. `missing = zero` keeps a
dimension in the denominator with a zero row; `missing = skip` drops it (`applicable = False`).

A weighted mean Σ(w·p)/Σw of 0–100 points is this formula with every dimension `skip`; a
ceiling-normalized sum is this formula with every dimension `zero`.

## Refresh

`_score_refresh()` is an `ir.job` on channel `scoring.refresh`: one ceiling per dimension per
wave, rows reconciled by (`subject_id`, `dimension_id`, `source_key`) so ids survive,
`score_date` stamped by SQL so `write_date` stays the last real edit. `_delay_score_refresh()`
queues batches of 200 under a deduplicating identity key. A catalog edit
(`mixin.score.catalog`) reaches the dimensions that read it; a dimension, band or scorecard
edit reaches its subjects; a scale edit (`mixin.score.scale`) queues `_score_reclassify()`, rows
untouched.

## Migrating a host onto the engine

Two rules, both learnt on the production copy: a new stored compute is filled at load, *before*
a post-migrate has populated the columns it reads, so an end-migrate recomputes; and an
upper-inclusive band converts to half-open exactly only when the observation is rounded to a
declared precision (`(a, b]` → `[a + step, b + step)`).
