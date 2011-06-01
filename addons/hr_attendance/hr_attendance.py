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

from osv import fields, osv
from tools.translate import _

class hr_action_reason(osv.osv):
    _name = "hr.action.reason"
    _description = "Action Reason"
    _columns = {
        'name': fields.char('Reason', size=64, required=True, help='Specifies the reason for Signing In/Signing Out.'),
        'action_type': fields.selection([('sign_in', 'Sign in'), ('sign_out', 'Sign out')], "Action Type"),
    }
    _defaults = {
        'action_type': 'sign_in',
    }

hr_action_reason()

def _employee_get(obj, cr, uid, context=None):
    ids = obj.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context)
    return ids and ids[0] or False

class hr_attendance(osv.osv):
    _name = "hr.attendance"
    _description = "Attendance"

    def _day_compute(self, cr, uid, ids, fieldnames, args, context=None):
        res = dict.fromkeys(ids, '')
        for obj in self.browse(cr, uid, ids, context=context):
            res[obj.id] = time.strftime('%Y-%m-%d', time.strptime(obj.name, '%Y-%m-%d %H:%M:%S'))
        return res

    _columns = {
        'name': fields.datetime('Date', required=True, select=1),
        'action': fields.selection([('sign_in', 'Sign In'), ('sign_out', 'Sign Out'), ('action','Action')], 'Action', required=True),
        'action_desc': fields.many2one("hr.action.reason", "Action Reason", domain="[('action_type', '=', action)]", help='Specifies the reason for Signing In/Signing Out in case of extra hours.'),
        'employee_id': fields.many2one('hr.employee', "Employee's Name", required=True, select=True),
        'day': fields.function(_day_compute, method=True, type='char', string='Day', store=True, select=1, size=32),
    }
    _defaults = {
        'name': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'), #please don't remove the lambda, if you remove it then the current time will not change
        'employee_id': _employee_get,
    }

    def _altern_si_so(self, cr, uid, ids, context=None):
        for id in ids:
            sql = '''
            SELECT action, name
            FROM hr_attendance AS att
            WHERE employee_id = (SELECT employee_id FROM hr_attendance WHERE id=%s)
            AND action IN ('sign_in','sign_out')
            AND name <= (SELECT name FROM hr_attendance WHERE id=%s)
            ORDER BY name DESC
            LIMIT 2 '''
            cr.execute(sql,(id,id))
            atts = cr.fetchall()
            if not ((len(atts)==1 and atts[0][0] == 'sign_in') or (len(atts)==2 and atts[0][0] != atts[1][0] and atts[0][1] != atts[1][1])):
                return False
        return True

    _constraints = [(_altern_si_so, 'Error: Sign in (resp. Sign out) must follow Sign out (resp. Sign in)', ['action'])]
    _order = 'name desc'

hr_attendance()

class hr_employee(osv.osv):
    _inherit = "hr.employee"
    _description = "Employee"

    def _state(self, cr, uid, ids, name, args, context=None):
        result = {}
        if not ids:
            return result
        for id in ids:
            result[id] = 'absent'
        cr.execute('SELECT hr_attendance.action, hr_attendance.employee_id \
                FROM ( \
                    SELECT MAX(name) AS name, employee_id \
                    FROM hr_attendance \
                    WHERE action in (\'sign_in\', \'sign_out\') \
                    GROUP BY employee_id \
                ) AS foo \
                LEFT JOIN hr_attendance \
                    ON (hr_attendance.employee_id = foo.employee_id \
                        AND hr_attendance.name = foo.name) \
                WHERE hr_attendance.employee_id IN %s',(tuple(ids),))
        for res in cr.fetchall():
            result[res[1]] = res[0] == 'sign_in' and 'present' or 'absent'
        return result

    _columns = {
       'state': fields.function(_state, method=True, type='selection', selection=[('absent', 'Absent'), ('present', 'Present')], string='Attendance'),
    }

    def _action_check(self, cr, uid, emp_id, dt=False, context=None):
        cr.execute('SELECT MAX(name) FROM hr_attendance WHERE employee_id=%s', (emp_id,))
        res = cr.fetchone()
        return not (res and (res[0]>=(dt or time.strftime('%Y-%m-%d %H:%M:%S'))))

    def attendance_action_change(self, cr, uid, ids, type='action', context=None, dt=False, *args):
        obj_attendance = self.pool.get('hr.attendance')
        id = False
        warning_sign = 'sign'
        res = {}

        #Special case when button calls this method: type=context
        if isinstance(type, dict):
            type = type.get('type','action')
        if type == 'sign_in':
            warning_sign = "Sign In"
        elif type == 'sign_out':
            warning_sign = "Sign Out"
        for emp in self.read(cr, uid, ids, ['id'], context=context):
            if not self._action_check(cr, uid, emp['id'], dt, context):
                raise osv.except_osv(_('Warning'), _('You tried to %s with a date anterior to another event !\nTry to contact the administrator to correct attendances.')%(warning_sign,))

            res = {'action': type, 'employee_id': emp['id']}
            if dt:
                res['name'] = dt
        id = obj_attendance.create(cr, uid, res, context=context)

        if type != 'action':
            return id
        return True

hr_employee()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
