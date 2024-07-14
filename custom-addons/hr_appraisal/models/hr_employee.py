# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    next_appraisal_date = fields.Date(
        string='Next Appraisal Date', compute='_compute_next_appraisal_date', groups="hr.group_hr_user", readonly=False, store=True,
        help="The date of the next appraisal is computed by the appraisal plan's dates (first appraisal + periodicity).")
    last_appraisal_date = fields.Date(
        string='Last Appraisal Date', groups="hr.group_hr_user",
        help="The date of the last appraisal")
    related_partner_id = fields.Many2one('res.partner', compute='_compute_related_partner', groups="hr.group_hr_user")
    ongoing_appraisal_count = fields.Integer(compute='_compute_ongoing_appraisal_count', store=True, groups="hr.group_hr_user")
    appraisal_count = fields.Integer(compute='_compute_appraisal_count', store=True, groups="hr.group_hr_user")
    uncomplete_goals_count = fields.Integer(compute='_compute_uncomplete_goals_count')
    appraisal_ids = fields.One2many('hr.appraisal', 'employee_id')

    @api.constrains('next_appraisal_date')
    def _check_next_appraisal_date(self):
        today = fields.Date.today()
        if not self.env.context.get('install_mode') and any(employee.next_appraisal_date and employee.next_appraisal_date < today for employee in self):
            raise ValidationError(_("You cannot set 'Next Appraisal Date' in the past."))

    def _compute_related_partner(self):
        for rec in self:
            rec.related_partner_id = rec.user_id.partner_id

    @api.depends('appraisal_ids')
    def _compute_appraisal_count(self):
        read_group_result = self.env['hr.appraisal'].with_context(active_test=False)._read_group([('employee_id', 'in', self.ids)], ['employee_id'], ['__count'])
        result = {employee.id: count for employee, count in read_group_result}
        for employee in self:
            employee.appraisal_count = result.get(employee.id, 0)

    @api.depends('appraisal_ids.state')
    def _compute_ongoing_appraisal_count(self):
        read_group_result = self.env['hr.appraisal'].with_context(active_test=False)._read_group([('employee_id', 'in', self.ids), ('state', 'in', ['new', 'pending'])], ['employee_id'], ['__count'])
        result = {employee.id: count for employee, count in read_group_result}
        for employee in self:
            employee.ongoing_appraisal_count = result.get(employee.id, 0)

    def _compute_uncomplete_goals_count(self):
        read_group_result = self.env['hr.appraisal.goal']._read_group([('employee_id', 'in', self.ids), ('progression', '!=', '100')], ['employee_id'], ['__count'])
        result = {employee.id: count for employee, count in read_group_result}
        for employee in self:
            employee.uncomplete_goals_count = result.get(employee.id, 0)

    @api.depends('ongoing_appraisal_count', 'company_id.appraisal_plan')
    def _compute_next_appraisal_date(self):
        self.filtered('ongoing_appraisal_count').next_appraisal_date = False
        employees_without_appraisal = self.filtered(lambda e: e.ongoing_appraisal_count == 0)
        dates = employees_without_appraisal._upcoming_appraisal_creation_date()
        for employee in employees_without_appraisal:
            employee.next_appraisal_date = dates[employee.id]

    def _upcoming_appraisal_creation_date(self):
        today = fields.Date.today()
        dates = {}
        for employee in self:
            if employee.appraisal_count == 0:
                months = employee.company_id.duration_after_recruitment
                starting_date = employee._get_appraisal_plan_starting_date() or today
            else:
                months = employee.company_id.duration_first_appraisal if employee.appraisal_count == 1 else employee.company_id.duration_next_appraisal
                starting_date = employee.last_appraisal_date

            if starting_date:
                # In case proposed next_appraisal_date is in the past, start counting from now
                starting_date = starting_date.date() if isinstance(starting_date, datetime.datetime) else starting_date
                original_next_appraisal_date = starting_date + relativedelta(months=months)
                dates[employee.id] = original_next_appraisal_date if original_next_appraisal_date >= today else today + relativedelta(months=months)
            else:
                dates[employee.id] = today + relativedelta(months=months)
        return dates

    def _get_appraisal_plan_starting_date(self):
        self.ensure_one()
        return self.create_date
