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

import time
import datetime
from itertools import groupby
from operator import itemgetter

import netsvc
from osv import fields, osv
from tools.translate import _


class hr_holidays_status(osv.osv):
    _name = "hr.holidays.status"
    _description = "Leave Type"

    def get_days_cat(self, cr, uid, ids, category_id, return_false, context=None):

        cr.execute("""SELECT id, type, number_of_days, holiday_status_id FROM hr_holidays WHERE category_id = %s AND state='validate' AND holiday_status_id in %s""",
            [category_id, tuple(ids)])
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

    # To do: we can add remaining_leaves_category field to display remaining leaves for particular type
    _columns = {
        'name': fields.char('Leave Type', size=64, required=True, translate=True),
        'categ_id': fields.many2one('crm.case.categ', 'Meeting Category', domain="[('object_id.model', '=', 'crm.meeting')]", help='If you link this type of leave with a category in the CRM, it will synchronize each leave asked with a case in this category, to display it in the company shared calendar for example.'),
        'color_name': fields.selection([('red', 'Red'),('blue','Blue'), ('lightgreen', 'Light Green'), ('lightblue','Light Blue'), ('lightyellow', 'Light Yellow'), ('magenta', 'Magenta'),('lightcyan', 'Light Cyan'),('black', 'Black'),('lightpink', 'Light Pink'),('brown', 'Brown'),('violet', 'Violet'),('lightcoral', 'Light Coral'),('lightsalmon', 'Light Salmon'),('lavender', 'Lavender'),('wheat', 'Wheat'),('ivory', 'Ivory')],'Color in Report', required=True, help='This color will be used in the leaves summary located in Reporting\Leaves by Departement'),
        'limit': fields.boolean('Allow to Override Limit', help='If you tick this checkbox, the system will allow, for this section, the employees to take more leaves than the available ones.'),
        'active': fields.boolean('Active', help="If the active field is set to false, it will allow you to hide the leave type without removing it."),
        'max_leaves': fields.function(_user_left_days, method=True, string='Maximum Leaves Allowed', help='This value is given by the sum of all holidays requests with a positive value.', multi='user_left_days'),
        'leaves_taken': fields.function(_user_left_days, method=True, string='Leaves Already Taken', help='This value is given by the sum of all holidays requests with a negative value.', multi='user_left_days'),
        'remaining_leaves': fields.function(_user_left_days, method=True, string='Remaining Leaves', help='Maximum Leaves Allowed - Leaves Already Taken', multi='user_left_days'),
        'double_validation': fields.boolean('Apply Double Validation', help="If its True then its Allocation/Request have to be validated by second validator")
    }
    _defaults = {
        'color_name': 'red',
        'active': True,
    }

hr_holidays_status()

