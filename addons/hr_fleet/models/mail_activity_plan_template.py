# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo import exceptions


class MailActivityPlanTemplate(models.Model):
    _inherit = 'mail.activity.plan.template'

    responsible_type = fields.Selection(
        selection_add=[('fleet_manager', "Fleet Manager")],
        ondelete={'fleet_manager': 'set default'})

    @api.constrains('plan_id', 'responsible_type')
    def _check_responsible_hr_fleet(self):
        """ Ensure that hr types are used only on employee model """
        for template in self.filtered(lambda tpl: tpl.plan_id.res_model != 'hr.employee'):
            if template.responsible_type == 'fleet_manager':
                raise exceptions.ValidationError(_("Fleet Manager is limited to Employee plans."))

    def _determine_responsible(self, on_demand_responsible, employee):
        if self.responsible_type == 'fleet_manager' and self.plan_id.res_model == 'hr.employee':
            employee_id = self.env['hr.employee'].browse(employee._origin.id)
            vehicle = employee_id.car_ids[:1]
            error = False
            if not vehicle:
                error = _('Employee %s is not linked to a vehicle.', employee_id.name)
            if vehicle and not vehicle.manager_id:
                error = _("The vehicle of employee %(employee)s is not linked to a fleet manager.", employee=employee_id.name)
            return {
                'responsible': vehicle.manager_id,
                'error': error,
            }
        return super()._determine_responsible(on_demand_responsible, employee)
