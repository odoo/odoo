# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class HrPlanActivityType(models.Model):
    _inherit = 'hr.plan.activity.type'

    responsible = fields.Selection(selection_add=[('fleet_manager', "Fleet Manager"), ('employee',)], ondelete={'fleet_manager': 'set default'})

    def get_responsible_id(self, employee):
        if self.responsible == 'fleet_manager':
            employee_id = self.env['hr.employee'].browse(employee._origin.id)
            vehicle = employee_id.car_ids[:1]
            warning = False
            if not vehicle:
                warning = _('Employee %s is not linked to a vehicle.', employee_id.name)
            if vehicle and not vehicle.manager_id:
                warning = _("Employee's vehicle %s is not linked to a fleet manager.", employee_id.name)
            return {
                'responsible': vehicle.manager_id,
                'warning': warning,
            }
        return super().get_responsible_id(employee)
