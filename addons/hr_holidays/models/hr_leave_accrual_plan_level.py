# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import calendar

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools.date_utils import get_timedelta


DAYS = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

def _get_date_check_month(year, month, day):
    """
    Returns the day it would be if day is outside of the month's range
    Example: 2021 feb 30 -> 2021 mar 2
    """
    month_range = calendar.monthrange(year, month)
    if day > month_range[1]:
        return datetime.date(year, month, min(day, month_range[1])) + relativedelta(days=(day - month_range[1]))
    return datetime.date(year, month, day)

class AccrualPlanLevel(models.Model):
    _name = "hr.leave.accrual.level"
    _description = "Accrual Plan Level"
    _order = 'sequence asc'

    sequence = fields.Integer(
        string='sequence', compute='_compute_sequence', store=True,
        help='Sequence is generated automatically by start time delta.')
    level = fields.Integer(compute='_compute_level', help='Level computed through the sequence.')
    accrual_plan_id = fields.Many2one('hr.leave.accrual.plan', "Accrual Plan", required=True)
    start_count = fields.Integer(
        "Start after",
        help="The accrual starts after a defined period from the employee start date. This field define the number of days, month or years after which accrual is used.", default="1")
    start_type = fields.Selection(
        [('day', 'day(s)'),
         ('month', 'month(s)'),
         ('year', 'year(s)')],
        default='day', string=" ", required=True,
        help="This field define the unit of time after which the accrual starts.")
    is_based_on_worked_time = fields.Boolean("Based on worked time")

    # Accrue of
    added_value = fields.Float(
        "Gain", required=True,
        help="The number of days that will be incremented for every period")
    added_value_type = fields.Selection(
        [('days', 'Days'),
         ('hours', 'Hours')],
        default='days', required=True)
    frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('bimonthly', 'Twice a month'),
        ('monthly', 'Monthly'),
        ('biyearly', 'Twice a year'),
        ('yearly', 'Yearly'),
    ], default='daily', required=True, string="Frequency")
    week_day = fields.Selection([
        ('mon', 'Monday'),
        ('tue', 'Tuesday'),
        ('wed', 'Wednesday'),
        ('thu', 'Thursday'),
        ('fri', 'Friday'),
        ('sat', 'Saturday'),
        ('sun', 'Sunday'),
    ], default='mon', required=True, string="Allocation on")
    first_day = fields.Integer(default=1)
    second_day = fields.Integer(default=15)
    first_month_day = fields.Integer(default=1)
    first_month = fields.Selection([
        ('jan', 'January'),
        ('feb', 'February'),
        ('mar', 'March'),
        ('apr', 'April'),
        ('may', 'May'),
        ('jun', 'June'),
    ], default="jan")
    second_month_day = fields.Integer(default=1)
    second_month = fields.Selection([
        ('jul', 'July'),
        ('aug', 'Augustus'),
        ('sep', 'September'),
        ('oct', 'October'),
        ('nov', 'November'),
        ('dec', 'December')
    ], default="jul")
    yearly_month = fields.Selection([
        ('jan', 'January'),
        ('feb', 'February'),
        ('mar', 'March'),
        ('apr', 'April'),
        ('may', 'May'),
        ('jun', 'June'),
        ('jul', 'July'),
        ('aug', 'Augustus'),
        ('sep', 'September'),
        ('oct', 'October'),
        ('nov', 'November'),
        ('dec', 'December')
    ], default="jan")
    yearly_day = fields.Integer(default=1)
    maximum_leave = fields.Float(
        'Limit to', required=False, default=100,
        help="Choose a maximum limit of days for this accrual. 0 means no limit.")
    parent_id = fields.Many2one(
        'hr.leave.accrual.level', string="Previous Level",
        help="If this field is empty, this level is the first one.")
    action_with_unused_accruals = fields.Selection(
        [('postponed', 'Postponed to next year'),
         ('lost', 'Lost')],
        string="At the end of the year, unused accruals will be",
        default='postponed', required='True')

    _sql_constraints = [
        ('check_dates',
         "CHECK( (frequency = 'daily') or"
         "(week_day IS NOT NULL AND frequency = 'weekly') or "
         "(first_day > 0 AND second_day > first_day AND first_day <= 31 AND second_day <= 31 AND frequency = 'bimonthly') or "
         "(first_day > 0 AND first_day <= 31 AND frequency = 'monthly')or "
         "(first_month_day > 0 AND first_month_day <= 31 AND second_month_day > 0 AND second_month_day <= 31 AND frequency = 'biyearly') or "
         "(yearly_day > 0 AND yearly_day <= 31 AND frequency = 'yearly'))",
         "The dates you've set up aren't correct. Please check them."),
        ('start_count_check', "CHECK( start_count >= 1 )", "You must start after more than 0 days."),
        ('added_value_greater_than_zero', 'CHECK(added_value > 0)', 'You must give the gain greater than 0 in accrual plan levels.')
    ]

    @api.depends('start_count', 'start_type')
    def _compute_sequence(self):
        # Not 100% accurate because of odd months/years, but good enough
        start_type_multipliers = {
            'day': 1,
            'month': 30,
            'year': 365,
        }
        for level in self:
            level.sequence = level.start_count * start_type_multipliers[level.start_type]

    @api.depends('sequence', 'accrual_plan_id')
    def _compute_level(self):
        #Mapped level_ids.ids ordered by sequence per plan
        mapped_level_ids = {}
        for plan in self.accrual_plan_id:
            # We can not use .ids here because we also deal with NewIds
            mapped_level_ids[plan] = [level.id for level in plan.level_ids.sorted('sequence')]
        for level in self:
            if level.accrual_plan_id:
                level.level = mapped_level_ids[level.accrual_plan_id].index(level.id) + 1
            else:
                level.level = 1

    def _get_accrual_values(self, allocation_create_date):
        """
        This method returns all the accrual linked to their accrual_plan with the updated dynamic parameters depending
        on the date.
        :return: dict: {accrual_id, accrual_start, accrual_stop, nextcall, sufficient_seniority}
         where accrual_start and accrual_stop are start and stop of the current period
        """
        today = fields.Date.context_today(self, )
        results = []
        for accrual in self:
            seniority = allocation_create_date + get_timedelta(accrual.start_count, accrual.start_type)
            frequency = accrual.frequency
            if frequency == 'daily':
                accrual_start = max(today, seniority.date())
                accrual_stop = accrual_start + relativedelta(days=1)
                nextcall = accrual_stop
            elif frequency == 'weekly':
                min_accrual_date = max(today, seniority.date())
                if min_accrual_date.isoweekday() == DAYS.index(accrual.week_day):
                    accrual_stop = min_accrual_date
                else:
                    accrual_stop = accrual._get_next_weekday(min_accrual_date, accrual.week_day)
                accrual_start = accrual_stop - relativedelta(days=7)
                nextcall = accrual._get_next_weekday(min_accrual_date, accrual.week_day)
            elif frequency == 'bimonthly':
                if today.day <= accrual.first_day:
                    accrual_start = datetime.date(today.year, today.month, accrual.second_day) - relativedelta(months=1)
                    accrual_stop = datetime.date(today.year, today.month, accrual.first_day)
                    nextcall = datetime.date(today.year, today.month, accrual.second_day)
                else:
                    if today.day <= accrual.second_day:
                        accrual_start = datetime.date(today.year, today.month, accrual.first_day)
                        accrual_stop = datetime.date(today.year, today.month, accrual.second_day)
                        nextcall = datetime.date(today.year, today.month, accrual.first_day) + relativedelta(months=1)
                    else:
                        accrual_start = datetime.date(today.year, today.month, accrual.second_day)
                        accrual_stop = datetime.date(today.year, today.month, accrual.first_day) + relativedelta(months=1)
                        nextcall = datetime.date(today.year, today.month, accrual.second_day) + relativedelta(months=1)
            elif frequency == 'monthly':
                if today.day <= accrual.first_day:
                    accrual_start = datetime.date(today.year, today.month, accrual.first_day) - relativedelta(months=1)
                    accrual_stop = datetime.date(today.year, today.month, accrual.first_day)
                    nextcall = datetime.date(today.year, today.month, accrual.first_day) + relativedelta(months=1)
                else:
                    accrual_start = datetime.date(today.year, today.month, accrual.first_day)
                    accrual_stop = datetime.date(today.year, today.month, accrual.first_day) + relativedelta(months=1)
                    nextcall = datetime.date(today.year, today.month, accrual.first_day) + relativedelta(months=2)
            elif frequency == 'biyearly':
                first_month = MONTHS.index(accrual.first_month) + 1
                second_month = MONTHS.index(accrual.second_month) + 1
                potential_first_accrual_date = datetime.date(today.year, first_month, accrual.first_month_day)
                potential_second_accrual_date = datetime.date(today.year, second_month, accrual.second_month_day)
                if today <= potential_first_accrual_date:
                    accrual_start = potential_second_accrual_date - relativedelta(years=1)
                    accrual_stop = potential_first_accrual_date
                    nextcall = potential_second_accrual_date
                else:
                    if today <= potential_second_accrual_date:
                        accrual_start = potential_first_accrual_date
                        accrual_stop = potential_second_accrual_date
                        nextcall = potential_first_accrual_date + relativedelta(years=1)
                    else:
                        accrual_start = potential_second_accrual_date
                        accrual_stop = potential_first_accrual_date + relativedelta(years=1)
                        nextcall = potential_first_accrual_date + relativedelta(years=1)
            elif frequency == 'yearly':
                month = MONTHS.index(accrual.yearly_month) + 1
                potential_accrual_date = datetime.date(today.year, month, accrual.yearly_day)
                if today <= potential_accrual_date:
                    accrual_start = potential_accrual_date - relativedelta(years=1)
                    accrual_stop = potential_accrual_date
                    nextcall = potential_accrual_date + relativedelta(years=1)
                else:
                    accrual_start = potential_accrual_date
                    accrual_stop = potential_accrual_date + relativedelta(years=1)
                    nextcall = accrual_stop

            results.append({'accrual_level_id': accrual.id,
                            'start_after': accrual.start_count,
                            'accrual_start': datetime.datetime.combine(accrual_start, datetime.datetime.min.time()),
                            'accrual_stop': datetime.datetime.combine(accrual_stop, datetime.datetime.min.time()),
                            'nextcall': nextcall,
                            'sufficient_seniority': seniority.date() <= today})
        return results

    def _get_next_date(self, last_call):
        """
        Returns the next date with the given last call
        """
        self.ensure_one()
        if self.frequency == 'daily':
            return last_call + relativedelta(days=1)
        elif self.frequency == 'weekly':
            return self._get_next_weekday(last_call, self.week_day)
        elif self.frequency == 'bimonthly':
            if last_call.day < self.first_day:
                return _get_date_check_month(last_call.year, last_call.month, self.first_day)
            elif last_call.day < self.second_day:
                return _get_date_check_month(last_call.year, last_call.month, self.second_day)
            else:
                return _get_date_check_month(last_call.year, last_call.month, self.first_day) + relativedelta(months=1)
        elif self.frequency == 'monthly':
            if last_call.day < self.first_day:
                return _get_date_check_month(last_call.year, last_call.month, self.first_day)
            else:
                return _get_date_check_month(last_call.year, last_call.month, self.first_day) + relativedelta(months=1)
        elif self.frequency == 'biyearly':
            first_month = MONTHS.index(self.first_month) + 1
            second_month = MONTHS.index(self.second_month) + 1
            if last_call < _get_date_check_month(last_call.year, first_month, self.first_month_day):
                return _get_date_check_month(last_call.year, first_month, self.first_month_day)
            elif last_call < _get_date_check_month(last_call.year, second_month, self.second_month_day):
                return _get_date_check_month(last_call.year, second_month, self.second_month_day)
            else:
                return _get_date_check_month(last_call.year, first_month, self.first_month_day) + relativedelta(years=1)
        elif self.frequency == 'yearly':
            month = MONTHS.index(self.yearly_month) + 1
            if last_call < _get_date_check_month(last_call.year, month, self.yearly_day):
                return _get_date_check_month(last_call.year, month, self.yearly_day)
            else:
                return _get_date_check_month(last_call.year, month, self.yearly_day) + relativedelta(years=1)
        else:
            return False

    @api.model
    def _get_next_weekday(self, day, weekday):
        """
        :param day: a datetime object
        :param weekday: Weekday as a decimal number, where 0 is Sunday and 6 is Saturday.
        :return: datetime of the next weekday
        """
        daynames = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
        weekday = daynames.index(weekday)
        days_ahead = weekday - day.isoweekday()
        if days_ahead <= 0:
            days_ahead += 7
        return day + relativedelta(days=days_ahead)
