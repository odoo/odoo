# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_sale_gelato = fields.Boolean("Gelato")

    gelato_api_key = fields.Char(related='company_id.gelato_api_key', readonly=False)
    gelato_webhook_secret = fields.Char(related='company_id.gelato_webhook_secret', readonly=False)
