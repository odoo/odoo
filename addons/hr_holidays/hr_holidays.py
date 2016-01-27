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
from werkzeug import url_encode

from dateutil.relativedelta import relativedelta

from openerp.exceptions import UserError, AccessError
from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class hr_holidays_status(osv.osv):
    _name = "hr.holidays.status"
    _description = "Leave Type"

    def get_days(self, cr, uid, ids, employee_id, context=None):
        result = dict((id, dict(max_leaves=0, leaves_taken=0, remaining_leaves=0,
                                virtual_remaining_leaves=0)) for id in ids)
        holiday_ids = self.pool['hr.holidays'].search(cr, uid, [('employee_id', '=', employee_id),
                                                                ('state', 'in', ['confirm', 'validate1', 'validate']),
                                                                ('holiday_status_id', 'in', ids)
                                                                ], context=context)
        for holiday in self.pool['hr.holidays'].browse(cr, uid, holiday_ids, context=context):
            status_dict = result[holiday.holiday_status_id.id]
            if holiday.type == 'add':
                if holiday.state == 'validate':
                    # note: add only validated allocation even for the virtual
                    # count; otherwise pending then refused allocation allow
                    # the employee to create more leaves than possible
                    status_dict['virtual_remaining_leaves'] += holiday.number_of_days_temp
                    status_dict['max_leaves'] += holiday.number_of_days_temp
                    status_dict['remaining_leaves'] += holiday.number_of_days_temp
            elif holiday.type == 'remove':  # number of days is negative
                status_dict['virtual_remaining_leaves'] -= holiday.number_of_days_temp
                if holiday.state == 'validate':
                    status_dict['leaves_taken'] += holiday.number_of_days_temp
                    status_dict['remaining_leaves'] -= holiday.number_of_days_temp
        return result

    def _user_left_days(self, cr, uid, ids, name, args, context=None):
        employee_id = False
        if context and 'employee_id' in context:
            employee_id = context['employee_id']
        else:
            employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context)
            if employee_ids:
                employee_id = employee_ids[0]
        if employee_id:
            res = self.get_days(cr, uid, ids, employee_id, context=context)
        else:
            res = dict((res_id, {'leaves_taken': 0, 'remaining_leaves': 0, 'max_leaves': 0}) for res_id in ids)
        return res

    _columns = {
        'name': fields.char('Leave Type', size=64, required=True, translate=True),
        'categ_id': fields.many2one('calendar.event.type', 'Meeting Type',
            help='Once a leave is validated, Odoo will create a corresponding meeting of this type in the calendar.'),
        'color_name': fields.selection([('red', 'Red'),('blue','Blue'), ('lightgreen', 'Light Green'), ('lightblue','Light Blue'), ('lightyellow', 'Light Yellow'), ('magenta', 'Magenta'),('lightcyan', 'Light Cyan'),('black', 'Black'),('lightpink', 'Light Pink'),('brown', 'Brown'),('violet', 'Violet'),('lightcoral', 'Light Coral'),('lightsalmon', 'Light Salmon'),('lavender', 'Lavender'),('wheat', 'Wheat'),('ivory', 'Ivory')],'Color in Report', required=True, help='This color will be used in the leaves summary located in Reporting\Leaves by Department.'),
        'limit': fields.boolean('Allow to Override Limit', help='If you select this check box, the system allows the employees to take more leaves than the available ones for this type and will not take them into account for the "Remaining Legal Leaves" defined on the employee form.'),
        'active': fields.boolean('Active', help="If the active field is set to false, it will allow you to hide the leave type without removing it."),
        'max_leaves': fields.function(_user_left_days, string='Maximum Allowed', help='This value is given by the sum of all holidays requests with a positive value.', multi='user_left_days'),
        'leaves_taken': fields.function(_user_left_days, string='Leaves Already Taken', help='This value is given by the sum of all holidays requests with a negative value.', multi='user_left_days'),
        'remaining_leaves': fields.function(_user_left_days, string='Remaining Leaves', help='Maximum Leaves Allowed - Leaves Already Taken', multi='user_left_days'),
        'virtual_remaining_leaves': fields.function(_user_left_days, string='Virtual Remaining Leaves', help='Maximum Leaves Allowed - Leaves Already Taken - Leaves Waiting Approval', multi='user_left_days'),
        'double_validation': fields.boolean('Apply Double Validation', help="When selected, the Allocation/Leave Requests for this type require a second validation to be approved."),
        'company_id': fields.many2one('res.company', 'Company'),
    }
    _defaults = {
        'color_name': 'red',
        'active': True,
    }

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not context.get('employee_id'):
            # leave counts is based on employee_id, would be inaccurate if not based on correct employee
            return super(hr_holidays_status, self).name_get(cr, uid, ids, context=context)
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            if not record.limit:
                name = name + ('  (%g/%g)' % (record.virtual_remaining_leaves or 0.0, record.max_leaves or 0.0))
            res.append((record.id, name))
        return res

    def _search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False, access_rights_uid=None):
        """ Override _search to order the results, according to some employee.
        The order is the following

         - limit (limited leaves first, such as Legal Leaves)
         - virtual remaining leaves (higher the better, so using reverse on sorted)

        This override is necessary because those fields are not stored and depends
        on an employee_id given in context. This sort will be done when there
        is an employee_id in context and that no other order has been given
        to the method. """
        if context is None:
            context = {}
        ids = super(hr_holidays_status, self)._search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count, access_rights_uid=access_rights_uid)
        if not count and not order and context.get('employee_id'):
            leaves = self.browse(cr, uid, ids, context=context)
            sort_key = lambda l: (not l.limit, l.virtual_remaining_leaves)
            return map(int, leaves.sorted(key=sort_key, reverse=True))
        return ids


