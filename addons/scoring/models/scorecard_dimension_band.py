from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ScorecardDimensionBand(models.Model):
    _name = "scorecard.dimension.band"
    _inherit = ["mixin.band"]
    _description = "Scorecard Dimension Band"
    _order = "dimension_id, min_value, id"

    # An early payment is a negative days-beyond-terms and a distressed Z'' is
    # negative: a band says what it covers rather than have the engine clamp.
    _band_allow_negative = True

    dimension_id = fields.Many2one(
        comodel_name="scorecard.dimension",
        index=True,
        required=True,
        ondelete="cascade",
    )
    points = fields.Float(
        digits=(5, 2),
        required=True,
        help="Points, 0 to 100, an observation in this band earns, as a share "
        "of the dimension's weight.",
    )

    def _get_domain_band_scope(self):
        self.check_singleton()
        return [("dimension_id", "=", self.dimension_id.id)]

    @api.depends("min_value", "max_value", "points")
    def _compute_display_name(self):
        for band in self:
            upper = "" if not band.max_value else f"{band.max_value:g}"
            band.display_name = f"[{band.min_value:g}, {upper}) → {band.points:g}"

    @api.constrains("points")
    def _check_points(self):
        if any(not 0 <= band.points <= 100 for band in self):
            raise ValidationError(self.env._("Points lie between 0 and 100."))

    def _notify_band_changed(self):
        self.dimension_id._notify_dimension_changed()

    @api.model_create_multi
    def create(self, vals_list):
        bands = super().create(vals_list)
        bands._notify_band_changed()
        return bands

    def write(self, vals):
        result = super().write(vals)
        if any(name in vals for name in ("min_value", "max_value", "points", "active")):
            self._notify_band_changed()
        return result

    def unlink(self):
        dimensions = self.dimension_id
        result = super().unlink()
        dimensions._notify_dimension_changed()
        return result
