# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployeeDepartureWizard(models.TransientModel):
    _inherit = 'hr.employee.departure.wizard'

    do_unassign_campany_car = fields.Boolean("Release Company Car", default=lambda self: self.env.user.has_group('fleet.fleet_group_user'))

    def _get_departure_values(self):
        res = super()._get_departure_values()
        res['departure_do_unassign_campany_car'] = self.do_unassign_campany_car
        return res
