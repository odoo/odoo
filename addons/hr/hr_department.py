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

from osv import fields, osv
import tools

class hr_department(osv.osv):
    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not len(ids):
            return []
        reads = self.read(cr, uid, ids, ['name','parent_id'], context=context)
        res = []
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1]+' / '+name
            res.append((record['id'], name))
        return res

    def _dept_name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        if context is None:
            context = {}
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    _name = "hr.department"
    _columns = {
        'name': fields.char('Department Name', size=64, required=True),
        'complete_name': fields.function(_dept_name_get_fnc, method=True, type="char", string='Name'),
        'company_id': fields.many2one('res.company', 'Company', select=True, required=False),
        'parent_id': fields.many2one('hr.department', 'Parent Department', select=True),
        'child_ids': fields.one2many('hr.department', 'parent_id', 'Child Departments'),
        'note': fields.text('Note'),
    }

    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'hr.department', context=c),
                }

    def _get_members(self, cr, uid, context=None):
        if context is None:
            context = {}
        mids = self.search(cr, uid, [('manager_id', '=', uid)], context=context)
        result = {uid: 1}
        for m in self.browse(cr, uid, mids, context=context):
            for user in m.member_ids:
                result[user.id] = 1
        return result.keys()

    def _check_recursion(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        level = 100
        while len(ids):
            cr.execute('select distinct parent_id from hr_department where id IN %s',(tuple(ids),))
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

    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        if context is None:
            context = {}
        obj_dept = self.pool.get('hr.department')
        select = ids
        if isinstance(ids, (int, long)):
            select = [ids]
        res = super(ir_action_window, self).read(cr, uid, select, fields=fields, context=context, load=load)
        for r in res:
            mystring = 'department_users_get()'
            if mystring in (r.get('domain', '[]') or ''):
                r['domain'] = r['domain'].replace(mystring, str(obj_dept._get_members(cr, uid)))
        if isinstance(ids, (int, long)):
            if res:
                return res[0]
            else:
                return False
        return res

ir_action_window()

class res_users(osv.osv):
    _inherit = 'res.users'
    _description = 'User'

    def _parent_compute(self, cr, uid, ids, name, args, context=None):
        if context is None:
            context = {}
        result = {}
        obj_dept = self.pool.get('hr.department')
        for user_id in ids:
            emp_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', user_id)], context=context)
            cr.execute('SELECT emp.department_id FROM hr_employee AS emp \
                        JOIN resource_resource AS res ON res.id = emp.resource_id \
                        JOIN hr_department as dept ON dept.id = emp.department_id \
                        WHERE res.user_id = %s AND emp.department_id IS NOT NULL AND dept.manager_id IS NOT NULL', (user_id,))
            ids_dept = [x[0] for x in cr.fetchall()]
            parent_ids = []
            if ids_dept:
                data_dept = obj_dept.read(cr, uid, ids_dept, ['manager_id'], context=context)
                parent_ids = map(lambda x: x['manager_id'][0], data_dept)
                cr.execute('SELECT res.user_id FROM hr_employee AS emp JOIN resource_resource AS res ON res.id=emp.resource_id \
                        WHERE emp.id IN %s AND res.user_id IS NOT NULL', (tuple(parent_ids),))
                parent_ids = [x[0] for x in cr.fetchall()]
            result[user_id] = parent_ids
        return result

    def _parent_search(self, cr, uid, obj, name, args, context=None):
        if context is None:
            context = {}
        parent = []
        for arg in args:
            if arg[0] == 'parent_id':
                parent = arg[2]
        child_ids = self._child_compute(cr, uid, parent, name, args, context=context)
        if not child_ids:
            return [('id', 'in', [0])]
        return [('id', 'in', child_ids.get(uid, []))]

    def _child_compute(self, cr, uid, ids, name, args, context=None):
        if context is None:
            context = {}
        obj_dept = self.pool.get('hr.department')
        obj_user = self.pool.get('res.users')
        result = {}
        for user_id in ids:
            child_ids = []
            cr.execute('SELECT dept.id FROM hr_department AS dept \
                        LEFT JOIN hr_employee AS emp ON dept.manager_id = emp.id \
                        WHERE emp.id IN \
                            (SELECT emp.id FROM hr_employee \
                                JOIN resource_resource r ON r.id = emp.resource_id WHERE r.user_id=' + str(user_id) + ') ')
            mgnt_dept_ids = [x[0] for x in cr.fetchall()]
            ids_dept = obj_dept.search(cr, uid, [('id', 'child_of', mgnt_dept_ids)], context=context)
            if ids_dept:
                data_dept = obj_dept.read(cr, uid, ids_dept, ['member_ids'], context=context)
                childs = map(lambda x: x['member_ids'], data_dept)
                childs = tools.flatten(childs)
                childs = obj_user.search(cr, uid, [('id', 'in', childs),('active', '=', True)], context=context)
                if user_id in childs:
                    childs.remove(user_id)
                child_ids.extend(tools.flatten(childs))
                set = {}
                map(set.__setitem__, child_ids, [])
                child_ids = set.keys()
            result[user_id] = child_ids
        return result

    def _child_search(self, cr, uid, obj, name, args, context=None):
        if context is None:
            context = {}
        parent = []
        for arg in args:
            if arg[0] == 'child_ids':
                parent = arg[2]
        child_ids = self._child_compute(cr, uid, parent, name, args, context=context)
        if not child_ids:
            return [('id', 'in', [0])]
        return [('id', 'in', child_ids.get(uid, []))]

    _columns = {
        'parent_id': fields.function(_parent_compute, relation='res.users', fnct_search=_parent_search, method=True, string="Managers", type='many2many'),
        'child_ids': fields.function(_child_compute, relation='res.users', fnct_search=_child_search, method=True, string="Subordinates", type='many2many'),
        'context_department_id': fields.many2one('hr.department', 'Departments'),
    }

res_users()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: