# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPlanActivityType(models.Model):
    _name = 'hr.plan.activity.type'
    _description = 'Plan activity type'
    _rec_name = 'summary'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    activity_type_id = fields.Many2one(
        'mail.activity.type', 'Activity Type',
        default=lambda self: self.env.ref('mail.mail_activity_data_todo'),
        domain=lambda self: ['|', ('res_model', '=', False), ('res_model', '=', 'hr.employee')],
        ondelete='restrict'
    )
    summary = fields.Char('Summary', compute="_compute_default_summary", store=True, readonly=False)
    responsible = fields.Selection([
        ('coach', 'Coach'),
        ('manager', 'Manager'),
        ('employee', 'Employee'),
        ('other', 'Other')], default='employee', string='Responsible', required=True)
    responsible_id = fields.Many2one(
        'res.users',
        'Other Responsible',
        check_company=True,
        help='Specific responsible of activity if not linked to the employee.')
    plan_id = fields.Many2one('hr.plan')
    note = fields.Html('Note')

    @api.depends('activity_type_id')
    def _compute_default_summary(self):
        for plan_type in self:
            if plan_type.activity_type_id and plan_type.activity_type_id.summary:
                plan_type.summary = plan_type.activity_type_id.summary
            else:
                plan_type.summary = False

    def get_responsible_id(self, employee):
        warning = False
        if self.responsible == 'coach':
            if not employee.coach_id:
                warning = _('Coach of employee %s is not set.', employee.name)
            responsible = employee.coach_id.user_id
            if employee.coach_id and not responsible:
                warning = _("The user of %s's coach is not set.", employee.name)
        elif self.responsible == 'manager':
            if not employee.parent_id:
                warning = _('Manager of employee %s is not set.', employee.name)
            responsible = employee.parent_id.user_id
            if employee.parent_id and not responsible:
                warning = _("The manager of %s should be linked to a user.", employee.name)
        elif self.responsible == 'employee':
            responsible = employee.user_id
            if not responsible:
                warning = _('The employee %s should be linked to a user.', employee.name)
        elif self.responsible == 'other':
            responsible = self.responsible_id
            if not responsible:
                warning = _('No specific user given on activity %s.', self.activity_type_id.name)
        return {
            'responsible': responsible,
            'warning': warning,
        }
