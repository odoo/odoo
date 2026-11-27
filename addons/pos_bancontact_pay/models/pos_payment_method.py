import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    bancontact_usage = fields.Selection(related="electronic_payment_id.bancontact_usage")

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ["bancontact_usage"]

    @api.constrains("config_ids")
    def _check_bancontact_sticker_one_pos_config(self):
        """Restrict Bancontact sticker methods to a single PoS configuration."""
        for record in self:
            if (
                record.payment_provider == "bancontact_pay"
                and record.bancontact_usage == "sticker"
                and len(record.config_ids) > 1
            ):
                raise ValidationError(_("One Bancontact Pay sticker payment method can only be linked to one POS configuration."))
