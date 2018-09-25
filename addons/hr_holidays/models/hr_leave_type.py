# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

import datetime
import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
from odoo.tools.float_utils import float_round

_logger = logging.getLogger(__name__)


class HolidaysType(models.Model):
    _name = "hr.leave.type"
    _description = "Leave Type"
    _order = "sequence, id"

    name = fields.Char('Leave Type', required=True, translate=True)
    sequence = fields.Integer(default=100,
                              help='The type with the smallest sequence is the default value in leave request')
    categ_id = fields.Many2one(
        'calendar.event.type', string='Meeting Type',
        help='Once a leave is validated, Odoo will create a corresponding meeting of this type in the calendar.')
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
        help='This color will be used in the leaves summary located in Reporting > Leaves by Department.')
    active = fields.Boolean('Active', default=True,
                            help="If the active field is set to false, it will allow you to hide the leave type without removing it.")
    group_days_allocation = fields.Float(
        compute='_compute_group_days_allocation', string='Days Allocated')
    group_days_leave = fields.Float(
        compute='_compute_group_days_leave', string='Group Leaves')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    validation_type = fields.Selection([
        ('hr', 'Human Resource officer'),
        ('manager', 'Employee Manager'),
        ('both', 'Double Validation')], default='hr', string='Validation By')
    allocation_type = fields.Selection([
        ('fixed', 'Fixed by HR'),
        ('fixed_allocation', 'Fixed by HR + allocation request'),
        ('no', 'No allocation')],
        default='fixed', string='Mode',
        help='\tFixed by HR: allocated by HR and cannot be bypassed; users can request leaves;'
             '\tFixed by HR + allocation request: allocated by HR and users can request leaves and allocations;'
             '\tNo allocation: no allocation by default, users can freely request leaves;')
    validity_start = fields.Date("Start Date", default=fields.Date.today,
                                 help='Adding validity to types of leaves so that it cannot be selected outside this time period')
    validity_stop = fields.Date("End Date")
    valid = fields.Boolean(compute='_compute_valid', search='_search_valid', help='This indicates if it is still possible to use this type of leave')
    time_type = fields.Selection([('leave', 'Leave'), ('other', 'Other')], default='leave', string="Kind of Leave",
                                 help="Whether this should be computed as a holiday or as work time (eg: formation)")
    request_unit = fields.Selection([
        ('day', 'Day'), ('hour', 'Hours')],
        default='day', string='Take Leaves in', required=True)
    unpaid = fields.Boolean('Is Unpaid', default=False)

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
        dt = self._context.get('default_date_from') or fields.Datetime.now()

        for holiday_type in self:
            if holiday_type.validity_start and holiday_type.validity_stop:
                holiday_type.valid = ((dt < holiday_type.validity_stop) and (dt > holiday_type.validity_start))
            elif holiday_type.validity_start and (dt > holiday_type.validity_start):
                holiday_type.valid = False
            else:
                holiday_type.valid = True

    def _search_valid(self, operator, value):
        dt = self._context.get('default_date_from') or fields.Datetime.now()

        signs = ['>=', '<='] if operator == '=' else ['<=', '>=']

        return ['|', ('validity_stop', operator, False), '&',
                ('validity_stop', signs[0] if value else signs[1], dt),
                ('validity_start', signs[1] if value else signs[0], dt)]

    @api.multi
    def _compute_group_days_allocation(self):
        grouped_res = self.env['hr.leave.allocation'].read_group(
            [('holiday_status_id', 'in', self.ids), ('holiday_type', '!=', 'employee'), ('state', '=', 'validate'),
             ('date_from', '>=', fields.Datetime.to_string(datetime.datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)))],
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
        employee_id = self._context.get('employee_id')
        if not employee_id:
            # leave counts is based on employee_id, would be inaccurate if not based on correct employee
            return super(HolidaysType, self).name_get()
        res = []
        employee = self.env['hr.employee'].browse(employee_id).get_remaining_leave_data(self.ids)[employee_id]
        for record in self:
            name = record.name
            if record.allocation_type != 'no':
                virtual_remaining_leaves = float_round(employee[record.id].get('virtual_remaining_leaves', 0), precision_digits=2)
                max_leaves = float_round(employee[record.id].get('max_leaves', 0), precision_digits=2)
                name = "%(name)s (%(count)s)" % {
                    'name': name,
                    'count': _('%g remaining out of %g') % (virtual_remaining_leaves, max_leaves)
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
        leave_ids = super(HolidaysType, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)
        employee_id = self._context.get('employee_id')
        if not count and not order and employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
            leaves = self.browse(leave_ids)
            sort_key = lambda l: (l.allocation_type == 'fixed', l.allocation_type == 'fixed_allocation', employee.get_remaining_leave_data([l.id])[employee_id]['virtual_remaining_leaves'])
            return leaves.sorted(key=sort_key, reverse=True).ids
        return leave_ids

    @api.multi
    def action_see_days_allocated(self):
        self.ensure_one()
        action = self.env.ref('hr_holidays.hr_leave_allocation_action_all').read()[0]
        action['domain'] = [
            ('holiday_type', '!=', 'employee'),
            ('holiday_status_id', '=', self.ids[0]),
            ('date_from', '>=', fields.Datetime.to_string(datetime.datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)))
        ]
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
