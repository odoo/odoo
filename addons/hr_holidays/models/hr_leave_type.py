# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

import logging

from odoo import api, fields, models
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class HolidaysType(models.Model):
    _name = "hr.leave.type"
    _description = "Leave Type"

    name = fields.Char('Leave Type', required=True, translate=True)
    categ_id = fields.Many2one('calendar.event.type', string='Meeting Type',
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
    limit = fields.Boolean('Allow to Override Limit',
        help='If you select this check box, the system allows the employees to take more leaves '
             'than the available ones for this type and will not take them into account for the '
             '"Remaining Legal Leaves" defined on the employee form.')
    active = fields.Boolean('Active', default=True,
        help="If the active field is set to false, it will allow you to hide the leave type without removing it.")

    max_leaves = fields.Float(compute='_compute_leaves', string='Maximum Allowed',
        help='This value is given by the sum of all leaves requests with a positive value.')
    leaves_taken = fields.Float(compute='_compute_leaves', string='Leaves Already Taken',
        help='This value is given by the sum of all leaves requests with a negative value.')
    remaining_leaves = fields.Float(compute='_compute_leaves', string='Remaining Leaves',
        help='Maximum Leaves Allowed - Leaves Already Taken')
    virtual_remaining_leaves = fields.Float(compute='_compute_leaves', string='Virtual Remaining Leaves',
        help='Maximum Leaves Allowed - Leaves Already Taken - Leaves Waiting Approval')

    double_validation = fields.Boolean(string='Apply Double Validation',
        help="When selected, the Allocation/Leave Requests for this type require a second validation to be approved.")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)

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
            status_dict['virtual_remaining_leaves'] -= request.number_of_days_temp
            if request.state == 'validate':
                status_dict['leaves_taken'] += request.number_of_days_temp
                status_dict['remaining_leaves'] -= request.number_of_days_temp

        for allocation in allocations:
            status_dict = result[allocation.holiday_status_id.id]
            if allocation.state == 'validate':
                # note: add only validated allocation even for the virtual
                # count; otherwise pending then refused allocation allow
                # the employee to create more leaves than possible
                status_dict['virtual_remaining_leaves'] += allocation.number_of_days_temp
                status_dict['max_leaves'] += allocation.number_of_days_temp
                status_dict['remaining_leaves'] += allocation.number_of_days_temp

        return result

    @api.multi
    def _compute_leaves(self):
        data_days = {}
        if 'employee_id' in self._context:
            employee_id = self._context['employee_id']
        else:
            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1).id

        if employee_id:
            data_days = self.get_days(employee_id)

        for holiday_status in self:
            result = data_days.get(holiday_status.id, {})
            holiday_status.max_leaves = result.get('max_leaves', 0)
            holiday_status.leaves_taken = result.get('leaves_taken', 0)
            holiday_status.remaining_leaves = result.get('remaining_leaves', 0)
            holiday_status.virtual_remaining_leaves = result.get('virtual_remaining_leaves', 0)

    @api.multi
    def name_get(self):
        if not self._context.get('employee_id'):
            # leave counts is based on employee_id, would be inaccurate if not based on correct employee
            return super(HolidaysType, self).name_get()
        res = []
        for record in self:
            name = record.name
            if not record.limit:
                name = "%(name)s (%(count)s)" % {
                    'name': name,
                    'count': _('%g remaining out of %g') % (record.virtual_remaining_leaves or 0.0, record.max_leaves or 0.0)
                }
            res.append((record.id, name))
        return res

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """ Override _search to order the results, according to some employee.
        The order is the following

         - limit (limited leaves first, such as Legal Leaves)
         - virtual remaining leaves (higher the better, so using reverse on sorted)

        This override is necessary because those fields are not stored and depends
        on an employee_id given in context. This sort will be done when there
        is an employee_id in context and that no other order has been given
        to the method.
        """
        leave_ids = super(HolidaysType, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)
        if not count and not order and self._context.get('employee_id'):
            leaves = self.browse(leave_ids)
            sort_key = lambda l: (not l.limit, l.virtual_remaining_leaves)
            return leaves.sorted(key=sort_key, reverse=True).ids
        return leave_ids
