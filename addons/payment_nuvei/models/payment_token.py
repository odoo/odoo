# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    nuvei_upi_id = fields.Char(string="Nuvei UPI", readonly=True)
    ITID = fields.Char(string="ITID", readonly=True)
