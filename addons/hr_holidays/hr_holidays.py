# -*- coding: utf-8 -*-
##################################################################################
#
# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)
# and 2004-2010 Tiny SPRL (<http://tiny.be>).
#
# $Id: hr.py 4656 2006-11-24 09:58:42Z Cyp $
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU Affero General Public License as
#     published by the Free Software Foundation, either version 3 of the
#     License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Affero General Public License for more details.
#
#     You should have received a copy of the GNU Affero General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import datetime
import time
from itertools import groupby
from operator import itemgetter

import math
from openerp import netsvc
from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _


class hr_holidays_status(osv.osv):
    _name = "hr.holidays.status"
    _description = "Leave Type"

    def get_days(self, cr, uid, ids, employee_id, return_false, context=None):
        cr.execute("""SELECT id, type, number_of_days, holiday_status_id FROM hr_holidays WHERE employee_id = %s AND state='validate' AND holiday_status_id in %s""",
            [employee_id, tuple(ids)])
        result = sorted(cr.dictfetchall(), key=lambda x: x['holiday_status_id'])
        grouped_lines = dict((k, [v for v in itr]) for k, itr in groupby(result, itemgetter('holiday_status_id')))
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = {}
            max_leaves = leaves_taken = 0
            if not return_false:
                if record.id in grouped_lines:
                    leaves_taken = -sum([item['number_of_days'] for item in grouped_lines[record.id] if item['type'] == 'remove'])
                    max_leaves = sum([item['number_of_days'] for item in grouped_lines[record.id] if item['type'] == 'add'])
            res[record.id]['max_leaves'] = max_leaves
            res[record.id]['leaves_taken'] = leaves_taken
            res[record.id]['remaining_leaves'] = max_leaves - leaves_taken
        return res

    def _user_left_days(self, cr, uid, ids, name, args, context=None):
        return_false = False
        employee_id = False
        res = {}
        if context and context.has_key('employee_id'):
            if not context['employee_id']:
                return_false = True
            employee_id = context['employee_id']
        else:
            employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)], context=context)
            if employee_ids:
                employee_id = employee_ids[0]
            else:
                return_false = True
        if employee_id:
            res = self.get_days(cr, uid, ids, employee_id, return_false, context=context)
        else:
            res = dict.fromkeys(ids, {'leaves_taken': 0, 'remaining_leaves': 0, 'max_leaves': 0})
        return res

    _columns = {
        'name': fields.char('Leave Type', size=64, required=True, translate=True),
        'categ_id': fields.many2one('crm.meeting.type', 'Meeting Type',
            help='Once a leave is validated, OpenERP will create a corresponding meeting of this type in the calendar.'),
        'color_name': fields.selection([('red', 'Red'),('blue','Blue'), ('lightgreen', 'Light Green'), ('lightblue','Light Blue'), ('lightyellow', 'Light Yellow'), ('magenta', 'Magenta'),('lightcyan', 'Light Cyan'),('black', 'Black'),('lightpink', 'Light Pink'),('brown', 'Brown'),('violet', 'Violet'),('lightcoral', 'Light Coral'),('lightsalmon', 'Light Salmon'),('lavender', 'Lavender'),('wheat', 'Wheat'),('ivory', 'Ivory')],'Color in Report', required=True, help='This color will be used in the leaves summary located in Reporting\Leaves by Department.'),
        'limit': fields.boolean('Allow to Override Limit', help='If you select this check box, the system allows the employees to take more leaves than the available ones for this type and take them into account for the "Remaining Legal Leaves" defined on the employee form.'),
        'active': fields.boolean('Active', help="If the active field is set to false, it will allow you to hide the leave type without removing it."),
        'max_leaves': fields.function(_user_left_days, string='Maximum Allowed', help='This value is given by the sum of all holidays requests with a positive value.', multi='user_left_days'),
        'leaves_taken': fields.function(_user_left_days, string='Leaves Already Taken', help='This value is given by the sum of all holidays requests with a negative value.', multi='user_left_days'),
        'remaining_leaves': fields.function(_user_left_days, string='Remaining Leaves', help='Maximum Leaves Allowed - Leaves Already Taken', multi='user_left_days'),
        'double_validation': fields.boolean('Apply Double Validation', help="When selected, the Allocation/Leave Requests for this type require a second validation to be approved."),
    }
    _defaults = {
        'color_name': 'red',
        'active': True,
    }

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            if not record.limit:
                name = name + ('  (%d/%d)' % (record.leaves_taken or 0.0, record.max_leaves or 0.0))
            res.append((record.id, name))
        return res


