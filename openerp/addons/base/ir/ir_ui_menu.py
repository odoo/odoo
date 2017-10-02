# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2012 OpenERP SA (<http://openerp.com>).
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

import base64
import operator
import re
import threading

import openerp.modules
from openerp.osv import fields, osv
from openerp import api, tools
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _

MENU_ITEM_SEPARATOR = "/"


class ir_ui_menu(osv.osv):
    _name = 'ir.ui.menu'

    def __init__(self, *args, **kwargs):
        cls = type(self)
        # by design, self._menu_cache is specific to the database
        cls._menu_cache_lock = threading.RLock()
        cls._menu_cache = {}
        super(ir_ui_menu, self).__init__(*args, **kwargs)
        self.pool.get('ir.model.access').register_cache_clearing_method(self._name, 'clear_cache')

    def clear_cache(self):
        with self._menu_cache_lock:
            # radical but this doesn't frequently happen
            if self._menu_cache:
                # Normally this is done by openerp.tools.ormcache
                # but since we do not use it, set it by ourself.
                self.pool._any_cache_cleared = True
            self._menu_cache.clear()
        self.load_menus_root._orig.clear_cache(self)
        self.load_menus._orig.clear_cache(self)

    @api.multi
    @api.returns('self')
    def _filter_visible_menus(self):
        """ Filter `self` to only keep the menu items that should be visible in
            the menu hierarchy of the current user.
            Uses a cache for speeding up the computation.
        """
        with self._menu_cache_lock:
            groups = self.env.user.groups_id

            # visibility is entirely based on the user's groups;
            # self._menu_cache[key] gives the ids of all visible menus
            key = frozenset(groups._ids)
            if key in self._menu_cache:
                visible = self.browse(self._menu_cache[key])

            else:
                # retrieve all menus, and determine which ones are visible
                context = {'ir.ui.menu.full_list': True}
                menus = self.with_context(context).search([])

                # first discard all menus with groups the user does not have
                menus = menus.filtered(
                    lambda menu: not menu.groups_id or menu.groups_id & groups)

                # take apart menus that have an action
                action_menus = menus.filtered('action')
                folder_menus = menus - action_menus
                visible = self.browse()

                # process action menus, check whether their action is allowed
                access = self.env['ir.model.access']
                model_fname = {
                    'ir.actions.act_window': 'res_model',
                    'ir.actions.report.xml': 'model',
                    'ir.actions.wizard': 'model',
                    'ir.actions.server': 'model_id',
                }
                for menu in action_menus:
                    fname = model_fname.get(menu.action._name)
                    if not fname or not menu.action[fname] or \
                            access.check(menu.action[fname], 'read', False):
                        # make menu visible, and its folder ancestors, too
                        visible += menu
                        menu = menu.parent_id
                        while menu and menu in folder_menus and menu not in visible:
                            visible += menu
                            menu = menu.parent_id

                self._menu_cache[key] = visible._ids

            return self.filtered(lambda menu: menu in visible)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}

        ids = super(ir_ui_menu, self).search(cr, uid, args, offset=0,
            limit=None, order=order, context=context, count=False)

        if not ids:
            if count:
                return 0
            return []

        # menu filtering is done only on main menu tree, not other menu lists
        if context.get('ir.ui.menu.full_list'):
            result = ids
        else:
            result = self._filter_visible_menus(cr, uid, ids, context=context)

        if offset:
            result = result[long(offset):]
        if limit:
            result = result[:long(limit)]

        if count:
            return len(result)
        return result

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for id in ids:
            elmt = self.browse(cr, uid, id, context=context)
            res.append((id, self._get_one_full_name(elmt)))
        return res

    def _get_full_name(self, cr, uid, ids, name=None, args=None, context=None):
        if context is None:
            context = {}
        res = {}
        for elmt in self.browse(cr, uid, ids, context=context):
            res[elmt.id] = self._get_one_full_name(elmt)
        return res

    def _get_one_full_name(self, elmt, level=6):
        if level<=0:
            return '...'
        if elmt.parent_id:
            parent_path = self._get_one_full_name(elmt.parent_id, level-1) + MENU_ITEM_SEPARATOR
        else:
            parent_path = ''
        return parent_path + elmt.name

    def create(self, cr, uid, values, context=None):
        self.clear_cache()
        return super(ir_ui_menu, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        self.clear_cache()
        return super(ir_ui_menu, self).write(cr, uid, ids, values, context=context)

    def unlink(self, cr, uid, ids, context=None):
        # Detach children and promote them to top-level, because it would be unwise to
        # cascade-delete submenus blindly. We also can't use ondelete=set null because
        # that is not supported when _parent_store is used (would silently corrupt it).
        # TODO: ideally we should move them under a generic "Orphans" menu somewhere?
        if isinstance(ids, (int, long)):
            ids = [ids]
        local_context = dict(context or {})
        local_context['ir.ui.menu.full_list'] = True
        direct_children_ids = self.search(cr, uid, [('parent_id', 'in', ids)], context=local_context)
        if direct_children_ids:
            self.write(cr, uid, direct_children_ids, {'parent_id': False})

        result = super(ir_ui_menu, self).unlink(cr, uid, ids, context=context)
        self.clear_cache()
        return result

    def copy(self, cr, uid, id, default=None, context=None):
        ir_values_obj = self.pool.get('ir.values')
        res = super(ir_ui_menu, self).copy(cr, uid, id, default=default, context=context)
        datas=self.read(cr,uid,[res],['name'])[0]
        rex=re.compile('\([0-9]+\)')
        concat=rex.findall(datas['name'])
        if concat:
            next_num=int(concat[0])+1
            datas['name']=rex.sub(('(%d)'%next_num),datas['name'])
        else:
            datas['name'] += '(1)'
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
        ir_values_obj = self.pool.get('ir.values')
        value_ids = ir_values_obj.search(cursor, user, [
            ('model', '=', self._name), ('key', '=', 'action'),
            ('key2', '=', 'tree_but_open'), ('res_id', 'in', ids)],
            context=context)
        values_action = {}
        for value in ir_values_obj.browse(cursor, user, value_ids, context=context):
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
        ir_values_obj = self.pool.get('ir.values')
        values_ids = ir_values_obj.search(cursor, user, [
            ('model', '=', self._name), ('key', '=', 'action'),
            ('key2', '=', 'tree_but_open'), ('res_id', '=', menu_id)],
            context=context)
        if value and values_ids:
            ir_values_obj.write(cursor, user, values_ids, {'value': value}, context=ctx)
        elif value:
            # no values_ids, create binding
            ir_values_obj.create(cursor, user, {
                'name': 'Menuitem',
                'model': self._name,
                'value': value,
                'key': 'action',
                'key2': 'tree_but_open',
                'res_id': menu_id,
                }, context=ctx)
        elif values_ids:
            # value is False, remove existing binding
            ir_values_obj.unlink(cursor, user, values_ids, context=ctx)

    def _get_icon_pict(self, cr, uid, ids, name, args, context):
        res = {}
        for m in self.browse(cr, uid, ids, context=context):
            res[m.id] = ('stock', (m.icon,'ICON_SIZE_MENU'))
        return res

    def onchange_icon(self, cr, uid, ids, icon):
        if not icon:
            return {}
        return {'type': {'icon_pict': 'picture'}, 'value': {'icon_pict': ('stock', (icon,'ICON_SIZE_MENU'))}}

    def read_image(self, path):
        if not path:
            return False
        path_info = path.split(',')
        icon_path = openerp.modules.get_module_resource(path_info[0],path_info[1])
        icon_image = False
        if icon_path:
            try:
                icon_file = tools.file_open(icon_path,'rb')
                icon_image = base64.encodestring(icon_file.read())
            finally:
                icon_file.close()
        return icon_image

    def _get_image_icon(self, cr, uid, ids, names, args, context=None):
        res = {}
        for menu in self.browse(cr, uid, ids, context=context):
            res[menu.id] = r = {}
            for fn in names:
                fn_src = fn[:-5]    # remove _data
                r[fn] = self.read_image(menu[fn_src])

        return res

    def _get_needaction_enabled(self, cr, uid, ids, field_names, args, context=None):
        """ needaction_enabled: tell whether the menu has a related action
            that uses the needaction mechanism. """
        res = dict.fromkeys(ids, False)
        for menu in self.browse(cr, uid, ids, context=context):
            if menu.action and menu.action.type in ('ir.actions.act_window', 'ir.actions.client') and menu.action.res_model:
                if menu.action.res_model in self.pool and self.pool[menu.action.res_model]._needaction:
                    res[menu.id] = True
        return res

    def get_needaction_data(self, cr, uid, ids, context=None):
        """ Return for each menu entry of ids :
            - if it uses the needaction mechanism (needaction_enabled)
            - the needaction counter of the related action, taking into account
              the action domain
        """
        if context is None:
            context = {}
        res = {}
        menu_ids = set()
        for menu in self.browse(cr, uid, ids, context=context):
            menu_ids.add(menu.id)
            ctx = None
            if menu.action and menu.action.type in ('ir.actions.act_window', 'ir.actions.client') and menu.action.context:
                try:
                    # use magical UnquoteEvalContext to ignore undefined client-side variables such as `active_id`
                    eval_ctx = tools.UnquoteEvalContext(**context)
                    ctx = eval(menu.action.context, locals_dict=eval_ctx, nocopy=True) or None
                except Exception:
                    # if the eval still fails for some reason, we'll simply skip this menu
                    pass
            menu_ref = ctx and ctx.get('needaction_menu_ref')
            if menu_ref:
                if not isinstance(menu_ref, list):
                    menu_ref = [menu_ref]
                model_data_obj = self.pool.get('ir.model.data')
                for menu_data in menu_ref:
                    try:
                        model, id = model_data_obj.get_object_reference(cr, uid, menu_data.split('.')[0], menu_data.split('.')[1])
                        if (model == 'ir.ui.menu'):
                            menu_ids.add(id)
                    except Exception:
                        pass

        menu_ids = list(menu_ids)

        for menu in self.browse(cr, uid, menu_ids, context=context):
            res[menu.id] = {
                'needaction_enabled': False,
                'needaction_counter': False,
            }
            if menu.action and menu.action.type in ('ir.actions.act_window', 'ir.actions.client') and menu.action.res_model:
                if menu.action.res_model in self.pool:
                    obj = self.pool[menu.action.res_model]
                    if obj._needaction:
                        if menu.action.type == 'ir.actions.act_window':
                            dom = menu.action.domain and eval(menu.action.domain, {'uid': uid}) or []
                        else:
                            dom = eval(menu.action.params_store or '{}', {'uid': uid}).get('domain')
                        res[menu.id]['needaction_enabled'] = obj._needaction
                        ctx = context
                        if menu.action.context:
                            try:
                                # use magical UnquoteEvalContext to ignore undefined client-side variables such as `active_id`
                                eval_ctx = tools.UnquoteEvalContext(**context)
                                ctx = eval(menu.action.context, locals_dict=eval_ctx, nocopy=True) or None
                            except Exception:
                                pass
                        res[menu.id]['needaction_counter'] = obj._needaction_count(cr, uid, dom, context=ctx)
        return res

    def get_user_roots(self, cr, uid, context=None):
        """ Return all root menu ids visible for the user.

        :return: the root menu ids
        :rtype: list(int)
        """
        menu_domain = [('parent_id', '=', False)]
        return self.search(cr, uid, menu_domain, context=context)

    @api.cr_uid_context
    @tools.ormcache_context(accepted_keys=('lang',))
    def load_menus_root(self, cr, uid, context=None):
        fields = ['name', 'sequence', 'parent_id', 'action']
        menu_root_ids = self.get_user_roots(cr, uid, context=context)
        menu_roots = self.read(cr, uid, menu_root_ids, fields, context=context) if menu_root_ids else []
        return {
            'id': False,
            'name': 'root',
            'parent_id': [-1, ''],
            'children': menu_roots,
            'all_menu_ids': menu_root_ids,
        }


    @api.cr_uid_context
    @tools.ormcache_context(accepted_keys=('lang',))
    def load_menus(self, cr, uid, context=None):
        """ Loads all menu items (all applications and their sub-menus).

        :return: the menu root
        :rtype: dict('children': menu_nodes)
        """
        fields = ['name', 'sequence', 'parent_id', 'action']
        menu_root_ids = self.get_user_roots(cr, uid, context=context)
        menu_roots = self.read(cr, uid, menu_root_ids, fields, context=context) if menu_root_ids else []
        menu_root = {
            'id': False,
            'name': 'root',
            'parent_id': [-1, ''],
            'children': menu_roots,
            'all_menu_ids': menu_root_ids,
        }
        if not menu_roots:
            return menu_root

        # menus are loaded fully unlike a regular tree view, cause there are a
        # limited number of items (752 when all 6.1 addons are installed)
        menu_ids = self.search(cr, uid, [('id', 'child_of', menu_root_ids)], 0, False, False, context=context)
        menu_items = self.read(cr, uid, menu_ids, fields, context=context)
        # adds roots at the end of the sequence, so that they will overwrite
        # equivalent menu items from full menu read when put into id:item
        # mapping, resulting in children being correctly set on the roots.
        menu_items.extend(menu_roots)
        menu_root['all_menu_ids'] = menu_ids  # includes menu_root_ids!

        # make a tree using parent_id
        menu_items_map = dict(
            (menu_item["id"], menu_item) for menu_item in menu_items)
        for menu_item in menu_items:
            if menu_item['parent_id']:
                parent = menu_item['parent_id'][0]
            else:
                parent = False
            if parent in menu_items_map:
                menu_items_map[parent].setdefault(
                    'children', []).append(menu_item)

        # sort by sequence a tree using parent_id
        for menu_item in menu_items:
            menu_item.setdefault('children', []).sort(
                key=operator.itemgetter('sequence'))

        return menu_root

    _columns = {
        'name': fields.char('Menu', required=True, translate=True),
        'sequence': fields.integer('Sequence'),
        'child_id': fields.one2many('ir.ui.menu', 'parent_id', 'Child IDs'),
        'parent_id': fields.many2one('ir.ui.menu', 'Parent Menu', select=True, ondelete="restrict"),
        'parent_left': fields.integer('Parent Left', select=True),
        'parent_right': fields.integer('Parent Right', select=True),
        'groups_id': fields.many2many('res.groups', 'ir_ui_menu_group_rel',
            'menu_id', 'gid', 'Groups', help="If you have groups, the visibility of this menu will be based on these groups. "\
                "If this field is empty, Odoo will compute visibility based on the related object's read access."),
        'complete_name': fields.function(_get_full_name,
            string='Full Path', type='char', size=128),
        'icon': fields.selection(tools.icons, 'Icon', size=64),
        'icon_pict': fields.function(_get_icon_pict, type='char', size=32),
        'web_icon': fields.char('Web Icon File'),
        'web_icon_hover': fields.char('Web Icon File (hover)'),
        'web_icon_data': fields.function(_get_image_icon, string='Web Icon Image', type='binary', readonly=True, store=True, multi='icon'),
        'web_icon_hover_data': fields.function(_get_image_icon, string='Web Icon Image (hover)', type='binary', readonly=True, store=True, multi='icon'),
        'needaction_enabled': fields.function(_get_needaction_enabled,
            type='boolean',
            store=True,
            string='Target model uses the need action mechanism',
            help='If the menu entry action is an act_window action, and if this action is related to a model that uses the need_action mechanism, this field is set to true. Otherwise, it is false.'),
        'action': fields.function(_action, fnct_inv=_action_inv,
            type='reference', string='Action', size=21,
            selection=[
                ('ir.actions.report.xml', 'ir.actions.report.xml'),
                ('ir.actions.act_window', 'ir.actions.act_window'),
                ('ir.actions.wizard', 'ir.actions.wizard'),
                ('ir.actions.act_url', 'ir.actions.act_url'),
                ('ir.actions.server', 'ir.actions.server'),
                ('ir.actions.client', 'ir.actions.client'),
            ]),
    }

    def _rec_message(self, cr, uid, ids, context=None):
        return _('Error ! You can not create recursive Menu.')

    _constraints = [
        (osv.osv._check_recursion, _rec_message, ['parent_id'])
    ]
    _defaults = {
        'icon': 'STOCK_OPEN',
        'icon_pict': ('stock', ('STOCK_OPEN', 'ICON_SIZE_MENU')),
        'sequence': 10,
    }
    _order = "sequence,id"
    _parent_store = True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
