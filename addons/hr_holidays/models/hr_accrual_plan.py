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
    accrual_ids = fields.One2many(
        'hr.accrual', 'plan_id',
        string='Accrual')
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, readonly=True, default=lambda self: self.env.company)
    employee_ids = fields.One2many('hr.employee', 'accrual_plan_id')
    allocation_ids = fields.One2many('hr.leave.allocation', 'accrual_plan_id')



class AccrualPlanLine(models.Model):
    _name = "hr.accrual"
    _description = "Accrual"
    _order = 'start_delta'

    name = fields.Char('Accrual Name', required=True)
    plan_id = fields.Many2one('hr.accrual.plan', "Accrual Plan")
    # Start date
    start_count = fields.Float("Start after", default=0, help="This field determines the number for the interval of time before the accrual plan starts.")
    start_type = fields.Selection(
        [('days', 'day(s)'), ('months', 'month(s)'), ('years', 'year(s)')], default='days', string=" ", help="This field determines the unit for the interval of time.", required=True)
    start_delta = fields.Datetime(compute="_compute_start_delta", store=True)
    # Accrue of
    added_hours = fields.Float("Hours per worked hours", required=True, help="The number of hours that will be incremented for every period")
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
    period = fields.Selection([
        ('first', 'on the first day'),
        ('last', 'on the last day'),
        ('first monday', 'on the first monday'),
        ('last friday', 'on the last friday')
    ], default='first')
    # Max accrual
    maximum = fields.Float('Maximum accrual hours', help="The maximum allocated hours. The hours above this limit will not be added")
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

    def _get_start_after_delta(self):
        delta = relativedelta(days=0)
        if self.start_type == 'days':
            delta = relativedelta(days=self.start_count)
        if self.start_type == 'months':
            delta = relativedelta(months=self.start_count)
        if self.start_type == 'years':
            delta = relativedelta(years=self.start_count)
        return delta

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


