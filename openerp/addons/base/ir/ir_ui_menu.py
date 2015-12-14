# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import operator
import re

import odoo
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools.safe_eval import safe_eval as eval

MENU_ITEM_SEPARATOR = "/"


class IrUiMenu(models.Model):
    _name = 'ir.ui.menu'
    _order = "sequence,id"
    _parent_store = True

    def __init__(self, *args, **kwargs):
        super(IrUiMenu, self).__init__(*args, **kwargs)
        self.pool['ir.model.access'].register_cache_clearing_method(self._name, 'clear_caches')

    name = fields.Char(string='Menu', required=True, translate=True)
    sequence = fields.Integer(default=10)
    child_id = fields.One2many('ir.ui.menu', 'parent_id', string='Child IDs')
    parent_id = fields.Many2one('ir.ui.menu', string='Parent Menu', index=True, ondelete="restrict")
    parent_left = fields.Integer(index=True)
    parent_right = fields.Integer(index=True)
    groups_id = fields.Many2many('res.groups', 'ir_ui_menu_group_rel',
                                 'menu_id', 'gid', string='Groups',
                                 help="If you have groups, the visibility of this menu will be based on these groups. "\
                                      "If this field is empty, Odoo will compute visibility based on the related object's read access.")
    complete_name = fields.Char(compute='_get_full_name', string='Full Path')
    web_icon = fields.Char(string='Web Icon File')
    action = fields.Reference(selection=[('ir.actions.report.xml', 'ir.actions.report.xml'),
                                         ('ir.actions.act_window', 'ir.actions.act_window'),
                                         ('ir.actions.act_url', 'ir.actions.act_url'),
                                         ('ir.actions.server', 'ir.actions.server'),
                                         ('ir.actions.client', 'ir.actions.client')])

    web_icon_data = fields.Binary(string='Web Icon Image', compute="_compute_web_icon", store=True, attachment=True)

    @api.depends('web_icon')
    def _compute_web_icon(self):
        for menu in self:
            menu.web_icon_data = self.read_image(menu.web_icon)

    def read_image(self, path):
        if not path:
            return False
        path_info = path.split(',')
        icon_path = odoo.modules.get_module_resource(path_info[0], path_info[1])
        icon_image = False
        if icon_path:
            try:
                icon_file = tools.file_open(icon_path, 'rb')
                icon_image = base64.encodestring(icon_file.read())
            finally:
                icon_file.close()
        return icon_image

    @api.depends('complete_name')
    def _get_full_name(self):
        for element in self:
            element.complete_name = self._get_one_full_name(element)

    def _get_one_full_name(self, elmt, level=6):
        if level <= 0:
            return '...'
        if elmt.parent_id:
            parent_path = self._get_one_full_name(elmt.parent_id, level-1) + MENU_ITEM_SEPARATOR
        else:
            parent_path = ''
        return parent_path + elmt.name

    @api.model
    @tools.ormcache('frozenset(self.env.user.groups_id.ids)', 'debug')
    def _visible_menu_ids(self, debug=False):
        """ Return the ids of the menu items visible to the user. """
        # retrieve all menus, and determine which ones are visible
        context = {'ir.ui.menu.full_list': True}
        menus = self.with_context(context).search([])

        groups = self.env.user.groups_id if debug else self.env.user.groups_id - self.env.ref('base.group_no_one')
        # first discard all menus with groups the user does not have
        menus = menus.filtered(
            lambda menu: not menu.groups_id or menu.groups_id & groups)

        # take apart menus that have an action
        action_menus = menus.filtered(lambda m: m.action and m.action.exists())
        folder_menus = menus - action_menus
        visible = self.browse()

        # process action menus, check whether their action is allowed
        access = self.env['ir.model.access']
        model_fname = {
            'ir.actions.act_window': 'res_model',
            'ir.actions.report.xml': 'model',
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

        return set(visible.ids)

    @api.multi
    @api.returns('self')
    def _filter_visible_menus(self):
        """ Filter `self` to only keep the menu items that should be visible in
            the menu hierarchy of the current user.
            Uses a cache for speeding up the computation.
        """
        visible_ids = self._visible_menu_ids(request.debug if request else False)
        return self.filtered(lambda menu: menu.id in visible_ids)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}

        ids = super(IrUiMenu, self).search(cr, uid, args, offset=0,
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

    @api.multi
    def name_get(self):
        res = []
        for element in self:
            res.append((element.id, self._get_one_full_name(element)))
        return res

    @api.model
    def create(self, values):
        self.clear_caches()
        return super(IrUiMenu, self).create(values)

    @api.multi
    def write(self, values):
        self.clear_caches()
        return super(IrUiMenu, self).write(values)

    @api.multi
    def unlink(self):
        # Detach children and promote them to top-level, because it would be unwise to
        # cascade-delete submenus blindly. We also can't use ondelete=set null because
        # that is not supported when _parent_store is used (would silently corrupt it).
        # TODO: ideally we should move them under a generic "Orphans" menu somewhere?
        local_context = dict(self.env.context or {})
        local_context['ir.ui.menu.full_list'] = True
        direct_children = self.with_context(local_context).search([('parent_id', 'in', self.ids)])
        if direct_children:
            direct_children.write({'parent_id': False})

        result = super(IrUiMenu, self).unlink()
        self.clear_caches()
        return result

    @api.multi
    def copy(self, default=None):
        res = super(IrUiMenu, self).copy(default=default)
        rex = re.compile('\([0-9]+\)')
        concat = rex.findall(res.name)
        if concat:
            next_num = int(concat[0])+1
            res.name = rex.sub(('(%d)' % next_num), res.name)
        else:
            res.name += '(1)'
        res.write({'name': res.name})
        return res

    @api.multi
    def get_needaction_data(self):
        """ Return for each menu entry of ids :
            - if it uses the needaction mechanism (needaction_enabled)
            - the needaction counter of the related action, taking into account
              the action domain
        """
        res = {}
        menu_ids = set()
        for menu in self:
            menu_ids.add(menu.id)
            ctx = None
            if menu.action and menu.action.type in ('ir.actions.act_window', 'ir.actions.client') and menu.action.context:
                try:
                    # use magical UnquoteEvalContext to ignore undefined client-side variables such as `active_id`
                    ctxt = dict(self.env.context or {})
                    eval_ctx = tools.UnquoteEvalContext(**ctxt)
                    ctx = eval(menu.action.context, locals_dict=eval_ctx, nocopy=True) or None
                except Exception:
                    # if the eval still fails for some reason, we'll simply skip this menu
                    pass
            menu_ref = ctx and ctx.get('needaction_menu_ref')
            if menu_ref:
                if not isinstance(menu_ref, list):
                    menu_ref = [menu_ref]
                model_data_obj = self.env['ir.model.data']
                for menu_data in menu_ref:
                    try:
                        model, model_id = model_data_obj.get_object_reference(menu_data.split('.')[0], menu_data.split('.')[1])
                        if (model == 'ir.ui.menu'):
                            menu_ids.add(model_id)
                    except Exception:
                        pass

        menu_ids = list(menu_ids)

        for menu in self:
            res[menu.id] = {
                'needaction_enabled': False,
                'needaction_counter': False,
            }
            if menu.action and menu.action.type in ('ir.actions.act_window', 'ir.actions.client') and menu.action.res_model:
                if menu.action.res_model in self.pool:
                    obj = self.env[menu.action.res_model]
                    if obj._needaction:
                        if menu.action.type == 'ir.actions.act_window':
                            eval_context = self.env['ir.actions.act_window']._get_eval_context()
                            dom = menu.action.domain and eval(menu.action.domain, eval_context) or []
                        else:
                            dom = eval(menu.action.params_store or '{}', {'uid': self.env.uid}).get('domain')
                        res[menu.id]['needaction_enabled'] = obj._needaction
                        res[menu.id]['needaction_counter'] = obj._needaction_count(dom)
        return res

    @api.model
    @api.returns('self')
    def get_user_roots(self):
        """ Return all root menu ids visible for the user.

        :return: the root menu ids
        :rtype: list(int)
        """
        return self.search([('parent_id', '=', False)])

    @api.cr_uid_context
    @tools.ormcache_context('uid', keys=('lang',))
    def load_menus_root(self, cr, uid, context=None):
        fields = ['name', 'sequence', 'parent_id', 'action', 'web_icon_data']
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
    @tools.ormcache_context('uid', 'debug', keys=('lang',))
    def load_menus(self, cr, uid, debug, context=None):
        """ Loads all menu items (all applications and their sub-menus).

        :return: the menu root
        :rtype: dict('children': menu_nodes)
        """
        fields = ['name', 'sequence', 'parent_id', 'action', 'web_icon_data']
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
