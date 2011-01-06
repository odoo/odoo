# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields,osv
import tools

class hr_department(osv.osv):
    _name = "hr.department"
    _columns = {
        'name': fields.char('Department Name', size=64, required=True),
        'company_id': fields.many2one('res.company', 'Company', select=True, required=True),
        'parent_id': fields.many2one('hr.department', 'Parent Department', select=True),
        'child_ids': fields.one2many('hr.department', 'parent_id', 'Child Departments'),
        'note': fields.text('Note'),
        'manager_id': fields.many2one('res.users', 'Manager', required=True),
        'member_ids': fields.many2many('res.users', 'hr_department_user_rel', 'department_id', 'user_id', 'Members'),
    }
    def _get_members(self,cr, uid, context={}):
        mids = self.search(cr, uid, [('manager_id','=',uid)])
        result = {uid:1}
        for m in self.browse(cr, uid, mids, context):
            for user in m.member_ids:
                result[user.id] = 1
        return result.keys()
    def _check_recursion(self, cr, uid, ids):
        level = 100
        while len(ids):
            cr.execute('SELECT DISTINCT parent_id FROM hr_department '\
                       'WHERE id IN %s', (tuple(ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    _constraints = [
        (_check_recursion, 'Error! You can not create recursive departments.', ['parent_id'])
    ]

hr_department()


class ir_action_window(osv.osv):
    _inherit = 'ir.actions.act_window'

    def read(self, cr, uid, ids, fields=None, context=None,
            load='_classic_read'):
        select = ids
        if isinstance(ids, (int, long)):
            select = [ids]
        res = super(ir_action_window, self).read(cr, uid, select, fields=fields,
                context=context, load=load)
        for r in res:
            mystring = 'department_users_get()'
            if mystring in (r.get('domain', '[]') or ''):
                r['domain'] = r['domain'].replace(mystring, str(
                    self.pool.get('hr.department')._get_members(cr, uid)))
        if isinstance(ids, (int, long)):
            if res:
                return res[0]
            else:
                return False
        return res

ir_action_window()

class res_users(osv.osv):
    _inherit = 'res.users'
    _description = 'res.users'

    def _parent_compute(self, cr, uid, ids, name, arg, context={}):
        result = {}
        obj_dept = self.pool.get('hr.department')
        for id in ids:
            ids_dept = obj_dept.search(cr, uid, [('member_ids', 'in', [id])])
            parent_ids = []
            if ids_dept:
                data_dept = obj_dept.read(cr, uid, ids_dept, ['manager_id'])
                parent_ids = map(lambda x: x['manager_id'][0], data_dept)
            result[id] = parent_ids
        return result

    def _child_compute(self, cr, uid, ids):
        obj_dept = self.pool.get('hr.department')
        child_ids = []
        for id in ids:
            ids_dept = obj_dept.search(cr, uid, [('manager_id', '=', id)])
            if ids_dept:
                data_dept = obj_dept.read(cr, uid, ids_dept, ['member_ids'])
                childs = map(lambda x: x['member_ids'], data_dept)
                childs = tools.flatten(childs)
                if id in childs:
                    childs.remove(id)
                child_ids.extend(tools.flatten(childs))
        return child_ids

    def _parent_search(self, cr, uid, obj, name, args, context):
        parent = []
        for arg in args:
            if arg[0] == 'parent_id':
                parent = arg[2]
        child_ids = self._child_compute(cr, uid, parent)
        if not child_ids:
            return [('id', 'in', [0])]
        return [('id', 'in', child_ids)]

    _columns = {
        'parent_id': fields.function(_parent_compute, relation='res.users',fnct_search=_parent_search, method=True, string="Parent Users", type='many2many'),
               }

res_users()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
