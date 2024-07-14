# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    wsServer = fields.Char(
        "WebSocket", help="The URL of your WebSocket", default="ws://localhost", config_parameter="voip.wsServer"
    )
    pbx_ip = fields.Char(
        "PBX Server IP", help="The IP address of your PBX Server", default="localhost", config_parameter="voip.pbx_ip"
    )
    mode = fields.Selection(
        [
            ("demo", "Demo"),
            ("prod", "Production"),
        ],
        string="VoIP Environment",
        default="demo",
        config_parameter="voip.mode",
        required=True,
    )
