# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pay_invoices_online = fields.Boolean(config_parameter='account_payment.enable_portal_payment')
