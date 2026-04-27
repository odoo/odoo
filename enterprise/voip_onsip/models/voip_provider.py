from odoo import fields, models


class VoipProvider(models.Model):
    _inherit = "voip.provider"

    ws_server = fields.Char(default="wss://edge.sip.onsip.com")
