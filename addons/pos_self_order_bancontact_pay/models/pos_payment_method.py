from odoo import _, api, models
from odoo.exceptions import ValidationError


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    @api.constrains("payment_provider", "config_ids")
    def _check_unsupported_kiosks(self):
        for record in self:
            if record.payment_provider == "bancontact_pay" and any(config.self_ordering_mode == "kiosk" for config in record.config_ids):
                raise ValidationError(_("Bancontact Pay is not supported in kiosk (self-ordering) mode."))
