from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PartnerTier(models.Model):
    _name = "partner.tier"
    _inherit = ["mixin.score.scale"]
    _description = "Partner Commercial Tier"

    _score_host_model = "res.partner"

    name = fields.Char(
        string="Tier Name",
        help="Name of the customer tier",
    )
    factor = fields.Float(
        default=1.0,
        help="Multiplicative percentage factor (e.g., 1.2 for 120%)",
    )
    min_value = fields.Float(
        string="Minimum Score (%)",
        help="Lower bound of the normalized score, inclusive.",
    )
    max_value = fields.Float(
        string="Maximum Score (%)",
        help="Upper bound of the normalized score, exclusive -- it is the lower "
        "bound of the next tier. 0 means no upper limit, which the top tier "
        "should use so a perfect score still classifies.",
    )

    @api.constrains("factor")
    def _check_factor(self):
        for tier in self:
            if tier.factor <= 0:
                raise ValidationError(
                    self.env._(
                        "The factor must be greater than 0. Current value: %(factor)s",
                        factor=tier.factor,
                    )
                )

    @api.constrains("min_value", "max_value")
    def _check_percentage_domain(self):
        for tier in self:
            if tier.min_value > 100:
                raise ValidationError(
                    self.env._("Minimum score cannot exceed 100 (percentage scale).")
                )
            if tier.max_value > 100:
                raise ValidationError(
                    self.env._("Maximum score cannot exceed 100 (percentage scale).")
                )
            if tier.max_value == 100:
                raise ValidationError(
                    self.env._(
                        "%(name)s ends at exactly 100, which excludes a perfect "
                        "score: the bounds are half-open. Leave the maximum at 0 "
                        "on the highest tier to make it open-ended.",
                        name=tier.display_name,
                    )
                )

    @api.depends("name")
    def _compute_display_name(self):
        for tier in self:
            tier.display_name = tier.name or self.env._("New Tier")
