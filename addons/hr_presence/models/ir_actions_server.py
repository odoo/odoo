from odoo import fields, models

from odoo.addons.base.models.ir_actions_actions import IrActionsActions as BaseActions


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    hr_presence_section = fields.Selection(
        selection=[("state", "Set the presence"), ("follow_up", "Follow it up")],
        string="Presence Menu Section",
        help="Groups this action under the gear menu's Presence Control "
        "submenu, in the named section.",
    )


class IrActionsActions(models.Model):
    _inherit = "ir.actions.actions"

    # _get_bindings ships these to the client for whichever action model
    # declares them, so the section travels with the binding and the gear menu
    # needs no round-trip of its own.
    _BINDING_OPTIONAL_FIELDS = (
        *BaseActions._BINDING_OPTIONAL_FIELDS,
        "hr_presence_section",
    )
