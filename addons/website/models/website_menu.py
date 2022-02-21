# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug.exceptions

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class Menu(models.Model):

    _name = "website.menu"
    _description = "Website Menu"

    _parent_store = True
    _order = "sequence, id"

    def _default_sequence(self):
        menu = self.search([], limit=1, order="sequence DESC")
        return menu.sequence or 0

    @api.depends('mega_menu_content')
    def _compute_field_is_mega_menu(self):
        for menu in self:
            menu.is_mega_menu = bool(menu.mega_menu_content)

    def _set_field_is_mega_menu(self):
        for menu in self:
            if menu.is_mega_menu:
                if not menu.mega_menu_content:
                    menu.mega_menu_content = self.env['ir.ui.view']._render_template('website.s_mega_menu_odoo_menu')
            else:
                menu.mega_menu_content = False
                menu.mega_menu_classes = False

    name = fields.Char('Menu', required=True, translate=True)
    url = fields.Char('Url', default='')
    page_id = fields.Many2one('website.page', 'Related Page', ondelete='cascade')
    new_window = fields.Boolean('New Window')
    sequence = fields.Integer(default=_default_sequence)
    website_id = fields.Many2one('website', 'Website', ondelete='cascade')
    parent_id = fields.Many2one('website.menu', 'Parent Menu', index=True, ondelete="cascade")
    child_id = fields.One2many('website.menu', 'parent_id', string='Child Menus')
    parent_path = fields.Char(index=True)
    is_visible = fields.Boolean(compute='_compute_visible', string='Is Visible')
    group_ids = fields.Many2many('res.groups', string='Visible Groups',
                                 help="User need to be at least in one of these groups to see the menu")
    is_mega_menu = fields.Boolean(compute=_compute_field_is_mega_menu, inverse=_set_field_is_mega_menu)
    mega_menu_content = fields.Html(translate=html_translate, sanitize=False, prefetch=True)
    mega_menu_classes = fields.Char()

    def name_get(self):
        if not self._context.get('display_website') and not self.env.user.has_group('website.group_multi_website'):
            return super(Menu, self).name_get()

        res = []
        for menu in self:
            menu_name = menu.name
            if menu.website_id:
                menu_name += ' [%s]' % menu.website_id.name
            res.append((menu.id, menu_name))
        return res

    @api.model
    def create(self, vals):
        ''' In case a menu without a website_id is trying to be created, we duplicate
            it for every website.
            Note: Particulary useful when installing a module that adds a menu like
                  /shop. So every website has the shop menu.
                  Be careful to return correct record for ir.model.data xml_id in case
                  of default main menus creation.
        '''
        self.clear_caches()
        # Only used when creating website_data.xml default menu
        if vals.get('url') == '/default-main-menu':
            return super(Menu, self).create(vals)

        if 'website_id' in vals:
            return super(Menu, self).create(vals)
        elif self._context.get('website_id'):
            vals['website_id'] = self._context.get('website_id')
            return super(Menu, self).create(vals)
        else:
            # create for every site
            for website in self.env['website'].search([]):
                w_vals = dict(vals, **{
                    'website_id': website.id,
                    'parent_id': website.menu_id.id,
                })
                res = super(Menu, self).create(w_vals)
            # if creating a default menu, we should also save it as such
            default_menu = self.env.ref('website.main_menu', raise_if_not_found=False)
            if default_menu and vals.get('parent_id') == default_menu.id:
                res = super(Menu, self).create(vals)
        return res  # Only one record is returned but multiple could have been created

    def write(self, values):
        res = super().write(values)
        if 'website_id' in values or 'group_ids' in values or 'sequence' in values or 'page_id' in values:
            self.clear_caches()
        return res

    def unlink(self):
        self.clear_caches()
        default_menu = self.env.ref('website.main_menu', raise_if_not_found=False)
        menus_to_remove = self
        for menu in self.filtered(lambda m: default_menu and m.parent_id.id == default_menu.id):
            menus_to_remove |= self.env['website.menu'].search([('url', '=', menu.url),
                                                                ('website_id', '!=', False),
                                                                ('id', '!=', menu.id)])
        return super(Menu, menus_to_remove).unlink()

    def _compute_visible(self):
        for menu in self:
            visible = True
            if menu.page_id and not menu.user_has_groups('base.group_user') and \
                (not menu.page_id.sudo().is_visible or
                 (not menu.page_id.view_id._handle_visibility(do_raise=False) and
                 menu.page_id.view_id.visibility != "password")):
                visible = False
            menu.is_visible = visible

    @api.model
    def clean_url(self):
        # clean the url with heuristic
        if self.page_id:
            url = self.page_id.sudo().url
        else:
            url = self.url
            if url and not self.url.startswith('/'):
                if '@' in self.url:
                    if not self.url.startswith('mailto'):
                        url = 'mailto:%s' % self.url
                elif not self.url.startswith('http'):
                    url = '/%s' % self.url
        return url

    # would be better to take a menu_id as argument
    @api.model
    def get_tree(self, website_id, menu_id=None):
        def make_tree(node):
            is_homepage = bool(node.page_id and self.env['website'].browse(website_id).homepage_id.id == node.page_id.id)
            menu_node = {
                'fields': {
                    'id': node.id,
                    'name': node.name,
                    'url': node.page_id.url if node.page_id else node.url,
                    'new_window': node.new_window,
                    'is_mega_menu': node.is_mega_menu,
                    'sequence': node.sequence,
                    'parent_id': node.parent_id.id,
                },
                'children': [],
                'is_homepage': is_homepage,
            }
            for child in node.child_id:
                menu_node['children'].append(make_tree(child))
            return menu_node

        menu = menu_id and self.browse(menu_id) or self.env['website'].browse(website_id).menu_id
        return make_tree(menu)

    @api.model
    def save(self, website_id, data):
        def replace_id(old_id, new_id):
            for menu in data['data']:
                if menu['id'] == old_id:
                    menu['id'] = new_id
                if menu['parent_id'] == old_id:
                    menu['parent_id'] = new_id
        to_delete = data.get('to_delete')
        if to_delete:
            self.browse(to_delete).unlink()
        for menu in data['data']:
            mid = menu['id']
            # new menu are prefixed by new-
            if isinstance(mid, str):
                new_menu = self.create({'name': menu['name'], 'website_id': website_id})
                replace_id(mid, new_menu.id)
        for menu in data['data']:
            menu_id = self.browse(menu['id'])
            # if the url match a website.page, set the m2o relation
            # except if the menu url is '#', meaning it will be used as a menu container, most likely for a dropdown
            if menu['url'] == '#':
                if menu_id.page_id:
                    menu_id.page_id = None
            else:
                domain = self.env["website"].website_domain(website_id) + [
                    "|",
                    ("url", "=", menu["url"]),
                    ("url", "=", "/" + menu["url"]),
                ]
                page = self.env["website.page"].search(domain, limit=1)
                if page:
                    menu['page_id'] = page.id
                    menu['url'] = page.url
                elif menu_id.page_id:
                    try:
                        # a page shouldn't have the same url as a controller
                        self.env['ir.http']._match(menu['url'])
                        menu_id.page_id = None
                    except werkzeug.exceptions.NotFound:
                        menu_id.page_id.write({'url': menu['url']})
            menu_id.write(menu)

        return True
