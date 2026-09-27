# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MailActivityPlan(models.Model):
    _inherit = 'mail.activity.plan'

    department_id = fields.Many2one(
        'hr.department', check_company=True, index='btree_not_null',
        compute='_compute_department_id', ondelete='cascade', readonly=False, store=True)
    department_assignable = fields.Boolean(compute='_compute_department_assignable')

    @api.constrains('res_model')
    def _check_compatibility_with_model(self):
        """ Check that when the model is updated to a model different from employee,
        there are no remaining specific values to employee. """
        plan_tocheck = self.filtered(lambda plan: not plan.department_assignable)
        failing_plans = plan_tocheck.filtered('department_id')
        if failing_plans:
            raise UserError(
                _('Plan %(plan_names)s cannot use a department as it is used only for some HR plans.',
                  plan_names=', '.join(failing_plans.mapped('name')))
            )
        plan_tocheck = self.filtered(lambda plan: plan.res_model != 'hr.employee')
        failing_templates = plan_tocheck.template_ids.filtered(
            lambda tpl: tpl.responsible_type in {'coach', 'manager', 'employee'}
        )
        if failing_templates:
            raise UserError(
                _('Plan activities %(template_names)s cannot use coach, manager or employee responsible as it is used only for employee plans.',
                  template_names=', '.join(failing_templates.mapped('activity_type_id.name')))
            )

    @api.depends('res_model')
    def _compute_department_assignable(self):
        for plan in self:
            plan.department_assignable = plan.res_model == 'hr.employee'

    @api.depends('res_model')
    def _compute_department_id(self):
        for plan in self.filtered(lambda plan: not plan.department_assignable):
            plan.department_id = False
