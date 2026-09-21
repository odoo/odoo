from odoo import api, fields, models


class MixinScoreScale(models.AbstractModel):
    """A band of a classification scale: a tier, a grade.

    The concrete model names its host in ``_score_host_model`` and keeps its own
    consequences (a factor, a limit, a term). A band that moves reclassifies the
    host's subjects without a rescore.
    """

    _name = "mixin.score.scale"
    _inherit = ["mixin.catalog", "mixin.band"]
    _description = "Score Scale Mixin"
    _order = "sequence, id"

    _score_host_model = None

    # Fields whose change moves which subjects fall into which band. A
    # consequence field is deliberately absent: it is read downstream from the
    # band, and changing it reclassifies nobody.
    _BAND_SCALE_FIELDS = ("min_value", "max_value", "active", "company_id")

    sequence = fields.Integer(
        default=10,
        help="Used to order the bands. Lower values have higher precedence.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        help="Leave empty for a scale every subject is measured against. "
        "Setting it narrows the scale to that company's subjects -- and to "
        "*only* those: a subject with no company of its own resolves against "
        "company-less bands, so a scale that is scoped by accident classifies "
        "nobody.",
    )

    @api.model
    def _scale_domain(self, company):
        return [("company_id", "in", [False, company.id])]

    def _get_domain_band_scope(self):
        self.check_singleton()
        if self.company_id:
            return self._scale_domain(self.company_id)
        # A company-less band belongs to every scale, so nothing narrows it.
        return []

    @api.model
    def _scale(self, company):
        return self.search(
            [("active", "=", True)] + self._scale_domain(company),
            order="sequence, id",
        )

    @api.model
    def _classify(self, value, company):
        return next(
            (
                band
                for band in self._scale(company)
                if band._is_band() and band._is_covering(value)
            ),
            self.browse(),
        )

    def _notify_band_scale_changed(self):
        if self._score_host_model:
            self.env[self._score_host_model]._score_notify_scale_changed()

    @api.model_create_multi
    def create(self, vals_list):
        bands = super().create(vals_list)
        bands._notify_band_scale_changed()
        return bands

    def write(self, vals):
        moved = bool(self) and any(name in vals for name in self._BAND_SCALE_FIELDS)
        result = super().write(vals)
        if moved:
            self._notify_band_scale_changed()
        return result

    def unlink(self):
        existed = bool(self)
        result = super().unlink()
        if existed:
            self._notify_band_scale_changed()
        return result
