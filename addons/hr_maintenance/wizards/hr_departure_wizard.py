from odoo import Command, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrDepartureWizard(models.TransientModel):
    _inherit = "hr.departure.wizard"

    unassign_equipment = fields.Boolean(
        string="Free Equiments",
        default=True,
        help="Unassign Employee from Equipments",
    )

    def action_register_departure(self):
        action = super().action_register_departure()
        if self.unassign_equipment:
            _debug.pipeline(
                "departure_unassigns_equipment",
                employees=self.employee_ids,
                equipments=self.employee_ids.equipment_ids,
            )
            self.employee_ids.write({"equipment_ids": [Command.clear()]})
        return action
