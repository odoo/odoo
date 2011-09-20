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
from itertools import groupby
from operator import itemgetter

import netsvc
from osv import fields, osv
from tools.translate import _


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
        'categ_id': fields.many2one('crm.case.categ', 'Meeting', domain="[('object_id.model', '=', 'crm.meeting')]", help='If you set a meeting type, OpenERP will create a meeting in the calendar once a leave is validated.'),
        'color_name': fields.selection([('red', 'Red'),('blue','Blue'), ('lightgreen', 'Light Green'), ('lightblue','Light Blue'), ('lightyellow', 'Light Yellow'), ('magenta', 'Magenta'),('lightcyan', 'Light Cyan'),('black', 'Black'),('lightpink', 'Light Pink'),('brown', 'Brown'),('violet', 'Violet'),('lightcoral', 'Light Coral'),('lightsalmon', 'Light Salmon'),('lavender', 'Lavender'),('wheat', 'Wheat'),('ivory', 'Ivory')],'Color in Report', required=True, help='This color will be used in the leaves summary located in Reporting\Leaves by Departement'),
        'limit': fields.boolean('Allow to Override Limit', help='If you tick this checkbox, the system will allow, for this section, the employees to take more leaves than the available ones.'),
        'active': fields.boolean('Active', help="If the active field is set to false, it will allow you to hide the leave type without removing it."),
        'max_leaves': fields.function(_user_left_days, string='Maximum Allowed', help='This value is given by the sum of all holidays requests with a positive value.', multi='user_left_days'),
        'leaves_taken': fields.function(_user_left_days, string='Leaves Already Taken', help='This value is given by the sum of all holidays requests with a negative value.', multi='user_left_days'),
        'remaining_leaves': fields.function(_user_left_days, string='Remaining Leaves', help='Maximum Leaves Allowed - Leaves Already Taken', multi='user_left_days'),
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

    _columns = {
        'name': fields.char('Description', required=True, size=64),
        'state': fields.selection([('draft', 'Draft'), ('confirm', 'Waiting Approval'), ('refuse', 'Refused'),
            ('validate1', 'Waiting Second Approval'), ('validate', 'Approved'), ('cancel', 'Cancelled')],
            'State', readonly=True, help='The state is set to \'Draft\', when a holiday request is created.\
            \nThe state is \'Waiting Approval\', when holiday request is confirmed by user.\
            \nThe state is \'Refused\', when holiday request is refused by manager.\
            \nThe state is \'Approved\', when holiday request is approved by manager.'),
        'user_id':fields.related('employee_id', 'user_id', type='many2one', relation='res.users', string='User', store=True),
        'date_from': fields.datetime('Start Date', readonly=True, states={'draft':[('readonly',False)]}),
        'date_to': fields.datetime('End Date', readonly=True, states={'draft':[('readonly',False)]}),
        'holiday_status_id': fields.many2one("hr.holidays.status", "Leave Type", required=True,readonly=True, states={'draft':[('readonly',False)]}),
        'employee_id': fields.many2one('hr.employee', "Employee", select=True, invisible=False, readonly=True, states={'draft':[('readonly',False)]}, help='Leave Manager can let this field empty if this leave request/allocation is for every employee'),
        #'manager_id': fields.many2one('hr.employee', 'Leave Manager', invisible=False, readonly=True, help='This area is automatically filled by the user who validate the leave'),
        #'notes': fields.text('Notes',readonly=True, states={'draft':[('readonly',False)]}),
        'manager_id': fields.many2one('hr.employee', 'First Approval', invisible=False, readonly=True, help='This area is automatically filled by the user who validate the leave'),
        'notes': fields.text('Reasons',readonly=True, states={'draft':[('readonly',False)]}),
        'number_of_days_temp': fields.float('Number of Days', readonly=True, states={'draft':[('readonly',False)]}),
        'number_of_days': fields.function(_compute_number_of_days, string='Number of Days', store=True),
        'case_id': fields.many2one('crm.meeting', 'Meeting'),
        'type': fields.selection([('remove','Leave Request'),('add','Allocation Request')], 'Request Type', required=True, readonly=True, states={'draft':[('readonly',False)]}, help="Choose 'Leave Request' if someone wants to take an off-day. \nChoose 'Allocation Request' if you want to increase the number of leaves available for someone"),
        'parent_id': fields.many2one('hr.holidays', 'Parent'),
        'linked_request_ids': fields.one2many('hr.holidays', 'parent_id', 'Linked Requests',),
        'department_id':fields.related('employee_id', 'department_id', string='Department', type='many2one', relation='hr.department', readonly=True, store=True),
        'category_id': fields.many2one('hr.employee.category', "Category", help='Category of Employee'),
        'holiday_type': fields.selection([('employee','By Employee'),('category','By Employee Category')], 'Allocation Type', help='By Employee: Allocation/Request for individual Employee, By Employee Category: Allocation/Request for group of employees in category', required=True),
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
    _sql_constraints = [
        ('type_value', "CHECK( (holiday_type='employee' AND employee_id IS NOT NULL) or (holiday_type='category' AND category_id IS NOT NULL))", "You have to select an employee or a category"),
        ('date_check2', "CHECK ( (type='add') OR (date_from <= date_to))", "The start date must be before the end date !"),
        ('date_check', "CHECK ( number_of_days_temp >= 0 )", "The number of days must be greater than 0 !"),
    ]

    def _create_resource_leave(self, cr, uid, vals, context=None):
        '''This method will create entry in resource calendar leave object at the time of holidays validated '''
        obj_res_leave = self.pool.get('resource.calendar.leaves')
        return obj_res_leave.create(cr, uid, vals, context=context)

    def _remove_resouce_leave(self, cr, uid, ids, context=None):
        '''This method will create entry in resource calendar leave object at the time of holidays cancel/removed'''
        obj_res_leave = self.pool.get('resource.calendar.leaves')
        leave_ids = obj_res_leave.search(cr, uid, [('holiday_id', 'in', ids)], context=context)
        return obj_res_leave.unlink(cr, uid, leave_ids)

    def onchange_type(self, cr, uid, ids, holiday_type):
        result = {'value': {'employee_id': False}}
        if holiday_type == 'employee':
            ids_employee = self.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)])
            if ids_employee:
                result['value'] = {
                    'employee_id': ids_employee[0]
                }
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
            if rec.state<>'draft':
                raise osv.except_osv(_('Warning!'),_('You cannot delete a leave which is not in draft state !'))
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

    def onchange_sec_id(self, cr, uid, ids, status, context=None):
        warning = {}
        obj_holiday_status = self.pool.get('hr.holidays.status')
        if status:
            holiday_status = obj_holiday_status.browse(cr, uid, status, context=context)
            double_validation = holiday_status.double_validation
            if holiday_status.categ_id and holiday_status.categ_id.section_id and not holiday_status.categ_id.section_id.allow_unlink:
                warning = {
                    'title': "Warning for ",
                    'message': "You won\'t be able to cancel this leave request because the CRM Sales Team of the leave type disallows."
                }
        return {'warning': warning, 'value': {'double_validation': double_validation}}

    def set_to_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {
            'state': 'draft',
            'manager_id': False,
            'manager_id2': False,
        })
        wf_service = netsvc.LocalService("workflow")
        for id in ids:
            wf_service.trg_delete(uid, 'hr.holidays', id, cr)
            wf_service.trg_create(uid, 'hr.holidays', id, cr)
        return True

    def holidays_validate(self, cr, uid, ids, *args):
        self.check_holidays(cr, uid, ids)
        obj_emp = self.pool.get('hr.employee')
        ids2 = obj_emp.search(cr, uid, [('user_id', '=', uid)])
        manager = ids2 and ids2[0] or False
        return self.write(cr, uid, ids, {'state':'validate1', 'manager_id': manager})

    def holidays_validate2(self, cr, uid, ids, *args):
        self.check_holidays(cr, uid, ids)
        obj_emp = self.pool.get('hr.employee')
        ids2 = obj_emp.search(cr, uid, [('user_id', '=', uid)])
        manager = ids2 and ids2[0] or False
        self.write(cr, uid, ids, {'state':'validate'})
        data_holiday = self.browse(cr, uid, ids)
        holiday_ids = []
        for record in data_holiday:
            if record.holiday_status_id.double_validation:
                holiday_ids.append(record.id)
            if record.holiday_type == 'employee' and record.type == 'remove':
                meeting_obj = self.pool.get('crm.meeting')
                vals = {
                    'name': record.name,
                    'categ_id': record.holiday_status_id.categ_id.id,
                    'duration': record.number_of_days_temp * 8,
                    'note': record.notes,
                    'user_id': record.user_id.id,
                    'date': record.date_from,
                    'end_date': record.date_to,
                    'date_deadline': record.date_to,
                }
                case_id = meeting_obj.create(cr, uid, vals)
                self.write(cr, uid, ids, {'case_id': case_id})
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
        if holiday_ids:
            self.write(cr, uid, holiday_ids, {'manager_id2': manager})
        return True

    def holidays_confirm(self, cr, uid, ids, *args):
        self.check_holidays(cr, uid, ids)
        return self.write(cr, uid, ids, {'state':'confirm'})

    def holidays_refuse(self, cr, uid, ids, approval, *args):
        obj_emp = self.pool.get('hr.employee')
        ids2 = obj_emp.search(cr, uid, [('user_id', '=', uid)])
        manager = ids2 and ids2[0] or False
        if approval == 'first_approval':
            self.write(cr, uid, ids, {'manager_id': manager})
        else:
            self.write(cr, uid, ids, {'manager_id2': manager})
        self.write(cr, uid, ids, {'state': 'refuse'})
        self.holidays_cancel(cr, uid, ids)
        return True

    def holidays_cancel(self, cr, uid, ids, *args):
        obj_crm_meeting = self.pool.get('crm.meeting')
        for record in self.browse(cr, uid, ids):
            # Delete the meeting
            if record.case_id:
                obj_crm_meeting.unlink(cr, uid, [record.case_id.id])

            # If a category that created several holidays, cancel all related
            wf_service = netsvc.LocalService("workflow")
            for request in record.linked_request_ids or []:
                wf_service.trg_validate(uid, 'hr.holidays', request.id, 'cancel', cr)

        return True

    def check_holidays(self, cr, uid, ids):
        holi_status_obj = self.pool.get('hr.holidays.status')
        for record in self.browse(cr, uid, ids):
            if record.holiday_type == 'employee' and record.type == 'remove':
                if record.employee_id and not record.holiday_status_id.limit:
                    leaves_rest = holi_status_obj.get_days( cr, uid, [record.holiday_status_id.id], record.employee_id.id, False)[record.holiday_status_id.id]['remaining_leaves']
                    if leaves_rest < record.number_of_days_temp:
                        raise osv.except_osv(_('Warning!'),_('You cannot validate leaves for employee %s: too few remaining days (%s).') % (record.employee_id.name, leaves_rest))
        return True
