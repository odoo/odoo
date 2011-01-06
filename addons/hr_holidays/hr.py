# -*- encoding: utf-8 -*-
##################################################################################
#
# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com) All Rights Reserved.
#
# $Id: hr.py 4656 2006-11-24 09:58:42Z Cyp $
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from mx import DateTime
import time
import pooler
import netsvc
import datetime
from osv import fields, osv
from tools.translate import _

def _employee_get(obj,cr,uid,context={}):
    ids = obj.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)])
    if ids:
        return ids[0]
    return False

def strToDate(dt):
    dt_date=datetime.date(int(dt[0:4]),int(dt[5:7]),int(dt[8:10]))
    return dt_date

class hr_holidays_status(osv.osv):
    _name = "hr.holidays.status"
    _description = "Holidays Status"
    _columns = {
        'name' : fields.char('Holiday Status', size=64, required=True, translate=True),
        'section_id': fields.many2one('crm.case.section', 'Section'),
        'color_name' : fields.selection([('red', 'Red'), ('lightgreen', 'Light Green'), ('lightblue','Light Blue'), ('lightyellow', 'Light Yellow'), ('magenta', 'Magenta'),('lightcyan', 'Light Cyan'),('black', 'Black'),('lightpink', 'Light Pink'),('brown', 'Brown'),('violet', 'Violet'),('lightcoral', 'Light Coral'),('lightsalmon', 'Light Salmon'),('lavender', 'Lavender'),('wheat', 'Wheat'),('ivory', 'Ivory')],'Color of the status', required=True),
        'limit' : fields.boolean('Allow to override Limit'),
        'active' : fields.boolean('Active')
    }
    _defaults = {
        'color_name': lambda *args: 'red',
        'active' : lambda *a: True,
    }
hr_holidays_status()

class hr_holidays_per_user(osv.osv):
    _name = "hr.holidays.per.user"
    _description = "Holidays Per User"
    _rec_name = "user_id"

    def _get_remaining_leaves(self, cr, uid, ids, field_name, arg=None, context={}):
        obj_holiday = self.pool.get('hr.holidays')
        result = {}
        for holiday_user in self.browse(cr, uid, ids):
            days = 0.0
            ids_request = obj_holiday.search(cr, uid, [('employee_id', '=', holiday_user.employee_id.id),('state', '=', 'validate'),('holiday_status', '=', holiday_user.holiday_status.id)])
            if ids_request:
                holidays = obj_holiday.browse(cr, uid, ids_request)
                for holiday in holidays:
                    if holiday.number_of_days > 0:
                        days += holiday.number_of_days
            days = holiday_user.max_leaves - days
            result[holiday_user.id] = days
        return result

    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee',required=True),
        'user_id' : fields.many2one('res.users','User'),
        'holiday_status' : fields.many2one("hr.holidays.status", "Holiday's Status", required=True),
        'max_leaves' : fields.float('Maximum Leaves Allowed',required=True),
        'leaves_taken' : fields.float('Leaves Already Taken',readonly=True),
        'active' : fields.boolean('Active'),
        'notes' : fields.text('Notes'),
        'remaining_leaves': fields.function(_get_remaining_leaves, method=True, string='Remaining Leaves', type='float'),
        'holiday_ids': fields.one2many('hr.holidays', 'holiday_user_id', 'Holidays')
    }
    _defaults = {
        'active' : lambda *a: True,
    }

    def create(self, cr, uid, vals, *args, **kwargs):
        if vals['employee_id']:
            obj_emp=self.pool.get('hr.employee').browse(cr,uid,vals['employee_id'])
            vals.update({'user_id': obj_emp.user_id.id})
        return super(osv.osv,self).create(cr, uid, vals, *args, **kwargs)

hr_holidays_per_user()

