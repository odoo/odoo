# # -*- coding: utf-8 -*-

import datetime
import logging

from odoo import api, fields, models
from odoo.tools.date_utils import get_quarter, end_of, get_timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime, time

_logger = logging.getLogger(__name__)


class AccrualPlanLine(models.Model):
    _name = "hr.leave.accrual"
    _description = "Accrual"

    name = fields.Char(required=True)
    plan_id = fields.Many2one('hr.leave.accrual.plan', "Accrual Plan")
    start_count = fields.Float("Start after",
                               help="The accrual starts after a defined period from the employee start date. "
                                    "This field define the number of days, month or years after which accrual is used.")
    start_type = fields.Selection(
        [('day', 'day(s)'), ('month', 'month(s)'), ('year', 'year(s)')], default='day', string=" ",
        help="This field define the unit of time after which the accrual starts.", required=True)

    # Accrue of
    added_days = fields.Float("Days per period", required=True,
                               help="The number of days that will be incremented for every period")
    frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('bimonthly', 'Twice a month'),
        ('monthly', 'Monthly'),
        ('biyearly', 'Twice a year'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('anniversary', 'Anniversary'),
    ], default='yearly', required=True, string="Accrual period")
    week_day = fields.Selection([
        ('mon', 'Monday'),
        ('tue', 'Tuesday'),
        ('wed', 'Wednesday'),
        ('thu', 'Thursday'),
        ('fri', 'Friday'),
        ('sat', 'Saturday'),
        ('sun', 'Sunday'),
    ], default='mon', required=True, string="Allocation on")
    # arj fixme: we can't say: no value: then no limit because of auto edit that will set value = 0. It is disturbing
    # arj fixme: We cannot let it be false...
    maximum_leave = fields.Float('Limit to',
                                 help="Define a maximum limit of days for this accrual. 0 means no limit.",
                                 required=False, default=100)

    def _get_accrual_values(self, employee_first_date):
        """
        This method returns all the accrual linked to their accrual_plan with the updated dynamic parameters depending
        on the date.
        :return: dict: {accrual_id ,employee_id, candidate, accrual_start, accrual_stop}
         where accrual_start and accrual_stop and start and stop of the current period
         The accrual is a candidate when its start date is in the past.
        """
        today = fields.Date.context_today(self, )
        periods = self._get_accural_periods()
        results = []
        for accrual in self:
            frequency = accrual.frequency
            selected_period = periods[frequency] if frequency != 'weekly' else periods[accrual.frequency][accrual.week_day]
            accrual_start = selected_period['start_date']
            accrual_stop = selected_period['end_date']
            validity_date = employee_first_date + get_timedelta(accrual.start_count, accrual.start_type)
            results.append({'accrual_id': accrual.id,
                            'accrual_start': accrual_start, 'accrual_stop': accrual_stop,
                            'sufficient_seniority': validity_date.date() <= today, 'seniority': validity_date})
        return results

    @api.model
    def _get_accural_periods(self):
        """
            The accrual is incremented according to the period properties.
        :return: a dict with periods that does not depend on employee properties.
                 The periods are start at the first matching day and it finishes at 00:00 after given relative delta.
        """

        today = datetime.combine(fields.Date.today(), time(0, 0, 0))
        # The sixth day of the week is saturday, the last one. Sunday is 0
        daynames = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
        weekly_dates = {}
        for idx, day in enumerate(daynames):
            previous_day = self._get_previous_weekday(today, idx)
            # For example: from monday 00:00 to next thuesday 00:00
            weekly_dates[day] = {'start': previous_day, 'end': previous_day + relativedelta(days=7)}
        # bimonthly: 2 periods: ~1-15 and ~15-31
        month_first_day = today.replace(day=1)
        next_month_start = end_of(today, 'month') + relativedelta(days=1)
        next_month_start = next_month_start.replace(hour=0, minute=0, second=0, microsecond=0)
        if today > month_first_day + relativedelta(weeks=2):
            # 15 to 31
            bimonthly_first_day = month_first_day + relativedelta(weeks=2)
            bimonthly_end_day = next_month_start
        else:
            # We are in the first 2 weeks of the month
            bimonthly_first_day = month_first_day
            bimonthly_end_day = month_first_day + relativedelta(weeks=2)

        # quaterly
        current_quarter = get_quarter(today)

        first_half_year = datetime(today.year, 1, 1)
        second_half_year = datetime(today.year, 7, 1)
        # biyearly
        if today >= second_half_year:
            # second period
            biyearly_start = second_half_year
        else:
            biyearly_start = first_half_year

        periods = {
            # from the saturday 00:00 to sunday 00:00
            'weekly': {'mon': {'start_date': weekly_dates['mon']['start'], 'end_date': weekly_dates['mon']['end']},
                       'tue': {'start_date': weekly_dates['tue']['start'], 'end_date': weekly_dates['tue']['end']},
                       'wed': {'start_date': weekly_dates['wed']['start'], 'end_date': weekly_dates['wed']['end']},
                       'thu': {'start_date': weekly_dates['thu']['start'], 'end_date': weekly_dates['thu']['end']},
                       'fri': {'start_date': weekly_dates['fri']['start'], 'end_date': weekly_dates['fri']['end']},
                       'sat': {'start_date': weekly_dates['sat']['start'], 'end_date': weekly_dates['sat']['end']},
                       'sun': {'start_date': weekly_dates['sun']['start'], 'end_date': weekly_dates['sun']['end']},
                       },
            'bimonthly': {
                'start_date': bimonthly_first_day,
                'end_date': bimonthly_end_day},
            'monthly': {
                'start_date': month_first_day, 'end_date': next_month_start},
            'biyearly': {
                'start_date': biyearly_start, 'end_date': biyearly_start + relativedelta(months=6)},
            'quarterly': {
                # We need the quarter goes to the end of the last day = start of the next quarter
                'start_date': current_quarter[0], 'end_date': current_quarter[1] + relativedelta(days=1)},
            'yearly': {
                'start_date': datetime(today.year, 1, 1), 'end_date': datetime(today.year + 1, 1, 1)}
        }

        return periods

    @api.model
    def _get_next_weekday(self, day, weekday):
        """
        :param day: a datetime object
        :param weekday: Weekday as a decimal number, where 0 is Sunday and 6 is Saturday.
        :return: datetime of the next weekday
        """
        days_ahead = weekday - day.isoweekday()
        if days_ahead <= 0:
            days_ahead += 7
        return day + relativedelta(days=days_ahead)

    @api.model
    def _get_previous_weekday(self, day, weekday):
        """
        :param day: a datetime object
        :param weekday: Weekday as a decimal number, where 0 is Sunday and 6 is Saturday.
        :return: datetime of the next weekday
        """
        days_before = day.isoweekday() - weekday
        if days_before <= 0:
            days_before += 7
        return day - relativedelta(days=days_before)
