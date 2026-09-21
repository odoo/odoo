from odoo import api, fields, models
from odoo.exceptions import ValidationError


class Scorecard(models.Model):
    _name = "scorecard"
    _inherit = ["mixin.catalog"]
    _description = "Scorecard"
    _order = "res_model, company_id, id"

    res_model = fields.Selection(
        selection="_selection_res_model",
        string="Scored Model",
        required=True,
        help="The model whose records this scorecard measures.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        help="Leave empty for a scorecard every company shares. A company with "
        "its own scorecard measures its subjects against that one only.",
    )
    dimension_ids = fields.One2many(
        comodel_name="scorecard.dimension",
        inverse_name="scorecard_id",
        string="Dimensions",
    )
    max_points = fields.Float(
        compute="_compute_max_points",
        help="What a full score is worth: the ceilings of the active dimensions "
        "added together. A property of the configuration, read live.",
    )

    @api.model
    def _selection_res_model(self):
        mixin = self.pool["mixin.scored"]
        return [
            (name, self.env[name]._description)
            for name in self.env.registry.get_descendants(["mixin.scored"], "_inherit")
            if name != mixin._name and not self.env[name]._abstract
        ]

    @api.depends("dimension_ids.max_points", "dimension_ids.active")
    def _compute_max_points(self):
        for scorecard in self:
            scorecard.max_points = sum(
                scorecard.dimension_ids.filtered("active").mapped("max_points")
            )

    @api.constrains("res_model", "company_id", "active")
    def _check_one_per_scope(self):
        checked = self.filtered("active")
        peers = self.search(
            [
                ("id", "not in", checked.ids),
                ("active", "=", True),
                ("res_model", "in", checked.mapped("res_model")),
            ]
        )
        by_scope = {(peer.res_model, peer.company_id.id): peer for peer in peers}
        for scorecard in checked:
            twin = by_scope.get((scorecard.res_model, scorecard.company_id.id))
            if twin:
                raise ValidationError(
                    self.env._(
                        "%(name)s and %(twin)s both score %(model)s for the same "
                        "company; a subject is measured against one scorecard.",
                        name=scorecard.display_name,
                        twin=twin.display_name,
                        model=scorecard.res_model,
                    )
                )

    @api.model
    def _for(self, res_model, company):
        # Superuser: which scorecard applies to a subject is a fact of the
        # configuration, not of who asks.
        candidates = (
            self.env(su=True)[self._name]
            .with_context(active_test=True)
            .search(
                [
                    ("res_model", "=", res_model),
                    ("company_id", "in", [False, company.id]),
                ]
            )
        )
        return next(
            iter(candidates.sorted(lambda card: not card.company_id)), candidates
        )

    @api.model
    def _host_models(self):
        return [name for name, _label in self._selection_res_model()]

    @api.model
    def _notify_catalog_changed(self, model_names):
        # The ceilings are read live from the catalog; the cached computes must
        # not outlive the weight they summed.
        self.env["scorecard.dimension"].invalidate_model(["max_points"])
        self.invalidate_model(["max_points"])
        if not self.env.registry.ready:
            return
        dimensions = (
            self.env(su=True)["scorecard.dimension"]
            .with_context(active_test=True)
            .search(
                [("kind", "=", "catalog"), ("catalog_model", "in", list(model_names))]
            )
        )
        for res_model in set(dimensions.scorecard_id.mapped("res_model")):
            self.env[res_model]._score_notify_scorecard_changed()

    def _notify_scorecard_changed(self):
        if not self.env.registry.ready:
            return
        for res_model in set(self.mapped("res_model")):
            self.env[res_model]._score_notify_scorecard_changed()

    @api.model
    def _invalidate_line_labels(self):
        for res_model in self._host_models():
            line_model = self.env[res_model]._score_line_model
            if line_model:
                self.env[line_model].invalidate_model(["source_ref"])

    def write(self, vals):
        result = super().write(vals)
        if "active" in vals or "company_id" in vals:
            self._notify_scorecard_changed()
        return result
