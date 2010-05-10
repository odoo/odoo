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
from mx import DateTime
import time

import pooler
import netsvc
from osv import fields, osv
from tools.translate import _

class hr_holidays_status(osv.osv):
    _name = "hr.holidays.status"
    _description = "Leave Types"

    def get_days_cat(self, cr, uid, ids, category_id, return_false, context={}):
        res = {}
        for record in self.browse(cr, uid, ids, context):
            res[record.id] = {}
            max_leaves = leaves_taken = 0
            if not return_false:
                cr.execute("""SELECT type, sum(number_of_days) FROM hr_holidays WHERE category_id = %s AND state='validate' AND holiday_status_id = %s GROUP BY type""", (str(category_id), str(record.id)))
                for line in cr.fetchall():
                    if line[0] =='remove':
                        leaves_taken = -line[1]
                    if line[0] =='add':
                        max_leaves = line[1]
            res[record.id]['max_leaves'] = max_leaves
            res[record.id]['leaves_taken'] = leaves_taken
            res[record.id]['remaining_leaves'] = max_leaves - leaves_taken
        return res

    def get_days(self, cr, uid, ids, employee_id, return_false, context={}):
        res = {}
        for record in self.browse(cr, uid, ids, context):
            res[record.id] = {}
            max_leaves = leaves_taken = 0
            if not return_false:
                cr.execute("""SELECT type, sum(number_of_days) FROM hr_holidays WHERE employee_id = %s AND state='validate' AND holiday_status_id = %s GROUP BY type""", (str(employee_id), str(record.id)))
                for line in cr.fetchall():
                    if line[0] =='remove':
                        leaves_taken = -line[1]
                    if line[0] =='add':
                        max_leaves = line[1]
            res[record.id]['max_leaves'] = max_leaves
            res[record.id]['leaves_taken'] = leaves_taken
            res[record.id]['remaining_leaves'] = max_leaves - leaves_taken
        return res

    def _user_left_days(self, cr, uid, ids, name, args, context={}):
        return_false = False
        employee_id = False
        res = {}
        for id in ids:
            res[id] = {}.fromkeys(name, 0)
        if context and context.has_key('employee_id'):
            if not context['employee_id']:
                return_false = True
            employee_id = context['employee_id']
        else:
            employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
            if employee_ids:
                employee_id = employee_ids[0]
            else:
                return_false = True
        if employee_id:
            res = self.get_days(cr, uid, ids, employee_id, return_false, context=context)
        return res

    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'categ_id': fields.many2one('crm.case.categ', 'Meeting Category', domain="[('object_id.model', '=', 'crm.meeting')]", help='If you link this type of leave with a category in the CRM, it will synchronize each leave asked with a case in this category, to display it in the company shared calendar for example.'),
        'color_name': fields.selection([('red', 'Red'), ('lightgreen', 'Light Green'), ('lightblue','Light Blue'), ('lightyellow', 'Light Yellow'), ('magenta', 'Magenta'),('lightcyan', 'Light Cyan'),('black', 'Black'),('lightpink', 'Light Pink'),('brown', 'Brown'),('violet', 'Violet'),('lightcoral', 'Light Coral'),('lightsalmon', 'Light Salmon'),('lavender', 'Lavender'),('wheat', 'Wheat'),('ivory', 'Ivory')],'Color in Report', required=True, help='This color will be used in the leaves summary located in Reporting\Leaves by Departement'),
        'limit': fields.boolean('Allow to Override Limit', help='If you thick this checkbox, the system will allow, for this section, the employees to take more leaves than the available ones.'),
        'active': fields.boolean('Active', help="If the active field is set to false, it will allow you to hide the leave type without removing it."),
        'max_leaves': fields.function(_user_left_days, method=True, string='Maximum Leaves Allowed', help='This value is given by the sum of all holidays requests with a positive value.', multi='user_left_days'),
        'leaves_taken': fields.function(_user_left_days, method=True, string='Leaves Already Taken', help='This value is given by the sum of all holidays requests with a negative value.', multi='user_left_days'),
        'remaining_leaves': fields.function(_user_left_days, method=True, string='Remaining Leaves', help='Maximum Leaves Allowed - Leaves Already Taken', multi='user_left_days'),
    }
    _defaults = {
        'color_name': 'red',
        'active': True,
    }

hr_holidays_status()

class hr_holidays(osv.osv):
    _name = "hr.holidays"
    _description = "Holidays"
    _order = "type desc, date_from asc"

