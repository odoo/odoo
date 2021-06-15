# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPlanActivityType(models.Model):
    _name = 'hr.plan.activity.type'
    _description = 'Plan activity type'
    _rec_name = 'summary'

    _sql_constraints = [
        (
            'check_deadline_days', 'CHECK (COALESCE(deadline_days) >= 0)',
            'Days deadline must be positive.'
        ),
    ]

    activity_type_id = fields.Many2one(
        'mail.activity.type', 'Activity Type',
        default=lambda self: self.env.ref('mail.mail_activity_data_todo'),
        domain=lambda self: ['|', ('res_model_id', '=', False), ('res_model_id', '=', self.env['ir.model']._get('hr.employee').id)],
        ondelete='restrict'
    )
    summary = fields.Char('Summary', compute="_compute_default_summary", store=True, readonly=False)
    responsible = fields.Selection([
        ('coach', 'Coach'),
        ('manager', 'Manager'),
        ('employee', 'Employee'),
        ('other', 'Other')], default='employee', string='Responsible', required=True)
    responsible_id = fields.Many2one('res.users', 'Name', help='Specific responsible of activity if not linked to the employee.')
    note = fields.Html('Note')
    deadline_type = fields.Selection(
        [
            ('default', 'Default value'),
            ('plan_active', "At plan's activation"),
            ('trigger_offset', 'Days after activation trigger'),
        ],
        string='Activity Deadline',
        default='default',
        required=True,
    )
    deadline_days = fields.Integer(string='Days Deadline')
    company_id = fields.Many2one(
         'res.company',
         string='Company',
         default=lambda self: self.env.company,
     )

    @api.depends('activity_type_id')
    def _compute_default_summary(self):
        for plan_type in self:
            if not plan_type.summary and plan_type.activity_type_id and plan_type.activity_type_id.summary:
                plan_type.summary = plan_type.activity_type_id.summary

    def get_responsible_id(self, employee):
        if self.responsible == 'coach':
            if not employee.coach_id:
                raise UserError(_('Coach of employee %s is not set.', employee.name))
            responsible = employee.coach_id.user_id
            if not responsible:
                raise UserError(_('User of coach of employee %s is not set.', employee.name))
        elif self.responsible == 'manager':
            if not employee.parent_id:
                raise UserError(_('Manager of employee %s is not set.', employee.name))
            responsible = employee.parent_id.user_id
            if not responsible:
                raise UserError(_('User of manager of employee %s is not set.', employee.name))
        elif self.responsible == 'employee':
            responsible = employee.user_id
            if not responsible:
                raise UserError(_('User linked to employee %s is required.', employee.name))
        elif self.responsible == 'other':
            responsible = self.responsible_id
            if not responsible:
                raise UserError(_('No specific user given on activity %s.', self.activity_type_id.name))
        return responsible


class HrPlan(models.Model):
    _name = 'hr.plan'
    _description = 'plan'

    name = fields.Char('Name', required=True)
    plan_activity_type_ids = fields.Many2many('hr.plan.activity.type', string='Activities')
    active = fields.Boolean(default=True)
    plan_type = fields.Selection(
        [
            ('onboarding', 'Onboarding'),
            ('offboarding', 'Offboarding'),
            ('other', 'Other'),
        ], string='Type', default='onboarding', required=True,
    )
    trigger_onboarding = fields.Selection(
        [
            ('manual', 'Manual'),
            ('employee_creation', 'Employee Creation'),
        ], compute='_compute_triggers', inverse='_inverse_triggers',
        required=True, readonly=False,
    )
    trigger_offboarding = fields.Selection(
        [
            ('manual', 'Manual'),
            ('employee_archive', 'Archived Employee'),
        ], compute='_compute_triggers', inverse='_inverse_triggers',
        required=True, readonly=False,
    )
    trigger_other = fields.Selection(
        [
            ('manual', 'Manual'),
        ], compute='_compute_triggers', inverse='_inverse_triggers',
        required=True, readonly=False,
    )
    trigger = fields.Char(default='manual', compute='_compute_trigger', store=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.depends('trigger')
    def _compute_triggers(self):
        trigger_types = {'trigger_onboarding', 'trigger_offboarding', 'trigger_other'}
        type_to_trigger = {
            'onboarding': 'trigger_onboarding',
            'offboarding': 'trigger_offboarding',
            'other': 'trigger_other',
        }
        for record in self:
            #trigger for active
            record[type_to_trigger[record.plan_type]] = record.trigger or 'manual'
            #'manual' for all others
            for disabled_trigger in trigger_types - {type_to_trigger[record.plan_type]}:
                record[disabled_trigger] = 'manual'

    def _inverse_triggers(self):
        type_to_trigger = {
            'onboarding': 'trigger_onboarding',
            'offboarding': 'trigger_offboarding',
            'other': 'trigger_other',
        }
        for record in self:
            # or 'manual' required is for trigger_other since it can not be changed it's always False here
            record.trigger = record[type_to_trigger[record.plan_type]] or 'manual'

    @api.depends('plan_type')
    def _compute_trigger(self):
        # In case only plan_type changes
        type_to_trigger = {
            'onboarding': 'trigger_onboarding',
            'offboarding': 'trigger_offboarding',
            'other': 'trigger_other',
        }
        for record in self:
            record.trigger = record[type_to_trigger[record.plan_type]] or 'manual'
