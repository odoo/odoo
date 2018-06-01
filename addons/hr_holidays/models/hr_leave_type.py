# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class HolidaysType(models.Model):
    _name = "hr.leave.type"
    _description = "Leave Type"
    _order = "sequence, id"

    name = fields.Char('Leave Type', required=True, translate=True)
    sequence = fields.Integer(default=100,
                              help='The type with the smallest sequence is the default value in leave request')
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
    limit = fields.Boolean('Unlimited',
        help="If you select this check box, the system will allow the employees to ask"
             "for leaves without allocating some beforehand")
    active = fields.Boolean('Active', default=True,
        help="If the active field is set to false, it will allow you to hide the leave type without removing it.")

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)

    validation_type = fields.Selection([('hr', 'Human Resource Responsible'),
                                      ('manager', 'Manager'),
                                      ('both', 'Double Validation')],
                                     default='hr',
                                     string='Validation By')

    employee_applicability = fields.Selection([('both', 'On Leave As Well As On Allocation'),
                                            ('leave', 'Only On Leave'),
                                            ('allocation', 'Only On Allocation')],
                                           default=lambda self: 'leave' if self.limit else 'both', string='Available For Employee :',
                                           help='This leave type will be available on Leave / Allocation request based on selected value')

    validity_start = fields.Date("Start Date", default=fields.Date.today,
                                 help='Adding validity to types of leaves so that it cannot be selected outside'
                                 'this time period')
    validity_stop = fields.Date("End Date")

    valid = fields.Boolean(compute='_compute_valid', search='_search_valid', help='This indicates if it is still possible to use this type of leave')

    time_type = fields.Selection([('leave', 'Leave'), ('other', 'Other')], default='leave', string="Kind of Leave",
                                 help="Whether this should be computed as a holiday or as work time (eg: formation)")

    @api.multi
    @api.constrains('validity_start', 'validity_stop')
    def _check_validity_dates(self):
        for htype in self:
            if htype.validity_start and htype.validity_stop and \
               htype.validity_start > htype.validity_stop:
                raise ValidationError(_("End of validity period should be greater than start of validity period"))

    @api.onchange('limit')
    def _onchange_limit(self):
        if self.limit:
            self.employee_applicability = 'leave'

    @api.multi
    @api.depends('validity_start', 'validity_stop', 'limit')
    def _compute_valid(self):
        dt = self._context.get('default_date_from', fields.Date.today())

        for holiday_type in self:
            if holiday_type.validity_start and holiday_type.validity_stop:
                holiday_type.valid = ((dt < holiday_type.validity_stop) and (dt > holiday_type.validity_start))
            else:
                holiday_type.valid = not holiday_type.validity_stop

    def _search_valid(self, operator, value):
        dt = self._context.get('default_date_from', fields.Date.today())
        signs = ['>=', '<='] if operator == '=' else ['<=', '>=']

        return ['|', ('validity_stop', operator, False), '&',
                ('validity_stop', signs[0] if value else signs[1], dt),
                ('validity_start', signs[1] if value else signs[0], dt)]

    @api.multi
    def name_get(self):
        employee_id = self._context.get('employee_id')
        if not employee_id:
            # leave counts is based on employee_id, would be inaccurate if not based on correct employee
            return super(HolidaysType, self).name_get()
        res = []
        for record in self:
            employee = self.env['hr.employee'].browse(employee_id).with_context(holiday_status_ids=record.ids)
            name = record.name
            if not record.limit:
                name = "%(name)s (%(count)s)" % {
                    'name': name,
                    'count': _('%g remaining out of %g') % (employee.virtual_remaining_leaves or 0.0, employee.max_leaves or 0.0)
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
        employee_id = self._context.get('employee_id')
        if not count and not order and employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
            leaves = self.browse(leave_ids)
            sort_key = lambda l: (not l.limit, employee.get_days([l.id])['virtual_remaining_leaves'])
            return leaves.sorted(key=sort_key, reverse=True).ids
        return leave_ids
