from odoo import api, models
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = "pos.config"

    @api.constrains("payment_method_ids")
    def _check_online_payment_methods(self):
        """Checks the journal currency with _get_online_payment_providers(..., error_if_invalid=True)"""
        for config in self:
            opm_amount = 0
            for pm in config.payment_method_ids:
                if pm.is_online_payment:
                    opm_amount += 1
                    if opm_amount > 1:
                        raise ValidationError(
                            self.env._(
                                "A POS config cannot have more than one online payment method."
                            )
                        )
                    if not pm._get_online_payment_providers(
                        config.id, error_if_invalid=True
                    ):
                        raise ValidationError(
                            self.env._(
                                "To use an online payment method in a POS config, it must have at least one published payment provider supporting the currency of that POS config."
                            )
                        )

    def _get_cashier_online_payment_method(self):
        self.check_singleton()
        return self.payment_method_ids.filtered("is_online_payment")[:1]
