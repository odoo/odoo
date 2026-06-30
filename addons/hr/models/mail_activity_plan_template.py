# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MailActivityPlanTemplate(models.Model):
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

    def _get_closest_parent_user(self, employee, responsible, error_message):
        responsible_parent = responsible
        viewed_responsible = [employee]
        while True:
            if not responsible_parent:
                return {
                    'error': False,
                    'responsible': self.env.user,
                    'warning': error_message
                }
            if responsible_parent.user_id:
                return {
                    'error': False,
                    'responsible': responsible_parent.user_id,
                    'warning': False
                }
            if responsible_parent in viewed_responsible:
                return {
                    "error": _(
                        "Oops! It seems there is a problem with your team structure.\
                        We found a circular reporting loop and no one in that loop is linked to a user.\
                        Please double-check that everyone reports to the correct manager."
                    ),
                    'warning': False,
                    "responsible": False,
                }
            else:
                viewed_responsible.append(responsible_parent)
                responsible_parent = responsible_parent.parent_id

    def _determine_responsible(self, on_demand_responsible, employee):
        if self.plan_id.res_model != 'hr.employee' or self.responsible_type not in {'coach', 'manager', 'employee'}:
            return super()._determine_responsible(on_demand_responsible, employee)
        result = {"error": "", "warning": "", "responsible": False}
        if self.responsible_type == 'coach':
            if not employee.coach_id:
                result['error'] = _('Coach of employee %s is not set.', employee.name)
            result['responsible'] = employee.coach_id.user_id
            if employee.coach_id and not result['responsible']:
                # If a plan cannot be launched due to the coach not being linked to an user,
                # attempt to assign it to the coach's manager user. If that manager is also not linked
                # to an user, continue searching upwards until a manager with a linked user is found.
                # If no one is found still, assign to current user.
                result = self._get_closest_parent_user(
                    employee=employee,
                    responsible=employee.coach_id.parent_id,
                    error_message=_(
                        "The user of %s's coach is not set.", employee.name
                    ),
                )

        elif self.responsible_type == 'manager':
            if not employee.parent_id:
                result['error'] = _('Manager of employee %s is not set.', employee.name)
            result['responsible'] = employee.parent_id.user_id
            if employee.parent_id and not result['responsible']:
                # If a plan cannot be launched due to the manager not being linked to an user,
                # attempt to assign it to the manager's manager user. If that manager is also not linked
                # to an user, continue searching upwards until a manager with a linked user is found.
                # If no one is found still, assign to current user.
                result = self._get_closest_parent_user(
                    employee=employee,
                    responsible=employee.parent_id.parent_id,
                    error_message=_(
                        "The manager of %s should be linked to a user.", employee.name
                    ),
                )

        elif self.responsible_type == 'employee':
            result['responsible'] = employee.user_id
            if not result['responsible']:
                # If a plan cannot be launched due to the employee not being linked to an user,
                # attempt to assign it to the manager's user. If the manager is also not linked
                # to an user, continue searching upwards until a manager with a linked user is found.
                # If no one is found still, assign to current user.
                result = self._get_closest_parent_user(
                    employee=employee,
                    responsible=employee.parent_id,
                    error_message=_(
                        "The employee %s should be linked to a user.", employee.name
                    ),
                )

        if result['error'] or result['responsible']:
            return result
