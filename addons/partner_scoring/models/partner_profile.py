from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PartnerProfile(models.Model):
    _name = "partner.profile"
    _inherit = "mixin.band"
    _description = "Partner Commercial Profile"
    _order = "sequence, id"

    name = fields.Char(
        string="Profile Name",
        required=True,
        help="Name of the customer profile",
    )
    active = fields.Boolean(
        default=True,
        help="If unchecked, the profile will not appear in default views",
    )
    sequence = fields.Integer(
        default=10,
        help="Used to order profiles. Lower values have higher precedence.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        help="Leave empty for a scale every partner is measured against. "
        "Setting it narrows the scale to that company's partners -- and to "
        "*only* those: a partner with no company of its own resolves "
        "against company-less bands, so a scale that is scoped by accident "
        "classifies nobody.",
    )
    factor = fields.Float(
        default=1.0,
        help="Multiplicative percentage factor (e.g., 1.2 for 120%)",
    )
    min_value = fields.Float(
        string="Minimum Score (%)",
        help="Lower bound of the normalized score percentage, inclusive.",
    )
    max_value = fields.Float(
        string="Maximum Score (%)",
        help="Upper bound of the normalized score percentage, exclusive -- it "
        "is the lower bound of the next profile. 0 means no upper limit, "
        "which the top profile should use so a perfect score still classifies.",
    )

    # Fields whose change moves which partners fall into which band. factor is
    # deliberately absent: it is read downstream from the band, and changing it
    # reclassifies nobody.
    _BAND_SCALE_FIELDS = ("min_value", "max_value", "active", "company_id")

    def _notify_band_scale_changed(self):
        self.env["res.partner"]._notify_score_bands_changed()

    @api.model_create_multi
    def create(self, vals_list):
        profiles = super().create(vals_list)
        profiles._notify_band_scale_changed()
        return profiles

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

    @api.constrains("factor")
    def _check_factor(self):
        for profile in self:
            if profile.factor <= 0:
                raise ValidationError(
                    self.env._(
                        "The factor must be greater than 0. Current value: %(factor)s",
                        factor=profile.factor,
                    )
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

    @api.constrains("min_value", "max_value")
    def _check_percentage_domain(self):
        for profile in self:
            if profile.min_value > 100:
                raise ValidationError(
                    self.env._("Minimum score cannot exceed 100 (percentage scale).")
                )
            if profile.max_value > 100:
                raise ValidationError(
                    self.env._("Maximum score cannot exceed 100 (percentage scale).")
                )
            if profile.max_value == 100:
                raise ValidationError(
                    self.env._(
                        "%(name)s ends at exactly 100, which excludes a perfect "
                        "score: the bounds are half-open. Leave the maximum at 0 "
                        "on the highest profile to make it open-ended.",
                        name=profile.display_name,
                    )
                )

    @api.depends("name")
    def _compute_display_name(self):
        for profile in self:
            profile.display_name = profile.name or self.env._("New Profile")
