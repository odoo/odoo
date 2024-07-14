# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)


class Company(models.Model):
    _inherit = 'res.company'

    # reminder for employees
    timesheet_mail_employee_allow = fields.Boolean("Employee Reminder", default=True)
    timesheet_mail_employee_delay = fields.Integer("Employee Reminder Days", default=1)
    timesheet_mail_employee_interval = fields.Selection([
        ('weeks', 'after the end of the week'),
        ('months', 'after the end of the month')
    ], string='Employee Frequency', required=True, default="weeks")
    timesheet_mail_employee_nextdate = fields.Datetime('Next scheduled date for employee reminder', readonly=True)

    # reminder for approver
    timesheet_mail_allow = fields.Boolean("Approver Reminder", default=True)
    timesheet_mail_delay = fields.Integer("Approver Reminder Days", default=3)
    timesheet_mail_interval = fields.Selection([
        ('weeks', 'after the end of the week'),
        ('months', 'after the end of the month')
    ], string='Approver Reminder Frequency', required=True, default="weeks")
    timesheet_mail_nextdate = fields.Datetime('Next scheduled date for approver reminder', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        for company, values in zip(companies, vals_list):
            company.with_context(force_nextdates_calculation=True)._timesheet_postprocess(values)
        return companies

    def write(self, values):
        result = super(Company, self).write(values)
        self.with_context(force_nextdates_calculation=False)._timesheet_postprocess(values)
        return result

    def _timesheet_postprocess(self, values):
        if (
            values.get('timesheet_mail_employee_allow') or
            self.env.context.get('force_nextdates_calculation') or
            any(field_name in values for field_name in ['timesheet_mail_employee_delay', 'timesheet_mail_employee_interval'])
        ):
            self._calculate_timesheet_mail_employee_nextdate()
        if (
            values.get('timesheet_mail_allow') or
            self.env.context.get('force_nextdates_calculation') or
            any(field_name in values for field_name in ['timesheet_mail_delay', 'timesheet_mail_interval'])
        ):
            self._calculate_timesheet_mail_nextdate()

    def _calculate_next_week_date(self, delay):
        now = fields.Datetime.now()
        nextdate = now + relativedelta(weeks=1, days=-now.weekday() + delay - 1)
        if nextdate < now or nextdate.date() == now.date():
            nextdate = now + relativedelta(weeks=2, days=-now.weekday() + delay - 1)
        return nextdate

    def _calculate_next_month_date(self, delay):
        now = fields.Datetime.now()
        nextdate = now + relativedelta(day=1, months=1, days=delay - 1)
        if nextdate < now or nextdate.date() == now.date():
            nextdate = now + relativedelta(day=1, months=2, days=delay - 1)
        return nextdate

    def _calculate_timesheet_mail_employee_nextdate(self):
        for company in self:
            delay = company.timesheet_mail_employee_delay
            if company.timesheet_mail_employee_interval == 'weeks':
                nextdate = self._calculate_next_week_date(delay)
            else:
                nextdate = self._calculate_next_month_date(delay)
            company.timesheet_mail_employee_nextdate = fields.Datetime.to_string(nextdate)

    def _calculate_timesheet_mail_nextdate(self):
        for company in self:
            delay = company.timesheet_mail_delay
            if company.timesheet_mail_interval == 'weeks':
                nextdate = self._calculate_next_week_date(delay)
            else:
                nextdate = self._calculate_next_month_date(delay)
            company.timesheet_mail_nextdate = fields.Datetime.to_string(nextdate)

    @api.model
    def _cron_timesheet_reminder_employee(self):
        """ Send an email reminder to the user having at least one timesheet since the last 3 month. From those ones, we exclude
            ones having complete their timesheet (meaning timesheeted the same hours amount than their working calendar).
        """
        today_max = fields.Datetime.to_string(datetime.combine(date.today(), time.max))
        companies = self.search([('timesheet_mail_employee_allow', '=', True), ('timesheet_mail_employee_nextdate', '<', today_max)])
        for company in companies:
            if company.timesheet_mail_employee_nextdate < fields.Datetime.today():
                _logger.warning('The cron "Timesheet: Employees Email Reminder" should have run on %s' % company.timesheet_mail_employee_nextdate)

            # get the employee that have at least a timesheet for the last 3 months
            # and that are still active; don't spam retired users
            users = self.env['account.analytic.line'].search([
                ('date', '>=', fields.Date.to_string(date.today() - relativedelta(months=3))),
                ('date', '<=', fields.Date.today()),
                ('is_timesheet', '=', True),
                ('company_id', '=', company.id),
            ]).mapped('user_id').filtered('active')

            # calculate the period
            if company.timesheet_mail_employee_interval == 'months':
                date_start = (date.today() - timedelta(days=company.timesheet_mail_employee_delay)) + relativedelta(day=1)
                date_stop = date_start + relativedelta(months=1, days=-1)
            else:
                date_start = date.today() - timedelta(weeks=1, days=company.timesheet_mail_employee_delay - 1)
                date_stop = date_start + timedelta(days=6)

            date_start = fields.Date.to_string(date_start)
            date_stop = fields.Date.to_string(date_stop)

            # get the related employees timesheet status for the cron period
            employees = self.env['hr.employee'].search([('company_id', '=', company.id), ('user_id', 'in', users.ids)])
            work_hours_struct = employees.get_timesheet_and_working_hours(date_start, date_stop)

            for employee in employees:
                if employee.user_id and work_hours_struct[employee.id]['timesheet_hours'] < work_hours_struct[employee.id]['working_hours']:
                    self._cron_timesheet_send_reminder(
                        employee,
                        'timesheet_grid.mail_template_timesheet_reminder_user',
                        'hr_timesheet.act_hr_timesheet_line',
                        additionnal_values=work_hours_struct[employee.id],
                    )

        # compute the next execution date
        companies._calculate_timesheet_mail_employee_nextdate()

    @api.model
    def _cron_timesheet_reminder(self):
        """ Send a email reminder to all users having the group 'timesheet approver'. """
        today_max = fields.Datetime.to_string(datetime.combine(date.today(), time.max))
        companies = self.search([('timesheet_mail_allow', '=', True), ('timesheet_mail_nextdate', '<', today_max)])
        for company in companies:
            if company.timesheet_mail_nextdate < fields.Datetime.today():
                _logger.warning('The cron "Timesheet: Approver Email Reminder" should have run on %s', company.timesheet_mail_nextdate)
            # calculate the period
            if company.timesheet_mail_interval == 'months':
                date_start = (date.today() - timedelta(days=company.timesheet_mail_delay)) + relativedelta(day=1)
                date_stop = date_start + relativedelta(months=1, days=-1)
            else:
                date_start = date.today() - timedelta(weeks=1, days=company.timesheet_mail_delay - 1)
                date_stop = date_start + timedelta(days=6)

            date_start = fields.Date.to_string(date_start)
            date_stop = fields.Date.to_string(date_stop)

            values = {
                'date_start': date_start,
                'date_stop': date_stop,
            }
            users = self.env['res.users'].search([('groups_id', 'in', [self.env.ref('hr_timesheet.group_hr_timesheet_approver').id])])
            self._cron_timesheet_send_reminder(
                self.env['hr.employee'].search([('company_id', '=', company.id), ('user_id', 'in', users.ids)]),
                'timesheet_grid.mail_template_timesheet_reminder',
                'timesheet_grid.action_timesheet_previous_week',
                additionnal_values=values)

        # compute the next execution date
        companies._calculate_timesheet_mail_nextdate()

    @api.model
    def _cron_timesheet_send_reminder(self, employees, template_xmlid, action_xmlid, additionnal_values=None):
        """ Send the email reminder to specified users
            :param user_ids : list of user identifier to send the reminder
            :param template_xmlid : xml id of the reminder mail template
        """
        action_url = '%s/web#menu_id=%s&action=%s' % (
            self.get_base_url(),
            self.env.ref('hr_timesheet.timesheet_menu_root').id,
            self.env.ref(action_xmlid).id,
        )

        # send mail template to users having email address
        template = self.env.ref(template_xmlid)
        template_ctx = {'action_url': action_url}
        if additionnal_values:
            template_ctx.update(additionnal_values)

        for employee in employees.filtered('user_id'):
            template.with_context(**template_ctx).send_mail(employee.id)
