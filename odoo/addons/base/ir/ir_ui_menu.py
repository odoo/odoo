# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import operator
import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.modules import get_module_resource
from odoo.tools.safe_eval import safe_eval

MENU_ITEM_SEPARATOR = "/"
NUMBER_PARENS = re.compile(r"\(([0-9]+)\)")


class IrUiMenu(models.Model):
    _name = 'ir.ui.menu'
    _order = "sequence,id"
    _parent_store = True

    def __init__(self, *args, **kwargs):
        super(IrUiMenu, self).__init__(*args, **kwargs)
        self.pool['ir.model.access'].register_cache_clearing_method(self._name, 'clear_caches')

    name = fields.Char(string='Menu', required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    child_id = fields.One2many('ir.ui.menu', 'parent_id', string='Child IDs')
    parent_id = fields.Many2one('ir.ui.menu', string='Parent Menu', index=True, ondelete="restrict")
    parent_left = fields.Integer(index=True)
    parent_right = fields.Integer(index=True)
    groups_id = fields.Many2many('res.groups', 'ir_ui_menu_group_rel',
                                 'menu_id', 'gid', string='Groups',
                                 help="If you have groups, the visibility of this menu will be based on these groups. "\
                                      "If this field is empty, Odoo will compute visibility based on the related object's read access.")
    complete_name = fields.Char(compute='_compute_complete_name', string='Full Path')
    web_icon = fields.Char(string='Web Icon File')
    action = fields.Reference(selection=[('ir.actions.report', 'ir.actions.report'),
                                         ('ir.actions.act_window', 'ir.actions.act_window'),
                                         ('ir.actions.act_url', 'ir.actions.act_url'),
                                         ('ir.actions.server', 'ir.actions.server'),
                                         ('ir.actions.client', 'ir.actions.client')])

    web_icon_data = fields.Binary(string='Web Icon Image', attachment=True)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for menu in self:
            menu.complete_name = menu._get_full_name()

    def _get_full_name(self, level=6):
        """ Return the full name of ``self`` (up to a certain level). """
        if level <= 0:
            return '...'
        if self.parent_id:
            return self.parent_id._get_full_name(level - 1) + MENU_ITEM_SEPARATOR + (self.name or "")
        else:
            return self.name

    def read_image(self, path):
        if not path:
            return False
        path_info = path.split(',')
        icon_path = get_module_resource(path_info[0], path_info[1])
        icon_image = False
        if icon_path:
            with tools.file_open(icon_path, 'rb') as icon_file:
                icon_image = base64.encodestring(icon_file.read())
        return icon_image

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('Error! You cannot create recursive menus.'))

    @api.model
    @tools.ormcache('frozenset(self.env.user.groups_id.ids)', 'debug')
    def _visible_menu_ids(self, debug=False):
        """ Return the ids of the menu items visible to the user. """
        # retrieve all menus, and determine which ones are visible
        context = {'ir.ui.menu.full_list': True}
        menus = self.with_context(context).search([])

        groups = self.env.user.groups_id
        if not debug:
            groups = groups - self.env.ref('base.group_no_one')
        # first discard all menus with groups the user does not have
        menus = menus.filtered(
            lambda menu: not menu.groups_id or menu.groups_id & groups)

        # take apart menus that have an action
        action_menus = menus.filtered(lambda m: m.action and m.action.exists())
        folder_menus = menus - action_menus
        visible = self.browse()

        # process action menus, check whether their action is allowed
        access = self.env['ir.model.access']
        MODEL_GETTER = {
            'ir.actions.act_window': lambda action: action.res_model,
            'ir.actions.report': lambda action: action.model,
            'ir.actions.server': lambda action: action.model_id.model,
        }
        for menu in action_menus:
            get_model = MODEL_GETTER.get(menu.action._name)
            if not get_model or not get_model(menu.action) or \
                    access.check(get_model(menu.action), 'read', False):
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

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        menus = super(IrUiMenu, self).search(args, offset=0, limit=None, order=order, count=False)
        if menus:
            # menu filtering is done only on main menu tree, not other menu lists
            if not self._context.get('ir.ui.menu.full_list'):
                menus = menus._filter_visible_menus()
            if offset:
                menus = menus[offset:]
            if limit:
                menus = menus[:limit]
        return len(menus) if count else menus

    @api.multi
    def name_get(self):
        return [(menu.id, menu._get_full_name()) for menu in self]

    @api.model
    def create(self, values):
        self.clear_caches()
        if 'web_icon' in values:
            values['web_icon_data'] = self._compute_web_icon_data(values.get('web_icon'))
        return super(IrUiMenu, self).create(values)

    @api.multi
    def write(self, values):
        self.clear_caches()
        if 'web_icon' in values:
            values['web_icon_data'] = self._compute_web_icon_data(values.get('web_icon'))
        return super(IrUiMenu, self).write(values)

    def _compute_web_icon_data(self, web_icon):
        """ Returns the image associated to `web_icon`.
            `web_icon` can either be:
              - an image icon [module, path]
              - a built icon [icon_class, icon_color, background_color]
            and it only has to call `read_image` if it's an image.
        """
        if web_icon and len(web_icon.split(',')) == 2:
            return self.read_image(web_icon)

    @api.multi
    def unlink(self):
        # Detach children and promote them to top-level, because it would be unwise to
        # cascade-delete submenus blindly. We also can't use ondelete=set null because
        # that is not supported when _parent_store is used (would silently corrupt it).
        # TODO: ideally we should move them under a generic "Orphans" menu somewhere?
        extra = {'ir.ui.menu.full_list': True}
        direct_children = self.with_context(**extra).search([('parent_id', 'in', self.ids)])
        direct_children.write({'parent_id': False})

        self.clear_caches()
        return super(IrUiMenu, self).unlink()

    @api.multi
    def copy(self, default=None):
        record = super(IrUiMenu, self).copy(default=default)
        match = NUMBER_PARENS.search(record.name)
        if match:
            next_num = int(match.group(1)) + 1
            record.name = NUMBER_PARENS.sub('(%d)' % next_num, record.name)
        else:
            record.name = record.name + '(1)'
        return record

    @api.model
    @api.returns('self')
    def get_user_roots(self):
        """ Return all root menu ids visible for the user.

        :return: the root menu ids
        :rtype: list(int)
        """
        return self.search([('parent_id', '=', False)])

    @api.model
    @tools.ormcache_context('self._uid', keys=('lang',))
    def load_menus_root(self):
        fields = ['name', 'sequence', 'parent_id', 'action', 'web_icon_data']
        menu_roots = self.get_user_roots()
        menu_roots_data = menu_roots.read(fields) if menu_roots else []

        menu_root = {
            'id': False,
            'name': 'root',
            'parent_id': [-1, ''],
            'children': menu_roots_data,
            'all_menu_ids': menu_roots.ids,
        }

        menu_roots._set_menuitems_xmlids(menu_root)

        return menu_root

    @api.model
    @tools.ormcache_context('self._uid', 'debug', keys=('lang',))
    def load_menus(self, debug):
        """ Loads all menu items (all applications and their sub-menus).

        :return: the menu root
        :rtype: dict('children': menu_nodes)
        """
        fields = ['name', 'sequence', 'parent_id', 'action', 'web_icon', 'web_icon_data']
        menu_roots = self.get_user_roots()
        menu_roots_data = menu_roots.read(fields) if menu_roots else []
        menu_root = {
            'id': False,
            'name': 'root',
            'parent_id': [-1, ''],
            'children': menu_roots_data,
            'all_menu_ids': menu_roots.ids,
        }

        if not menu_roots_data:
            return menu_root

        # menus are loaded fully unlike a regular tree view, cause there are a
        # limited number of items (752 when all 6.1 addons are installed)
        menus = self.search([('id', 'child_of', menu_roots.ids)])
        menu_items = menus.read(fields)

        # add roots at the end of the sequence, so that they will overwrite
        # equivalent menu items from full menu read when put into id:item
        # mapping, resulting in children being correctly set on the roots.
        menu_items.extend(menu_roots_data)
        menu_root['all_menu_ids'] = menus.ids  # includes menu_roots!

        # make a tree using parent_id
        menu_items_map = {menu_item["id"]: menu_item for menu_item in menu_items}
        for menu_item in menu_items:
            parent = menu_item['parent_id'] and menu_item['parent_id'][0]
            if parent in menu_items_map:
                menu_items_map[parent].setdefault(
                    'children', []).append(menu_item)

        # sort by sequence a tree using parent_id
        for menu_item in menu_items:
            menu_item.setdefault('children', []).sort(key=operator.itemgetter('sequence'))

        (menu_roots + menus)._set_menuitems_xmlids(menu_root)

        return menu_root

    def _set_menuitems_xmlids(self, menu_root):
        menuitems = self.env['ir.model.data'].sudo().search([
                ('res_id', 'in', self.ids),
                ('model', '=', 'ir.ui.menu')
            ])

        xmlids = {
            menu.res_id: menu.complete_name
            for menu in menuitems
        }

        def _set_xmlids(tree, xmlids):
            tree['xmlid'] = xmlids.get(tree['id'], '')
            if 'children' in tree:
                for child in tree['children']:
                    _set_xmlids(child, xmlids)

        _set_xmlids(menu_root, xmlids)
