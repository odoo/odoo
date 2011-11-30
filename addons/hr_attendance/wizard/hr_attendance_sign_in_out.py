# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import time

from osv import osv, fields
from tools.translate import _

class hr_si_so_ask(osv.osv_memory):
    _name = 'hr.sign.in.out.ask'
    _description = 'Ask for Sign In Out'
    _columns = {
        'name': fields.char('Employees name', size=32, required=True, readonly=True),
        'last_time': fields.datetime('Your last sign out', required=True),
        'emp_id': fields.many2one('hr.employee', 'Empoyee ID', readonly=True),
        }

    def _get_empname(self, cr, uid, context=None):
        emp_id = context.get('emp_id', self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context))
        if emp_id:
            employee = self.pool.get('hr.employee').browse(cr, uid, emp_id, context=context)[0].name
            return employee
        return ''

    def _get_empid(self, cr, uid, context=None):
        emp_id = context.get('emp_id', self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context))
        if emp_id:
            return emp_id[0]
        return False

    _defaults = {
         'name': _get_empname,
         'emp_id': _get_empid,
                 }

    def sign_in(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, [], context=context)[0]
        data['emp_id'] = data['emp_id'] and data['emp_id'][0]
        return self.pool.get('hr.sign.in.out').sign_in(cr, uid, data, context)

    def sign_out(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, [], context=context)[0]
        data['emp_id'] = data['emp_id'] and data['emp_id'][0]
        return self.pool.get('hr.sign.in.out').sign_out(cr, uid, data, context)

hr_si_so_ask()

class hr_sign_in_out(osv.osv_memory):
    _name = 'hr.sign.in.out'
    _description = 'Sign In Sign Out'

    _columns = {
        'name': fields.char('Employees name', size=32, required=True, readonly=True),
        'state': fields.char('Current state', size=32, required=True, readonly=True),
        'emp_id': fields.many2one('hr.employee', 'Empoyee ID', readonly=True),
                }

    def _get_empid(self, cr, uid, context=None):
        emp_id = context.get('emp_id', self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context))
        if emp_id:
            employee = self.pool.get('hr.employee').browse(cr, uid, emp_id, context=context)[0]
            return {'name': employee.name, 'state': employee.state, 'emp_id': emp_id[0]}
        return {}

    def default_get(self, cr, uid, fields_list, context=None):
        res = super(hr_sign_in_out, self).default_get(cr, uid, fields_list, context=context)
        res_emp = self._get_empid(cr, uid, context=context)
        res.update(res_emp)
        return res

    def si_check(self, cr, uid, ids, context=None):
        obj_model = self.pool.get('ir.model.data')
        att_obj = self.pool.get('hr.attendance')
        data = self.read(cr, uid, ids, [], context=context)[0]
        data['emp_id'] = data['emp_id'] and data['emp_id'][0]
        emp_id = data['emp_id']
        att_id = att_obj.search(cr, uid, [('employee_id', '=', emp_id)], limit=1, order='name desc')
        last_att = att_obj.browse(cr, uid, att_id, context=context)
        if last_att:
            last_att = last_att[0]
        cond = not last_att or last_att.action == 'sign_out'
        if cond:
            return self.sign_in(cr, uid, data, context)
        else:
            model_data_ids = obj_model.search(cr,uid,[('model','=','ir.ui.view'),('name','=','view_hr_attendance_so_ask')], context=context)
            resource_id = obj_model.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
            return {
                'name': _('Sign in / Sign out'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'hr.sign.in.out.ask',
                'views': [(resource_id,'form')],
                'type': 'ir.actions.act_window',
                'context': context,
                'target': 'new',
            }

    def so_check(self, cr, uid, ids, context=None):
        obj_model = self.pool.get('ir.model.data')
        att_obj = self.pool.get('hr.attendance')
        data = self.read(cr, uid, ids, [], context=context)[0]
        data['emp_id'] = data['emp_id'] and data['emp_id'][0]
        emp_id = data['emp_id']
        att_id = att_obj.search(cr, uid, [('employee_id', '=', emp_id),('action', '!=', 'action')], limit=1, order='name desc')
        last_att = att_obj.browse(cr, uid, att_id, context=context)
        if last_att:
            last_att = last_att[0]
        if not att_id and not last_att:
            model_data_ids = obj_model.search(cr, uid, [('model','=','ir.ui.view'),('name','=','view_hr_attendance_message')], context=context)
            resource_id = obj_model.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
            return {
                'name': _('Sign in / Sign out'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'hr.sign.in.out',
                'views': [(resource_id,'form')],
                'type': 'ir.actions.act_window',
                'context': context,
                'target': 'new',
            }

        cond = last_att and last_att['action'] == 'sign_in'
        if cond:
            return self.sign_out(cr, uid, data, context)
        else:
            model_data_ids = obj_model.search(cr, uid, [('model','=','ir.ui.view'),('name','=','view_hr_attendance_si_ask')], context=context)
            resource_id = obj_model.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
            return {
                'name': _('Sign in / Sign out'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'hr.sign.in.out.ask',
                'views': [(resource_id,'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
            }

    def sign_in(self, cr, uid, data, context=None):
        if context is None:
            context = {}
        emp_id = data['emp_id']
        if 'last_time' in data:
            if data['last_time'] > time.strftime('%Y-%m-%d %H:%M:%S'):
                raise osv.except_osv(_('UserError'), _('The sign-out date must be in the past'))
            self.pool.get('hr.attendance').create(cr, uid, {'name': data['last_time'], 'action': 'sign_out',
                'employee_id': emp_id}, context=context)
        try:
            self.pool.get('hr.employee').attendance_action_change(cr, uid, [emp_id], 'sign_in')
        except:
            raise osv.except_osv(_('UserError'), _('A sign-in must be right after a sign-out !'))
        return {'type': 'ir.actions.act_window_close'} # To do: Return Success message

    def sign_out(self, cr, uid, data, context=None):
        emp_id = data['emp_id']
        if 'last_time' in data:
            if data['last_time'] > time.strftime('%Y-%m-%d %H:%M:%S'):
                raise osv.except_osv(_('UserError'), _('The Sign-in date must be in the past'))
            self.pool.get('hr.attendance').create(cr, uid, {'name':data['last_time'], 'action':'sign_in',  'employee_id':emp_id}, context=context)
        try:
            self.pool.get('hr.employee').attendance_action_change(cr, uid, [emp_id], 'sign_out')
        except:
            raise osv.except_osv(_('UserError'), _('A sign-out must be right after a sign-in !'))
        return {'type': 'ir.actions.act_window_close'} # To do: Return Success message

hr_sign_in_out()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
