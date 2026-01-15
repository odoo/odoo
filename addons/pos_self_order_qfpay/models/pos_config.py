# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosConfig(models.Model):
    _inherit = "pos.config"

    def _supported_kiosk_payment_terminal(self):
        res = super()._supported_kiosk_payment_terminal()
        res.append('qfpay')
        return res