class hr_holidays(osv.osv):
    _name = "hr.holidays"
    _description = "Holidays"

    _columns = {
        'name' : fields.char('Description', required=True, readonly=True, size=64, states={'draft':[('readonly',False)]}),
        'state': fields.selection([('draft', 'Draft'), ('confirm', 'Waiting Validation'), ('refuse', 'Refused'), ('validate', 'Validate'), ('cancel', 'Cancel')], 'Status', readonly=True),
        'date_from' : fields.datetime('Vacation start day', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'date_to' : fields.datetime('Vacation end day',required=True,readonly=True, states={'draft':[('readonly',False)]}),
        'holiday_status' : fields.many2one("hr.holidays.status", "Holiday's Status", required=True,readonly=True, states={'draft':[('readonly',False)]}),
        'employee_id' : fields.many2one('hr.employee', 'Employee', select=True, invisible=False, readonly=True, states={'draft':[('readonly',False)]}),
        'user_id':fields.many2one('res.users', 'Employee_id', states={'draft':[('readonly',False)]}, select=True, readonly=True),
        'manager_id' : fields.many2one('hr.employee', 'Holiday manager', invisible=False, readonly=True),
        'notes' : fields.text('Notes',readonly=True, states={'draft':[('readonly',False)]}),
        'number_of_days': fields.float('Number of Days in this Holiday Request', required=True, readonly=True, states={'draft': [('readonly', False)]}, help="An employee can make a negative holiday request (holiday request of -2 days for example), this is considered by the system as an ask for more off-days. It will increase his total of that holiday status available (if the request is accepted). For the same, make sure the days you enter are negative and both the dates are same."),
        'case_id': fields.many2one('crm.case', 'Case'),
        'holiday_user_id': fields.many2one('hr.holidays.per.user', 'Holiday per user')
    }

    _defaults = {
        'employee_id' : _employee_get ,
        'state' : lambda *a: 'draft',
        'user_id': lambda obj, cr, uid, context: uid,
    }
    _order = 'date_from desc'

    def _update_user_holidays(self, cr, uid, ids):
        for record in self.browse(cr, uid, ids):
            if record.state=='validate':
                holiday_id=self.pool.get('hr.holidays.per.user').search(cr, uid, [('employee_id','=', record.employee_id.id),('holiday_status','=',record.holiday_status.id)])
                if holiday_id:
                    obj_holidays_per_user=self.pool.get('hr.holidays.per.user').browse(cr, uid,holiday_id[0])
                    self.pool.get('hr.holidays.per.user').write(cr,uid,obj_holidays_per_user.id,{'leaves_taken':obj_holidays_per_user.leaves_taken - record.number_of_days})
                if record.case_id:
                    if record.case_id.state <> 'draft':
                        raise osv.except_osv(_('Warning !'),
                    _('You can not cancel this holiday request. first You have to make its case in draft state.'))
                    else:
                        self.pool.get('crm.case').unlink(cr,uid,[record.case_id.id])
                        
    def _check_date(self, cr, uid, ids):
        for rec in self.read(cr, uid, ids, ['number_of_days','date_from','date_to']):
            if rec['number_of_days'] == 0.0:
                return False
            date_from = time.strptime(rec['date_from'], '%Y-%m-%d %H:%M:%S')
            date_to = time.strptime(rec['date_to'], '%Y-%m-%d %H:%M:%S')
            if rec['number_of_days'] < 0:
                if date_from <> date_to:
                    return False
            else:
                if date_from > date_to:
                    return False
        return True

    _constraints = [(_check_date, 'The Holiday request seems invalid due to one of the following reasons:\n1. Start date is greater than End date!\n2. Number of Day(s) asked for leave(s) are zero!\n3. You are requesting more holidays by putting negative days,but both the dates are not same! ', ['number_of_days'])]

    def create(self, cr, uid, vals, *args, **kwargs):
        id_holiday = super(hr_holidays, self).create(cr, uid, vals, *args, **kwargs)
        self._create_holiday(cr, uid, [id_holiday])
        return id_holiday
    
    def unlink(self, cr, uid, ids, context={}):
        self._update_user_holidays(cr, uid, ids)
        return super(hr_holidays, self).unlink(cr, uid, ids, context)

    def _create_holiday(self, cr, uid, ids):
        holidays_user_obj = self.pool.get('hr.holidays.per.user')
        holidays_data = self.browse(cr, uid, ids[0])
        list_holiday = []
        ids_user_hdays = holidays_user_obj.search(cr, uid, [('employee_id', '=', holidays_data.employee_id.id),('holiday_status', '=', holidays_data.holiday_status.id)])
        for hdays in holidays_user_obj.browse(cr, uid, ids_user_hdays):
            for req in hdays.holiday_ids:
                list_holiday.append(req.id)
        list_holiday.append(ids[0])
        holidays_user_obj.write(cr, uid, ids_user_hdays, {'holiday_ids': [(6, 0, list_holiday)]})
        return True

    def onchange_date_to(self, cr, uid, ids, date_from, date_to):
        result = {}
        if date_from:
            if date_to:
                from_dt = time.mktime(time.strptime(date_from,'%Y-%m-%d %H:%M:%S'))
                to_dt = time.mktime(time.strptime(date_to,'%Y-%m-%d %H:%M:%S'))
                diff_day = (to_dt-from_dt)/(3600*24)
                result['value'] = {
                    'number_of_days': round(diff_day)+1
                }
                return result
        result['value'] = {
            'number_of_days': 0
        }
        return result

    def set_to_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {
            'state':'draft',
            'manager_id': False
        })
        self._create_holiday(cr, uid, ids)
        return True

    def holidays_validate(self, cr, uid, ids, *args):
        self.check_holidays(cr,uid,ids)
        vals = {
            'state':'validate',
        }
        ids2 = self.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)])
        
        if ids2:
            vals['manager_id'] = ids2[0]
        else:
            raise osv.except_osv(_('Warning !'),_('Either there is no Employee defined, or no User attached with it.'))    
        self.write(cr, uid, ids, vals)
        self._create_holiday(cr, uid, ids)
        return True

    def holidays_confirm(self, cr, uid, ids, *args):
        user = False
        for id in self.browse(cr, uid, ids):
            if id.employee_id.user_id:
                user = id.employee_id.user_id.id
        self.write(cr, uid, ids, {
            'state':'confirm',
            'user_id': user,
        })
        self._create_holiday(cr, uid, ids)
        return True

    def holidays_refuse(self, cr, uid, ids, *args):
        ids2 = self.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)])
        if not ids2:
            raise osv.except_osv(_('Warning !'),_('Either there is no Employee defined, or no User attached with it.'))
        self.write(cr, uid, ids, {
            'state':'refuse',
            'manager_id':ids2[0]
        })
        self._create_holiday(cr, uid, ids)
        return True

    def holidays_cancel(self, cr, uid, ids, *args):
        self._update_user_holidays(cr, uid, ids)
        self.write(cr, uid, ids, {
            'state':'cancel'
            })
        self._create_holiday(cr, uid, ids)
        return True

    def holidays_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {
            'state':'draft'
        })
        self._create_holiday(cr, uid, ids)
        return True

    def check_holidays(self,cr,uid,ids):

        holiday_user_pool = self.pool.get('hr.holidays.per.user')
        for record in self.browse(cr, uid, ids):
            leave_asked = record.number_of_days
            holiday_id = holiday_user_pool.search(cr, uid, [('employee_id','=', record.employee_id.id),('holiday_status','=',record.holiday_status.id)])
            if leave_asked>=0.00:
                if holiday_id:
                    obj_holidays_per_user = holiday_user_pool.browse(cr, uid,holiday_id[0])
                    leaves_rest = obj_holidays_per_user.max_leaves - obj_holidays_per_user.leaves_taken
                    if not obj_holidays_per_user.holiday_status.limit:
                        if leaves_rest < leave_asked:
                            raise osv.except_osv(_('Attention!'),_('You Cannot Validate leaves while available leaves are less than asked leaves.'))
                    holiday_user_pool.write(cr,uid,obj_holidays_per_user.id,{'leaves_taken':obj_holidays_per_user.leaves_taken + leave_asked})
                if record.holiday_status.section_id:
                    vals={}
                    vals['name']=record.name
                    vals['section_id']=record.holiday_status.section_id.id
                    epoch_c = time.mktime(time.strptime(record.date_to,'%Y-%m-%d %H:%M:%S'))
                    epoch_d = time.mktime(time.strptime(record.date_from,'%Y-%m-%d %H:%M:%S'))
                    diff_day = (epoch_c - epoch_d)/(3600*24)
                    vals['duration']= (diff_day) * 8
                    vals['note']=record.notes
                    vals['user_id']=record.user_id.id
                    vals['date']=record.date_from
                    case_id=self.pool.get('crm.case').create(cr,uid,vals)
                    self.write(cr, uid, ids, {'case_id':case_id})
            else:
                if holiday_id:
                    obj_holidays_per_user = holiday_user_pool.browse(cr, uid,holiday_id[0])
                    note = obj_holidays_per_user.notes or ''
                    notes = note + '\n*** Reference Id [' + str(record.id) + '] : ' + str(abs(leave_asked)) + ' leaves added on ' + time.strftime('%Y-%m-%d %H:%M:%S') + ' Description: ' + record.name
                    holiday_user_pool.write(cr,uid,obj_holidays_per_user.id,{'max_leaves':obj_holidays_per_user.max_leaves + abs(leave_asked),'notes':notes})
                else:
                    vals = {}
                    vals['employee_id'] = record.employee_id.id
                    vals['holiday_status'] = record.holiday_status.id
                    vals['max_leaves'] = abs(leave_asked)
                    vals['leaves_taken'] = 0.00
                    holiday_user_pool.create(cr,uid,vals)

        return True
hr_holidays()

class holiday_user_log(osv.osv):
    _name = 'hr.holidays.log'
    _description = 'hr.holidays.log'
    _order = "holiday_req_id desc"
    _columns = {
        'name' : fields.char('Action', size=64, readonly=True),
        'holiday_req_id' : fields.char('Holiday Request ID', size=64),
        'nb_holidays' : fields.float('Number of Holidays Requested'),
        'employee_id' : fields.many2one('hr.employee', 'Employee', readonly=True),
        'holiday_status' : fields.many2one("hr.holidays.status", "Holiday's Status", readonly=True),
        'holiday_user_id' : fields.many2one('hr.holidays.per.user', 'Holidays user'),
        'date': fields.datetime('Date'),
                }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }
holiday_user_log()
