from odoo import fields, models


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    hr_presence_section = fields.Selection(
        selection=[("state", "Set the presence"), ("follow_up", "Follow it up")],
        string="Presence Menu Section",
        help="Groups this action under the gear menu's Presence Control "
        "submenu, in the named section.",
    )

    def _get_fields_binding_extra(self) -> tuple[str, ...]:
        return (*super()._get_fields_binding_extra(), "hr_presence_section")
