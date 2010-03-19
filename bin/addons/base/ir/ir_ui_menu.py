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

from osv import fields, osv
import re
import tools

def one_in(setA, setB):
    """Check the presence of an element of setA in setB
    """
    for x in setA:
        if x in setB:
            return True
    return False

def cond(C, X, Y):
    if C: return X
    return Y

class many2many_unique(fields.many2many):
    def set(self, cr, obj, id, name, values, user=None, context=None):
        if not values:
            return
        val = values[:]
        for act in values:
            if act[0]==4:
                cr.execute('SELECT * FROM '+self._rel+' \
                        WHERE '+self._id1+'=%s AND '+self._id2+'=%s', (id, act[1]))
                if cr.fetchall():
                    val.remove(act)
        return super(many2many_unique, self).set(cr, obj, id, name, val, user=user,
                context=context)


class ir_ui_menu(osv.osv):
    _name = 'ir.ui.menu'

    def __init__(self, *args, **kwargs):
        self._cache = {}
        r = super(ir_ui_menu, self).__init__(*args, **kwargs)
        self.pool.get('ir.model.access').register_cache_clearing_method(self._name, 'clear_cache')
        return r

    def __del__(self):
        self.pool.get('ir.model.access').unregister_cache_clearing_method(self._name, 'clear_cache')
        return super(ir_ui_menu, self).__del__()

    def clear_cache(self):
        # radical but this doesn't frequently happen
        self._cache = {}

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
               context=None, count=False):

        super_offset = cond(uid == 1, offset, 0)
        super_limit = cond(uid == 1, limit, None)
        super_count = cond(uid == 1, count, False)

        ids = super(ir_ui_menu, self).search(cr, uid, args, super_offset,
                                             super_limit, order,
                                             context=context, count=super_count)
        if uid == 1:
            return ids

        if not ids:
            if count:
                return 0
            return []

        modelaccess = self.pool.get('ir.model.access')
        user_groups = set(self.pool.get('res.users').read(cr, 1, uid, ['groups_id'])['groups_id'])
        result = []
        for menu in self.browse(cr, uid, ids):
            # this key works because user access rights are all based on user's groups (cfr ir_model_access.check)
            key = (cr.dbname, menu.id, tuple(user_groups))
            if key in self._cache:
                if self._cache[key]:
                    result.append(menu.id)
                continue

            self._cache[key] = False
            if menu.groups_id:
                restrict_to_groups = [g.id for g in menu.groups_id]
                if not user_groups.intersection(restrict_to_groups):
                    continue
                result.append(menu.id)
                self._cache[key] = True
                continue

            if menu.action:
                # we check if the user has access to the action of the menu
                m, oid = menu.action.split(',', 1)
                data = self.pool.get(m).browse(cr, 1, int(oid))

                if data:
                    model_field = { 'ir.actions.act_window':    'res_model',
                                    'ir.actions.report.custom': 'model',
                                    'ir.actions.report.xml':    'model',
                                    'ir.actions.wizard':        'model',
                                    'ir.actions.server':        'model_id',
                                  }

                    field = model_field.get(m)
                    if field and data[field]:
                        if not modelaccess.check(cr, uid, data[field], raise_exception=False):
                            continue
            else:
                # if there is no action, it's a 'folder' menu
                if not menu.child_id:
                    # not displayed if there is no children 
                    continue

            result.append(menu.id)
            self._cache[key] = True

        if offset:
            result = result[long(offset):]
        if limit:
            result = result[:long(limit)]

        if count:
            return len(result)
        return result

    def _get_full_name(self, cr, uid, ids, name, args, context):
        res = {}
        for m in self.browse(cr, uid, ids, context=context):
            res[m.id] = self._get_one_full_name(m)
        return res

    def _get_one_full_name(self, menu, level=6):
        if level<=0:
            return '...'
        if menu.parent_id:
            parent_path = self._get_one_full_name(menu.parent_id, level-1) + "/"
        else:
            parent_path = ''
        return parent_path + menu.name

    def write(self, *args, **kwargs):
        self.clear_cache()
        return super(ir_ui_menu, self).write(*args, **kwargs)

    def unlink(self, *args, **kwargs):
        self.clear_cache()
        return super(ir_ui_menu, self).unlink(*args, **kwargs)

    def copy(self, cr, uid, id, default=None, context=None):
        ir_values_obj = self.pool.get('ir.values')
        res = super(ir_ui_menu, self).copy(cr, uid, id, context=context)
        datas=self.read(cr,uid,[res],['name'])[0]
        rex=re.compile('\([0-9]+\)')
        concat=rex.findall(datas['name'])
        if concat:
            next_num=eval(concat[0])+1
            datas['name']=rex.sub(('(%d)'%next_num),datas['name'])
        else:
            datas['name']=datas['name']+'(1)'
        self.write(cr,uid,[res],{'name':datas['name']})
        ids = ir_values_obj.search(cr, uid, [
            ('model', '=', 'ir.ui.menu'),
            ('res_id', '=', id),
            ])
        for iv in ir_values_obj.browse(cr, uid, ids):
            ir_values_obj.copy(cr, uid, iv.id, default={'res_id': res},
                               context=context)
        return res

    def _action(self, cursor, user, ids, name, arg, context=None):
        res = {}
        values_obj = self.pool.get('ir.values')
        value_ids = values_obj.search(cursor, user, [
            ('model', '=', self._name), ('key', '=', 'action'),
            ('key2', '=', 'tree_but_open'), ('res_id', 'in', ids)],
            context=context)
        values_action = {}
        for value in values_obj.browse(cursor, user, value_ids, context=context):
            values_action[value.res_id] = value.value
        for menu_id in ids:
            res[menu_id] = values_action.get(menu_id, False)
        return res

    def _action_inv(self, cursor, user, menu_id, name, value, arg, context=None):
        if context is None:
            context = {}
        ctx = context.copy()
        if self.CONCURRENCY_CHECK_FIELD in ctx:
            del ctx[self.CONCURRENCY_CHECK_FIELD]
        values_obj = self.pool.get('ir.values')
        values_ids = values_obj.search(cursor, user, [
            ('model', '=', self._name), ('key', '=', 'action'),
            ('key2', '=', 'tree_but_open'), ('res_id', '=', menu_id)],
            context=context)
        if values_ids:
            values_obj.write(cursor, user, values_ids[0], {'value': value},
                    context=ctx)
        elif ctx:
            values_obj.create(cursor, user, {
                'name': 'Menuitem',
                'model': self._name,
                'value': value,
                'object': True,
                'key': 'action',
                'key2': 'tree_but_open',
                'res_id': menu_id,
                }, context=ctx)

    def _get_icon_pict(self, cr, uid, ids, name, args, context):
        res = {}
        for m in self.browse(cr, uid, ids, context=context):
            res[m.id] = ('stock', (m.icon,'ICON_SIZE_MENU'))
        return res

    def onchange_icon(self, cr, uid, ids, icon):
        if not icon:
            return {}
        return {'type': {'icon_pict': 'picture'}, 'value': {'icon_pict': ('stock', (icon,'ICON_SIZE_MENU'))}}

    _columns = {
        'name': fields.char('Menu', size=64, required=True, translate=True),
        'sequence': fields.integer('Sequence'),
        'child_id' : fields.one2many('ir.ui.menu', 'parent_id','Child IDs'),
        'parent_id': fields.many2one('ir.ui.menu', 'Parent Menu', select=True),
        'groups_id': many2many_unique('res.groups', 'ir_ui_menu_group_rel',
            'menu_id', 'gid', 'Groups', help="If you have groups, the visibility of this menu will be based on these groups. "\
                "If this field is empty, Open ERP will compute visibility based on the related object's read access."),
        'complete_name': fields.function(_get_full_name, method=True,
            string='Complete Name', type='char', size=128),
        'icon': fields.selection(tools.icons, 'Icon', size=64),
        'icon_pict': fields.function(_get_icon_pict, method=True, type='char', size=32),
        'action': fields.function(_action, fnct_inv=_action_inv,
            method=True, type='reference', string='Action',
            selection=[
                ('ir.actions.report.custom', 'ir.actions.report.custom'),
                ('ir.actions.report.xml', 'ir.actions.report.xml'),
                ('ir.actions.act_window', 'ir.actions.act_window'),
                ('ir.actions.wizard', 'ir.actions.wizard'),
                ('ir.actions.url', 'ir.actions.url'),
                ('ir.actions.server', 'ir.actions.server'),
            ]),
    }
    _defaults = {
        'icon' : lambda *a: 'STOCK_OPEN',
        'icon_pict': lambda *a: ('stock', ('STOCK_OPEN','ICON_SIZE_MENU')),
        'sequence' : lambda *a: 10
    }
    _order = "sequence,id"
ir_ui_menu()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

