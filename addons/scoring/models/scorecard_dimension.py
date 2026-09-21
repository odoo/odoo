from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ScorecardDimension(models.Model):
    _name = "scorecard.dimension"
    _description = "Scorecard Dimension"
    _order = "scorecard_id, sequence, id"

    _code_per_scorecard_uniq = models.UniqueIndex(
        "(scorecard_id, code)",
        "A scorecard scores each dimension once.",
    )

    scorecard_id = fields.Many2one(
        comodel_name="scorecard",
        index=True,
        required=True,
        ondelete="cascade",
    )
    res_model = fields.Selection(related="scorecard_id.res_model")
    code = fields.Selection(
        selection=[],
        required=True,
        help="What the subject is scored on; the host answers it with "
        "_score_observe_<code>. A module adds a code with selection_add.",
    )
    name = fields.Char(
        translate=True,
        compute="_compute_name",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )
    kind = fields.Selection(
        selection=[
            ("catalog", "Catalog values carrying their own weight"),
            ("measure", "A measured value banded into points"),
        ],
        default="measure",
        required=True,
    )
    catalog_model = fields.Char(
        help="For a catalog dimension: the model whose weights are the ceiling, "
        "so that a weight edited there refreshes this scorecard's subjects.",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    weight = fields.Float(
        digits=(16, 2),
        help="For a measured dimension: its ceiling, the points a full band is "
        "worth. A catalog dimension's ceiling comes from the catalog.",
    )
    missing = fields.Selection(
        selection=[
            ("zero", "Scores zero over the full ceiling"),
            ("skip", "Leaves the denominator"),
        ],
        default="zero",
        required=True,
        help="What a subject with nothing to observe on this dimension gets: a "
        "zero against the ceiling (the commercial rule -- an unknown customer "
        "is a poor one), or no verdict at all (the credit rule -- no payment "
        "history is not bad payment history).",
    )
    precision = fields.Integer(
        default=2,
        help="Decimals the observation is rounded to before banding, so that a "
        "value on a band's bound lands where the bound says.",
    )
    band_ids = fields.One2many(
        comodel_name="scorecard.dimension.band",
        inverse_name="dimension_id",
        string="Bands",
    )
    max_points = fields.Float(
        compute="_compute_max_points",
        help="This dimension's ceiling: the weight, or the catalog's total.",
    )

    _SCORECARD_FIELDS = (
        "kind",
        "catalog_model",
        "weight",
        "missing",
        "precision",
        "active",
        "scorecard_id",
    )

    @api.depends("code")
    def _compute_name(self):
        labels = dict(self._fields["code"]._description_selection(self.env))
        for dimension in self:
            if not dimension.name:
                dimension.name = labels.get(dimension.code) or dimension.code

    @api.depends("kind", "weight", "catalog_model", "band_ids.points", "code")
    def _compute_max_points(self):
        for dimension in self:
            if dimension.kind == "measure":
                dimension.max_points = dimension.weight
                continue
            host = dimension.res_model and self.env.get(dimension.res_model)
            dimension.max_points = (
                host._score_ceiling(dimension)["total"] if host is not None else 0.0
            )

    @api.constrains("kind", "weight", "catalog_model", "precision")
    def _check_shape(self):
        for dimension in self:
            if dimension.kind == "measure" and dimension.weight <= 0:
                raise ValidationError(
                    self.env._(
                        "%(name)s: a measured dimension needs a positive weight.",
                        name=dimension.display_name,
                    )
                )
            if dimension.precision < 0:
                raise ValidationError(
                    self.env._("Precision is a number of decimals, 0 or more.")
                )

    @api.model
    def _score_band_labels(self, keys):
        # Called on a dimension: the rows of a measured dimension name a band.
        return {}

    def _score_band_labels_for(self, keys):
        self.check_singleton()
        bands = self.band_ids.with_context(active_test=False)
        by_id = {band.id: band for band in bands}
        labels = {}
        for key in keys:
            _code, band_id = key.split(":")
            if band_id == "none":
                labels[key] = self.env._("%(name)s: not measured", name=self.name)
                continue
            band = by_id.get(int(band_id))
            if band is not None:
                labels[key] = f"{self.name}: {band.display_name}"
        return labels

    def _notify_dimension_changed(self):
        self.scorecard_id._notify_scorecard_changed()

    @api.model_create_multi
    def create(self, vals_list):
        dimensions = super().create(vals_list)
        dimensions._notify_dimension_changed()
        return dimensions

    def write(self, vals):
        result = super().write(vals)
        if any(name in vals for name in self._SCORECARD_FIELDS):
            self._notify_dimension_changed()
        if "name" in vals:
            self.env["scorecard"]._invalidate_line_labels()
        return result

    def unlink(self):
        scorecards = self.scorecard_id
        result = super().unlink()
        scorecards._notify_scorecard_changed()
        return result
