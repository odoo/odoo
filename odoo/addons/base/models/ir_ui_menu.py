# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from collections import defaultdict
from os.path import join as opj
import operator
import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.osv import expression

MENU_ITEM_SEPARATOR = "/"
NUMBER_PARENS = re.compile(r"\(([0-9]+)\)")


class IrUiMenu(models.Model):
    _name = 'ir.ui.menu'
    _description = 'Menu'
    _order = "sequence,id"
    _parent_store = True
    _allow_sudo_commands = False

    name = fields.Char(string='Menu', required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    child_id = fields.One2many('ir.ui.menu', 'parent_id', string='Child IDs')
    parent_id = fields.Many2one('ir.ui.menu', string='Parent Menu', index=True, ondelete="restrict")
    parent_path = fields.Char(index=True)
    groups_id = fields.Many2many('res.groups', 'ir_ui_menu_group_rel',
                                 'menu_id', 'gid', string='Groups',
                                 help="If you have groups, the visibility of this menu will be based on these groups. "\
                                      "If this field is empty, Odoo will compute visibility based on the related object's read access.")
    complete_name = fields.Char(string='Full Path', compute='_compute_complete_name', recursive=True)
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

    def _read_image(self, path):
        if not path:
            return False
        path_info = path.split(',')
        icon_path = opj(path_info[0], path_info[1])
        try:
            with tools.file_open(icon_path, 'rb', filter_ext=('.png',)) as icon_file:
                return base64.encodebytes(icon_file.read())
        except FileNotFoundError:
            return False

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if self._has_cycle():
            raise ValidationError(_('Error! You cannot create recursive menus.'))

    @api.model
    @tools.ormcache('frozenset(self.env.user._get_group_ids())', 'debug')
    def _visible_menu_ids(self, debug=False):
        """ Return the ids of the menu items visible to the user. """
        group_ids = set(self.env.user._get_group_ids())
        if not debug:
            group_ids.discard(self.env['ir.model.data']._xmlid_to_res_id('base.group_no_one', raise_if_not_found=False))

        # retrieve menus with a domain to filter out menus with groups the user does not have.
        # It will be used to determine which ones are visible
        menus = self.with_context({}).search_fetch(
            # Don't use 'any' operator in the domain to avoid ir.rule
            ['|', ('groups_id', '=', False), ('groups_id', 'in', tuple(group_ids))],
            ['parent_id', 'action'], order='id',
        ).sudo()

        # take apart menus that have an action
        action_ids_by_model = defaultdict(list)
        for action in menus.mapped('action'):
            if action:
                action_ids_by_model[action._name].append(action.id)

        MODEL_BY_TYPE = {
            'ir.actions.act_window': 'res_model',
            'ir.actions.report': 'model',
            'ir.actions.server': 'model_name',
        }
        def exists_actions(model_name, action_ids):
            """ Return existing actions and fetch model name field if exists"""
            if model_name not in MODEL_BY_TYPE:
                return self.env[model_name].browse(action_ids).exists()
            records = self.env[model_name].sudo().with_context(active_test=False).search_fetch(
                [('id', 'in', action_ids)], [MODEL_BY_TYPE[model_name]], order='id',
            )
            if model_name == 'ir.actions.server':
                # Because it is computed, `search_fetch` doesn't fill the cache for it
                records.mapped('model_name')
            return records

        existing_actions = {
            action
            for model_name, action_ids in action_ids_by_model.items()
            for action in exists_actions(model_name, action_ids)
        }
        menu_ids = set(menus._ids)
        visible_ids = set()
        access = self.env['ir.model.access']
        # process action menus, check whether their action is allowed
        for menu in menus:
            action = menu.action
            if not action or action not in existing_actions:
                continue
            model_fname = MODEL_BY_TYPE.get(action._name)
            # action[model_fname] has been fetched in batch in `exists_actions`
            if model_fname and not access.check(action[model_fname], 'read', False):
                continue
            # make menu visible, and its folder ancestors, too
            menu_id = menu.id
            while menu_id not in visible_ids and menu_id in menu_ids:
                visible_ids.add(menu_id)
                menu = menu.parent_id
                menu_id =  menu.id

        return frozenset(visible_ids)

    def _filter_visible_menus(self):
        """ Filter `self` to only keep the menu items that should be visible in
            the menu hierarchy of the current user.
            Uses a cache for speeding up the computation.
        """
        visible_ids = self._visible_menu_ids(request.session.debug if request else False)
        return self.filtered(lambda menu: menu.id in visible_ids)

    @api.depends('parent_id')
    def _compute_display_name(self):
        for menu in self:
            menu.display_name = menu._get_full_name()

    @api.model_create_multi
    def create(self, vals_list):
        self.env.registry.clear_cache()
        for values in vals_list:
            if 'web_icon' in values:
                values['web_icon_data'] = self._compute_web_icon_data(values.get('web_icon'))
        return super(IrUiMenu, self).create(vals_list)

    def write(self, values):
        self.env.registry.clear_cache()
        if 'web_icon' in values:
            values['web_icon_data'] = self._compute_web_icon_data(values.get('web_icon'))
        return super(IrUiMenu, self).write(values)

    def _compute_web_icon_data(self, web_icon):
        """ Returns the image associated to `web_icon`.
            `web_icon` can either be:
              - an image icon [module, path]
              - a built icon [icon_class, icon_color, background_color]
            and it only has to call `_read_image` if it's an image.
        """
        if web_icon and len(web_icon.split(',')) == 2:
            return self._read_image(web_icon)

    def unlink(self):
        # Detach children and promote them to top-level, because it would be unwise to
        # cascade-delete submenus blindly. We also can't use ondelete=set null because
        # that is not supported when _parent_store is used (would silently corrupt it).
        # TODO: ideally we should move them under a generic "Orphans" menu somewhere?
        direct_children = self.with_context(active_test=False).search([('parent_id', 'in', self.ids)])
        direct_children.write({'parent_id': False})

        self.env.registry.clear_cache()
        return super(IrUiMenu, self).unlink()

    def copy(self, default=None):
        new_menus = super().copy(default=default)
        for new_menu in new_menus:
            match = NUMBER_PARENS.search(new_menu.name)
            if match:
                next_num = int(match.group(1)) + 1
                new_menu.name = NUMBER_PARENS.sub('(%d)' % next_num, new_menu.name)
            else:
                new_menu.name = new_menu.name + '(1)'
        return new_menus

    @api.model
    def get_user_roots(self):
        """ Return all root menu ids visible for the user.

        :return: the root menu ids
        :rtype: list(int)
        """
        return self.search([('parent_id', '=', False)])._filter_visible_menus()

    def _load_menus_blacklist(self):
        return []

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

        xmlids = menu_roots._get_menuitems_xmlids()
        for menu in menu_roots_data:
            menu['xmlid'] = xmlids.get(menu['id'], '')

        return menu_root

    @api.model
    @tools.ormcache_context('self._uid', 'debug', keys=('lang',))
    def load_menus(self, debug):
        blacklisted_menu_ids = self._load_menus_blacklist()
        visible_menus = self.search_fetch(
            [('id', 'not in', blacklisted_menu_ids)],
            ['name', 'parent_id', 'action', 'web_icon'],
        )._filter_visible_menus()

        children_dict = defaultdict(list)  # {parent_id: []} / parent_id == False for root menus
        for menu in visible_menus:
            children_dict[menu.parent_id.id].append(menu.id)

        app_info = {}
        # recursively set app ids to related children
        def _set_app_id(menu_app_id, menu_id):
            app_info[menu_id] = menu_app_id
            for child_id in children_dict[menu_id]:
                _set_app_id(menu_app_id, child_id)

        for root_menu_id in children_dict[False]:
            _set_app_id(root_menu_id, root_menu_id)

        # Filter out menus not related to an app (+ keep root menu), it happens when
        # some parent menu are not visible for group.
        visible_menus = visible_menus.filtered(lambda menu: menu.id in app_info)

        xmlids = visible_menus._get_menuitems_xmlids()
        icon_attachments = self.env['ir.attachment'].sudo().search_read(
            domain=[('res_model', '=', 'ir.ui.menu'),
                    ('res_id', 'in', visible_menus._ids),
                    ('res_field', '=', 'web_icon_data')],
            fields=['res_id', 'datas', 'mimetype'])
        icon_attachments_res_id = {attachment['res_id']: attachment for attachment in icon_attachments}

        menus_dict = {}
        action_ids_by_type = defaultdict(list)
        for menu in visible_menus:

            menu_id = menu.id
            attachment = icon_attachments_res_id.get(menu_id)

            if action := menu.action:
                action_model = action._name
                action_id = action.id
                action_ids_by_type[action_model].append(action_id)
            else:
                action_model = False
                action_id = False

            menus_dict[menu_id] = {
                'id': menu_id,
                'name': menu.name,
                'app_id': app_info[menu_id],
                'action_model': action_model,
                'action_id': action_id,
                'web_icon': menu.web_icon,
                'web_icon_data': attachment['datas'].decode() if attachment else False,
                'web_icon_data_mimetype': attachment['mimetype'] if attachment else False,
                'xmlid': xmlids.get(menu_id, ""),
            }

        # prefetch action.path
        for model_name, action_ids in action_ids_by_type.items():
            self.env[model_name].sudo().browse(action_ids).fetch(['path'])

        # set children + model_path
        for menu_dict in menus_dict.values():
            if menu_dict['action_model']:
                menu_dict['action_path'] = self.env[menu_dict['action_model']].sudo().browse(menu_dict['action_id']).path
            else:
                menu_dict['action_path'] = False
            menu_dict['children'] = children_dict[menu_dict['id']]

        menus_dict['root'] = {
            'id': False,
            'name': 'root',
            'children': children_dict[False],
        }
        return menus_dict

    def _get_menuitems_xmlids(self):
        menuitems = self.env['ir.model.data'].sudo().search_fetch(
            [('res_id', 'in', self.ids), ('model', '=', 'ir.ui.menu')],
            ['res_id', 'complete_name'],
        )

        return {
            menu.res_id: menu.complete_name
            for menu in menuitems
        }
