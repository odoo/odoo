# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_pos_kpay = fields.Boolean(string="KPay Payment Terminal", help="The transactions are processed by KPay. Set the IP address of the terminal on the related payment method.")
