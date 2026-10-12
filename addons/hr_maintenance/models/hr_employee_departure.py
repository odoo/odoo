# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrEmployeeDeparture(models.Model):
    _inherit = 'hr.employee.departure'

    def action_register(self):
        res = super().action_register()
        all_equipments = self.employee_id.equipment_ids
        for departure in self:
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
        return res
