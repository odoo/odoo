# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)


import calendar
import datetime
from datetime import date
import logging
import math
import time
from operator import attrgetter

from dateutil.relativedelta import relativedelta
import pytz

from openerp.exceptions import UserError, AccessError
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class hr_holidays(osv.osv):
    _name = "hr.holidays"
    _description = "Leave"
    _order = "type desc, date_from asc"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    def _employee_get(self, cr, uid, context=None):
        emp_id = context.get('default_employee_id', False)
        if emp_id:
            return emp_id
        ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context)
        if ids:
            return ids[0]
        return False

    def _compute_number_of_days(self, cr, uid, ids, name, args, context=None):
        result = {}
        for hol in self.browse(cr, uid, ids, context=context):
            if hol.type=='remove':
                result[hol.id] = -hol.number_of_days_temp
            else:
                result[hol.id] = hol.number_of_days_temp
        return result

    def _get_can_reset(self, cr, uid, ids, name, arg, context=None):
        """User can reset a leave request if it is its own leave request or if
        he is an Hr Manager. """
        user = self.pool['res.users'].browse(cr, uid, uid, context=context)
        group_hr_manager_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'group_hr_manager')[1]
        if group_hr_manager_id in [g.id for g in user.groups_id]:
            return dict.fromkeys(ids, True)
        result = dict.fromkeys(ids, False)
        for holiday in self.browse(cr, uid, ids, context=context):
            if holiday.employee_id and holiday.employee_id.user_id and holiday.employee_id.user_id.id == uid:
                result[holiday.id] = True
        return result

    def _check_date(self, cr, uid, ids, context=None):
        for holiday in self.browse(cr, uid, ids, context=context):
            domain = [
                ('date_from', '<=', holiday.date_to),
                ('date_to', '>=', holiday.date_from),
                ('employee_id', '=', holiday.employee_id.id),
                ('id', '!=', holiday.id),
                ('state', 'not in', ['cancel', 'refuse']),
            ]
            nholidays = self.search_count(cr, uid, domain, context=context)
            if nholidays:
                return False
        return True

    _check_holidays = lambda self, cr, uid, ids, context=None: self.check_holidays(cr, uid, ids, context=context)

    _columns = {
        'name': fields.char('Description', size=64),
        'state': fields.selection([('draft', 'To Submit'), ('cancel', 'Cancelled'),('confirm', 'To Approve'), ('refuse', 'Refused'), ('validate1', 'Second Approval'), ('validate', 'Approved')],
            'Status', readonly=True, track_visibility='onchange', copy=False,
            help='The status is set to \'To Submit\', when a holiday request is created.\
            \nThe status is \'To Approve\', when holiday request is confirmed by user.\
            \nThe status is \'Refused\', when holiday request is refused by manager.\
            \nThe status is \'Approved\', when holiday request is approved by manager.'),
        'payslip_status': fields.boolean(string='Reported in last payslips',
            help='Green this button when the leave has been taken into account in the payslip.'),
        'report_note': fields.text('HR Comments'),
        'user_id':fields.related('employee_id', 'user_id', type='many2one', relation='res.users', string='User', store=True),
        'date_from': fields.datetime('Start Date', readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}, select=True, copy=False),
        'date_to': fields.datetime('End Date', readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}, copy=False),
        'holiday_status_id': fields.many2one("hr.holidays.status", "Leave Type", required=True,readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}),
        'employee_id': fields.many2one('hr.employee', "Employee", select=True, invisible=False, readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}),
        'manager_id': fields.many2one('hr.employee', 'First Approval', invisible=False, readonly=True, copy=False,
                                      help='This area is automatically filled by the user who validate the leave'),
        'notes': fields.text('Reasons',readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}),
        'number_of_days_temp': fields.float('Allocation', readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}, copy=False),
        'number_of_days': fields.function(_compute_number_of_days, string='Number of Days', store=True),
        'meeting_id': fields.many2one('calendar.event', 'Meeting'),
        'type': fields.selection([('remove','Leave Request'),('add','Allocation Request')], 'Request Type', required=True, readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}, help="Choose 'Leave Request' if someone wants to take an off-day. \nChoose 'Allocation Request' if you want to increase the number of leaves available for someone", select=True),
        'parent_id': fields.many2one('hr.holidays', 'Parent'),
        'linked_request_ids': fields.one2many('hr.holidays', 'parent_id', 'Linked Requests',),
        'department_id':fields.related('employee_id', 'department_id', string='Department', type='many2one', relation='hr.department', readonly=True, store=True),
        'category_id': fields.many2one('hr.employee.category', "Employee Tag", help='Category of Employee', readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}),
        'holiday_type': fields.selection([('employee','By Employee'),('category','By Employee Tag')], 'Allocation Mode', readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}, help='By Employee: Allocation/Request for individual Employee, By Employee Tag: Allocation/Request for group of employees in category', required=True),
        'manager_id2': fields.many2one('hr.employee', 'Second Approval', readonly=True, copy=False,
                                       help='This area is automaticly filled by the user who validate the leave with second level (If Leave type need second validation)'),
        'double_validation': fields.related('holiday_status_id', 'double_validation', type='boolean', relation='hr.holidays.status', string='Apply Double Validation'),
        'can_reset': fields.function(
            _get_can_reset, string="Can reset",
            type='boolean'),
    }
    _defaults = {
        'employee_id': _employee_get,
        'state': 'confirm',
        'type': 'remove',
        'user_id': lambda obj, cr, uid, context: uid,
        'holiday_type': 'employee',
        'payslip_status': False,
    }
    _constraints = [
        (_check_date, 'You can not have 2 leaves that overlaps on same day!', ['date_from', 'date_to']),
        (_check_holidays, 'The number of remaining leaves is not sufficient for this leave type.\n'
                          'Please verify also the leaves waiting for validation.', ['state', 'number_of_days_temp'])
    ]

    _sql_constraints = [
        ('type_value', "CHECK( (holiday_type='employee' AND employee_id IS NOT NULL) or (holiday_type='category' AND category_id IS NOT NULL))",
         "The employee or employee category of this request is missing. Please make sure that your user login is linked to an employee."),
        ('date_check2', "CHECK ( (type='add') OR (date_from <= date_to))", "The start date must be anterior to the end date."),
        ('date_check', "CHECK ( number_of_days_temp >= 0 )", "The number of days must be greater than 0."),
    ]

    def _create_resource_leave(self, cr, uid, leaves, context=None):
        '''This method will create entry in resource calendar leave object at the time of holidays validated '''
        obj_res_leave = self.pool.get('resource.calendar.leaves')
        for leave in leaves:
            vals = {
                'name': leave.name,
                'date_from': leave.date_from,
                'holiday_id': leave.id,
                'date_to': leave.date_to,
                'resource_id': leave.employee_id.resource_id.id,
                'calendar_id': leave.employee_id.resource_id.calendar_id.id
            }
            obj_res_leave.create(cr, uid, vals, context=context)
        return True

    def _remove_resource_leave(self, cr, uid, ids, context=None):
        '''This method will create entry in resource calendar leave object at the time of holidays cancel/removed'''
        obj_res_leave = self.pool.get('resource.calendar.leaves')
        leave_ids = obj_res_leave.search(cr, uid, [('holiday_id', 'in', ids)], context=context)
        return obj_res_leave.unlink(cr, uid, leave_ids, context=context)

    def onchange_type(self, cr, uid, ids, holiday_type, employee_id=False, context=None):
        result = {}
        if holiday_type == 'employee' and not employee_id:
            ids_employee = self.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)])
            if ids_employee:
                result['value'] = {
                    'employee_id': ids_employee[0]
                }
        elif holiday_type != 'employee':
            result['value'] = {
                    'employee_id': False
                }
        return result

    def onchange_employee(self, cr, uid, ids, employee_id):
        result = {'value': {'department_id': False}}
        if employee_id:
            employee = self.pool.get('hr.employee').browse(cr, uid, employee_id)
            result['value'] = {'department_id': employee.department_id.id}
        return result

    # TODO: can be improved using resource calendar method
    def _get_number_of_days(self, date_from, date_to):
        """Returns a float equals to the timedelta between two dates given as string."""

        DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
        from_dt = datetime.datetime.strptime(date_from, DATETIME_FORMAT)
        to_dt = datetime.datetime.strptime(date_to, DATETIME_FORMAT)
        timedelta = to_dt - from_dt
        diff_day = timedelta.days + float(timedelta.seconds) / 86400
        return diff_day

    def unlink(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.state not in ['draft', 'cancel', 'confirm']:
                raise UserError(_('You cannot delete a leave which is in %s state.') % (rec.state,))
        return super(hr_holidays, self).unlink(cr, uid, ids, context)

    def onchange_date_from(self, cr, uid, ids, date_to, date_from):
        """
        If there are no date set for date_to, automatically set one 8 hours later than
        the date_from.
        Also update the number_of_days.
        """
        # date_to has to be greater than date_from
        if (date_from and date_to) and (date_from > date_to):
            raise UserError(_('The start date must be anterior to the end date.'))

        result = {'value': {}}

        # No date_to set so far: automatically compute one 8 hours later
        if date_from and not date_to:
            date_to_with_delta = datetime.datetime.strptime(date_from, tools.DEFAULT_SERVER_DATETIME_FORMAT) + datetime.timedelta(hours=8)
            result['value']['date_to'] = str(date_to_with_delta)

        # Compute and update the number of days
        if (date_to and date_from) and (date_from <= date_to):
            diff_day = self._get_number_of_days(date_from, date_to)
            result['value']['number_of_days_temp'] = round(math.floor(diff_day))+1
        else:
            result['value']['number_of_days_temp'] = 0

        return result

    def onchange_date_to(self, cr, uid, ids, date_to, date_from):
        """
        Update the number_of_days.
        """
        # date_to has to be greater than date_from
        if (date_from and date_to) and (date_from > date_to):
            raise UserError(_('The start date must be anterior to the end date.'))

        result = {'value': {}}

        # Compute and update the number of days
        if (date_to and date_from) and (date_from <= date_to):
            diff_day = self._get_number_of_days(date_from, date_to)
            result['value']['number_of_days_temp'] = round(math.floor(diff_day))+1
        else:
            result['value']['number_of_days_temp'] = 0
        return result

    def add_follower(self, cr, uid, ids, employee_id, context=None):
        employee = self.pool.get('hr.employee').browse(cr, uid, employee_id, context=context)
        if employee and employee.user_id:
            self.message_subscribe_users(cr, uid, ids, user_ids=[employee.user_id.id], context=context)

    def create(self, cr, uid, values, context=None):
        """ Override to avoid automatic logging of creation """
        if context is None:
            context = {}
        employee_id = values.get('employee_id', False)
        context = dict(context, mail_create_nolog=True)
        if values.get('state') and values['state'] not in ['draft', 'confirm', 'cancel'] and not self.pool['res.users'].has_group(cr, uid, 'base.group_hr_user'):
            raise AccessError(_('You cannot set a leave request as \'%s\'. Contact a human resource manager.') % values.get('state'))
        hr_holiday_id = super(hr_holidays, self).create(cr, uid, values, context=context)
        self.add_follower(cr, uid, [hr_holiday_id], employee_id, context=context)
        return hr_holiday_id

    def write(self, cr, uid, ids, vals, context=None):
        employee_id = vals.get('employee_id', False)
        if vals.get('state') and vals['state'] not in ['draft', 'confirm', 'cancel'] and not self.pool['res.users'].has_group(cr, uid, 'base.group_hr_user'):
            raise AccessError(_('You cannot set a leave request as \'%s\'. Contact a human resource manager.') % vals.get('state'))
        hr_holiday_id = super(hr_holidays, self).write(cr, uid, ids, vals, context=context)
        self.add_follower(cr, uid, ids, employee_id, context=context)
        return hr_holiday_id

    def holidays_reset(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'draft',
            'manager_id': False,
            'manager_id2': False,
        })
        to_unlink = []
        for record in self.browse(cr, uid, ids, context=context):
            for record2 in record.linked_request_ids:
                self.holidays_reset(cr, uid, [record2.id], context=context)
                to_unlink.append(record2.id)
        if to_unlink:
            self.unlink(cr, uid, to_unlink, context=context)
        return True

    def holidays_first_validate(self, cr, uid, ids, context=None):
        obj_emp = self.pool.get('hr.employee')
        ids2 = obj_emp.search(cr, uid, [('user_id', '=', uid)])
        manager = ids2 and ids2[0] or False
        return self.write(cr, uid, ids, {'state': 'validate1', 'manager_id': manager}, context=context)

    def holidays_validate(self, cr, uid, ids, context=None):
        obj_emp = self.pool.get('hr.employee')
        ids2 = obj_emp.search(cr, uid, [('user_id', '=', uid)])
        manager = ids2 and ids2[0] or False
        self.write(cr, uid, ids, {'state': 'validate'}, context=context)
        data_holiday = self.browse(cr, uid, ids)
        for record in data_holiday:
            if record.double_validation:
                self.write(cr, uid, [record.id], {'manager_id2': manager})
            else:
                self.write(cr, uid, [record.id], {'manager_id': manager})
            if record.holiday_type == 'employee' and record.type == 'remove':
                meeting_obj = self.pool.get('calendar.event')
                meeting_vals = {
                    'name': record.name or _('Leave Request'),
                    'categ_ids': record.holiday_status_id.categ_id and [(6,0,[record.holiday_status_id.categ_id.id])] or [],
                    'duration': record.number_of_days_temp * 8,
                    'description': record.notes,
                    'user_id': record.user_id.id,
                    'start': record.date_from,
                    'stop': record.date_to,
                    'allday': False,
                    'state': 'open',            # to block that meeting date in the calendar
                    'class': 'confidential'
                }
                #Add the partner_id (if exist) as an attendee
                if record.user_id and record.user_id.partner_id:
                    meeting_vals['partner_ids'] = [(4,record.user_id.partner_id.id)]

                ctx_no_email = dict(context or {}, no_email=True)
                meeting_id = meeting_obj.create(cr, uid, meeting_vals, context=ctx_no_email)
                self._create_resource_leave(cr, uid, [record], context=context)
                self.write(cr, uid, ids, {'meeting_id': meeting_id})
            elif record.holiday_type == 'category':
                emp_ids = obj_emp.search(cr, uid, [('category_ids', 'child_of', [record.category_id.id])])
                leave_ids = []
                for emp in obj_emp.browse(cr, uid, emp_ids):
                    vals = {
                        'name': record.name,
                        'type': record.type,
                        'holiday_type': 'employee',
                        'holiday_status_id': record.holiday_status_id.id,
                        'date_from': record.date_from,
                        'date_to': record.date_to,
                        'notes': record.notes,
                        'number_of_days_temp': record.number_of_days_temp,
                        'parent_id': record.id,
                        'employee_id': emp.id
                    }
                    leave_ids.append(self.create(cr, uid, vals, context=None))
                for leave_id in leave_ids:
                    # TODO is it necessary to interleave the calls?
                    for sig in ('confirm', 'validate', 'second_validate'):
                        self.signal_workflow(cr, uid, [leave_id], sig)
        return True

    def holidays_confirm(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            if record.employee_id and record.employee_id.parent_id and record.employee_id.parent_id.user_id:
                self.message_subscribe_users(cr, uid, [record.id], user_ids=[record.employee_id.parent_id.user_id.id], context=context)
        return self.write(cr, uid, ids, {'state': 'confirm'})

    def holidays_refuse(self, cr, uid, ids, context=None):
        obj_emp = self.pool.get('hr.employee')
        ids2 = obj_emp.search(cr, uid, [('user_id', '=', uid)])
        manager = ids2 and ids2[0] or False
        for holiday in self.browse(cr, uid, ids, context=context):
            if holiday.state == 'validate1':
                self.write(cr, uid, [holiday.id], {'state': 'refuse', 'manager_id': manager})
            else:
                self.write(cr, uid, [holiday.id], {'state': 'refuse', 'manager_id2': manager})
        self.holidays_cancel(cr, uid, ids, context=context)
        return True

    def holidays_cancel(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids):
            # Delete the meeting
            if record.meeting_id:
                record.meeting_id.unlink()

            # If a category that created several holidays, cancel all related
            self.signal_workflow(cr, uid, map(attrgetter('id'), record.linked_request_ids or []), 'refuse')

        self._remove_resource_leave(cr, uid, ids, context=context)
        return True

    def check_holidays(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            if record.holiday_type != 'employee' or record.type != 'remove' or not record.employee_id or record.holiday_status_id.limit:
                continue
            leave_days = self.pool.get('hr.holidays.status').get_days(cr, uid, [record.holiday_status_id.id], record.employee_id.id, context=context)[record.holiday_status_id.id]
            if leave_days['remaining_leaves'] < 0 or leave_days['virtual_remaining_leaves'] < 0:
                return False
        return True

    def toggle_payslip_status(self, cr, uid, ids, context=None):
        ids_to_set_true = self.search(cr, uid, [('id', 'in', ids), ('payslip_status', '=', False)], context=context)
        ids_to_set_false = list(set(ids) - set(ids_to_set_true))
        return self.write(cr, uid, ids_to_set_true, {'payslip_status': True}, context=context) and self.write(cr, uid, ids_to_set_false, {'payslip_status': False}, context=context)

    def _track_subtype(self, cr, uid, ids, init_values, context=None):
        record = self.browse(cr, uid, ids[0], context=context)
        if 'state' in init_values and record.state == 'validate':
            return 'hr_holidays.mt_holidays_approved'
        elif 'state' in init_values and record.state == 'validate1':
            return 'hr_holidays.mt_holidays_first_validated'
        elif 'state' in init_values and record.state == 'confirm':
            return 'hr_holidays.mt_holidays_confirmed'
        elif 'state' in init_values and record.state == 'refuse':
            return 'hr_holidays.mt_holidays_refused'
        return super(hr_holidays, self)._track_subtype(cr, uid, ids, init_values, context=context)
