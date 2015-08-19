# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class HrHolidaysStatus(models.Model):
    _name = "hr.holidays.status"
    _description = "Leave Type"

    @api.multi
    def name_get(self):
        if not self.env.context.get('employee_id'):
            # leave counts is based on correct employee_id
            return super(HrHolidaysStatus, self).name_get()
        result = []
        for record in self:
            name = record.name
            if not record.limit:
                name = name + ('  (%g/%g)' %
                    (record.virtual_remaining_leaves or 0.0, record.max_leaves or 0.0))
            result.append((record.id, name))
        return result

    name = fields.Char(string='Leave Type', required=True, translate=True)
    categ_id = fields.Many2one('calendar.event.type', string='Meeting Type',
        help='Once a leave is validated, Odoo will create a corresponding '
             'meeting of this type in the calendar.')
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
        ('ivory', 'Ivory')
    ], string='Color in Report', default='red', required=True,
        help='This color will be used in the leaves summary '
             'located in Reporting\Leaves by Department.')
    limit = fields.Boolean(string='Allow to Override Limit',
        help='If you select this check box, the system allows the employees '
             'to take more leaves than the available ones for this type and '
             'will not take them into account for the "Remaining Legal '
             'Leaves" defined on the employee form.')
    active = fields.Boolean(string='Active', default=True,
        help='If the active field is set to false, it will allow you to hide '
             'the leave type without removing it.')
    max_leaves = fields.Integer(compute='_compute_user_left_days', string='Maximum Allowed',
        help='This value is given by the sum of all holidays requests with a '
             'positive value.')
    leaves_taken = fields.Integer(compute='_compute_user_left_days', string='Leaves Already Taken',
        help='This value is given by the sum of all holidays requests with a negative value.')
    remaining_leaves = fields.Integer(compute='_compute_user_left_days', string='Remaining Leaves',
        help='Maximum Leaves Allowed - Leaves Already Taken')
    virtual_remaining_leaves = fields.Integer(compute='_compute_user_left_days',
        string='Virtual Remaining Leaves',
        help='Maximum Leaves Allowed - Leaves Already Taken - Leaves Waiting Approval')
    double_validation = fields.Boolean('Apply Double Validation',
        help='When selected, the Allocation/Leave Requests for this type '
             'require a second validation to be approved.')

    @api.one
    def _compute_user_left_days(self):
        if self.env.context.get('employee_id'):
            employee_id = self.env.context['employee_id']
        else:
            employee = self.env['hr.employee'].search([
                ('user_id', '=', self.env.user.id)], limit=1)
            employee_id = employee.id or False
        if employee_id:
            self.compute_holidays(employee_id)

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """ Override _search to order the results, according to some employee.
        The order is the following

         - limit (limited leaves first, such as Legal Leaves)
         - virtual remaining leaves (higher the better, so using reverse on sorted)

        This override is necessary because those fields are not stored and
        depends on an employee_id given in context. This sort will be done
        when there is an employee_id in context and that no other order has
        been given to the method. """
        status_ids = super(HrHolidaysStatus, self)._search(args, offset=offset,
            limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)

        if not count and not order and self.env.context.get('employee_id'):
            leaves = self.browse(status_ids)
            sort_key = lambda l: (not l.limit, l.virtual_remaining_leaves)
            return map(int, leaves.sorted(key=sort_key, reverse=True))
        return status_ids

    def compute_holidays(self, employee_id):
        holidays = self.env['hr.holidays'].search([
            ('employee_id', '=', employee_id),
            ('state', 'in', ['confirm', 'validate1', 'validate']),
            ('holiday_status_id', '=', self.id)
        ])

        for holiday in holidays:
            if holiday.request_type == 'add' and holiday.state == 'validate':
                    self.virtual_remaining_leaves += holiday.number_of_days_temp
                    self.max_leaves += holiday.number_of_days_temp
                    self.remaining_leaves += holiday.number_of_days_temp
            elif holiday.request_type == 'remove':
                self.virtual_remaining_leaves -= holiday.number_of_days_temp
                if holiday.state == 'validate':
                    self.leaves_taken += holiday.number_of_days_temp
                    self.remaining_leaves -= holiday.number_of_days_temp
