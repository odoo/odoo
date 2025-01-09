# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gelato_api_key = fields.Char(
        string="API KEY",
        related='company_id.gelato_api_key',
        readonly=False
    )
    gelato_webhook_secret = fields.Char(
        string="Webhook secret",
        related='company_id.gelato_webhook_secret',
        readonly=False
    )
