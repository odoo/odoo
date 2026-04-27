from odoo import fields, models


class VoipProvider(models.Model):
    _name = "voip.provider"
    _description = "VoIP Provider"

    name = fields.Char(required=True)
    company_id = fields.Many2one("res.company", string="Company")

    ws_server = fields.Char(
        "WebSocket", help="The URL of your WebSocket", default="ws://localhost", groups="base.group_system",
    )
    pbx_ip = fields.Char(
        "PBX Server IP", help="The IP address of your PBX Server", default="localhost", groups="base.group_system",
    )
    mode = fields.Selection(
        [
            ("demo", "Demo"),
            ("prod", "Production"),
        ],
        string="VoIP Environment",
        default="demo",
        required=True,
    )
