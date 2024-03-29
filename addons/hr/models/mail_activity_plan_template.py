# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MailActivityPLanTemplate(models.Model):
    _inherit = 'mail.activity.plan.template'

    responsible_type = fields.Selection(selection_add=[
        ('coach', 'Coach'),
        ('manager', 'Manager'),
        ('employee', 'Employee'),
    ], ondelete={'coach': 'cascade', 'manager': 'cascade', 'employee': 'cascade'})

    @api.constrains('plan_id', 'responsible_type')
    def _check_responsible_hr(self):
        """ Ensure that hr types are used only on employee model """
        for template in self.filtered(lambda tpl: tpl.plan_id.res_model != 'hr.employee'):
            if template.responsible_type in {'coach', 'manager', 'employee'}:
                raise ValidationError(_('Those responsible types are limited to Employee plans.'))

    def _determine_responsible(self, on_demand_responsible, employee):
        if self.plan_id.res_model != 'hr.employee' or self.responsible_type not in {'coach', 'manager', 'employee'}:
            return super()._determine_responsible(on_demand_responsible, employee)
        error = False
        responsible = False
        if self.responsible_type == 'coach':
            if not employee.coach_id:
                error = _('Coach of employee %s is not set.', employee.name)
            responsible = employee.coach_id.user_id
            if employee.coach_id and not responsible:
                error = _("The user of %s's coach is not set.", employee.name)
        elif self.responsible_type == 'manager':
            if not employee.parent_id:
                error = _('Manager of employee %s is not set.', employee.name)
            responsible = employee.parent_id.user_id
            if employee.parent_id and not responsible:
                error = _("The manager of %s should be linked to a user.", employee.name)
        elif self.responsible_type == 'employee':
            responsible = employee.user_id
            if not responsible:
                error = _('The employee %s should be linked to a user.', employee.name)
        if error or responsible:
            return {
                'responsible': responsible,
                'error': error,
            }
