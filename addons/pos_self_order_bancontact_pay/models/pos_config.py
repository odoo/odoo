from odoo import _, api, models
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.constrains("payment_method_ids")
    def _check_unsupported_kiosks(self):
        for config in self:
            if config.self_ordering_mode == "kiosk" and any(method.payment_provider == "bancontact_pay" and method.bancontact_usage == "sticker" for method in config.payment_method_ids):
                raise ValidationError(_("Bancontact Pay stickers are not supported for kiosks."))
