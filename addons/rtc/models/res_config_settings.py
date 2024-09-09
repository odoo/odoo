# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sfu_server_url = fields.Char("SFU Server URL", config_parameter="rtc.sfu_server_url")
    sfu_server_key = fields.Char("SFU Server key", config_parameter="rtc.sfu_server_key", help="Base64 encoded key")
