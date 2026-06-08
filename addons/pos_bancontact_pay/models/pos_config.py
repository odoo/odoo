from odoo import _, api, models
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _default_payment_methods(self):
        """Exclude Bancontact Pay sticker methods from the default PoS configuration setup."""
        base = super()._default_payment_methods()
        return base.filtered_domain(['|', ('payment_provider', '!=', 'bancontact_pay'), ('bancontact_usage', '!=', 'sticker')])

    @api.constrains('payment_method_ids')
    def _check_bancontact_payment_methods(self):
        """Ensure Bancontact Pay sticker methods are not shared across PoS configurations."""
        for config in self:
            bancontact_sticker_methods = config.payment_method_ids.filtered_domain(
                [
                    ('payment_provider', '=', 'bancontact_pay'),
                    ('bancontact_usage', '=', 'sticker'),
                ],
            )
            for method in bancontact_sticker_methods:
                other_configs = method.config_ids - config
                if other_configs:
                    raise ValidationError(
                        _(
                            "The Bancontact sticker payment method '%(method_name)s' is already assigned to another POS configuration (%(config_names)s).\n"
                            "A sticker can only be linked to one POS configuration at a time.",
                            method_name=method.name,
                            config_names=", ".join(other_configs.mapped('name')),
                        ),
                    )