class hr_holidays(osv.osv):
    _name = "hr.holidays"
    _description = "Leave"
    _order = "type desc, date_from asc"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _track = {
        'state': {
            'hr_holidays.mt_holidays_approved': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'validate',
            'hr_holidays.mt_holidays_refused': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'refuse',
            'hr_holidays.mt_holidays_confirmed': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'confirm',
        },
    }

    def _employee_get(self, cr, uid, context=None):
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

    def _check_date(self, cr, uid, ids):
        for holiday in self.browse(cr, uid, ids):
            holiday_ids = self.search(cr, uid, [('date_from', '<=', holiday.date_to), ('date_to', '>=', holiday.date_from), ('employee_id', '=', holiday.employee_id.id), ('id', '<>', holiday.id)])
            if holiday_ids:
                return False
        return True

    _columns = {
        'name': fields.char('Description', size=64),
        'state': fields.selection([('draft', 'To Submit'), ('cancel', 'Cancelled'),('confirm', 'To Approve'), ('refuse', 'Refused'), ('validate1', 'Second Approval'), ('validate', 'Approved')],
            'Status', readonly=True, track_visibility='onchange',
            help='The status is set to \'To Submit\', when a holiday request is created.\
            \nThe status is \'To Approve\', when holiday request is confirmed by user.\
            \nThe status is \'Refused\', when holiday request is refused by manager.\
            \nThe status is \'Approved\', when holiday request is approved by manager.'),
        'user_id':fields.related('employee_id', 'user_id', type='many2one', relation='res.users', string='User', store=True),
        'date_from': fields.datetime('Start Date', readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}, select=True),
        'date_to': fields.datetime('End Date', readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}),
        'holiday_status_id': fields.many2one("hr.holidays.status", "Leave Type", required=True,readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}),
        'employee_id': fields.many2one('hr.employee', "Employee", select=True, invisible=False, readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}),
        'manager_id': fields.many2one('hr.employee', 'First Approval', invisible=False, readonly=True, help='This area is automatically filled by the user who validate the leave'),
        'notes': fields.text('Reasons',readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}),
        'number_of_days_temp': fields.float('Allocation', readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}),
        'number_of_days': fields.function(_compute_number_of_days, string='Number of Days', store=True),
        'meeting_id': fields.many2one('crm.meeting', 'Meeting'),
        'type': fields.selection([('remove','Leave Request'),('add','Allocation Request')], 'Request Type', required=True, readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}, help="Choose 'Leave Request' if someone wants to take an off-day. \nChoose 'Allocation Request' if you want to increase the number of leaves available for someone", select=True),
        'parent_id': fields.many2one('hr.holidays', 'Parent'),
        'linked_request_ids': fields.one2many('hr.holidays', 'parent_id', 'Linked Requests',),
        'department_id':fields.related('employee_id', 'department_id', string='Department', type='many2one', relation='hr.department', readonly=True, store=True),
        'category_id': fields.many2one('hr.employee.category', "Employee Tag", help='Category of Employee', readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}),
        'holiday_type': fields.selection([('employee','By Employee'),('category','By Employee Tag')], 'Allocation Mode', readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}, help='By Employee: Allocation/Request for individual Employee, By Employee Tag: Allocation/Request for group of employees in category', required=True),
        'manager_id2': fields.many2one('hr.employee', 'Second Approval', readonly=True, help='This area is automaticly filled by the user who validate the leave with second level (If Leave type need second validation)'),
        'double_validation': fields.related('holiday_status_id', 'double_validation', type='boolean', relation='hr.holidays.status', string='Apply Double Validation'),
    }
    _defaults = {
        'employee_id': _employee_get,
        'state': 'draft',
        'type': 'remove',
        'user_id': lambda obj, cr, uid, context: uid,
        'holiday_type': 'employee'
    }
    _constraints = [
        (_check_date, 'You can not have 2 leaves that overlaps on same day!', ['date_from','date_to']),
    ] 
    
    _sql_constraints = [
        ('type_value', "CHECK( (holiday_type='employee' AND employee_id IS NOT NULL) or (holiday_type='category' AND category_id IS NOT NULL))", 
         "The employee or employee category of this request is missing. Please ask HR to link your user login to an employee or employee category. "),
        ('date_check2', "CHECK ( (type='add') OR (date_from <= date_to))", "The start date must be anterior to the end date."),
        ('date_check', "CHECK ( number_of_days_temp >= 0 )", "The number of days must be greater than 0."),
    ]
    
    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        if context is None:
            context = {}
        default = default.copy()
        default['date_from'] = False
        default['date_to'] = False
        return super(hr_holidays, self).copy(cr, uid, id, default, context=context)

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

    def onchange_type(self, cr, uid, ids, holiday_type):
        result = {'value': {'employee_id': False}}
        if holiday_type == 'employee':
            ids_employee = self.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)])
            if ids_employee:
                result['value'] = {
                    'employee_id': ids_employee[0]
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
                raise osv.except_osv(_('Warning!'),_('You cannot delete a leave which is in %s state.')%(rec.state))
        return super(hr_holidays, self).unlink(cr, uid, ids, context)

    def onchange_date_from(self, cr, uid, ids, date_to, date_from):
        """
        If there are no date set for date_to, automatically set one 8 hours later than
        the date_from.
        Also update the number_of_days.
        """
        # date_to has to be greater than date_from
        if (date_from and date_to) and (date_from > date_to):
            raise osv.except_osv(_('Warning!'),_('The start date must be anterior to the end date.'))

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
            raise osv.except_osv(_('Warning!'),_('The start date must be anterior to the end date.'))

        result = {'value': {}}

        # Compute and update the number of days
        if (date_to and date_from) and (date_from <= date_to):
            diff_day = self._get_number_of_days(date_from, date_to)
            result['value']['number_of_days_temp'] = round(math.floor(diff_day))+1
        else:
            result['value']['number_of_days_temp'] = 0

        return result

    def create(self, cr, uid, values, context=None):
        """ Override to avoid automatic logging of creation """
        if context is None:
            context = {}
        context = dict(context, mail_create_nolog=True)
        return super(hr_holidays, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        check_fnct = self.pool.get('hr.holidays.status').check_access_rights
        for  holiday in self.browse(cr, uid, ids, context=context):
            if holiday.state in ('validate','validate1') and not check_fnct(cr, uid, 'write', raise_exception=False):
                raise osv.except_osv(_('Warning!'),_('You cannot modify a leave request that has been approved. Contact a human resource manager.'))
        return super(hr_holidays, self).write(cr, uid, ids, vals, context=context)

    def set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'draft',
            'manager_id': False,
            'manager_id2': False,
        })
        wf_service = netsvc.LocalService("workflow")
        for id in ids:
            wf_service.trg_delete(uid, 'hr.holidays', id, cr)
            wf_service.trg_create(uid, 'hr.holidays', id, cr)
        to_unlink = []
        for record in self.browse(cr, uid, ids, context=context):
            for record2 in record.linked_request_ids:
                self.set_to_draft(cr, uid, [record2.id], context=context)
                to_unlink.append(record2.id)
        if to_unlink:
            self.unlink(cr, uid, to_unlink, context=context)
        return True

    def holidays_first_validate(self, cr, uid, ids, context=None):
        self.check_holidays(cr, uid, ids, context=context)
        obj_emp = self.pool.get('hr.employee')
        ids2 = obj_emp.search(cr, uid, [('user_id', '=', uid)])
        manager = ids2 and ids2[0] or False
        self.holidays_first_validate_notificate(cr, uid, ids, context=context)
        return self.write(cr, uid, ids, {'state':'validate1', 'manager_id': manager})

    def holidays_validate(self, cr, uid, ids, context=None):
        self.check_holidays(cr, uid, ids, context=context)
        obj_emp = self.pool.get('hr.employee')
        ids2 = obj_emp.search(cr, uid, [('user_id', '=', uid)])
        manager = ids2 and ids2[0] or False
        self.write(cr, uid, ids, {'state':'validate'})
        data_holiday = self.browse(cr, uid, ids)
        for record in data_holiday:
            if record.double_validation:
                self.write(cr, uid, [record.id], {'manager_id2': manager})
            else:
                self.write(cr, uid, [record.id], {'manager_id': manager})
            if record.holiday_type == 'employee' and record.type == 'remove':
                meeting_obj = self.pool.get('crm.meeting')
                meeting_vals = {
                    'name': record.name or _('Leave Request'),
                    'categ_ids': record.holiday_status_id.categ_id and [(6,0,[record.holiday_status_id.categ_id.id])] or [],
                    'duration': record.number_of_days_temp * 8,
                    'description': record.notes,
                    'user_id': record.user_id.id,
                    'date': record.date_from,
                    'end_date': record.date_to,
                    'date_deadline': record.date_to,
                    'state': 'open',            # to block that meeting date in the calendar
                }
                meeting_id = meeting_obj.create(cr, uid, meeting_vals)
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
                wf_service = netsvc.LocalService("workflow")
                for leave_id in leave_ids:
                    wf_service.trg_validate(uid, 'hr.holidays', leave_id, 'confirm', cr)
                    wf_service.trg_validate(uid, 'hr.holidays', leave_id, 'validate', cr)
                    wf_service.trg_validate(uid, 'hr.holidays', leave_id, 'second_validate', cr)
        return True

    def holidays_confirm(self, cr, uid, ids, context=None):
        self.check_holidays(cr, uid, ids, context=context)
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
        meeting_obj = self.pool.get('crm.meeting')
        for record in self.browse(cr, uid, ids):
            # Delete the meeting
            if record.meeting_id:
                meeting_obj.unlink(cr, uid, [record.meeting_id.id])

            # If a category that created several holidays, cancel all related
            wf_service = netsvc.LocalService("workflow")
            for request in record.linked_request_ids or []:
                wf_service.trg_validate(uid, 'hr.holidays', request.id, 'refuse', cr)

        self._remove_resource_leave(cr, uid, ids, context=context)
        return True

    def check_holidays(self, cr, uid, ids, context=None):
        holi_status_obj = self.pool.get('hr.holidays.status')
        for record in self.browse(cr, uid, ids):
            if record.holiday_type == 'employee' and record.type == 'remove':
                if record.employee_id and not record.holiday_status_id.limit:
                    leaves_rest = holi_status_obj.get_days( cr, uid, [record.holiday_status_id.id], record.employee_id.id, False)[record.holiday_status_id.id]['remaining_leaves']
                    if leaves_rest < record.number_of_days_temp:
                        raise osv.except_osv(_('Warning!'), _('There are not enough %s allocated for employee %s; please create an allocation request for this leave type.') % (record.holiday_status_id.name, record.employee_id.name))
        return True

    # -----------------------------
    # OpenChatter and notifications
    # -----------------------------

    def _needaction_domain_get(self, cr, uid, context=None):
        emp_obj = self.pool.get('hr.employee')
        empids = emp_obj.search(cr, uid, [('parent_id.user_id', '=', uid)], context=context)
        dom = ['&', ('state', '=', 'confirm'), ('employee_id', 'in', empids)]
        # if this user is a hr.manager, he should do second validations
        if self.pool.get('res.users').has_group(cr, uid, 'base.group_hr_manager'):
            dom = ['|'] + dom + [('state', '=', 'validate1')]
        return dom

    def holidays_first_validate_notificate(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            self.message_post(cr, uid, [obj.id],
                _("Request approved, waiting second validation."), context=context)

class resource_calendar_leaves(osv.osv):
    _inherit = "resource.calendar.leaves"
    _description = "Leave Detail"
    _columns = {
        'holiday_id': fields.many2one("hr.holidays", "Leave Request"),
    }

resource_calendar_leaves()


class hr_employee(osv.osv):
    _inherit="hr.employee"

    def create(self, cr, uid, vals, context=None):
        # don't pass the value of remaining leave if it's 0 at the creation time, otherwise it will trigger the inverse
        # function _set_remaining_days and the system may not be configured for. Note that we don't have this problem on
        # the write because the clients only send the fields that have been modified.
        if 'remaining_leaves' in vals and not vals['remaining_leaves']:
            del(vals['remaining_leaves'])
        return super(hr_employee, self).create(cr, uid, vals, context=context)

    def _set_remaining_days(self, cr, uid, empl_id, name, value, arg, context=None):
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
            leave_id = holiday_obj.create(cr, uid, {'name': _('Leave Request for %s') % employee.name, 'employee_id': employee.id, 'holiday_status_id': status_id, 'type': 'remove', 'holiday_type': 'employee', 'number_of_days_temp': abs(diff)}, context=context)
        else:
            return False
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'hr.holidays', leave_id, 'confirm', cr)
        wf_service.trg_validate(uid, 'hr.holidays', leave_id, 'validate', cr)
        wf_service.trg_validate(uid, 'hr.holidays', leave_id, 'second_validate', cr)
        return True

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
                h.employee_id in (%s)
            group by h.employee_id"""% (','.join(map(str,ids)),) )
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
           ('date_to','>=',time.strftime('%Y-%m-%d 23:59:59')),('type','=','remove'),('state','not in',('cancel','refuse'))],
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

    _columns = {
        'remaining_leaves': fields.function(_get_remaining_days, string='Remaining Legal Leaves', fnct_inv=_set_remaining_days, type="float", help='Total number of legal leaves allocated to this employee, change this value to create allocation/leave request. Total based on all the leave types without overriding limit.'),
        'current_leave_state': fields.function(_get_leave_status, multi="leave_status", string="Current Leave Status", type="selection",
            selection=[('draft', 'New'), ('confirm', 'Waiting Approval'), ('refuse', 'Refused'),
            ('validate1', 'Waiting Second Approval'), ('validate', 'Approved'), ('cancel', 'Cancelled')]),
        'current_leave_id': fields.function(_get_leave_status, multi="leave_status", string="Current Leave Type",type='many2one', relation='hr.holidays.status'),
        'leave_date_from': fields.function(_get_leave_status, multi='leave_status', type='date', string='From Date'),
        'leave_date_to': fields.function(_get_leave_status, multi='leave_status', type='date', string='To Date'),
    }

hr_employee()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