hr_holidays()

class resource_calendar_leaves(osv.osv):
    _inherit = "resource.calendar.leaves"
    _description = "Leave Detail"
    _columns = {
        'holiday_id': fields.many2one("hr.holidays", "Holiday"),
    }

resource_calendar_leaves()


class hr_employee(osv.osv):
   _inherit="hr.employee"

   def _set_remaining_days(self, cr, uid, empl_id, name, value, arg, context=None):
        employee = self.browse(cr, uid, empl_id, context=context)
        diff = value - employee.remaining_leaves
        type_obj = self.pool.get('hr.holidays.status')
        holiday_obj = self.pool.get('hr.holidays')
        # Find for holidays status
        status_ids = type_obj.search(cr, uid, [('limit', '=', False)], context=context)
        if len(status_ids) != 1 :
            raise osv.except_osv(_('Warning !'),_("To use this feature, you must have only one leave type without the option 'Allow to Override Limit' set. (%s Found).") % (len(status_ids)))
        status_id = status_ids and status_ids[0] or False
        if not status_id:
            return False
        if diff > 0:
            leave_id = holiday_obj.create(cr, uid, {'name': _('Allocation for %s') % employee.name, 'employee_id': employee.id, 'holiday_status_id': status_id, 'type': 'add', 'holiday_type': 'employee', 'number_of_days_temp': diff}, context=context)
        elif diff < 0:
            leave_id = holiday_obj.create(cr, uid, {'name': _('Leave Request for %s') % employee.name, 'employee_id': employee.id, 'holiday_status_id': status_id, 'type': 'remove', 'holiday_type': 'employee', 'number_of_days_temp': abs(diff)}, context=context)
        else:
            return False
        holiday_obj.holidays_confirm(cr, uid, [leave_id])
        holiday_obj.holidays_validate2(cr, uid, [leave_id])
        return True

   def _get_remaining_days(self, cr, uid, ids, name, args, context=None):
        cr.execute("SELECT sum(h.number_of_days_temp) as days, h.employee_id from hr_holidays h join hr_holidays_status s on (s.id=h.holiday_status_id) where h.type='add' and h.state='validate' and s.limit=False group by h.employee_id")
        res = cr.dictfetchall()
        remaining = {}
        for r in res:
            remaining[r['employee_id']] = r['days']
        for employee_id in ids:
            if not remaining.get(employee_id):
                remaining[employee_id] = 0.0
        return remaining


   _columns = {
        'remaining_leaves': fields.function(_get_remaining_days, string='Remaining Legal Leaves', fnct_inv=_set_remaining_days, type="float", help='Total number of legal leaves allocated to this employee, change this value to create allocation/leave requests.', store=True),
    }

hr_employee()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: