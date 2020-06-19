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
    line_ids = fields.One2many(
        'hr.accrual.plan.line', 'plan_id',
        string='Accrual Plan Lines')
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, readonly=True, default=lambda self: self.env.company)


class AccrualPlanLine(models.Model):
    _name = "hr.accrual.plan.line"
    _description = "Accrual Plan Line"
    _order = 'start_delta'

    name = fields.Char('Level name', required=True)
    plan_id = fields.Many2one('hr.accrual.plan', "Accrual Plan")

    # Period of time after which the line start
    start_count = fields.Float("Start after", default=0, help="This field determines the number for the interval of time before the accrual plan starts.")
    start_type = fields.Selection(
        [('days', 'day(s)'), ('months', 'month(s)'), ('years', 'year(s)')], default='days', string=" ", help="This field determines the unit for the interval of time.", required=True)
    start_delta = fields.Datetime(compute="_compute_start_delta", store=True)

    # Hours incrementation
    added_hours = fields.Float("Hours", required=True, help="The number of hours that will be incremented for every period")
    maximum_hours = fields.Float('Maximum accrual hours', help="The maximum allocated hours. The hours above this limit will not be added")

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
        ('anniversary', "on the anniversary of the employee's hire date"),
        ('per hours worked', 'per hour worked')
    ], default='per hours worked', required=True,
    help="Per hours worked: Time off are accrualed only if this is mentionned on Work Entry (see field 'Work entry type' on related Time Off type. If 'Keep Time Off Right' is selected; the wrok entry is considered.")

    # Optionnal fields depending on the frequency
    period_weekday = fields.Selection(string="Day of week",
                                      selection=[('mon', 'monday'), ('tue', 'tuesday'), (
                                          'wed', 'wednesday'), ('thu', 'thursday'), ('fri', 'friday'), ('sat', 'saturday'), ('sun', 'sunday')],
                                      default='mon', required=True)
    period_weekday_number = fields.Integer(string="Day of week in number", compute="_compute_period_weekday_number")
    period_even_or_odd_week = fields.Selection(
        [('odd', 'odd'), ('even', 'even')], default='odd', required=True)

    # The line uses 4 days and months used to cover every use case of frequency
    period_day_1 = fields.Selection('_dates', default='1', required=True)
    period_day_2 = fields.Selection('_dates', default='16', required=True)
    period_day_3 = fields.Selection('_dates', default='1', required=True)
    period_day_4 = fields.Selection('_dates', default='1', required=True)

    period_month_1 = fields.Selection([('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'), ('5', 'May'), ('6', 'June'),
                ('7', 'July'), ('8', 'August'), ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')], default='1', required=True)
    period_month_2 = fields.Selection([('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'), ('5', 'May'), ('6', 'June'),
                ('7', 'July'), ('8', 'August'), ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')], default='1', required=True)
    period_month_3 = fields.Selection([('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'), ('5', 'May'), ('6', 'June'),
                ('7', 'July'), ('8', 'August'), ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')], default='7', required=True)
    period_month_4 = fields.Selection([('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'), ('5', 'May'), ('6', 'June'),
                ('7', 'July'), ('8', 'August'), ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')], default='10', required=True)

    carryover_type = fields.Selection([('none', 'none'), ('until', 'until'), (
        'unlimited', 'unlimited')], string='Carryover', default='none', required=True)

    # Optionnal field depending on the carryover type
    carryover_amount = fields.Float()
    allow_negative_hours = fields.Boolean('Negative hours')

    def _dates(self):
        list = []
        for d in range(1, 32):
            day = str(d)
            if d % 10 == 1 and d !=11:
                day += "st"
            elif d % 10 == 2:
                day += "nd"
            elif d % 10 == 3:
                day += "rd"
            else:
                day += "th"
            list.append((str(d), day))
        return list

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

    @api.depends('start_delta', 'start_count', 'start_type')
    def _compute_start_delta(self):
        year_zero = datetime.datetime(1, 1, 1)
        for record in self :
            delta = relativedelta(days=0)
            if record.start_type == 'days':
                delta = relativedelta(days=record.start_count)
            if record.start_type == 'months':
                delta = relativedelta(months=record.start_count)
            if record.start_type == 'years':
                delta = relativedelta(years=record.start_count)
            record.start_delta = year_zero + delta

    @api.onchange('frequency')
    def _on_change_frequency(self):
        #Initiate the default values for the periods
        self.period_day_1 = '1'
        self.period_day_2 = '1'
        self.period_day_3 = '1'
        self.period_day_4 = '1'
        self.period_month_3 = '7'
        self.period_month_4 = '10'
        if self.frequency == 'twice a month':
            self.period_day_2 = '16'
        if self.frequency == 'twice a year':
            self.period_day_2 = '1'
            self.period_month_2 = '7'
        if self.frequency == 'quarterly':
            self.period_day_2 = '1'
            self.period_month_2 = '4'

