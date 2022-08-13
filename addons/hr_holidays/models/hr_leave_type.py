# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

import datetime
import logging

from collections import defaultdict
from datetime import time, timedelta

from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools.translate import _
from odoo.tools.float_utils import float_round
from odoo.addons.resource.models.resource import Intervals

_logger = logging.getLogger(__name__)


class HolidaysType(models.Model):
    _name = "hr.leave.type"
    _description = "Time Off Type"
    _order = 'sequence'

    @api.model
    def _model_sorting_key(self, leave_type):
        remaining = leave_type.virtual_remaining_leaves > 0
        taken = leave_type.leaves_taken > 0
        return -1*leave_type.sequence, leave_type.employee_requests == 'no' and remaining, leave_type.employee_requests == 'yes' and remaining, taken

    name = fields.Char('Time Off Type', required=True, translate=True)
    sequence = fields.Integer(default=100,
                              help='The type with the smallest sequence is the default value in time off request')
    create_calendar_meeting = fields.Boolean(string="Display Time Off in Calendar", default=True)
    color_name = fields.Selection([
        ('red', 'Red'),
        ('blue', 'Blue'),
        ('lightgreen', 'Light Green'),
        ('lightblue', 'Light Blue'),
        ('lightyellow', 'Light Yellow'),
        ('magenta', 'Magenta'),
        ('lightcyan', 'Light Cyan'),
        ('black', 'Black'),
        ('lightpink', 'Light Pink'),
        ('brown', 'Brown'),
        ('violet', 'Violet'),
        ('lightcoral', 'Light Coral'),
        ('lightsalmon', 'Light Salmon'),
        ('lavender', 'Lavender'),
        ('wheat', 'Wheat'),
        ('ivory', 'Ivory')], string='Color in Report', required=True, default='red',
         help='This color will be used in the time off summary located in Reporting > Time off by Department.')
    color = fields.Integer(string='Color', help="The color selected here will be used in every screen with the time off type.")
    icon_id = fields.Many2one('ir.attachment', string='Cover Image', domain="[('res_model', '=', 'hr.leave.type'), ('res_field', '=', 'icon_id')]")
    active = fields.Boolean('Active', default=True,
                            help="If the active field is set to false, it will allow you to hide the time off type without removing it.")
    max_leaves = fields.Float(compute='_compute_leaves', string='Maximum Allowed', search='_search_max_leaves',
                              help='This value is given by the sum of all time off requests with a positive value.')
    leaves_taken = fields.Float(
        compute='_compute_leaves', string='Time off Already Taken',
        help='This value is given by the sum of all time off requests with a negative value.')
    remaining_leaves = fields.Float(
        compute='_compute_leaves', string='Remaining Time Off',
        help='Maximum Time Off Allowed - Time Off Already Taken')
    virtual_remaining_leaves = fields.Float(
        compute='_compute_leaves', search='_search_virtual_remaining_leaves', string='Virtual Remaining Time Off',
        help='Maximum Time Off Allowed - Time Off Already Taken - Time Off Waiting Approval')
    virtual_leaves_taken = fields.Float(
        compute='_compute_leaves', string='Virtual Time Off Already Taken',
        help='Sum of validated and non validated time off requests.')
    # KBA TODO in master: rename, change to int
    group_days_allocation = fields.Float(
        compute='_compute_group_days_allocation', string='Days Allocated')
    group_days_leave = fields.Float(
        compute='_compute_group_days_leave', string='Group Time Off')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    responsible_id = fields.Many2one(
        'res.users', 'Responsible Time Off Officer',
        domain=lambda self: [('groups_id', 'in', self.env.ref('hr_holidays.group_hr_holidays_user').id)],
        help="Choose the Time Off Officer who will be notified to approve allocation or Time Off request")
    leave_validation_type = fields.Selection([
        ('no_validation', 'No Validation'),
        ('hr', 'By Time Off Officer'),
        ('manager', "By Employee's Approver"),
        ('both', "By Employee's Approver and Time Off Officer")], default='hr', string='Leave Validation')
    requires_allocation = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No Limit')], default="yes", required=True, string='Requires allocation')
    employee_requests = fields.Selection([
        ('yes', 'Extra Days Requests Allowed'),
        ('no', 'Not Allowed')], default="no", required=True, string="Employee Requests")
    allocation_validation_type = fields.Selection([
        ('no', 'No validation needed'),
        ('officer', 'Approved by Time Off Officer'),
        ('set', "Set by Time Off Officer")], default='officer', string='Approval')
    has_valid_allocation = fields.Boolean(compute='_compute_valid', search='_search_valid', help='This indicates if it is still possible to use this type of leave')
    time_type = fields.Selection([('leave', 'Time Off'), ('other', 'Other')], default='leave', string="Kind of Leave",
                                 help="Whether this should be computed as a holiday or as work time (eg: formation)")
    request_unit = fields.Selection([
        ('day', 'Day'),
        ('half_day', 'Half Day'),
        ('hour', 'Hours')], default='day', string='Take Time Off in', required=True)
    unpaid = fields.Boolean('Is Unpaid', default=False)
    leave_notif_subtype_id = fields.Many2one('mail.message.subtype', string='Time Off Notification Subtype', default=lambda self: self.env.ref('hr_holidays.mt_leave', raise_if_not_found=False))
    allocation_notif_subtype_id = fields.Many2one('mail.message.subtype', string='Allocation Notification Subtype', default=lambda self: self.env.ref('hr_holidays.mt_leave_allocation', raise_if_not_found=False))
    support_document = fields.Boolean(string='Supporting Document')
    accruals_ids = fields.One2many('hr.leave.accrual.plan', 'time_off_type_id')
    accrual_count = fields.Float(compute="_compute_accrual_count", string="Accruals count")


    @api.model
    def _search_valid(self, operator, value):
        """ Returns leave_type ids for which a valid allocation exists
            or that don't need an allocation
            return [('id', domain_operator, [x['id'] for x in res])]
        """
        date_to = self._context.get('default_date_from') or fields.Date.today().strftime('%Y-1-1')
        date_from = self._context.get('default_date_to') or fields.Date.today().strftime('%Y-12-31')
        employee_id = self._context.get('default_employee_id', self._context.get('employee_id')) or self.env.user.employee_id.id

        if not isinstance(value, bool):
            raise ValueError('Invalid value: %s' % (value))
        if operator not in ['=', '!=']:
            raise ValueError('Invalid operator: %s' % (operator))
        new_operator = 'in' if operator == '=' else 'not in'

        query = '''
        SELECT
            holiday_status_id
        FROM
            hr_leave_allocation alloc
        WHERE
            alloc.employee_id = %s AND
            alloc.active = True AND alloc.state = 'validate' AND
            (alloc.date_to >= %s OR alloc.date_to IS NULL) AND
            alloc.date_from <= %s 
        '''

        self._cr.execute(query, (employee_id or None, date_to, date_from))

        return [('id', new_operator, [x['holiday_status_id'] for x in self._cr.dictfetchall()])]


    @api.depends('requires_allocation')
    def _compute_valid(self):
        date_to = self._context.get('default_date_to', fields.Datetime.today())
        date_from = self._context.get('default_date_from', fields.Datetime.today())
        employee_id = self._context.get('default_employee_id', self._context.get('employee_id', self.env.user.employee_id.id))
        for holiday_type in self:
            if holiday_type.requires_allocation:
                allocation = self.env['hr.leave.allocation'].search([
                    ('holiday_status_id', '=', holiday_type.id),
                    ('employee_id', '=', employee_id),
                    '|',
                    ('date_to', '>=', date_to),
                    '&',
                    ('date_to', '=', False),
                    ('date_from', '<=', date_from)])
                holiday_type.has_valid_allocation = bool(allocation)
            else:
                holiday_type.has_valid_allocation = True

    def _search_max_leaves(self, operator, value):
        value = float(value)
        employee_id = self._get_contextual_employee_id()
        leaves = defaultdict(int)

        if employee_id:
            allocations = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', employee_id),
                ('state', '=', 'validate')
            ])
            for allocation in allocations:
                leaves[allocation.holiday_status_id.id] += allocation.number_of_days
        valid_leave = []
        for leave in leaves:
            if operator == '>':
                if leaves[leave] > value:
                    valid_leave.append(leave)
            elif operator == '<':
                if leaves[leave] < value:
                    valid_leave.append(leave)
            elif operator == '=':
                if leaves[leave] == value:
                    valid_leave.append(leave)
            elif operator == '!=':
                if leaves[leave] != value:
                    valid_leave.append(leave)

        return [('id', 'in', valid_leave)]

    def _search_virtual_remaining_leaves(self, operator, value):
        value = float(value)
        leave_types = self.env['hr.leave.type'].search([])
        valid_leave_types = self.env['hr.leave.type']

        for leave_type in leave_types:
            if leave_type.requires_allocation == "yes":
                if operator == '>' and leave_type.virtual_remaining_leaves > value:
                    valid_leave_types |= leave_type
                elif operator == '<' and leave_type.virtual_remaining_leaves < value:
                    valid_leave_types |= leave_type
                elif operator == '>=' and leave_type.virtual_remaining_leaves >= value:
                    valid_leave_types |= leave_type
                elif operator == '<=' and leave_type.virtual_remaining_leaves <= value:
                    valid_leave_types |= leave_type
                elif operator == '=' and leave_type.virtual_remaining_leaves == value:
                    valid_leave_types |= leave_type
                elif operator == '!=' and leave_type.virtual_remaining_leaves != value:
                    valid_leave_types |= leave_type
            else:
                valid_leave_types |= leave_type

        return [('id', 'in', valid_leave_types.ids)]

    def _get_employees_days_per_allocation(self, employee_ids, date=None):
        leaves = self.env['hr.leave'].search([
            ('employee_id', 'in', employee_ids),
            ('state', 'in', ['confirm', 'validate1', 'validate']),
            ('holiday_status_id', 'in', self.ids)
        ])

        allocations = self.env['hr.leave.allocation'].search([
            ('employee_id', 'in', employee_ids),
            ('state', 'in', ['validate']),
            ('holiday_status_id', 'in', self.ids),
        ])

        if not date:
            date = fields.Date.to_date(self.env.context.get('default_date_from')) or fields.Date.context_today(self)

        # The allocation_employees dictionary groups the allocations based on the employee and the holiday type
        # The structure is the following:
        # - KEYS:
        # allocation_employees
        #   |--employee_id
        #      |--holiday_status_id
        # - VALUES:
        # Intervals with the start and end date of each allocation and associated allocations within this interval
        allocation_employees = defaultdict(lambda: defaultdict(list))

        ### Creation of the allocation intervals ###
        for holiday_status_id in allocations.holiday_status_id:
            for employee_id in employee_ids:
                allocation_intervals = Intervals([(
                    fields.datetime.combine(allocation.date_from, time.min),
                    fields.datetime.combine(allocation.date_to or datetime.date.max, time.max),
                    allocation)
                    for allocation in allocations.filtered(lambda allocation: allocation.employee_id.id == employee_id and allocation.holiday_status_id == holiday_status_id)])

                allocation_employees[employee_id][holiday_status_id] = allocation_intervals

        # The leave_employees dictionary groups the leavess based on the employee and the holiday type
        # The structure is the following:
        # - KEYS:
        # leave_employees
        #   |--employee_id
        #      |--holiday_status_id
        # - VALUES:
        # Intervals with the start and end date of each leave and associated leave within this interval
        leaves_employees = defaultdict(lambda: defaultdict(list))
        leave_intervals = []

        ### Creation of the leave intervals ###
        if leaves:
            for holiday_status_id in leaves.holiday_status_id:
                for employee_id in employee_ids:
                    leave_intervals = Intervals([(
                        fields.datetime.combine(leave.date_from, time.min),
                        fields.datetime.combine(leave.date_to, time.max),
                        leave)
                        for leave in leaves.filtered(lambda leave: leave.employee_id.id == employee_id and leave.holiday_status_id == holiday_status_id)])

                    leaves_employees[employee_id][holiday_status_id] = leave_intervals

        # allocation_days_consumed is a dictionary to map the number of days/hours of leaves taken per allocation
        # The structure is the following:
        # - KEYS:
        # allocation_days_consumed
        #  |--employee_id
        #      |--holiday_status_id
        #          |--allocation
        #              |--virtual_leaves_taken
        #              |--leaves_taken
        #              |--virtual_remaining_leaves
        #              |--remaining_leaves
        #              |--max_leaves
        # - VALUES:
        # Integer representing the number of (virtual) remaining leaves, (virtual) leaves taken or max leaves for each allocation.
        # The unit is in hour or days depending on the leave type request unit
        allocations_days_consumed = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0))))

        company_domain = [('company_id', 'in', list(set(self.env.company.ids + self.env.context.get('allowed_company_ids', []))))]

        ### Existing leaves assigned to allocations ###
        if leaves_employees:
            for employee_id, leaves_interval_by_status in leaves_employees.items():
                for holiday_status_id in leaves_interval_by_status:
                    days_consumed = allocations_days_consumed[employee_id][holiday_status_id]
                    if allocation_employees[employee_id][holiday_status_id]:
                        allocations = allocation_employees[employee_id][holiday_status_id] & leaves_interval_by_status[holiday_status_id]
                        available_allocations = self.env['hr.leave.allocation']
                        for allocation_interval in allocations._items:
                            available_allocations |= allocation_interval[2]
                        # Consume the allocations that are close to expiration first
                        sorted_available_allocations = available_allocations.filtered('date_to').sorted(key='date_to')
                        sorted_available_allocations += available_allocations.filtered(lambda allocation: not allocation.date_to)
                        leave_intervals = leaves_interval_by_status[holiday_status_id]._items
                        for leave_interval in leave_intervals:
                            leave = leave_interval[2]
                            if leave.leave_type_request_unit in ['day', 'half_day']:
                                leave_duration = leave.number_of_days
                                leave_unit = 'days'
                            else:
                                leave_duration = leave.number_of_hours_display
                                leave_unit = 'hours'
                            for available_allocation in sorted_available_allocations:
                                virtual_remaining_leaves = (available_allocation.number_of_days if leave_unit == 'days' else available_allocation.number_of_hours_display) - allocations_days_consumed[employee_id][holiday_status_id][available_allocation]['virtual_leaves_taken']
                                max_leaves = min(virtual_remaining_leaves, leave_duration)
                                days_consumed[available_allocation]['virtual_leaves_taken'] += max_leaves
                                if leave.state == 'validate':
                                    days_consumed[available_allocation]['leaves_taken'] += max_leaves
                                leave_duration -= max_leaves
                            if leave_duration > 0:
                                # There are not enough allocation for the number of leaves
                                days_consumed[False]['virtual_remaining_leaves'] -= leave_duration
                                return allocations_days_consumed

        # Future available leaves
        for employee_id, allocation_intervals_by_status in allocation_employees.items():
            for holiday_status_id, intervals in allocation_intervals_by_status.items():
                if not intervals:
                    continue
                future_allocation_intervals = intervals & Intervals([(
                    fields.datetime.combine(date, time.min),
                    fields.datetime.combine(date, time.max) + timedelta(days=5*365),
                    self.env['hr.leave'])])
                search_date = date
                for future_allocation_interval in future_allocation_intervals._items:
                    if future_allocation_interval[0].date() > search_date:
                        continue
                    for allocation in future_allocation_interval[2]:
                        days_consumed = allocations_days_consumed[employee_id][holiday_status_id][allocation]
                        if future_allocation_interval[1] != fields.datetime.combine(date, time.max) + timedelta(days=5*365):
                            # Compute the remaining number of days/hours in the allocation only if it has an end date
                            quantity_available = allocation.employee_id._get_work_days_data_batch(
                                future_allocation_interval[0],
                                future_allocation_interval[1],
                                compute_leaves=False,
                                domain=company_domain)[employee_id]
                        else:
                            # If no end date to the allocation, consider the number of days remaining as infinite
                            quantity_available = {'days': float('inf'), 'hours': float('inf')}
                        if allocation.type_request_unit in ['day', 'half_day']:
                            quantity_available = quantity_available['days']
                            remaining_days_allocation = (allocation.number_of_days - days_consumed['virtual_leaves_taken'])
                        else:
                            quantity_available = quantity_available['hours']
                            remaining_days_allocation = (allocation.number_of_hours_display - days_consumed['virtual_leaves_taken'])
                        if quantity_available <= remaining_days_allocation:
                            search_date = future_allocation_interval[1].date() + timedelta(days=1)
                        days_consumed['virtual_remaining_leaves'] += min(quantity_available, remaining_days_allocation)
                        days_consumed['max_leaves'] = allocation.number_of_days if allocation.type_request_unit == 'day' else allocation.number_of_hours_display
                        days_consumed['remaining_leaves'] = days_consumed['max_leaves'] - days_consumed['leaves_taken']
                        if remaining_days_allocation >= quantity_available:
                            break

        return allocations_days_consumed


    def get_employees_days(self, employee_ids, date=None):

        result = {
            employee_id: {
                leave_type.id: {
                    'max_leaves': 0,
                    'leaves_taken': 0,
                    'remaining_leaves': 0,
                    'virtual_remaining_leaves': 0,
                    'virtual_leaves_taken': 0,
                } for leave_type in self
            } for employee_id in employee_ids
        }

        allocations_days_consumed = self._get_employees_days_per_allocation(employee_ids, date)

        leave_keys = ['max_leaves', 'leaves_taken', 'remaining_leaves', 'virtual_remaining_leaves', 'virtual_leaves_taken']

        for employee_id in allocations_days_consumed:
            for holiday_status_id in allocations_days_consumed[employee_id]:
                for allocation in allocations_days_consumed[employee_id][holiday_status_id]:
                    for leave_key in leave_keys:
                        result[employee_id][holiday_status_id if isinstance(holiday_status_id, int) else holiday_status_id.id][leave_key] += allocations_days_consumed[employee_id][holiday_status_id][allocation][leave_key]

        return result

    @api.model
    def get_days_all_request(self):
        leave_types = sorted(self.search([]).filtered(lambda x: ((x.virtual_remaining_leaves > 0 or x.max_leaves))), key=self._model_sorting_key, reverse=True)
        return [lt._get_days_request() for lt in leave_types]

    def _get_days_request(self):
        self.ensure_one()
        return (self.name, {
                'remaining_leaves': ('%.2f' % self.remaining_leaves).rstrip('0').rstrip('.'),
                'virtual_remaining_leaves': ('%.2f' % self.virtual_remaining_leaves).rstrip('0').rstrip('.'),
                'max_leaves': ('%.2f' % self.max_leaves).rstrip('0').rstrip('.'),
                'leaves_taken': ('%.2f' % self.leaves_taken).rstrip('0').rstrip('.'),
                'virtual_leaves_taken': ('%.2f' % self.virtual_leaves_taken).rstrip('0').rstrip('.'),
                'request_unit': self.request_unit,
                'icon': self.sudo().icon_id.url,
                }, self.requires_allocation, self.id)

    def _get_contextual_employee_id(self):
        if 'employee_id' in self._context:
            employee_id = self._context['employee_id']
        elif 'default_employee_id' in self._context:
            employee_id = self._context['default_employee_id']
        else:
            employee_id = self.env.user.employee_id.id
        return employee_id

    @api.depends_context('employee_id', 'default_employee_id')
    def _compute_leaves(self):
        data_days = {}
        employee_id = self._get_contextual_employee_id()

        if employee_id:
            data_days = (self.get_employees_days(employee_id)[employee_id[0]] if isinstance(employee_id, list) else
                         self.get_employees_days([employee_id])[employee_id])

        for holiday_status in self:
            result = data_days.get(holiday_status.id, {})
            holiday_status.max_leaves = result.get('max_leaves', 0)
            holiday_status.leaves_taken = result.get('leaves_taken', 0)
            holiday_status.remaining_leaves = result.get('remaining_leaves', 0)
            holiday_status.virtual_remaining_leaves = result.get('virtual_remaining_leaves', 0)
            holiday_status.virtual_leaves_taken = result.get('virtual_leaves_taken', 0)

    def _compute_group_days_allocation(self):
        grouped_res = self.env['hr.leave.allocation'].read_group(
            [('holiday_status_id', 'in', self.ids), ],
            ['holiday_status_id'],
            ['holiday_status_id'],
        )
        grouped_dict = dict((data['holiday_status_id'][0], data['holiday_status_id_count']) for data in grouped_res)
        for allocation in self:
            allocation.group_days_allocation = grouped_dict.get(allocation.id, 0)

    def _compute_group_days_leave(self):
        grouped_res = self.env['hr.leave'].read_group(
            [('holiday_status_id', 'in', self.ids),
             ('date_from', '>=', fields.Datetime.to_string(datetime.datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)))],
            ['holiday_status_id'],
            ['holiday_status_id'],
        )
        grouped_dict = dict((data['holiday_status_id'][0], data['holiday_status_id_count']) for data in grouped_res)
        for allocation in self:
            allocation.group_days_leave = grouped_dict.get(allocation.id, 0)

    def _compute_accrual_count(self):
        accrual_allocations = self.env['hr.leave.accrual.plan'].read_group([('time_off_type_id', 'in', self.ids)], ['time_off_type_id'], ['time_off_type_id'])
        mapped_data = dict((data['time_off_type_id'][0], data['time_off_type_id_count']) for data in accrual_allocations)
        for leave_type in self:
            leave_type.accrual_count = mapped_data.get(leave_type.id, 0)

    def name_get(self):
        if not self._context.get('employee_id'):
            # leave counts is based on employee_id, would be inaccurate if not based on correct employee
            return super(HolidaysType, self).name_get()
        res = []
        for record in self:
            name = record.name
            if record.requires_allocation == "yes" and not self._context.get('from_manager_leave_form'):
                name = "%(name)s (%(count)s)" % {
                    'name': name,
                    'count': _('%g remaining out of %g') % (
                        float_round(record.virtual_remaining_leaves, precision_digits=2) or 0.0,
                        float_round(record.max_leaves, precision_digits=2) or 0.0,
                    ) + (_(' hours') if record.request_unit == 'hour' else _(' days'))
                }
            res.append((record.id, name))
        return res

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """ Override _search to order the results, according to some employee.
        The order is the following

         - allocation fixed first, then allowing allocation, then free allocation
         - virtual remaining leaves (higher the better, so using reverse on sorted)

        This override is necessary because those fields are not stored and depends
        on an employee_id given in context. This sort will be done when there
        is an employee_id in context and that no other order has been given
        to the method.
        """
        employee_id = self._get_contextual_employee_id()
        post_sort = (not count and not order and employee_id)
        leave_ids = super(HolidaysType, self)._search(args, offset=offset, limit=(None if post_sort else limit), order=order, count=count, access_rights_uid=access_rights_uid)
        leaves = self.browse(leave_ids)
        if post_sort:
            return leaves.sorted(key=self._model_sorting_key, reverse=True).ids[:limit or None]
        return leave_ids

    def action_see_days_allocated(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hr_holidays.hr_leave_allocation_action_all")
        action['domain'] = [
            ('holiday_status_id', 'in', self.ids),
        ]
        action['context'] = {
            'default_holiday_type': 'department',
            'default_holiday_status_id': self.ids[0],
        }
        return action

    def action_see_group_leaves(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hr_holidays.hr_leave_action_action_approve_department")
        action['domain'] = [
            ('holiday_status_id', '=', self.ids[0]),
            ('date_from', '>=', fields.Datetime.to_string(datetime.datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)))
        ]
        action['context'] = {
            'default_holiday_status_id': self.ids[0],
        }
        return action

    def action_see_accrual_plans(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hr_holidays.open_view_accrual_plans")
        action['domain'] = [
            ('time_off_type_id', '=', self.id),
        ]
        action['context'] = {
            'default_time_off_type_id': self.id,
        }
        return action
