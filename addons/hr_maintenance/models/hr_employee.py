# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    departure_do_unassign_equipment = fields.Boolean("Free Equiments", default=True, groups="hr.group_hr_user",
        help="Unassign Employee from Equipments")

    def _register_departure(self):
        super()._register_departure()
        if not self.departure_do_unassign_equipment:
            return
        equipments = self.equipment_ids
        if equipments:
            self.write({'equipment_ids': [(3, equipment.id) for equipment in equipments]})
            if len(equipments) == 1:
                self.message_post(body=self.env._("1 equipment has been unlinked from %s", self.name))
            else:
                self.message_post(body=self.env._("%(equipments_count)s equipments have been unlinked from %(employee_name)s", equipments_count=len(equipments), employee_name=self.name))
            for equipment in equipments:
                equipment.message_post(body=self.env._("Equipment unlinked due to the end of collaboration with %s", self.name))
