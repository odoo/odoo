# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class IotBox(models.Model):
    _inherit = "iot.box"

    six_terminal_id = fields.Char(
        string="Six Terminal ID (TID)",
        help="The ID of your Six payment terminal. Please note that after entering this, you will have to wait several seconds before the terminal will appear in your device list.",
    )