class hr_holidays(osv.osv):
    _name = "hr.holidays"
    _description = "Leave"
    _order = "type desc, date_from asc"

    def _employee_get(obj, cr, uid, context=None):
        ids = obj.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context)
        if ids:
            return ids[0]
        return False

    _columns = {
        'name': fields.char('Description', required=True, size=64),
        'state': fields.selection([('draft', 'Draft'), ('confirm', 'Waiting Approval'), ('refuse', 'Refused'), ('validate1', 'Waiting Second Approval'), ('validate', 'Approved'), ('cancel', 'Cancelled')], 'State', readonly=True, help='When the holiday request is created the state is \'Draft\'.\n It is confirmed by the user and request is sent to admin, the state is \'Waiting Approval\'.\
            If the admin accepts it, the state is \'Approved\'. If it is refused, the state is \'Refused\'.'),
        'date_from': fields.datetime('Start Date', readonly=True, states={'draft':[('readonly',False)]}),
        'user_id':fields.many2one('res.users', 'User', states={'draft':[('readonly',False)]}, select=True, readonly=True),
        'date_to': fields.datetime('End Date', readonly=True, states={'draft':[('readonly',False)]}),
        'holiday_status_id': fields.many2one("hr.holidays.status", "Leave Type", required=True,readonly=True, states={'draft':[('readonly',False)]}),
        'employee_id': fields.many2one('hr.employee', "Employee", select=True, invisible=False, readonly=True, states={'draft':[('readonly',False)]}, help='Leave Manager can let this field empty if this leave request/allocation is for every employee'),
        #'manager_id': fields.many2one('hr.employee', 'Leave Manager', invisible=False, readonly=True, help='This area is automaticly filled by the user who validate the leave'),
        #'notes': fields.text('Notes',readonly=True, states={'draft':[('readonly',False)]}),
        'manager_id': fields.many2one('hr.employee', 'First Approval', invisible=False, readonly=True, help='This area is automaticly filled by the user who validate the leave'),
        'notes': fields.text('Reasons',readonly=True, states={'draft':[('readonly',False)]}),
        'number_of_days': fields.float('Number of Days', readonly=True, states={'draft':[('readonly',False)]}),
        'number_of_days_temp': fields.float('Number of Days', readonly=True, states={'draft':[('readonly',False)]}),
        'case_id': fields.many2one('crm.meeting', 'Case'),
        'type': fields.selection([('remove','Leave Request'),('add','Allocation Request')], 'Request Type', required=True, readonly=True, states={'draft':[('readonly',False)]}, help="Choose 'Leave Request' if someone wants to take an off-day. \nChoose 'Allocation Request' if you want to increase the number of leaves available for someone"),
        'allocation_type': fields.selection([('employee','Employee Request'),('company','Company Allocation')], 'Allocation Type', required=True, readonly=True, states={'draft':[('readonly',False)]}, help='This field is only for informative purposes, to depict if the leave request/allocation comes from an employee or from the company'),
        'parent_id': fields.many2one('hr.holidays', 'Parent'),
        'linked_request_ids': fields.one2many('hr.holidays', 'parent_id', 'Linked Requests',),
        'department_id':fields.related('employee_id', 'department_id', string='Department', type='many2one', relation='hr.department', readonly=True, store=True),
        'category_id': fields.many2one('hr.employee.category', "Category", help='Category Of employee'),
        'holiday_type': fields.selection([('employee','By Employee'),('category','By Employee Category')], 'Allocation Type', help='By Employee: Allocation/Request for individual Employee, By Employee Category: Allocation/Request for group of employees in category', required=True),
        'manager_id2': fields.many2one('hr.employee', 'Second Approval', readonly=True, help='This area is automaticly filled by the user who validate the leave with second level (If Leave type need second validation)'),
        # Todo: Add below field in view?
        'category_holiday_id': fields.many2one('hr.holidays', 'Holiday', help='For allocation By Employee Category (Link between Employee Category holiday and related holidays for employees of that category)')
    }

    _defaults = {
        'employee_id': _employee_get,
        'state': 'draft',
        'type': 'remove',
        'allocation_type': 'employee',
        'user_id': lambda obj, cr, uid, context: uid,
        'holiday_type': 'employee'
    }

    def _get_category_leave_ids(self, cr, uid, ids):
        """Returns the leaves taken by the employees of the category if holiday type is 'category'."""
        leave_ids = []
        for record in self.browse(cr, uid, ids):
            if record.holiday_type == 'category' and record.type == 'remove':
                leave_ids += self.search(cr, uid, [('category_holiday_id', '=', record.id)])
        return leave_ids

    def _create_resource_leave(self, cr, uid, vals, context=None):
        '''This method will create entry in resource calendar leave object at the time of holidays validated '''
        obj_res_leave = self.pool.get('resource.calendar.leaves')
        return obj_res_leave.create(cr, uid, vals, context=context)

    def _remove_resouce_leave(self, cr, uid, ids, context=None):
        '''This method will create entry in resource calendar leave object at the time of holidays cancel/removed'''
        obj_res_leave = self.pool.get('resource.calendar.leaves')
        leave_ids = obj_res_leave.search(cr, uid, [('holiday_id', 'in', ids)], context=context)
        return obj_res_leave.unlink(cr, uid, leave_ids)

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if 'holiday_type' in vals:
            if vals['holiday_type'] == 'employee':
                vals.update({'category_id': False})
            else:
                vals.update({'employee_id': False})
        if context.has_key('type'):
            vals['type'] = context['type']
        if context.has_key('allocation_type'):
            vals['allocation_type'] = context['allocation_type']
        return super(hr_holidays, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if 'holiday_type' in vals:
            if vals['holiday_type'] == 'employee':
                vals.update({'category_id': False})
            else:
                vals.update({'employee_id': False})
        return super(hr_holidays, self).write(cr, uid, ids, vals, context=context)

    def onchange_type(self, cr, uid, ids, holiday_type):
        result = {}
        if holiday_type == 'employee':
            ids_employee = self.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)])
            if ids_employee:
                result['value'] = {
                    'employee_id': ids_employee[0]
                    }
        return result

    def _get_number_of_days(self, date_from, date_to):
        """Returns a float equals to the timedelta between two dates given as string."""

        DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
        from_dt = datetime.datetime.strptime(date_from, DATETIME_FORMAT)
        to_dt = datetime.datetime.strptime(date_to, DATETIME_FORMAT)
        timedelta = to_dt - from_dt
        diff_day = timedelta.days + float(timedelta.seconds) / 86400
        return diff_day

    def _update_user_holidays(self, cr, uid, ids):
        obj_crm_meeting = self.pool.get('crm.meeting')
        for record in self.browse(cr, uid, ids):
            if record.state=='validate':
                if record.case_id:
                    obj_crm_meeting.unlink(cr, uid, [record.case_id.id])
                if record.linked_request_ids:
                    list_ids = [ lr.id for lr in record.linked_request_ids]
                    self.holidays_cancel(cr, uid, list_ids)
                    self.unlink(cr, uid, list_ids)

    def _check_date(self, cr, uid, ids, context=None):
        for rec in self.read(cr, uid, ids, ['number_of_days_temp', 'date_from','date_to', 'type']):
            if rec['number_of_days_temp'] < 0:
                return False
            if rec['type'] == 'add':
                continue
            date_from = time.strptime(rec['date_from'], '%Y-%m-%d %H:%M:%S')
            date_to = time.strptime(rec['date_to'], '%Y-%m-%d %H:%M:%S')
            if date_from > date_to:
                return False
        return True

    _constraints = [(_check_date, 'Start date should not be larger than end date!\nNumber of Days should be greater than 1!', ['number_of_days_temp'])]

    def unlink(self, cr, uid, ids, context=None):
        self._update_user_holidays(cr, uid, ids)
        ids += self._get_category_leave_ids(cr, uid, ids)
        self._remove_resouce_leave(cr, uid, ids, context=context)
        return super(hr_holidays, self).unlink(cr, uid, ids, context)

    def onchange_date_from(self, cr, uid, ids, date_to, date_from):
        result = {}
        if date_to and date_from:
            diff_day = self._get_number_of_days(date_from, date_to)
            result['value'] = {
                'number_of_days_temp': round(diff_day)+1
            }
            return result
        result['value'] = {
            'number_of_days_temp': 0,
        }
        return result

    def onchange_date_to(self, cr, uid, ids, date_from, date_to):
        return self.onchange_date_from(cr, uid, ids, date_to, date_from)

    def onchange_sec_id(self, cr, uid, ids, status, context=None):
        warning = {}
        if status:
            brows_obj = self.pool.get('hr.holidays.status').browse(cr, uid, [status], context=context)[0]
            if brows_obj.categ_id and brows_obj.categ_id.section_id and not brows_obj.categ_id.section_id.allow_unlink:
                warning = {
                    'title': "Warning for ",
                    'message': "You won\'t be able to cancel this leave request because the CRM Sales Team of the leave type disallows."
                        }
        return {'warning': warning}

    def set_to_draft(self, cr, uid, ids, *args):
        wf_service = netsvc.LocalService("workflow")
        self.write(cr, uid, ids, {
            'state': 'draft',
            'manager_id': False,
            'number_of_days': 0,
        })
        for id in ids:
            wf_service.trg_create(uid, 'hr.holidays', id, cr)
        return True

    def holidays_validate2(self, cr, uid, ids, *args):
        obj_emp = self.pool.get('hr.employee')
        wf_service = netsvc.LocalService("workflow")
        vals = {'state':'validate1'}
        self.check_holidays(cr, uid, ids)
        ids2 = obj_emp.search(cr, uid, [('user_id', '=', uid)])
        if ids2:
            vals['manager_id'] = ids2[0]
        else:
            raise osv.except_osv(_('Warning !'),_('No user related to the selected employee.'))
        # Second Time Validate all the leave requests of the category
        for leave_id in self._get_category_leave_ids(cr, uid, ids):
            wf_service.trg_validate(uid, 'hr.holidays', leave_id, 'second_validate', cr)
        return self.write(cr, uid, ids, vals)

    def holidays_validate(self, cr, uid, ids, *args):
        obj_emp = self.pool.get('hr.employee')
        wf_service = netsvc.LocalService("workflow")
        data_holiday = self.browse(cr, uid, ids)
        self.check_holidays(cr, uid, ids)
        vals = {'state':'validate'}
        ids2 = obj_emp.search(cr, uid, [('user_id', '=', uid)])
        if ids2:
            if data_holiday[0].state == 'validate1':
                vals['manager_id2'] = ids2[0]
            else:
                vals['manager_id'] = ids2[0]
        else:
            raise osv.except_osv(_('Warning !'), _('No user related to the selected employee.'))
        self.write(cr, uid, ids, vals)
        for record in data_holiday:
            if record.holiday_type == 'employee' and record.type == 'remove':
                vals = {
                   'name': record.name,
                   'date_from': record.date_from,
                   'date_to': record.date_to,
                   'calendar_id': record.employee_id.calendar_id.id,
                   'company_id': record.employee_id.company_id.id,
                   'resource_id': record.employee_id.resource_id.id,
                   'holiday_id': record.id
                     }
                self._create_resource_leave(cr, uid, vals)
            elif record.holiday_type == 'category' and record.type == 'remove':
                emp_ids = obj_emp.search(cr, uid, [('category_ids', '=', record.category_id.id)])
                for emp in obj_emp.browse(cr, uid, emp_ids):
                    vals = {
                       'name': record.name,
                       'date_from': record.date_from,
                       'date_to': record.date_to,
                       'calendar_id': emp.calendar_id.id,
                       'company_id': emp.company_id.id,
                       'resource_id': emp.resource_id.id,
                       'holiday_id':record.id
                         }
