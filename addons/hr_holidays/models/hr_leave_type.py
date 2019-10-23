# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

import datetime
import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression
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
    max_leaves = fields.Float(compute='_compute_leaves', string='Maximum Allowed',
                              help='This value is given by the sum of all leaves requests with a positive value.')
    leaves_taken = fields.Float(
        compute='_compute_leaves', string='Leaves Already Taken',
        help='This value is given by the sum of all leaves requests with a negative value.')
    remaining_leaves = fields.Float(
        compute='_compute_leaves', string='Remaining Leaves',
        help='Maximum Leaves Allowed - Leaves Already Taken')
    virtual_remaining_leaves = fields.Float(
        compute='_compute_leaves', string='Virtual Remaining Leaves',
        help='Maximum Leaves Allowed - Leaves Already Taken - Leaves Waiting Approval')
    group_days_allocation = fields.Float(
        compute='_compute_group_days_allocation', string='Days Allocated')
    group_days_leave = fields.Float(
        compute='_compute_group_days_leave', string='Group Leaves')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    validation_type = fields.Selection([
        ('hr', 'Human Resource officer'),
        ('manager', 'Employee Manager'),
        ('both', 'Double Validation')], default='hr', string='Validation By')
    
    # TODO: remove me in master, the behavior is exactly the same if you choose 'hr' or 'manager'
    # in the validation_type field. This field is used only to hide this possibility to the user
    # to avoid misunderstandings. This field and its corresponding's functions must be removed once
    # the functional part is implemented.
    double_validation = fields.Boolean(string='Apply Double Validation',
        compute='_compute_validation_type', inverse='_inverse_validation_type',
        help="When selected, the Allocation/Leave Requests for this type require a second validation to be approved.")
    
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

    # TODO: remove me in master
    @api.depends('validation_type')
    def _compute_validation_type(self):
        for holiday_type in self:
            if holiday_type.validation_type == 'both':
                holiday_type.double_validation = True
            else:
                holiday_type.double_validation = False

    # TODO: remove me in master
    def _inverse_validation_type(self):
        for holiday_type in self:
            if holiday_type.double_validation == True:
                holiday_type.validation_type = 'both'
            else:
                #IF to preserve the information (hr or manager)
                if holiday_type.validation_type == 'both':
                    holiday_type.validation_type = 'hr'

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
            status_dict['virtual_remaining_leaves'] -= (request.number_of_hours_display
                                                    if request.leave_type_request_unit == 'hour'
                                                    else request.number_of_days)
            if request.state == 'validate':
                status_dict['leaves_taken'] += (request.number_of_hours_display
                                            if request.leave_type_request_unit == 'hour'
                                            else request.number_of_days)
                status_dict['remaining_leaves'] -= (request.number_of_hours_display
                                                if request.leave_type_request_unit == 'hour'
                                                else request.number_of_days)

        for allocation in allocations.sudo():
            status_dict = result[allocation.holiday_status_id.id]
            if allocation.state == 'validate':
                # note: add only validated allocation even for the virtual
                # count; otherwise pending then refused allocation allow
                # the employee to create more leaves than possible
                status_dict['virtual_remaining_leaves'] += (allocation.number_of_hours_display
                                                          if allocation.type_request_unit == 'hour'
                                                          else allocation.number_of_days)
                status_dict['max_leaves'] += (allocation.number_of_hours_display
                                            if allocation.type_request_unit == 'hour'
                                            else allocation.number_of_days)
                status_dict['remaining_leaves'] += (allocation.number_of_hours_display
                                                  if allocation.type_request_unit == 'hour'
                                                  else allocation.number_of_days)

        return result

    def _get_contextual_employee_id(self):
        if 'employee_id' in self._context:
            employee_id = self._context['employee_id']
        elif 'default_employee_id' in self._context:
            employee_id = self._context['default_employee_id']
        else:
            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1).id
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
                    ) + (_(' hours') if record.request_unit == 'hour' else _(' days'))
                }
            res.append((record.id, name))
        return res

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """ Override _search to order the results, according to some employee.
        The order is the following

         - allocation fixed (with remaining leaves),
         - allowing allocation (with remaining leaves),
         - no allocation,
         - allocation fixed (without remaining leaves),
         - allowing allocation (without remaining leaves).

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
            sort_key = lambda l: (
                l.allocation_type == 'fixed' and l.virtual_remaining_leaves > 0 and l.max_leaves > 0,
                l.allocation_type == 'fixed_allocation' and l.virtual_remaining_leaves > 0 and l.max_leaves > 0,
                l.allocation_type == 'no',
                l.allocation_type == 'fixed',
                l.allocation_type == 'fixed_allocation'
            )
            return leaves.sorted(key=sort_key, reverse=True).ids[:limit]
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
