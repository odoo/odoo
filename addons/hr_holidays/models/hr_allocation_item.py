# # -*- coding: utf-8 -*-

import logging
from dateutil.relativedelta import relativedelta
from datetime import datetime, time

from odoo import api, fields, models, _
from odoo.addons.resource.models.resource import HOURS_PER_DAY

_logger = logging.getLogger(__name__)


class AllocationItem(models.Model):
    _name = "hr.leave.allocation.item"
    _description = "Allocation Item"

    name = fields.Char('Allocation Item', required=True)
    active = fields.Boolean(default=True)
    employee_id = fields.Many2one('hr.employee', ondelete="restrict")
    accrual_plan_id = fields.Many2one('hr.leave.accrual.plan', string='Accrual Plan')
    allocation_id = fields.Many2one('hr.leave.allocation', ondelete="cascade")
    extra_days = fields.Float(related='allocation_id.extra_days')
    allocation_name = fields.Char(compute='_compute_allocation_description')
    holiday_status_id = fields.Many2one(related='allocation_id.holiday_status_id')
    state = fields.Selection(related='allocation_id.state')
    accrual_id = fields.Many2one('hr.leave.accrual', string='Accrual Step', compute='_compute_accrual_id', store=True)
    nextcall = fields.Date(compute='_compute_accrual_id', store=True)
    number_of_hours = fields.Float('Accrual available hours', compute='_compute_number_of_hours', store=True)
    number_of_days = fields.Float('Accrual available days', default=0)

    _sql_constraints = [
        ('employee_plan_allocation_combination_unique', 'unique (employee_id, allocation_id)', "An Item for this employee and this allocation already exists"),
    ]

    @api.depends('accrual_plan_id', 'employee_id', 'employee_id.accrual_plan_ids')
    def _compute_accrual_id(self):
        """
        The current accrual_id depends on conditions set on the accrual and the employee start date.
        This methods get all accrual potential values and chose the best suited:
           * The start_date (according to employee is past
           *
        """
        for item in self:
            start_date = item.sudo().employee_id.start_work_date or item.sudo().employee_id.create_date
            first_day = datetime.combine(start_date, time(0, 0, 0))
            accruals_dates = item.accrual_plan_id.accrual_ids._get_accrual_values(first_day)
            # The selection of the accrual_id (the current step) depends on
            # the seniority of the employee: it must be sufficient.
            canditate_cur = list(filter(lambda a: a['sufficient_seniority'] is True, accruals_dates))
            if canditate_cur:
                current_step = max(canditate_cur, key=lambda x: x['seniority'])
                values = {'accrual_id': current_step.get('accrual_id'),
                          'nextcall': current_step.get('accrual_stop')}
                item.write(values)

    def _increment_accural_items(self):
        """
        Called in a Cron: Update the allocation items depending on the date, the accrual_id and employee start date
        """
        periods = self.env['hr.leave.accrual']._get_accural_periods()
        today = datetime.combine(fields.Date.today(), time(0, 0, 0))
        # We update the currant accrual_id before anything
        self._compute_accrual_id()
        for item in self.filtered(lambda i: i.accrual_plan_id):
            start_date = item.employee_id.start_work_date or item.employee_id.create_date
            first_day = datetime.combine(item.employee_id.start_work_date, time(0, 0, 0))
            frequency = item.accrual_id.frequency
            if item.accrual_id.frequency == 'anniversary':
                end_date = datetime(today.year, first_day.month, first_day.day)
                if today >= end_date:
                    end_date = start_date + relativedelta(years=1)
                start_date = end_date - relativedelta(years=1)
            elif not frequency:
                # The accrual plan has no valid step.
                continue
            else:
                selected_period = periods[frequency] if frequency != 'weekly' else periods[frequency][item.accrual_id.week_day]
                start_date = selected_period['start_date']
                end_date = selected_period['end_date']
            item._compute_accrual_days(first_day, start_date, end_date)

    def _compute_accrual_days(self, first_day, start_date, end_date):
        """
        Increase the number of days depending on the period, the start date of the employee and how many days he worked according to his
        work entry.
        This method takes also in account if the employee started during the period to apply a prorata
        """
        for item in self:
            start_date_prorata = 1.0
            if first_day > start_date:
                # The employee was created during the period after the start_date
                # This prorata depends on the number of days worked during this period
                worked_days = end_date - first_day
                period_days = end_date - start_date
                start_date_prorata = worked_days.days / period_days.days
                # We calculate from the first_day to end_date
                start_date = first_day
            if end_date <= first_day or end_date < item.allocation_id.date_from:
                # Stop the calculation if
                # * the user was created after the period
                # * the period ends before the allocation is valid
                return
            # The prorata depends if the employee took holidays during the period.
            # Unpaid holidays and work_entry_type.leave_right = False decrease the amount of holidays
            worked = self.employee_id._get_work_days_data_batch(start_date, end_date, domain=[
                ('holiday_id.holiday_status_id.unpaid', '=', True), ('time_type', '=', 'leave')])[self.employee_id.id][
                'days']
            left = self.employee_id.sudo()._get_leave_days_data_batch(start_date, end_date, domain=[
                ('time_type', '=', 'leave'), '|', ('work_entry_type_id.leave_right', '=', False),
                ('holiday_id.holiday_status_id.unpaid', '=', True)
            ])[self.employee_id.id]['days']
            work_entry_prorata = worked / (left + worked) if worked else 0
            # Calculate the number of days that could be added
            added_days = work_entry_prorata * start_date_prorata * item.accrual_id.added_days
            number_of_days = item.number_of_days + added_days
            # Do not send a message if the maximum number of days is already reached
            # cancel_message = item.number_of_days == item.accrual_id.maximum_leave
            if item.accrual_id.maximum_leave > 0:
                # Check that the maximum allocation has not been reached.
                maximum_leave_difference = item.accrual_id.maximum_leave - item.number_of_days
                added_days = min(added_days, maximum_leave_difference)
                number_of_days = min(number_of_days, item.accrual_id.maximum_leave)
            item.number_of_days = number_of_days
            if added_days > 0:
                body = _("""Accrual update for employee <strong>%(employee)s</strong>
                        <br/>
                        Allocation rise: %(added_days)s Days<br/>
                        Total allocation: %(amount_days)s Days or %(amount_hours)s Hours.""",
                         employee=item.employee_id.name, added_days=round(added_days, 2),
                         amount_days=round(item.number_of_days, 2), amount_hours=round(item.number_of_hours, 2))
                item.allocation_id.message_post(body=body, message_type='comment', subtype_xmlid='mail.mt_comment')


    @api.depends('allocation_id', 'allocation_id.holiday_status_id', 'allocation_id.state')
    def _compute_allocation_fields(self):
        for item in self:
            item.write({'allocation_id': item.allocation_id,
                        'holiday_status_id': item.allocation_id.holiday_status_id,
                        'state': item.allocation_id.state})

    @api.depends('number_of_days')
    def _compute_number_of_hours(self):
        for item in self:
            item.number_of_hours = item.number_of_days * (
                        item.employee_id.sudo().resource_calendar_id.hours_per_day or HOURS_PER_DAY)

    def _compute_allocation_description(self):
        self.allocation_name = False
        for item in self.filtered(lambda item: item.allocation_id.name):
            item.write({'allocation_name': item.allocation_id.name})
