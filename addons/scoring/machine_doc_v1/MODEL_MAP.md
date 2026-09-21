# scoring — models

## scorecard

`models/scorecard.py`. One scale of weights for one host model, optionally per company.

**Fields:** `res_model` (Selection from the registry: every concrete `mixin.scored`), `company_id`
(empty = shared), `dimension_ids`, `max_points` (computed live: Σ of the active dimensions'
ceilings). `name` and `active` come from `mixin.catalog`.

**Key methods:** `_for(res_model, company)` (the company's own scorecard first, then the shared
one, as superuser), `_selection_res_model()`, `_host_models()`, `_notify_catalog_changed(models)`
(invalidates the live ceilings, queues the subjects of every dimension reading those catalogs),
`_notify_scorecard_changed()`, `_invalidate_line_labels()`, `_check_one_per_scope`.

## scorecard.dimension

`models/scorecard_dimension.py`. One thing the subject is scored on.

**Fields:** `scorecard_id`, `res_model` (related), `code` (Selection, `selection_add` per
module), `name` (precomputed from the code's label, translatable), `kind` (`catalog` /
`measure`), `catalog_model`, `sequence`, `active`, `weight`, `missing` (`zero` / `skip`),
`precision`, `band_ids`, `max_points` (computed: the weight, or the catalog's total through
the host's `_score_ceiling`).

**Key methods:** `_score_band_labels_for(keys)`, `_notify_dimension_changed()`, `_check_shape`.

## scorecard.dimension.band

`models/scorecard_dimension_band.py`. `mixin.band` with `points`; `_band_allow_negative = True`.

**Fields:** `dimension_id`, `points` (0–100, a share of the dimension's weight); `min_value`,
`max_value`, `active` from `mixin.band`.

## mixin.scored

`models/mixin_scored.py`. The subject.

**Fields:** `score`, `score_points`, `score_max_points` (stored computes over the lines),
`score_date`, `scorecard_id` (computed for the subject's company).

**Hook contract** (resolved by dimension code): `_score_observe_<code>`, `_score_ceiling_<code>`,
`_score_bands_<code>`, `_score_rows_<code>`, `_score_labels_<code>`; `_score_row_note`,
`_score_trigger_fields`, `_score_company`, `_score_classification_fields`.

**Engine methods:** `_score_refresh` (job), `_score_ceiling`, `_score_rows`,
`_prepare_measure_score_rows`, `_prepare_attribute_score_rows`, `_prepare_score_row`,
`_delay_score_refresh`, `_score_job_identity_key`, `_score_reclassify` (job),
`_score_notify_scorecard_changed`, `_score_notify_scale_changed`, `_get_score_max_points`,
`action_score_refresh`, `_score_labels`, `_compute_score`, `_compute_scorecard_id`; `create`
and `write` rescore on `_score_trigger_fields()`.

## mixin.score.line

`models/mixin_score_line.py`. One audit row; the concrete model declares `subject_id`.

**Fields:** `dimension_id`, `dimension_code` (related), `source_key`, `grouping_key`, `source_ref`
(computed through the host's labels), `value`, `points`, `max_points`, `applied`, `applicable`,
`note` (computed).

**Key methods:** `_reconcile_rows(subjects, rows)`, `_score_host(dimension)`.

## mixin.score.scale

`models/mixin_score_scale.py`. A band of a classification scale (a tier, a grade):
`mixin.catalog` + `mixin.band`, `_score_host_model` names the host.

**Fields:** `sequence`, `company_id`.

**Key methods:** `_scale(company)`, `_classify(value, company)`, `_scale_domain(company)`,
`_get_domain_band_scope()`, `_notify_band_scale_changed()`; `create`/`write`/`unlink` queue the
host's reclassification when a band moves.

## mixin.score.catalog

`models/mixin_score_catalog.py`. A catalog whose records carry weight (`_score_weight_field`,
`_score_catalog_fields`).

**Key methods:** `_score_ceilings(domain)`, `_score_labels(keys)`, `_score_catalog_models()`,
`_notify_score_catalog_changed()`, `_has_score_weight()`, `_score_catalog_trigger_fields()`,
`_score_catalog_changes(vals)`, `_score_catalog_field_moved()`.