class hr_holidays(osv.osv):
    _name = "hr.holidays"
    _description = "Leave"
    _order = "type desc, date_from desc"
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

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for leave in self.browse(cr, uid, ids, context=context):
            res.append((leave.id, leave.name or _("%s on %s") % (leave.employee_id.name, leave.holiday_status_id.name)))
        return res

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

    def _check_state_access_right(self, cr, uid, vals, context=None):
        if vals.get('state') and vals['state'] not in ['draft', 'confirm', 'cancel'] and not self.pool['res.users'].has_group(cr, uid, 'base.group_hr_user'):
            return False
        return True

    def add_follower(self, cr, uid, ids, employee_id, context=None):
        employee = self.pool.get('hr.employee').browse(cr, uid, employee_id, context=context)
        if employee and employee.user_id:
            self.message_subscribe_users(cr, uid, ids, user_ids=[employee.user_id.id], context=context)

    def create(self, cr, uid, values, context=None):
        """ Override to avoid automatic logging of creation """
        if context is None:
            context = {}
        employee_id = values.get('employee_id', False)
        context = dict(context, mail_create_nolog=True, mail_create_nosubscribe=True)
        if not self._check_state_access_right(cr, uid, values, context):
            raise AccessError(_('You cannot set a leave request as \'%s\'. Contact a human resource manager.') % values.get('state'))
        if not values.get('name'):
            employee_name = self.pool['hr.employee'].browse(cr, uid, employee_id, context=context).name
            holiday_type = self.pool['hr.holidays.status'].browse(cr, uid, values.get('holiday_status_id'), context=context).name
            values['name'] = _("%s on %s") % (employee_name, holiday_type)
        hr_holiday_id = super(hr_holidays, self).create(cr, uid, values, context=context)
        self.add_follower(cr, uid, [hr_holiday_id], employee_id, context=context)
        return hr_holiday_id

    def write(self, cr, uid, ids, vals, context=None):
        employee_id = vals.get('employee_id', False)
        if not self._check_state_access_right(cr, uid, vals, context):
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
                    'name': record.display_name,
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
                emp_ids = record.category_id.employee_ids.ids
                leave_ids = []
                batch_context = dict(context, mail_notify_force_send=False)
                for emp in obj_emp.browse(cr, uid, emp_ids, context=context):
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
                    leave_ids.append(self.create(cr, uid, vals, context=batch_context))
                for leave_id in leave_ids:
                    # TODO is it necessary to interleave the calls?
                    for sig in ('confirm', 'validate', 'second_validate'):
                        self.signal_workflow(cr, uid, [leave_id], sig)
        return True

    def holidays_confirm(self, cr, uid, ids, context=None):
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

    def _notification_group_recipients(self, cr, uid, ids, message, recipients, done_ids, group_data, context=None):
        """ Override the mail.thread method to handle HR users and officers
        recipients. Indeed those will have specific action in their notification
        emails. """
        group_hr_user = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'base.group_hr_user')
        for recipient in recipients:
            if recipient.id in done_ids:
                continue
            if recipient.user_ids and group_hr_user in recipient.user_ids[0].groups_id.ids:
                group_data['group_hr_user'] |= recipient
                done_ids.add(recipient.id)
        return super(hr_holidays, self)._notification_group_recipients(cr, uid, ids, message, recipients, done_ids, group_data, context=context)

    def _notification_get_recipient_groups(self, cr, uid, ids, message, recipients, context=None):
        res = super(hr_holidays, self)._notification_get_recipient_groups(cr, uid, ids, message, recipients, context=context)

        app_action = '/mail/workflow?%s' % url_encode({'model': self._name, 'res_id': ids[0], 'signal': 'validate'})
        ref_action = '/mail/workflow?%s' % url_encode({'model': self._name, 'res_id': ids[0], 'signal': 'refuse'})

        holiday = self.browse(cr, uid, ids[0], context=context)
        actions = []
        if holiday.state == 'confirm':
            actions.append({'url': app_action, 'title': 'Approve'})
        if holiday.state in ['confirm', 'validate', 'validate1']:
            actions.append({'url': ref_action, 'title': 'Refuse'})

        res['group_hr_user'] = {
            'actions': actions
        }
        return res


