# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

import datetime
import logging

from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools.translate import _
from odoo.tools.float_utils import float_round

_logger = logging.getLogger(__name__)


class HolidaysType(models.Model):
    _name = "hr.leave.type"
    _description = "Time Off Type"
    _order = "sequence, id"

    name = fields.Char('Time Off Type', required=True, translate=True)
    code = fields.Char('Code')
    sequence = fields.Integer(default=100,
                              help='The type with the smallest sequence is the default value in time off request')
    categ_id = fields.Many2one(
        'calendar.event.type', string='Meeting Type',
        help='Once a time off is validated, Odoo will create a corresponding meeting of this type in the calendar.')
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
        compute='_compute_leaves', string='Virtual Remaining Time Off',
        help='Maximum Time Off Allowed - Time Off Already Taken - Time Off Waiting Approval')
    group_days_allocation = fields.Float(
        compute='_compute_group_days_allocation', string='Days Allocated')
    group_days_leave = fields.Float(
        compute='_compute_group_days_leave', string='Group Time Off')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    responsible_id = fields.Many2one('res.users', 'Responsible', domain=lambda self: [('groups_id', 'in', self.env.ref('hr_holidays.group_hr_holidays_user').id)],
                                     help="This user will be responsible for approving this type of times off"
                                     "This is only used when validation is 'hr' or 'both'",)
    validation_type = fields.Selection([
        ('no_validation', 'No Validation'),
        ('hr', 'Time Off Officer'),
        ('manager', 'Team Leader'),
        ('both', 'Team Leader and Time Off Officer')], default='hr', string='Validation')
    allocation_type = fields.Selection([
        ('no', 'No Allocation Needed'),
        ('fixed_allocation', 'Free Allocation Request'),
        ('fixed', 'Allocated by HR only')],
        default='no', string='Mode',
        help='\tNo Allocation Needed: no allocation by default, users can freely request time off;'
             '\tFree Allocation Request: allocated by HR and users can request time off and allocations;'
             '\tAllocated by HR only: allocated by HR and cannot be bypassed; users can request time off;')
    validity_start = fields.Date("From", default=fields.Date.today,
                                 help='Adding validity to types of time off so that it cannot be selected outside this time period')
    validity_stop = fields.Date("To")
    valid = fields.Boolean(compute='_compute_valid', search='_search_valid', help='This indicates if it is still possible to use this type of leave')
    time_type = fields.Selection([('leave', 'Time Off'), ('other', 'Other')], default='leave', string="Kind of Leave",
                                 help="Whether this should be computed as a holiday or as work time (eg: formation)")
    request_unit = fields.Selection([
        ('day', 'Day'), ('half_day','Half Day'), ('hour', 'Hours')],
        default='day', string='Take Time Off in', required=True)
    unpaid = fields.Boolean('Is Unpaid', default=False)
    leave_notif_subtype_id = fields.Many2one('mail.message.subtype', string='Time Off Notification Subtype', default=lambda self: self.env.ref('hr_holidays.mt_leave', raise_if_not_found=False))
    allocation_notif_subtype_id = fields.Many2one('mail.message.subtype', string='Allocation Notification Subtype', default=lambda self: self.env.ref('hr_holidays.mt_leave_allocation', raise_if_not_found=False))

    @api.multi
    @api.constrains('validity_start', 'validity_stop')
    def _check_validity_dates(self):
        for leave_type in self:
            if leave_type.validity_start and leave_type.validity_stop and \
               leave_type.validity_start > leave_type.validity_stop:
                raise ValidationError(_("End of validity period should be greater than start of validity period"))

    @api.multi
    @api.depends('validity_start', 'validity_stop')
    def _compute_valid(self):
        dt = self._context.get('default_date_from') or fields.Date.context_today(self)

        for holiday_type in self:
            if holiday_type.validity_start and holiday_type.validity_stop:
                holiday_type.valid = ((dt < holiday_type.validity_stop) and (dt > holiday_type.validity_start))
            elif holiday_type.validity_start and (dt > holiday_type.validity_start):
                holiday_type.valid = False
            else:
                holiday_type.valid = True

    def _search_valid(self, operator, value):
        dt = self._context.get('default_date_from') or fields.Date.context_today(self)

        signs = ['>=', '<='] if operator == '=' else ['<=', '>=']

        return ['|', ('validity_stop', operator, False), '&',
                ('validity_stop', signs[0] if value else signs[1], dt),
                ('validity_start', signs[1] if value else signs[0], dt)]

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

    @api.multi
    def get_days(self, employee_id):
        # need to use `dict` constructor to create a dict per id
        result = dict((id, dict(max_leaves=0, leaves_taken=0, remaining_leaves=0, virtual_remaining_leaves=0)) for id in self.ids)

        requests = self.env['hr.leave'].search([
            ('employee_id', '=', employee_id),
            ('state', 'in', ['confirm', 'validate1', 'validate']),
            ('holiday_status_id', 'in', self.ids)
        ])

        allocations = self.env['hr.leave.allocation'].search([
            ('employee_id', '=', employee_id),
            ('state', 'in', ['confirm', 'validate1', 'validate']),
            ('holiday_status_id', 'in', self.ids)
        ])

        for request in requests:
            status_dict = result[request.holiday_status_id.id]
            status_dict['virtual_remaining_leaves'] -= request.number_of_days
            if request.state == 'validate':
                status_dict['leaves_taken'] += request.number_of_days
                status_dict['remaining_leaves'] -= request.number_of_days

        for allocation in allocations:
            status_dict = result[allocation.holiday_status_id.id]
            if allocation.state == 'validate':
                # note: add only validated allocation even for the virtual
                # count; otherwise pending then refused allocation allow
                # the employee to create more leaves than possible
                status_dict['virtual_remaining_leaves'] += allocation.number_of_days
                status_dict['max_leaves'] += allocation.number_of_days
                status_dict['remaining_leaves'] += allocation.number_of_days

        return result

    @api.multi
    def get_days_all_request(self):
        employee_id = self._get_contextual_employee_id()

        leaves_type = self.search([])
        leaves = leaves_type.get_days(employee_id)
        leave_id_name = dict(zip(leaves_type.ids, leaves_type.mapped('name')))
        leave_id_allocation_type = dict(zip(leaves_type.ids, leaves_type.mapped('allocation_type')))
        result = [(leave_id_name[leave_id], {key: round(value, 2) for (key, value) in leave.items()}, leave_id_allocation_type[leave_id]) for leave_id, leave in leaves.items() if leave['virtual_remaining_leaves'] or leave['max_leaves']]

        sort_key = lambda l: (l[2] == 'fixed', l[2] == 'fixed_allocation', l[1]['virtual_remaining_leaves'])
        return sorted(result, key=sort_key, reverse=True)

    def _get_contextual_employee_id(self):
        if 'employee_id' in self._context:
            employee_id = self._context['employee_id']
        elif 'default_employee_id' in self._context:
            employee_id = self._context['default_employee_id']
        else:
            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id), ('company_id', '=', self.env.user.company_id.id)], limit=1).id
        return employee_id

    @api.multi
    def _compute_leaves(self):
        data_days = {}
        employee_id = self._get_contextual_employee_id()

        if employee_id:
            data_days = self.get_days(employee_id)

        for holiday_status in self:
            result = data_days.get(holiday_status.id, {})
            holiday_status.max_leaves = result.get('max_leaves', 0)
            holiday_status.leaves_taken = result.get('leaves_taken', 0)
            holiday_status.remaining_leaves = result.get('remaining_leaves', 0)
            holiday_status.virtual_remaining_leaves = result.get('virtual_remaining_leaves', 0)

    @api.multi
    def _compute_group_days_allocation(self):
        domain = [
            ('holiday_status_id', 'in', self.ids),
            ('holiday_type', '!=', 'employee'),
            ('state', '=', 'validate'),
        ]
        domain2 = [
            '|',
            ('date_from', '>=', fields.Datetime.to_string(datetime.datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0))),
            ('date_from', '=', False),
        ]
        grouped_res = self.env['hr.leave.allocation'].read_group(
            expression.AND([domain, domain2]),
            ['holiday_status_id', 'number_of_days'],
            ['holiday_status_id'],
        )
        grouped_dict = dict((data['holiday_status_id'][0], data['number_of_days']) for data in grouped_res)
        for allocation in self:
            allocation.group_days_allocation = grouped_dict.get(allocation.id, 0)

    @api.multi
    def _compute_group_days_leave(self):
        grouped_res = self.env['hr.leave'].read_group(
            [('holiday_status_id', 'in', self.ids), ('holiday_type', '=', 'employee'), ('state', '=', 'validate'),
             ('date_from', '>=', fields.Datetime.to_string(datetime.datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)))],
            ['holiday_status_id'],
            ['holiday_status_id'],
        )
        grouped_dict = dict((data['holiday_status_id'][0], data['holiday_status_id_count']) for data in grouped_res)
        for allocation in self:
            allocation.group_days_leave = grouped_dict.get(allocation.id, 0)

    @api.multi
    def name_get(self):
        if not self._context.get('employee_id'):
            # leave counts is based on employee_id, would be inaccurate if not based on correct employee
            return super(HolidaysType, self).name_get()
        res = []
        for record in self:
            name = record.name
            if record.allocation_type != 'no':
                name = "%(name)s (%(count)s)" % {
                    'name': name,
                    'count': _('%g remaining out of %g') % (
                        float_round(record.virtual_remaining_leaves, precision_digits=2) or 0.0,
                        float_round(record.max_leaves, precision_digits=2) or 0.0,
                    )
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
        leave_ids = super(HolidaysType, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)
        if not count and not order and employee_id:
            leaves = self.browse(leave_ids)
            sort_key = lambda l: (l.allocation_type in ['fixed', 'fixed_allocation'], l.virtual_remaining_leaves)
            return leaves.sorted(key=sort_key, reverse=True).ids
        return leave_ids

    @api.multi
    def action_see_days_allocated(self):
        self.ensure_one()
        action = self.env.ref('hr_holidays.hr_leave_allocation_action_all').read()[0]
        domain = [
            ('holiday_status_id', 'in', self.ids),
            ('holiday_type', '!=', 'employee'),
        ]
        domain2 = [
            '|',
            ('date_from', '>=', fields.Datetime.to_string(datetime.datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0))),
            ('date_from', '=', False),
        ]
        action['domain'] = expression.AND([domain, domain2])
        action['context'] = {
            'default_holiday_type': 'department',
            'default_holiday_status_id': self.ids[0],
        }
        return action

    @api.multi
    def action_see_group_leaves(self):
        self.ensure_one()
        action = self.env.ref('hr_holidays.hr_leave_action_all').read()[0]
        action['domain'] = [
            ('holiday_status_id', '=', self.ids[0]),
            ('date_from', '>=', fields.Datetime.to_string(datetime.datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)))
        ]
        action['context'] = {
            'default_holiday_status_id': self.ids[0],
        }
        return action
