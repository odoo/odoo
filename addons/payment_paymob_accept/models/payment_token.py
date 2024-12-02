import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


class PaymentToken(models.Model):
    _inherit = "payment.token"

    paymob_order_id = fields.Char(
        string="Paymob Order ID", help="The Paymob Order ID associated with this token"
    )
    paymob_reference = fields.Char(
        string="Paymob Reference",
        help="The Paymob Reference associated with this token",
    )