#                    self._create_resource_leave(cr, uid, vals)
                # Validate all the leave requests of the category
                for leave_id in self.search(cr, uid, [('category_holiday_id', '=', record.id)]):
                    wf_service.trg_validate(uid, 'hr.holidays', leave_id, 'validate', cr)
        return True

    def holidays_confirm(self, cr, uid, ids, *args):
        obj_hr_holiday_status = self.pool.get('hr.holidays.status')
        obj_emp = self.pool.get('hr.employee')
        wf_service = netsvc.LocalService("workflow")
        for record in self.browse(cr, uid, ids):
            user_id = False
            leave_asked = record.number_of_days_temp
            leave_ids = []
            if record.holiday_type == 'employee' and record.type == 'remove':
                if record.employee_id and not record.holiday_status_id.limit:
                    leaves_rest = obj_hr_holiday_status.get_days( cr, uid, [record.holiday_status_id.id], record.employee_id.id, False)[record.holiday_status_id.id]['remaining_leaves']
                    if leaves_rest < leave_asked:
                        raise osv.except_osv(_('Warning!'),_('You cannot validate leaves for employee %s while there are too few remaining leave days.') % (record.employee_id.name))
                nb = -(record.number_of_days_temp)
            elif record.holiday_type == 'category' and record.type == 'remove':
                if record.category_id and not record.holiday_status_id.limit:
                    leaves_rest = obj_hr_holiday_status.get_days_cat( cr, uid, [record.holiday_status_id.id], record.category_id.id, False)[record.holiday_status_id.id]['remaining_leaves']
                    if leaves_rest < leave_asked:
                        raise osv.except_osv(_('Warning!'),_('You cannot validate leaves for category %s while there are too few remaining leave days.') % (record.category_id.name))
                nb = -(record.number_of_days_temp)
                # Create leave request for employees in the category
                emp_ids = obj_emp.search(cr, uid, [('category_ids', '=', record.category_id.id)])
                for emp in obj_emp.browse(cr, uid, emp_ids):
                    vals = {
                    'name': record.name,
                    'holiday_status_id': record.holiday_status_id.id,
                    'date_from': record.date_from,
                    'date_to': record.date_to,
                    'notes': record.notes,
                    'number_of_days_temp': record.number_of_days_temp,
                    'category_holiday_id': record.id,
                    'employee_id': emp.id
                }
                    leave_ids.append(self.create(cr, uid, vals, context=None))
                # Confirm all the leave requests of the category
                for leave_id in leave_ids:
                    wf_service.trg_validate(uid, 'hr.holidays', leave_id, 'confirm', cr)
            else:
                nb = record.number_of_days_temp

            if record.holiday_type == 'employee' and record.employee_id:
                user_id = record.employee_id.user_id and record.employee_id.user_id.id or uid

            self.write(cr, uid, [record.id], {'state':'confirm', 'number_of_days': nb, 'user_id': user_id})
        return True

    def holidays_refuse(self, cr, uid, ids, *args):
        obj_emp = self.pool.get('hr.employee')
        wf_service = netsvc.LocalService("workflow")
        vals = {'state': 'refuse'}
        ids2 = obj_emp.search(cr, uid, [('user_id','=', uid)])
        if ids2:
            vals['manager_id'] = ids2[0]
        # Refuse all the leave requests of the category
        for leave_id in self._get_category_leave_ids(cr, uid, ids):
            wf_service.trg_validate(uid, 'hr.holidays', leave_id, 'refuse', cr)
        self.write(cr, uid, ids, vals)
        return True

    def holidays_cancel(self, cr, uid, ids, *args):
        self._update_user_holidays(cr, uid, ids)
        self._remove_resouce_leave(cr, uid, ids)
        self.write(cr, uid, ids, {'state': 'cancel'})
        leave_ids = self._get_category_leave_ids(cr, uid, ids)
        if leave_ids:
            self.unlink(cr, uid, leave_ids) # unlink all the leave requests of the category
        return True

    def holidays_draft(self, cr, uid, ids, *args):
        wf_service = netsvc.LocalService("workflow")
        for leave_id in self._get_category_leave_ids(cr, uid, ids):
            wf_service.trg_validate(uid, 'hr.holidays', leave_id, 'draft', cr)
        return self.write(cr, uid, ids, {'state': 'draft'})

    def check_holidays(self, cr, uid, ids):
        holi_status_obj = self.pool.get('hr.holidays.status')
        emp_obj = self.pool.get('hr.employee')
        meeting_obj = self.pool.get('crm.meeting')
        for record in self.browse(cr, uid, ids):
            if not record.number_of_days:
                raise osv.except_osv(_('Warning!'), _('Wrong leave definition.'))
            if record.holiday_type=='employee' and record.employee_id:
                leave_asked = record.number_of_days
                if leave_asked < 0.00:
                    if not record.holiday_status_id.limit:
                        leaves_rest = holi_status_obj.get_days(cr, uid, [record.holiday_status_id.id], record.employee_id.id, False)[record.holiday_status_id.id]['remaining_leaves']
                        if leaves_rest < -(leave_asked):
                            raise osv.except_osv(_('Warning!'),_('You Cannot Validate leaves while available leaves are less than asked leaves.'))
            elif record.holiday_type == 'category' and record.category_id:
                leave_asked = record.number_of_days
                if leave_asked < 0.00:
                    if not record.holiday_status_id.limit:
                        leaves_rest = holi_status_obj.get_days_cat(cr, uid, [record.holiday_status_id.id], record.category_id.id, False)[record.holiday_status_id.id]['remaining_leaves']
                        if leaves_rest < -(leave_asked):
                            raise osv.except_osv(_('Warning!'),_('You Cannot Validate leaves while available leaves are less than asked leaves.'))
            else:# This condition will never meet!!
                holiday_ids = []
                vals = {
                    'name': record.name,
                    'holiday_status_id': record.holiday_status_id.id,
                    'state': 'draft',
                    'date_from': record.date_from,
                    'date_to': record.date_to,
                    'notes': record.notes,
                    'number_of_days': record.number_of_days,
                    'number_of_days_temp': record.number_of_days_temp,
                    'type': record.type,
                    'allocation_type': record.allocation_type,
                    'parent_id': record.id,
                }
                employee_ids = emp_obj.search(cr, uid, [])
                for employee in employee_ids:
                    vals['employee_id'] = employee
                    user_id = emp_obj.search(cr, uid, [('user_id','=',uid)])
                    if user_id:
                        vals['user_id'] = user_id[0]
                    holiday_ids.append(self.create(cr, uid, vals, context=None))
                self.holidays_confirm(cr, uid, holiday_ids)
                self.holidays_validate(cr, uid, holiday_ids)

            if record.holiday_status_id.categ_id and record.date_from and record.date_to and record.employee_id:
                diff_day = self._get_number_of_days(record.date_from, record.date_to)
                vals = {
                    'name': record.name,
                    'categ_id': record.holiday_status_id.categ_id.id,
                    'duration': (diff_day) * 8,
                    'note': record.notes,
                    'user_id': record.user_id.id,
                    'date': record.date_from,
                }
                case_id = meeting_obj.create(cr, uid, vals)
                self.write(cr, uid, ids, {'case_id': case_id})

        return True

hr_holidays()

class resource_calendar_leaves(osv.osv):
    _inherit = "resource.calendar.leaves"
    _description = "Leave Detail"
    _columns = {
        'holiday_id': fields.many2one("hr.holidays", "Holiday"),
    }

resource_calendar_leaves()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
