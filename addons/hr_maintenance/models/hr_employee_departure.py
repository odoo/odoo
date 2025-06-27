# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployeeDeparture(models.Model):
    _inherit = 'hr.employee.departure'

    do_unassign_equipment = fields.Boolean("Free Equiments", default=True, help="Unassign Employee from Equipments")

    def action_register(self):
        super().action_register()
        departure_with_unassign = self.filtered(lambda dep: dep.do_unassign_equipment)
        if not departure_with_unassign:
            return
        all_equipments = departure_with_unassign.employee_id.equipment_ids
        for departure in departure_with_unassign:
            equipments = departure.employee_id.equipment_ids
            if not equipments:
                continue
            if len(equipments) == 1:
                departure.employee_id.message_post(body=self.env._("1 equipment has been unassigned from %s", self.employee_id.name))
            else:
                departure.employee_id.message_post(body=self.env._(
                    "%(equipments_count)s equipments have been unassigned from %(employee_name)s",
                    equipments_count=len(equipments),
                    employee_name=departure.employee_id.name,
                ))
            for equipment in equipments:
                equipment.message_post(body=self.env._(
                    "Equipment unassigned due to the end of collaboration with %s",
                    departure.employee_id.name,
                ))
        all_equipments.sudo().write({'employee_id': False})