#    def _employee_get(obj, cr, uid, context=None):
#        ids = obj.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)])
#        if ids:
#            return ids[0]
#        return False

    _columns = {
        'name' : fields.char('Description', required=True, readonly=True, size=64, states={'draft':[('readonly',False)]}),
        'state': fields.selection([('draft', 'Draft'), ('confirm', 'Waiting Validation'), ('refuse', 'Refused'), ('validate', 'Validated'), ('cancel', 'Cancelled')], 'State', readonly=True, help='When the holiday request is created the state is \'Draft\'.\n It is confirmed by the user and request is sent to admin, the state is \'Waiting Validation\'.\
            If the admin accepts it, the state is \'Validated\'. If it is refused, the state is \'Refused\'.'),
        'date_from' : fields.datetime('Start Date', readonly=True, states={'draft':[('readonly',False)]}),
        'user_id':fields.many2one('res.users', 'User', states={'draft':[('readonly',False)]}, select=True, readonly=True),
        'date_to' : fields.datetime('End Date', readonly=True, states={'draft':[('readonly',False)]}),
        'holiday_status_id' : fields.many2one("hr.holidays.status", "Leave Type", required=True,readonly=True, states={'draft':[('readonly',False)]}),
        'employee_id' : fields.many2one('hr.employee', "Employee", select=True, invisible=False, readonly=True, states={'draft':[('readonly',False)]}, help='Leave Manager can let this field empty if this leave request/allocation is for every employee'),
        'manager_id' : fields.many2one('hr.employee', 'Leave Manager', invisible=False, readonly=True, help='This area is automaticly filled by the user who validate the leave'),
        'notes' : fields.text('Notes',readonly=True, states={'draft':[('readonly',False)]}),
        'number_of_days': fields.float('Number of Days', readonly=True, states={'draft':[('readonly',False)]}),
        'number_of_days_temp': fields.float('Number of Days', readonly=True, states={'draft':[('readonly',False)]}),
        'case_id': fields.many2one('crm.meeting', 'Case'),
        'type': fields.selection([('remove','Leave Request'),('add','Allocation Request')], 'Request Type', required=True, readonly=True, states={'draft':[('readonly',False)]}, help="Choose 'Leave Request' if someone wants to take an off-day. \nChoose 'Allocation Request' if you want to increase the number of leaves available for someone"),
        'allocation_type': fields.selection([('employee','Employee Request'),('company','Company Allocation')], 'Allocation Type', required=True, readonly=True, states={'draft':[('readonly',False)]}, help='This field is only for informative purposes, to depict if the leave request/allocation comes from an employee or from the company'),
        'parent_id': fields.many2one('hr.holidays', 'Parent'),
        'linked_request_ids': fields.one2many('hr.holidays', 'parent_id', 'Linked Requests',),
        'department_id':fields.related('employee_id', 'department_id', string='Department', type='many2one', relation='hr.department', readonly=True, store=True),
        'category_id': fields.many2one('hr.employee.category', "Employee Category", help='Category Of employee'),
        'holiday_type': fields.selection([('employee','Employee Request'),('category','Employee Category Request')], 'Holiday Type'),
            }

    _defaults = {
#        'employee_id' : _employee_get ,
        'state' : 'draft',
        'type': 'remove',
        'allocation_type': 'employee',
        'user_id': lambda obj, cr, uid, context: uid,
        'holiday_type': 'employee'
    }

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if context:
            if context.has_key('type'):
                vals['type'] = context['type']
            if context.has_key('allocation_type'):
                vals['allocation_type'] = context['allocation_type']
        return super(hr_holidays, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        if 'holiday_type' in vals:
            if vals['holiday_type'] == 'employee':
                vals.update({'category_id': False})
            else:
                vals.update({'employee_id': False})
        return super(hr_holidays, self).write(cr, uid, ids, vals, context=context)

    def onchange_date_from(self, cr, uid, ids, date_to, date_from):
        result = {}
        if date_to and date_from:
            from_dt = time.mktime(time.strptime(date_from,'%Y-%m-%d %H:%M:%S'))
            to_dt = time.mktime(time.strptime(date_to,'%Y-%m-%d %H:%M:%S'))
            diff_day = (to_dt-from_dt)/(3600*24)
            result['value'] = {
                'number_of_days_temp': round(diff_day)+1
            }
            return result
        result['value'] = {
            'number_of_days_temp': 0,
        }
        return result

    def _update_user_holidays(self, cr, uid, ids):
        for record in self.browse(cr, uid, ids):
            if record.state=='validate':
                if record.case_id:
                    self.pool.get('crm.meeting').unlink(cr,uid,[record.case_id.id])
                if record.linked_request_ids:
                    list_ids = []
                    [list_ids.append(i) for id in record.linked_request_ids]
                    self.holidays_cancel(cr, uid, list_ids)
                    self.unlink(cr, uid, list_ids)

    def _check_date(self, cr, uid, ids):
        if ids:
            cr.execute('select number_of_days_temp from hr_holidays where id in ('+','.join(map(str, ids))+')')
            res =  cr.fetchall()
            if res and res[0][0] and res[0][0] < 0:
                return False
        return True

    _constraints = [(_check_date, 'Start date should not be larger than end date! ', ['number_of_days'])]

    def unlink(self, cr, uid, ids, context={}):
        self._update_user_holidays(cr, uid, ids)
        return super(hr_holidays, self).unlink(cr, uid, ids, context)

    def onchange_date_to(self, cr, uid, ids, date_from, date_to):
        result = {}
        if date_from and date_to:
            from_dt = time.mktime(time.strptime(date_from,'%Y-%m-%d %H:%M:%S'))
            to_dt = time.mktime(time.strptime(date_to,'%Y-%m-%d %H:%M:%S'))
            diff_day = (to_dt-from_dt)/(3600*24)
            result['value'] = {
                'number_of_days_temp': round(diff_day)+1
            }
            return result
        result['value'] = {
            'number_of_days_temp': 0
        }
        return result

    def onchange_sec_id(self, cr, uid, ids, status, context={}):
        warning = {}
        if status:
            brows_obj = self.pool.get('hr.holidays.status').browse(cr, uid, [status])[0]
            if brows_obj.categ_id and brows_obj.categ_id.section_id and not brows_obj.categ_id.section_id.allow_unlink:
                warning = {
                    'title': "Warning for ",
                    'message': "You won\'t be able to cancel this leave request because the CRM Section of the leave type disallows."
                        }
        return {'warning': warning}


    def set_to_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {
            'state':'draft',
            'manager_id': False,
            'number_of_days': 0,
        })
        wf_service = netsvc.LocalService("workflow")
        for holiday_id in ids:
            wf_service.trg_create(uid, 'hr.holidays', holiday_id, cr)
        return True

    def holidays_validate(self, cr, uid, ids, *args):
        self.check_holidays(cr, uid, ids)
        vals = {
            'state':'validate',
        }
        ids2 = self.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)])
        if ids2:
            vals['manager_id'] = ids2[0]
        else:
            raise osv.except_osv(_('Warning !'),_('No user related to the selected employee.'))
        self.write(cr, uid, ids, vals)
        for record in self.browse(cr, uid, ids):
            if record.holiday_type=='employee' and record.type=='remove':
                vals= {
                   'name':record.name,
                   'date_from':record.date_from,
                   'date_to':record.date_to,
                   'calendar_id':record.employee_id.calendar_id.id,
                   'company_id':record.employee_id.company_id.id,
                   'resource_id':record.employee_id.resource_id.id
                     }
                self.pool.get('resource.calendar.leaves').create(cr, uid, vals)
        return True

    def holidays_confirm(self, cr, uid, ids, *args):
        for record in self.browse(cr, uid, ids):
            user_id = False
            leave_asked = record.number_of_days_temp
            if record.holiday_type=='employee' and record.type == 'remove':
                if record.employee_id and not record.holiday_status_id.limit:
                    leaves_rest = self.pool.get('hr.holidays.status').get_days( cr, uid, [record.holiday_status_id.id], record.employee_id.id, False)[record.holiday_status_id.id]['remaining_leaves']
                    if leaves_rest < leave_asked:
                        raise osv.except_osv(_('Warning!'),_('You cannot validate leaves for %s while available leaves are less than asked leaves.' %(record.employee_id.name)))
                nb = -(record.number_of_days_temp)
            elif record.holiday_type=='category' and record.type == 'remove':
                if record.category_id and not record.holiday_status_id.limit:
                    leaves_rest = self.pool.get('hr.holidays.status').get_days_cat( cr, uid, [record.holiday_status_id.id], record.category_id.id, False)[record.holiday_status_id.id]['remaining_leaves']
                    if leaves_rest < leave_asked:
                        raise osv.except_osv(_('Warning!'),_('You cannot validate leaves for %s while available leaves are less than asked leaves.' %(record.category_id.name)))
                nb = -(record.number_of_days_temp)
            else:
                nb = record.number_of_days_temp

            if record.holiday_type=='employee' and record.employee_id:
                user_id = record.employee_id.user_id and record.employee_id.user_id.id or uid

            self.write(cr, uid, [record.id], {
                'state':'confirm',
                'number_of_days': nb,
                'user_id': user_id
            })
        return True

    def holidays_refuse(self, cr, uid, ids, *args):
        vals = {
            'state':'refuse',
        }
        ids2 = self.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)])
        if ids2:
            vals['manager_id'] = ids2[0]
        self.write(cr, uid, ids, vals)
        return True

    def holidays_cancel(self, cr, uid, ids, *args):
        self._update_user_holidays(cr, uid, ids)
        self.write(cr, uid, ids, {
            'state':'cancel'
            })
        return True

    def holidays_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {
            'state':'draft'
        })
        return True

    def check_holidays(self, cr, uid, ids):
        for record in self.browse(cr, uid, ids):
            if not record.number_of_days:
                raise osv.except_osv(_('Warning!'),_('Wrong leave definition.'))
            if record.holiday_type=='employee' and record.employee_id:
                leave_asked = record.number_of_days
                if leave_asked < 0.00:
                    if not record.holiday_status_id.limit:
                        leaves_rest = self.pool.get('hr.holidays.status').get_days(cr, uid, [record.holiday_status_id.id], record.employee_id.id, False)[record.holiday_status_id.id]['remaining_leaves']
                        if leaves_rest < -(leave_asked):
                            raise osv.except_osv(_('Warning!'),_('You Cannot Validate leaves while available leaves are less than asked leaves.'))
            elif record.holiday_type=='category' and record.category_id:
                leave_asked = record.number_of_days
                if leave_asked < 0.00:
                    if not record.holiday_status_id.limit:
                        leaves_rest = self.pool.get('hr.holidays.status').get_days_cat(cr, uid, [record.holiday_status_id.id], record.category_id.id, False)[record.holiday_status_id.id]['remaining_leaves']
                        if leaves_rest < -(leave_asked):
                            raise osv.except_osv(_('Warning!'),_('You Cannot Validate leaves while available leaves are less than asked leaves.'))
            else:# This condition will never meet!!
                holiday_ids = []
                vals = {
                    'name' : record.name,
                    'holiday_status_id' : record.holiday_status_id.id,
                    'state': 'draft',
                    'date_from' : record.date_from,
                    'date_to' : record.date_to,
                    'notes' : record.notes,
                    'number_of_days': record.number_of_days,
                    'number_of_days_temp': record.number_of_days_temp,
                    'type': record.type,
                    'allocation_type': record.allocation_type,
                    'parent_id': record.id,
                }
                employee_ids = self.pool.get('hr.employee').search(cr, uid, [])
                for employee in employee_ids:
                    vals['employee_id'] = employee
                    user_id = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
                    if user_id:
                        vals['user_id'] = user_id[0]
                    holiday_ids.append(self.create(cr, uid, vals, context={}))
                self.holidays_confirm(cr, uid, holiday_ids)
                self.holidays_validate(cr, uid, holiday_ids)

            #if record.holiday_status_id.categ_id and record.date_from and record.date_to and record.employee_id:
            if record.holiday_status_id.categ_id and record.date_from and record.date_to:
                vals={}
                vals['name']=record.name
                vals['categ_id']=record.holiday_status_id.categ_id.id
                epoch_c = time.mktime(time.strptime(record.date_to,'%Y-%m-%d %H:%M:%S'))
                epoch_d = time.mktime(time.strptime(record.date_from,'%Y-%m-%d %H:%M:%S'))
                diff_day = (epoch_c - epoch_d)/(3600*24)
                vals['duration'] = (diff_day) * 8
                vals['note'] = record.notes
#                vals['user_id'] = record.user_id.id
                vals['date'] = record.date_from
                if record.holiday_type=='employee':
                    vals['user_id'] = record.user_id.id
                case_id = self.pool.get('crm.meeting').create(cr,uid,vals)
                self.write(cr, uid, ids, {'case_id':case_id})
        return True
hr_holidays()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: