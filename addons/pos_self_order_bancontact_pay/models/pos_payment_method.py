from odoo import _, api, models
from odoo.exceptions import ValidationError


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    @api.constrains("bancontact_product_id", "config_ids")
    def _check_unsupported_kiosks(self):
        for record in self:
            if record.bancontact_usage == "sticker" and any(config.self_ordering_mode == "kiosk" for config in record.config_ids):
                raise ValidationError(_("Bancontact Pay stickers are not supported for kiosks."))
