# # -*- coding: utf-8 -*-

import datetime
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import datetime, time

_logger = logging.getLogger(__name__)


class AccrualPlan(models.Model):
    _name = "hr.accrual.plan"
    _description = "Accrual Plan"

    name = fields.Char('Accrual Plan', required=True)
    accrual_ids = fields.One2many(
        'hr.accrual', 'plan_id',
        string='Accrual')
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, readonly=True, default=lambda self: self.env.company)
    employee_ids = fields.One2many('hr.employee', 'accrual_plan_id')
    allocation_ids = fields.One2many('hr.leave.allocation', 'accrual_plan_id')
    employees_count = fields.Integer("Employees", compute='_compute_employees_count')

    @api.depends('employee_ids')
    def _compute_employees_count(self):
        for plan in self:
            plan.employees_count = len(plan.employee_ids)

    def _get_accrual_line(self, employee):
        # Get the appropriate accrual line accorded to the start date of an employee
        line = False
        date_start_work = datetime.combine(employee._get_date_start_work(), time(0, 0, 0))
        today = datetime.combine(fields.Date.today(), time(0, 0, 0))
        for accrual_line in self.accrual_ids:
            if today > date_start_work + accrual_line._get_start_after_delta():
                if line:
                    if (date_start_work + line._get_start_after_delta()) < (
                            date_start_work + accrual_line._get_start_after_delta()):
                        line = accrual_line
                else:
                    line = accrual_line
            else:
                break
        return line

    def action_open_accrual_plan_employees(self):
        self.ensure_one()
        return {
            'name': _("Accrual Plan's Employees"),
            'type': 'ir.actions.act_window',
            'view_type': 'kanban',
            'view_mode': 'kanban',
            'res_model': 'hr.employee',
            'domain': [('accrual_plan_id', '=', self.id)],
        }