class resource_calendar_leaves(osv.osv):
    _inherit = "resource.calendar.leaves"
    _description = "Leave Detail"
    _columns = {
        'holiday_id': fields.many2one("hr.holidays", "Leave Request"),
    }


class hr_employee(osv.Model):
    _inherit = "hr.employee"

    def _set_remaining_days(self, cr, uid, empl_id, name, value, arg, context=None):
        if value:
            employee = self.browse(cr, uid, empl_id, context=context)
            diff = value - employee.remaining_leaves
            type_obj = self.pool.get('hr.holidays.status')
            holiday_obj = self.pool.get('hr.holidays')
            # Find for holidays status
            status_ids = type_obj.search(cr, uid, [('limit', '=', False)], context=context)
            if len(status_ids) != 1 :
                raise osv.except_osv(_('Warning!'),_("The feature behind the field 'Remaining Legal Leaves' can only be used when there is only one leave type with the option 'Allow to Override Limit' unchecked. (%s Found). Otherwise, the update is ambiguous as we cannot decide on which leave type the update has to be done. \nYou may prefer to use the classic menus 'Leave Requests' and 'Allocation Requests' located in 'Human Resources \ Leaves' to manage the leave days of the employees if the configuration does not allow to use this field.") % (len(status_ids)))
            status_id = status_ids and status_ids[0] or False
            if not status_id:
                return False
            if diff > 0:
                leave_id = holiday_obj.create(cr, uid, {'name': _('Allocation for %s') % employee.name, 'employee_id': employee.id, 'holiday_status_id': status_id, 'type': 'add', 'holiday_type': 'employee', 'number_of_days_temp': diff}, context=context)
            elif diff < 0:
                raise osv.except_osv(_('Warning!'), _('You cannot reduce validated allocation requests'))
            else:
                return False
            for sig in ('confirm', 'validate', 'second_validate'):
                holiday_obj.signal_workflow(cr, uid, [leave_id], sig)
            return True
        return False

    def _get_remaining_days(self, cr, uid, ids, name, args, context=None):
        cr.execute("""SELECT
                sum(h.number_of_days) as days,
                h.employee_id
            from
                hr_holidays h
                join hr_holidays_status s on (s.id=h.holiday_status_id)
            where
                h.state='validate' and
                s.limit=False and
                h.employee_id in %s
            group by h.employee_id""", (tuple(ids),))
        res = cr.dictfetchall()
        remaining = {}
        for r in res:
            remaining[r['employee_id']] = r['days']
        for employee_id in ids:
            if not remaining.get(employee_id):
                remaining[employee_id] = 0.0
        return remaining

    def _get_leave_status(self, cr, uid, ids, name, args, context=None):
        holidays_obj = self.pool.get('hr.holidays')
        holidays_id = holidays_obj.search(cr, uid,
           [('employee_id', 'in', ids), ('date_from','<=',time.strftime('%Y-%m-%d %H:%M:%S')),
           ('date_to','>=',time.strftime('%Y-%m-%d %H:%M:%S')),('type','=','remove'),('state','not in',('cancel','refuse'))],
           context=context)
        result = {}
        for id in ids:
            result[id] = {
                'current_leave_state': False,
                'current_leave_id': False,
                'leave_date_from':False,
                'leave_date_to':False,
            }
        for holiday in self.pool.get('hr.holidays').browse(cr, uid, holidays_id, context=context):
            result[holiday.employee_id.id]['leave_date_from'] = holiday.date_from
            result[holiday.employee_id.id]['leave_date_to'] = holiday.date_to
            result[holiday.employee_id.id]['current_leave_state'] = holiday.state
            result[holiday.employee_id.id]['current_leave_id'] = holiday.holiday_status_id.id
        return result

    def _leaves_count(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        leaves = self.pool['hr.holidays'].read_group(cr, uid, [
            ('employee_id', 'in', ids),
            ('holiday_status_id.limit', '=', False), ('state', '=', 'validate')], fields=['number_of_days', 'employee_id'], groupby=['employee_id'])
        res.update(dict([(leave['employee_id'][0], leave['number_of_days']) for leave in leaves ]))
        return res

    def _show_approved_remaining_leave(self, cr, uid, ids, name, args, context=None):
        if self.pool['res.users'].has_group(cr, uid, 'base.group_hr_user'):
            return dict([(employee_id, True) for employee_id in ids])
        return dict([(employee.id, True) for employee in self.browse(cr, uid, ids, context=context) if employee.user_id.id == uid])

    def _absent_employee(self, cr, uid, ids, field_name, arg, context=None):
        today_date = datetime.datetime.utcnow().date()
        today_start = today_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT) # get the midnight of the current utc day
        today_end = (today_date + relativedelta(hours=23, minutes=59, seconds=59)).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        data = self.pool['hr.holidays'].read_group(cr, uid,
            [('employee_id', 'in', ids), ('state', 'not in', ['cancel', 'refuse']),
             ('date_from', '<=', today_end), ('date_to', '>=', today_start), ('type', '=', 'remove')],
            ['employee_id'], ['employee_id'], context=context)
        result = dict.fromkeys(ids, False)
        for d in data:
            if d['employee_id_count'] >= 1:
                result[d['employee_id'][0]] = True
        return result

    def _search_absent_employee(self, cr, uid, obj, name, args, context=None):
        today_date = datetime.datetime.utcnow().date()
        today_start = today_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT) # get the midnight of the current utc day
        today_end = (today_date + relativedelta(hours=23, minutes=59, seconds=59)).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        holiday_ids = self.pool['hr.holidays'].search_read(cr, uid, [
            ('state', 'not in', ['cancel', 'refuse']),
            ('date_from', '<=', today_end),
            ('date_to', '>=', today_start),
            ('type', '=', 'remove')], ['employee_id'], context=context)
        absent_employee_ids = [holiday['employee_id'][0] for holiday in holiday_ids if holiday['employee_id']]
        return [('id', 'in', absent_employee_ids)]

    _columns = {
        'remaining_leaves': fields.function(_get_remaining_days, string='Remaining Legal Leaves', fnct_inv=_set_remaining_days, type="float", help='Total number of legal leaves allocated to this employee, change this value to create allocation/leave request. Total based on all the leave types without overriding limit.'),
        'current_leave_state': fields.function(
            _get_leave_status, multi="leave_status", string="Current Leave Status", type="selection",
            selection=[('draft', 'New'), ('confirm', 'Waiting Approval'), ('refuse', 'Refused'),
                       ('validate1', 'Waiting Second Approval'), ('validate', 'Approved'), ('cancel', 'Cancelled')]),
        'current_leave_id': fields.function(_get_leave_status, multi="leave_status", string="Current Leave Type", type='many2one', relation='hr.holidays.status'),
        'leave_date_from': fields.function(_get_leave_status, multi='leave_status', type='date', string='From Date'),
        'leave_date_to': fields.function(_get_leave_status, multi='leave_status', type='date', string='To Date'),
        'leaves_count': fields.function(_leaves_count, type='integer', string='Number of Leaves'),
        'show_leaves': fields.function(_show_approved_remaining_leave, type='boolean', string="Able to see Remaining Leaves"),
        'is_absent_totay': fields.function(_absent_employee, fnct_search=_search_absent_employee, type="boolean", string="Absent Today", default=False)
    }
