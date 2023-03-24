# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug.exceptions
import werkzeug.urls

from odoo import api, fields, models
from odoo.http import request
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
    parent_path = fields.Char(index=True, unaccent=False)
    is_visible = fields.Boolean(compute='_compute_visible', string='Is Visible')
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

    @api.model_create_multi
    def create(self, vals_list):
        ''' In case a menu without a website_id is trying to be created, we duplicate
            it for every website.
            Note: Particulary useful when installing a module that adds a menu like
                  /shop. So every website has the shop menu.
                  Be careful to return correct record for ir.model.data xml_id in case
                  of default main menus creation.
        '''
        self.clear_caches()
        # Only used when creating website_data.xml default menu
        menus = self.env['website.menu']
        for vals in vals_list:
            if vals.get('url') == '/default-main-menu':
                menus |= super().create(vals)
                continue
            if 'website_id' in vals:
                menus |= super().create(vals)
                continue
            elif self._context.get('website_id'):
                vals['website_id'] = self._context.get('website_id')
                menus |= super().create(vals)
                continue
            else:
                # create for every site
                w_vals = [dict(vals, **{
                    'website_id': website.id,
                    'parent_id': website.menu_id.id,
                }) for website in self.env['website'].search([])]
                new_menu = super().create(w_vals)[-1:]  # take the last one
                # if creating a default menu, we should also save it as such
                default_menu = self.env.ref('website.main_menu', raise_if_not_found=False)
                if default_menu and vals.get('parent_id') == default_menu.id:
                    new_menu = super().create(vals)
                menus |= new_menu
        # Only one record per vals is returned but multiple could have been created
        return menus

    def write(self, values):
        self.clear_caches()
        return super().write(values)

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
            if menu.page_id and not menu.user_has_groups('base.group_user'):
                page_sudo = menu.page_id.sudo()
                if (not page_sudo.is_visible
                    or (not page_sudo.view_id._handle_visibility(do_raise=False)
                        and page_sudo.view_id._get_cached_visibility() != "password")):
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
        website = self.env['website'].browse(website_id)

        def make_tree(node):
            menu_url = node.page_id.url if node.page_id else node.url
            menu_node = {
                'fields': {
                    'id': node.id,
                    'name': node.name,
                    'url': menu_url,
                    'new_window': node.new_window,
                    'is_mega_menu': node.is_mega_menu,
                    'sequence': node.sequence,
                    'parent_id': node.parent_id.id,
                },
                'children': [],
                'is_homepage': menu_url == (website.homepage_url or '/'),
            }
            for child in node.child_id:
                menu_node['children'].append(make_tree(child))
            return menu_node

        menu = menu_id and self.browse(menu_id) or website.menu_id
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
            # Check if the url match a website.page (to set the m2o relation),
            # except if the menu url contains '#', we then unset the page_id
            if not menu['url'] or '#' in menu['url']:
                # Multiple case possible
                # 1. `#` => menu container (dropdown, ..)
                # 2. `#anchor` => anchor on current page
                # 3. `/url#something` => valid internal URL
                # 4. https://google.com#smth => valid external URL
                if menu_id.page_id:
                    menu_id.page_id = None
                if request and menu['url'] and menu['url'].startswith('#') and len(menu['url']) > 1:
                    # Working on case 2.: prefix anchor with referer URL
                    referer_url = werkzeug.urls.url_parse(request.httprequest.headers.get('Referer', '')).path
                    menu['url'] = referer_url + menu['url']
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
                    if isinstance(menu.get('parent_id'), str):
                        # Avoid failure if parent_id is sent as a string from a customization.
                        menu['parent_id'] = int(menu['parent_id'])
                elif menu_id.page_id:
                    try:
                        # a page shouldn't have the same url as a controller
                        self.env['ir.http']._match(menu['url'])
                        menu_id.page_id = None
                    except werkzeug.exceptions.NotFound:
                        menu_id.page_id.write({'url': menu['url']})
            menu_id.write(menu)

        return True
