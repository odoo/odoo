# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployeeDeparture(models.Model):
    _inherit = ['hr.employee.departure']

    do_unassign_equipment = fields.Boolean("Free Equiments", default=True, help="Unassign Employee from Equipments")

    def action_register_departure(self):
        super().action_register_departure()
        if self.do_unassign_equipment:
            equipments = self.employee_id.equipment_ids
            if equipments:
                self.employee_id.write({'equipment_ids': [(3, equipment.id) for equipment in equipments]})
                if len(equipments) == 1:
                    self.employee_id.message_post(body=self.env._("1 equipment has been unlinked from %s", self.employee_id.name))
                else:
                    self.employee_id.message_post(body=self.env._("%(equipments_count)s equipments have been unlinked from %(employee_name)s", equipments_count=len(equipments), employee_name=self.employee_id.name))
                for equipment in equipments:
                    equipment.message_post(body=self.env._("Equipment unlinked due to the end of collaboration with %s", self.employee_id.name))
