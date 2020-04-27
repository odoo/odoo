# # -*- coding: utf-8 -*-

import datetime
import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

class AccrualPlan(models.Model):
    _name = "hr.accrual.plan"
    _description = "Accrual Plan"
    _order = 'sequence, id'

    name = fields.Char('Accrual Plan', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,default=lambda self: self.env.company)
    sequence = fields.Integer('Level', default=1)
    start_after_count = fields.Float(required=True,default=0)
    start_after_type = fields.Selection([('days', 'days'),('months', 'months'), ('years', 'years')],default='days')

    added_hours = fields.Float(required=True)
    maximum_hours = fields.Float('Maximum accrual hours')
   
    frequency = fields.Selection([
        ('daily','daily'),
        ('weekly','weekly'),
        ('every other week','every other week'),
        ('twice a month','twice a month'),
        ('monthly','monthly'),
        ('twice a year','twice a year'),
        ('quarterly','quarterly'),
        ('yearly','yearly'),
        ('anniversary','anniversary'),
        ('per hours worked','per hour worked')
        ], default='per hours worked')

    # pivot_ids=fields.One2many('hr.accrual.pivot', 'plan_id')

    period_weekday = fields.Selection('_weekdays', default='1')
    period_even_or_odd_week = fields.Selection('_even_or_odd_week', default='odd')

    period_day_1= fields.Selection('_dates', default='1')
    period_day_2 = fields.Selection('_dates', default='1')
    period_day_3 = fields.Selection('_dates', default='1')
    period_day_4 = fields.Selection('_dates', default='1')

    period_month_1 = fields.Selection('_months', default='1')
    period_month_2 = fields.Selection('_months', default='1')
    period_month_3 = fields.Selection('_months', default='1')
    period_month_4 = fields.Selection('_months', default='1')


    carryover_type=fields.Selection([('none','none'),('until','until'),('unlimited', 'unlimited')],string='Carryover', default='none')

    # Optionnal field depending on the carryover type
    carryover_amount=fields.Float()
    allow_negative_hours = fields.Boolean('Allow negative hours')

    def _weekdays(self):
        list=[('1','monday'),('2','tuesday'),('3','wednesday'),('4','thursday'),('5','friday'),('6','saturday'),('0','sunday')]
        return list

    def _dates(self):
        list=[]
        for d in range(1,32):
            day = str(d)
            if d%10 == 1:
                day +="st"
            elif d%10 == 2:
                day +="nd"
            elif d%10 == 3:
                day +="rd"
            else : 
                day += "th"
            list.append((str(d),day))
        return list

    def _months(self):
        list=[('1','January'),('2','February'),('3','March'),('4','April'),('5','May'),('6','June'),('7','July'),('8','August'),('9','September'),('10','October'),('11','November'),('12','December')]
        return list

    def _even_or_odd_week(self):
        return [('odd','odd'),('even','even')]




    