class AccrualPlanLine(models.Model):
    _name = "hr.accrual"
    _description = "Accrual"
    _order = 'start_delta'

    name = fields.Char('Accrual Name', required=True)
    plan_id = fields.Many2one('hr.accrual.plan', "Accrual Plan")
    # Start date
    start_count = fields.Float("Start after", help="This field determines the number for the interval of time before the accrual plan starts.")
    start_type = fields.Selection(
        [('days', 'day(s)'), ('months', 'month(s)'), ('years', 'year(s)')], default='days', string=" ", help="This field determines the unit for the interval of time.", required=True)
    start_delta = fields.Datetime(compute="_compute_start_delta", store=True)
    # Accrue of
    added_hours = fields.Float("Hours per worked days", required=True, help="The number of hours that will be incremented for every period")
    # Accrual period
    frequency = fields.Selection([
        ('daily', 'daily'),
        ('weekly', 'weekly'),
        ('twice a month', 'twice a month'),
        ('monthly', 'monthly'),
        ('twice a year', 'twice a year'),
        ('quarterly', 'quarterly'),
        ('yearly', 'yearly'),
        ('anniversary', 'anniversary'),
    ], default='daily', required=True)
    start_of_period = fields.Selection([
        ('first', 'on the first day'),
        ('last', 'on the last day'),
        ('first monday', 'on the first monday'),
        ('last friday', 'on the last friday')
    ], default='first')
    # Max accrual
    maximum = fields.Float('Maximum accrual hours', help="The maximum allocated hours. The hours above this limit will not be added", default="1000")
    maximum_type = fields.Selection([
        ('hours', 'hours'),
        ('days', 'days'),
    ], default='hours')
    maximum_period = fields.Selection([
        ('period', 'period'),
        ('days','days'),
        ('weeks', 'weeks'),
        ('months', 'months'),
        ('years', 'years'),
    ], default='days')

    @api.depends('start_delta', 'start_count', 'start_type')
    def _compute_start_delta(self):
        year_zero = datetime(1, 1, 1)
        for record in self :
            delta = relativedelta(days=0)
            if record.start_type == 'days':
                delta = relativedelta(days=record.start_count)
            if record.start_type == 'months':
                delta = relativedelta(months=record.start_count)
            if record.start_type == 'years':
                delta = relativedelta(years=record.start_count)
            record.start_delta = year_zero + delta

    def _get_start_after_delta(self):
        self.ensure_one()
        delta = relativedelta(days=0)
        if self.start_type == 'days':
            delta = relativedelta(days=self.start_count)
        if self.start_type == 'months':
            delta = relativedelta(months=self.start_count)
        if self.start_type == 'years':
            delta = relativedelta(years=self.start_count)
        return delta

    def _get_period(self, employee):
        # Find the first day of the next and previous periods
        period ={}
        next = False
        previous = False
        today = datetime.combine(fields.Date.today(), time(0, 0, 0))
        start_date = datetime.combine(employee._get_date_start_work(), time(0, 0, 0))

        if self.frequency == 'daily':
            next = today + relativedelta(days=1)
            previous = today

        if self.frequency == 'weekly':
            if self.start_of_period in ["first monday", "first"]:
                next = self._get_next_weekday(today, 1)
            elif self.start_of_period == "last":
                next = self._get_next_weekday(today, 4)
            else:
                next = self._get_next_weekday(today, 6)
            previous = next - relativedelta(days=7)

        if self.frequency == 'twice a month':
            if self.start_of_period.startswith("first"):
                previous = today.replace(day=1)
                if self.start_of_period == "first monday":
                    previous = self._get_next_weekday(previous, 1)
                next = previous + relativedelta(days=14)
                if next < today:
                    previous = next
                    next = today.replace(day=1) + relativedelta(months=1)
            elif self.start_of_period.startswith("last"):
                next = self._get_month_last_day(today)
                if self.start_of_period == "last friday":
                    next = self._get_previous_weekday(next, 5)
                previous = next - relativedelta(days=14)
                if today < previous:
                    next = previous
                    previous = self._get_month_last_day(today - relativedelta(months=1))
                    if self.start_of_period == "last friday":
                        previous = self._get_previous_weekday(previous, 5)

        if self.frequency == 'monthly':
            if self.start_of_period.startswith("first"):
                next = today.replace(day=1) + relativedelta(months=1)
                previous = next - relativedelta(months=1)
                if self.start_of_period == "first monday":
                    next = self._get_next_weekday(next, 1)
                    previous = self._get_next_weekday(previous, 1)
            elif self.start_of_period.startswith("last"):
                next = self._get_month_last_day(today)
                previous = self._get_month_last_day(today - relativedelta(months=1))
                if self.start_of_period == "last friday":
                    next = self._get_previous_weekday(next, 5)
                    previous = self._get_previous_weekday(previous, 5)

        if self.frequency == 'twice a year':
            first_period = datetime(today.year, 1, 1)
            second_period = datetime(today.year, 7, 1)
            if today < first_period or today >= second_period:
                next = first_period.replace(year=today.year + 1)
                previous = second_period
            else:
                next = second_period
                previous = first_period

        if self.frequency == 'quarterly':
            period_1 = datetime(today.year, 1, 1)
            period_2 = datetime(today.year, 4, 1)
            period_3 = datetime(today.year, 7, 1)
            period_4 = datetime(today.year, 10, 1)
            if today >= period_4:
                next = period_1 + relativedelta(years=1)
                previous = period_4
            elif today >= period_3:
                next = period_4
                previous = period_3
            elif today >= period_2:
                next = period_3
                previous = period_2
            else:
                next = period_2
                previous = period_1

        if self.frequency == 'yearly':
            next = datetime(today.year, 1, 1)
            if today >= next:
                next += relativedelta(years=1)
            previous = next - relativedelta(years=1)

        if self.frequency == 'anniversary':
            next = datetime(today.year, int(start_date.month), int(start_date.day))
            if today >= next:
                next += relativedelta(years=1)
            previous = next - relativedelta(years=1)

        # Adapt the period if the employee has started his contract in it
        if previous < start_date and start_date < next:
            previous = start_date
        period['next'] = next
        period['previous'] = previous
        return period

    def _get_month_last_day(self, day):
        next_month = day.replace(day=28) + relativedelta(days=4)
        last_day = next_month - relativedelta(days=next_month.day)
        return last_day

    def _get_next_weekday(self, day, weekday):
        days_ahead = weekday - int(day.strftime("%w"))
        if days_ahead <= 0:
            days_ahead += 7
        return day + relativedelta(days=days_ahead)

    def _get_previous_weekday(self, day, weekday):
        days_before = int(day.strftime("%w")) - weekday
        if days_before <= 0:
            days_before += 7
        return day - relativedelta(days=days_before)
