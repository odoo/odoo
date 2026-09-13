import hashlib

from odoo import api, fields, models

_RECOMPUTE_BATCH_SIZE = 200


class ResPartner(models.Model):
    _inherit = "res.partner"

    _SCORE_TRIGGERS = ()

    # Fields that can move a partner in or out of being the commercial entity.
    _COMMERCIAL_FIELDS = ("parent_id", "is_company", "type")

    attribute_line_ids = fields.One2many(
        comodel_name="res.partner.attribute.line",
        inverse_name="partner_id",
        string="Profile attributes",
    )
    score_points = fields.Float(
        compute="_compute_score",
        precompute=True,
        compute_sudo=True,
        store=True,
        help="Sum of the applied audit rows (see the score breakdown).",
    )
    score_max_possible = fields.Float(
        compute="_compute_score_max_possible",
        compute_sudo=True,
        help="Normalization denominator: the maximum points reachable "
        "across all active scoring dimensions with configured weights. A "
        "property of the catalog, read live rather than stored per partner.",
    )
    score_pct = fields.Float(
        string="Score (%)",
        compute="_compute_score",
        precompute=True,
        compute_sudo=True,
        store=True,
        help="Normalized score percentage (0-100) used to classify the "
        "partner into a commercial profile.",
    )
    date_last_score_update = fields.Datetime(
        string="Score Last Updated",
        readonly=True,
        help="When the score audit rows were last regenerated. A catalog "
        "weight change queues an async recompute (see "
        "_delay_profile_scores_recompute) -- this timestamp is how to tell "
        "the score is current versus still pending that background job.",
    )
    partner_profile_id = fields.Many2one(
        comodel_name="partner.profile",
        string="Commercial Profile",
        compute="_compute_partner_profile_id",
        compute_sudo=True,
        recursive=True,
        store=True,
        tracking=True,
        help="First active profile whose score range contains the partner's "
        "score percentage. A contact carries its commercial entity's profile: "
        "the score describes the customer, not the person. Tracked, so the "
        "chatter carries the band history. score_pct is deliberately not "
        "tracked: it moves on every catalog edit and every attribute capture, "
        "and would bury the transitions that carry commercial meaning.",
    )
    factor = fields.Float(
        related="partner_profile_id.factor",
        string="Profile Factor",
        readonly=True,
    )
    score_line_ids = fields.One2many(
        comodel_name="partner.score.line",
        inverse_name="partner_id",
        string="Score Breakdown",
    )
    score_line_count = fields.Count(
        count_of="score_line_ids",
        string="Score Rows",
        store=True,
        help="How many audit rows explain the score. Stored so the partner "
        "form can decide whether to offer the breakdown without loading "
        "every row of it.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        if not self._SCORE_TRIGGERS:
            return partners
        to_score_ids = [
            partner.id
            for partner, vals in zip(partners, vals_list, strict=True)
            if any(field in vals for field in self._SCORE_TRIGGERS)
        ]
        if to_score_ids:
            self.browse(to_score_ids)._update_profile_scores()
        return partners

    def write(self, vals):
        result = super().write(vals)
        if any(field in vals for field in self._SCORE_TRIGGERS):
            self._update_profile_scores()
        if any(field in vals for field in self._COMMERCIAL_FIELDS):
            self.env["res.partner.attribute.line"]._follow_commercial_partner(self)
        return result

    @api.depends(
        "score_line_ids.points",
        "score_line_ids.applied",
    )
    def _compute_score(self):
        max_possible = self._get_score_max_possible()
        for partner in self:
            applied_rows = partner.score_line_ids.filtered("applied")
            partner.score_points = sum(applied_rows.mapped("points"))
            # Clamped: a stored row can outlive the weight that produced it
            # until the queued rescore lands, so a stale numerator degrades to
            # a capped score rather than a band above the scale.
            partner.score_pct = (
                min(partner.score_points / max_possible * 100.0, 100.0)
                if max_possible
                else 0.0
            )

    def _compute_score_max_possible(self):
        self.score_max_possible = self._get_score_max_possible()

    @api.depends(
        "score_pct",
        "company_id",
        "commercial_partner_id",
        "commercial_partner_id.partner_profile_id",
    )
    def _compute_partner_profile_id(self):
        profile_model = self.env["partner.profile"]
        scales = {}
        commercial = self.filtered(lambda p: p.commercial_partner_id == p)
        for partner in commercial:
            # The partner's own company, never the acting user's: this field is
            # stored and shared, so falling back to env.company would store
            # whichever scale the last user to trigger the compute happened to
            # be in. A company-less partner resolves against company-less bands.
            company = partner.company_id
            if company.id not in scales:
                scales[company.id] = profile_model.search(
                    [("active", "=", True)] + profile_model._scale_domain(company),
                    order="sequence, id",
                )
            partner.partner_profile_id = next(
                (
                    profile
                    for profile in scales[company.id]
                    if profile._is_covering(partner.score_pct)
                ),
                profile_model,
            )
        for partner in self - commercial:
            partner.partner_profile_id = (
                partner.commercial_partner_id.partner_profile_id
            )

    def action_partner_score_recompute(self):
        """Score inline for one partner, in the background for a selection.

        The action is bound to the partner list, where a user can select a
        whole page and run this in the request. Anything past a single record
        goes to the queue the module already owns for exactly this work.
        """
        if len(self) <= 1:
            self._update_profile_scores()
            return None
        self._delay_profile_scores_recompute()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "info",
                "title": self.env._("Scoring in the background"),
                "message": self.env._(
                    "%(count)s partners queued for recomputation.",
                    count=len(self),
                ),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    @api.model
    def _get_score_dimensions(self):
        return ["partner_attr"]

    @api.model
    def _get_score_ceiling_data(self):
        # Superuser and a fixed active_test, whatever the caller carries: the
        # ceiling is a property of the catalog, not of who asks. An archived
        # value is not reachable, so it is not in the ceiling.
        partner = self.env(su=True)["res.partner"].with_context(active_test=True)
        return {
            dimension: getattr(partner, f"_score_ceiling_{dimension}")()
            for dimension in self._get_score_dimensions()
        }

    @api.model
    def _get_score_max_possible(self):
        return sum(
            ceiling["total"] for ceiling in self._get_score_ceiling_data().values()
        )

    @api.model
    def _score_ceiling_partner_attr(self):
        return self.env["res.partner.attribute"]._score_ceilings([])

    @api.job(channel="partner_scoring.recompute")
    def _update_profile_scores(self):
        env = self.env(su=True)
        ceilings = self._get_score_ceiling_data()
        dimensions = self._get_score_dimensions()

        rows = []
        for partner in self.with_env(env):
            for dimension in dimensions:
                rows += getattr(partner, f"_score_rows_{dimension}")(
                    ceilings[dimension]
                )
        self.env["partner.score.line"]._reconcile_rows(self, rows)
        for field_name in ("score_points", "score_pct", "partner_profile_id"):
            self.env.add_to_compute(self._fields[field_name], self)
        self.flush_recordset()
        # Raw SQL, deliberately: this is a bookkeeping stamp, not an edit of the
        # partner. Going through write() would move write_date on every catalog
        # recompute, so "when did this partner last change" would answer with a
        # background job instead of with the last real edit, and it would also
        # re-enter res.partner.write. The ORM cache is kept coherent by hand on
        # the line below.
        env.cr.execute(
            "UPDATE res_partner SET date_last_score_update = %s WHERE id = ANY(%s)",
            (fields.Datetime.now(), self.ids),
        )
        self.invalidate_recordset(["date_last_score_update"])

    @api.job(channel="partner_scoring.recompute")
    def _reclassify_profile_bands(self):
        """Re-run the classification only, leaving the audit rows alone."""
        self.env.add_to_compute(self._fields["partner_profile_id"], self)
        self.flush_recordset()

    @api.model
    def _notify_score_bands_changed(self):
        """Queue a reclassification after a change to the profile scale.

        Nothing depends on partner.profile itself, so an edited, archived or
        deleted band never reached the partners it governs and the stored
        classification drifted away from the configured scale. Cheaper than
        _notify_score_ceiling_changed: the audit rows and the percentage do
        not move, only the band the percentage falls into.

        Every partner, not only the scored or classified ones: a partner with
        no audit rows and no band is exactly the one a new band covering zero
        is meant to pick up.
        """
        if not self.env.registry.ready:
            return
        partners = (
            self.env(su=True)["res.partner"].with_context(active_test=False).search([])
        )
        for start in range(0, len(partners), _RECOMPUTE_BATCH_SIZE):
            batch = partners[start : start + _RECOMPUTE_BATCH_SIZE]
            batch.delayed(
                identity_key=batch._score_job_identity_key("reclassify")
            )._reclassify_profile_bands()

    def _score_job_identity_key(self, kind):
        """Deterministic key for a queued wave over exactly these partners.

        ir.job deduplicates queued jobs on identity_key, so a second wave over
        the same batch collapses onto the pending one instead of stacking. An
        admin tuning ten weights in one sitting otherwise queues ten complete
        recomputes of the whole customer base. Hashed over the ids rather than
        keyed on the batch bounds, so two different sets that happen to share
        their first and last partner do not collapse into one.
        """
        digest = hashlib.sha256(
            ",".join(str(partner_id) for partner_id in self.ids).encode()
        ).hexdigest()
        return f"partner_scoring.{kind}:{digest}"

    def _delay_profile_scores_recompute(self):
        for start in range(0, len(self), _RECOMPUTE_BATCH_SIZE):
            batch = self[start : start + _RECOMPUTE_BATCH_SIZE]
            batch.delayed(
                identity_key=batch._score_job_identity_key("recompute")
            )._update_profile_scores()

    @api.model
    def _notify_score_ceiling_changed(self):
        if not self.env.registry.ready:
            return
        # As superuser and without active_test: a catalog weight is shared, so
        # every partner carrying audit rows is stale, including the archived
        # ones and the ones the editing user's company rule hides.
        self.env(su=True)["res.partner"].with_context(active_test=False).search(
            [("score_line_ids", "!=", False)]
        )._delay_profile_scores_recompute()

    def _score_rows_partner_attr(self, ceiling):
        self.check_singleton()
        return self._prepare_attribute_score_rows(
            "partner_attr", ceiling, self.attribute_line_ids
        )

    def _prepare_attribute_score_rows(self, dimension, ceiling, lines):
        self.check_singleton()
        attribute_model = self.env[ceiling["model"]]
        # Keyed by id and browsed in one go: the mapping depends only on the
        # ceiling argument, which is identical for every partner in the batch,
        # and browsing per attribute per partner defeats the prefetch.
        ceilings = dict(ceiling["attributes"])
        values_by_attribute = {}
        for line in lines:
            attribute_id = line.attribute_id.id
            values_by_attribute.setdefault(attribute_id, line.value_ids.browse())
            values_by_attribute[attribute_id] |= line.value_ids

        rows = []
        for attribute in attribute_model.browse(ceilings):
            attribute_ceiling = ceilings[attribute.id]
            values = values_by_attribute.get(attribute.id)
            if not values:
                rows.append(
                    self._prepare_score_row(
                        dimension=dimension,
                        source_key=f"{dimension}:{attribute.id}:none",
                        points=0.0,
                        max_points=attribute_ceiling,
                    )
                )
                continue
            best_value = max(values, key=lambda value: value.score_value)
            rows.extend(
                self._prepare_score_row(
                    dimension=dimension,
                    source_key=f"{dimension}:{attribute.id}:{value.id}",
                    points=value.score_value,
                    max_points=attribute_ceiling,
                    applied=attribute.aggregation_mode == "sum" or value == best_value,
                )
                for value in values
            )
        return rows

    def _prepare_score_row(
        self, dimension, source_key, points, max_points, applied=True
    ):
        self.check_singleton()
        return {
            "partner_id": self.id,
            "dimension": dimension,
            "source_key": source_key,
            "points": points,
            "max_points": max_points,
            "applied": applied,
        }

    @api.model
    def _score_labels_partner_attr(self, keys):
        return self.env["res.partner.attribute"]._score_labels(keys)

    @api.model
    def _score_row_note(self, dimension, source_key, applied):
        if not applied:
            return self.env._("Discarded: only the highest value counts.")
        if source_key.endswith(":none"):
            return self.env._("No data captured.")
        return ""
