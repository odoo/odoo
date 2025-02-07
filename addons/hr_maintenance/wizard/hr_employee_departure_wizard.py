# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployeeDepartureWizard(models.TransientModel):
    _inherit = 'hr.employee.departure.wizard'

    do_unassign_equipment = fields.Boolean("Free Equiments", default=True, help="Unassign Employee from Equipments")

    def _get_departure_values(self):
        res = super()._get_departure_values()
        res['departure_do_unassign_equipment'] = self.do_unassign_equipment
        return res
