# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class MailActivityPlanTemplate(models.Model):
    _inherit = 'mail.activity.plan.template'

    responsible_type = fields.Selection(selection_add=[('fleet_manager', "Fleet Manager"), ('employee',)], ondelete={'fleet_manager': 'set default'})

    def _determine_responsible(self, on_demand_responsible, employee):
        if self.responsible_type == 'fleet_manager':
            employee_id = self.env['hr.employee'].browse(employee._origin.id)
            vehicle = employee_id.car_ids[:1]
            error = False
            if not vehicle:
                error = _('Employee %s is not linked to a vehicle.', employee_id.name)
            if vehicle and not vehicle.manager_id:
                error = _("Employee's vehicle %s is not linked to a fleet manager.", employee_id.name)
            return {
                'responsible': vehicle.manager_id,
                'error': error,
            }
        return super()._determine_responsible(on_demand_responsible, employee)
