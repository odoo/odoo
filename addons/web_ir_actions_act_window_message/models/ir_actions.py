# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class IrActionsActWindowMessage(models.Model):
    _name = "ir.actions.act_window.message"
    _description = "Action Window Message"
    _inherit = "ir.actions.actions"
    _table = "ir_actions"

    type = fields.Char(default="ir.actions.act_window.message")

    def _get_readable_fields(self):
        return super()._get_readable_fields() | {
            "title",
            "buttons",
            "close_button_title",
            "message",
            "is_html_message",
        }
