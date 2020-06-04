# # -*- coding: utf-8 -*-

import datetime
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class AccrualPlan(models.Model):
    _name = "hr.accrual.plan"
    _description = "Accrual Plan"

    name = fields.Char('Accrual Plan', required=True)
    line_ids = fields.Many2many(
        'hr.accrual.plan.line',
        string='Lines')
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, readonly=True, default=lambda self: self.env.company)


class AccrualPlanLine(models.Model):
    _name = "hr.accrual.plan.line"
    _description = "Accrual Plan Line"
    _order = 'sequence'

    # Order
    sequence = fields.Integer('Level', default=1)

    # Period of time after which the line start
    start_count = fields.Float("Start after", required=True, default=0)
    start_type = fields.Selection(
        [('days', 'days'), ('months', 'months'), ('years', 'years')], default='days', string=" ")

    # Hours incrementation
    added_hours = fields.Float("Hours", required=True)
    maximum_hours = fields.Float('Maximum')

    # Frequency of incrementation
    frequency = fields.Selection([
        ('daily', 'daily'),
        ('weekly', 'weekly'),
        ('every other week', 'every other week'),
        ('twice a month', 'twice a month'),
        ('monthly', 'monthly'),
        ('twice a year', 'twice a year'),
        ('quarterly', 'quarterly'),
        ('yearly', 'yearly'),
        ('anniversary', 'anniversary'),
        ('per hours worked', 'per hour worked')
    ], default='per hours worked')

    # Optionnal fields depending on the frequency
    period_weekday = fields.Selection(string="Day of week",
                                      selection=[('mon', 'monday'), ('tue', 'tuesday'), (
                                          'wed', 'wednesday'), ('thu', 'thursday'), ('fri', 'friday'), ('sat', 'saturday'), ('sun', 'sunday')],
                                      default='monday')
    period_weekday_number = fields.Integer(string="Day of week in number", compute="_compute_period_weekday_number")
    period_even_or_odd_week = fields.Selection(
        '_even_or_odd_week', default='odd')

    # The line uses 4 days and months used to cover every use case of frequency
    period_day_1 = fields.Selection('_dates', default='1')
    period_day_2 = fields.Selection('_dates', default='1')
    period_day_3 = fields.Selection('_dates', default='1')
    period_day_4 = fields.Selection('_dates', default='1')

    period_month_1 = fields.Selection('_months', default='1')
    period_month_2 = fields.Selection('_months', default='1')
    period_month_3 = fields.Selection('_months', default='1')
    period_month_4 = fields.Selection('_months', default='1')

    carryover_type = fields.Selection([('none', 'none'), ('until', 'until'), (
        'unlimited', 'unlimited')], string='Carryover', default='none')

    # Optionnal field depending on the carryover type
    carryover_amount = fields.Float()
    allow_negative_hours = fields.Boolean('Negative hours')

    def _dates(self):
        list = []
        for d in range(1, 32):
            day = str(d)
            if d % 10 == 1:
                day += "st"
            elif d % 10 == 2:
                day += "nd"
            elif d % 10 == 3:
                day += "rd"
            else:
                day += "th"
            list.append((str(d), day))
        return list

    def _months(self):
        list = [('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'), ('5', 'May'), ('6', 'June'),
                ('7', 'July'), ('8', 'August'), ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')]
        return list

    def _even_or_odd_week(self):
        return [('odd', 'odd'), ('even', 'even')]

    def _get_start_after_delta(self):
        delta = relativedelta(days=0)
        if self.start_type == 'days':
            delta = relativedelta(days=self.start_count)
        if self.start_type == 'months':
            delta = relativedelta(months=self.start_count)
        if self.start_type == 'years':
            delta = relativedelta(years=self.start_count)
        return delta

    @api.depends('period_weekday')
    def _compute_period_weekday_number(self):
        for record in self:
            if record.period_weekday =='sun':
                record.period_weekday_number = 0
            if record.period_weekday =='mon':
                record.period_weekday_number = 1
            if record.period_weekday =='tue':
                record.period_weekday_number = 2
            if record.period_weekday =='wed':
                record.period_weekday_number = 3
            if record.period_weekday =='thu':
                record.period_weekday_number = 4
            if record.period_weekday =='fri':
                record.period_weekday_number = 5
            if record.period_weekday =='sat':
                record.period_weekday_number = 6

            

