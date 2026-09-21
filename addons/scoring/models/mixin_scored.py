import hashlib
from collections import defaultdict

from odoo import api, fields, models
from odoo.tools import float_round

_REFRESH_BATCH_SIZE = 200


class MixinScored(models.AbstractModel):
    """A subject scored by a scorecard.

    The host names its concrete audit line in ``_score_line_model`` and declares
    ``score_line_ids`` (One2many to it through ``subject_id``); the fields
    written here read that line. ``_score_trigger_fields()`` names the host's
    own fields whose write rescores the record; a module extends it with super.

    A dimension of code ``x`` is answered on the host by ``_score_observe_x``
    (the observation: a number for a measured dimension, the attribute lines
    for a catalog one), and optionally by ``_score_ceiling_x`` (the catalog's
    ceiling, computed once per refresh), ``_score_bands_x`` (the bands a
    measured observation falls into, ``dimension.band_ids`` by default),
    ``_score_rows_x`` (the rows themselves, when neither shape fits) and
    ``_score_labels_x`` (reader-language labels for the rows' source keys).
    """

    _name = "mixin.scored"
    _description = "Scored Subject Mixin"

    _score_line_model = None

    score = fields.Float(
        string="Score (%)",
        compute="_compute_score",
        precompute=True,
        compute_sudo=True,
        store=True,
        help="Normalized score (0-100): the applied points over the ceiling of "
        "every applicable group of the audit rows.",
    )
    score_points = fields.Float(
        compute="_compute_score",
        precompute=True,
        compute_sudo=True,
        store=True,
        help="Sum of the applied audit rows (see the score breakdown).",
    )
    score_max_points = fields.Float(
        compute="_compute_score",
        precompute=True,
        compute_sudo=True,
        store=True,
        help="Normalization denominator: each applicable group of the audit "
        "rows counted once. Equal to the scorecard's ceiling when every "
        "dimension scores a missing observation as zero.",
    )
    score_date = fields.Datetime(
        string="Score Last Updated",
        readonly=True,
        help="When the audit rows were last regenerated. A catalog or scorecard "
        "change queues an async refresh -- this timestamp is how to tell the "
        "score is current versus still pending that background job.",
    )
    scorecard_id = fields.Many2one(
        comodel_name="scorecard",
        compute="_compute_scorecard_id",
        compute_sudo=True,
        help="The active scorecard for the subject's company, or the shared one.",
    )

    # ------------------------------------------------------------------ hooks

    @api.model
    def _score_trigger_fields(self):
        return ()

    def _score_company(self):
        self.check_singleton()
        if "company_id" in self._fields:
            return self.company_id
        return self.env.company

    def _score_classification_fields(self):
        """Stored computes the host derives from ``score`` through a scale."""
        return []

    @api.model
    def _score_labels(self, dimension, keys):
        custom = getattr(self, f"_score_labels_{dimension.code}", None)
        if custom is not None:
            return custom(keys)
        if dimension.kind == "catalog" and dimension.catalog_model:
            return self.env[dimension.catalog_model]._score_labels(keys)
        return dimension._score_band_labels(keys)

    @api.model
    def _score_row_note(self, dimension, source_key, applied, applicable):
        if not applicable:
            return self.env._("Not measured: left out of the score.")
        if not applied:
            return self.env._("Discarded: only the highest value counts.")
        if source_key.endswith(":none"):
            return self.env._("No data captured.")
        return ""

    # --------------------------------------------------------------- computes

    @api.depends(
        "score_line_ids.points",
        "score_line_ids.max_points",
        "score_line_ids.applied",
        "score_line_ids.applicable",
        "score_line_ids.grouping_key",
    )
    def _compute_score(self):
        for subject in self:
            rows = subject.score_line_ids.filtered("applicable")
            groups = {
                (row.dimension_id.id, row.grouping_key): row.max_points for row in rows
            }
            subject.score_points = sum(rows.filtered("applied").mapped("points"))
            subject.score_max_points = sum(groups.values())
            # Clamped: a stored row can outlive the weight that produced it
            # until the queued rescore lands, so a stale numerator degrades to
            # a capped score rather than a band above the scale.
            subject.score = (
                min(subject.score_points / subject.score_max_points * 100.0, 100.0)
                if subject.score_max_points
                else 0.0
            )

    @api.depends_context("company")
    def _compute_scorecard_id(self):
        scorecard_model = self.env["scorecard"]
        for subject in self:
            subject.scorecard_id = scorecard_model._for(
                self._name, subject._score_company()
            )

    @api.model
    def _get_score_max_points(self, company=None):
        """The scorecard's ceiling for a company: what a full score is worth."""
        scorecard = self.env["scorecard"]._for(self._name, company or self.env.company)
        return scorecard.max_points if scorecard else 0.0

    # ---------------------------------------------------------------- triggers

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        triggers = self._score_trigger_fields()
        if not triggers:
            return records
        to_score_ids = [
            record.id
            for record, vals in zip(records, vals_list, strict=True)
            if any(field in vals for field in triggers)
        ]
        if to_score_ids:
            self.browse(to_score_ids)._score_refresh()
        return records

    def write(self, vals):
        result = super().write(vals)
        if any(field in vals for field in self._score_trigger_fields()):
            self._score_refresh()
        return result

    def action_score_refresh(self):
        """Score inline for one subject, in the background for a selection.

        The action is bound to the host's list, where a user can select a whole
        page and run this in the request. Anything past a single record goes to
        the queue the engine owns for exactly this work.
        """
        if len(self) <= 1:
            self._score_refresh()
            return None
        self._delay_score_refresh()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "info",
                "title": self.env._("Scoring in the background"),
                "message": self.env._(
                    "%(count)s records queued for recomputation.",
                    count=len(self),
                ),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    # ----------------------------------------------------------------- refresh

    @api.job(channel="scoring.refresh")
    def _score_refresh(self):
        env = self.env(su=True)
        subjects = self.with_env(env)
        by_scorecard = defaultdict(env[self._name].browse)
        for subject in subjects:
            by_scorecard[subject.scorecard_id] |= subject
        rows = []
        for scorecard, scored in by_scorecard.items():
            dimensions = scorecard.dimension_ids.filtered("active")
            ceilings = {
                dimension: subjects._score_ceiling(dimension)
                for dimension in dimensions
            }
            for subject in scored:
                for dimension in dimensions:
                    rows += subject._score_rows(dimension, ceilings[dimension])
        env[self._score_line_model]._reconcile_rows(subjects, rows)
        for field_name in ["score", "score_points", "score_max_points"] + list(
            self._score_classification_fields()
        ):
            self.env.add_to_compute(self._fields[field_name], self)
        self.flush_recordset()
        # Raw SQL, deliberately: this is a bookkeeping stamp, not an edit of the
        # subject. Going through write() would move write_date on every catalog
        # refresh, so "when did this record last change" would answer with a
        # background job instead of with the last real edit, and it would also
        # re-enter the host's write. The ORM cache is kept coherent by hand on
        # the line below.
        env.cr.execute(
            f'UPDATE "{self._table}" SET score_date = %s WHERE id = ANY(%s)',
            (fields.Datetime.now(), self.ids),
        )
        self.invalidate_recordset(["score_date"])

    @api.model
    def _score_ceiling(self, dimension):
        # Superuser and a fixed active_test, whatever the caller carries: the
        # ceiling is a property of the catalog, not of who asks. An archived
        # value is not reachable, so it is not in the ceiling.
        host = self.env(su=True)[self._name].with_context(active_test=True)
        custom = getattr(host, f"_score_ceiling_{dimension.code}", None)
        if custom is not None:
            return custom(dimension)
        if dimension.kind == "catalog" and dimension.catalog_model:
            return host.env[dimension.catalog_model]._score_ceilings([])
        return {"total": dimension.weight}

    def _score_rows(self, dimension, ceiling):
        self.check_singleton()
        code = dimension.code
        custom = getattr(self, f"_score_rows_{code}", None)
        if custom is not None:
            return custom(dimension, ceiling)
        observation = getattr(self, f"_score_observe_{code}")(dimension)
        if dimension.kind == "catalog":
            return self._prepare_attribute_score_rows(dimension, ceiling, observation)
        return self._prepare_measure_score_rows(dimension, observation)

    def _prepare_measure_score_rows(self, dimension, value):
        self.check_singleton()
        code = dimension.code
        weight = dimension.weight
        if value is None:
            return [
                self._prepare_score_row(
                    dimension,
                    source_key=f"{code}:none",
                    points=0.0,
                    max_points=weight,
                    applicable=dimension.missing == "zero",
                )
            ]
        value = float_round(value, precision_digits=dimension.precision)
        bands = getattr(self, f"_score_bands_{code}", None)
        bands = bands(dimension) if bands is not None else dimension.band_ids
        band = next(
            (
                band
                for band in bands.sorted("min_value")
                if band.active and band._is_covering(value)
            ),
            None,
        )
        return [
            self._prepare_score_row(
                dimension,
                source_key=f"{code}:{band.id if band else 'none'}",
                points=band.points / 100.0 * weight if band else 0.0,
                max_points=weight,
                value=value,
            )
        ]

    def _prepare_attribute_score_rows(self, dimension, ceiling, lines):
        self.check_singleton()
        code = dimension.code
        attribute_model = self.env[ceiling["model"]]
        # Keyed by id and browsed in one go: the mapping depends only on the
        # ceiling argument, which is identical for every subject in the batch,
        # and browsing per attribute per subject defeats the prefetch.
        ceilings = dict(ceiling["attributes"])
        values_by_attribute = {}
        for line in lines:
            attribute_id = line.attribute_id.id
            values_by_attribute.setdefault(attribute_id, line.value_ids.browse())
            values_by_attribute[attribute_id] |= line.value_ids

        rows = []
        for attribute in attribute_model.browse(ceilings):
            attribute_ceiling = ceilings[attribute.id]
            grouping_key = f"{code}:{attribute.id}"
            values = values_by_attribute.get(attribute.id)
            if not values:
                rows.append(
                    self._prepare_score_row(
                        dimension,
                        source_key=f"{code}:{attribute.id}:none",
                        points=0.0,
                        max_points=attribute_ceiling,
                        grouping_key=grouping_key,
                    )
                )
                continue
            best_value = max(values, key=lambda value: value.score_value)
            rows.extend(
                self._prepare_score_row(
                    dimension,
                    source_key=f"{code}:{attribute.id}:{value.id}",
                    points=value.score_value,
                    max_points=attribute_ceiling,
                    applied=attribute.aggregation_mode == "sum" or value == best_value,
                    grouping_key=grouping_key,
                )
                for value in values
            )
        return rows

    def _prepare_score_row(
        self,
        dimension,
        source_key,
        points,
        max_points,
        applied=True,
        applicable=True,
        value=None,
        grouping_key=None,
    ):
        self.check_singleton()
        return {
            "subject_id": self.id,
            "dimension_id": dimension.id,
            "grouping_key": grouping_key or dimension.code,
            "source_key": source_key,
            "value": value,
            "points": points,
            "max_points": max_points,
            "applied": applied,
            "applicable": applicable,
        }

    # ------------------------------------------------------------------- queue

    def _score_job_identity_key(self, kind):
        """Deterministic key for a queued wave over exactly these subjects.

        ir.job deduplicates queued jobs on identity_key, so a second wave over
        the same batch collapses onto the pending one instead of stacking. An
        admin tuning ten weights in one sitting otherwise queues ten complete
        refreshes of the whole subject base. Hashed over the ids rather than
        keyed on the batch bounds, so two different sets that happen to share
        their first and last subject do not collapse into one.
        """
        digest = hashlib.sha256(
            ",".join(str(record_id) for record_id in self.ids).encode()
        ).hexdigest()
        return f"scoring.{kind}:{self._name}:{digest}"

    def _delay_score_refresh(self):
        for start in range(0, len(self), _REFRESH_BATCH_SIZE):
            batch = self[start : start + _REFRESH_BATCH_SIZE]
            batch.delayed(
                identity_key=batch._score_job_identity_key("refresh")
            )._score_refresh()

    @api.job(channel="scoring.refresh")
    def _score_reclassify(self):
        """Re-run the classification only, leaving the audit rows alone."""
        for field_name in self._score_classification_fields():
            self.env.add_to_compute(self._fields[field_name], self)
        self.flush_recordset()

    @api.model
    def _score_notify_scorecard_changed(self):
        """Queue a refresh of every subject carrying rows.

        As superuser and without active_test: a catalog weight or a dimension
        is shared, so every subject carrying audit rows is stale, including the
        archived ones and the ones the editing user's company rule hides.
        """
        if not self.env.registry.ready:
            return
        self.env(su=True)[self._name].with_context(active_test=False).search(
            [("score_line_ids", "!=", False)]
        )._delay_score_refresh()

    @api.model
    def _score_notify_scale_changed(self):
        """Queue a reclassification after a change to a scale of bands.

        Cheaper than a refresh: the audit rows and the score do not move, only
        the band the score falls into. Every subject, not only the scored or
        classified ones: a subject with no rows and no band is exactly the one
        a new band covering zero is meant to pick up.
        """
        if not self.env.registry.ready or not self._score_classification_fields():
            return
        subjects = (
            self.env(su=True)[self._name].with_context(active_test=False).search([])
        )
        for start in range(0, len(subjects), _REFRESH_BATCH_SIZE):
            batch = subjects[start : start + _REFRESH_BATCH_SIZE]
            batch.delayed(
                identity_key=batch._score_job_identity_key("reclassify")
            )._score_reclassify()
