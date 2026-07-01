# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug.exceptions
import werkzeug.urls

from werkzeug.urls import url_parse

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.http import request
from odoo.tools.translate import html_translate


class WebsiteMenu(models.Model):
    _name = 'website.menu'

    _description = "Website Menu"

    _parent_store = True
    _order = "sequence, id"

    def _default_sequence(self):
        menu = self.search([], limit=1, order="sequence DESC")
        return menu.sequence or 0

    name = fields.Char('Menu', required=True, translate=True)
    url = fields.Char("Url", compute="_compute_url", store=True, required=True, readonly=False, default="#", copy=True)
    page_id = fields.Many2one('website.page', 'Related Page', ondelete='cascade', index='btree_not_null')
    controller_page_id = fields.Many2one('website.controller.page', 'Related Model Page', ondelete='cascade', index='btree_not_null')
    new_window = fields.Boolean('New Window')
    sequence = fields.Integer(default=_default_sequence)
    website_id = fields.Many2one('website', 'Website', ondelete='cascade')
    parent_id = fields.Many2one('website.menu', 'Parent Menu', index=True, ondelete="cascade")
    child_id = fields.One2many('website.menu', 'parent_id', string='Child Menus')
    parent_path = fields.Char(index=True)
    is_visible = fields.Boolean(compute='_compute_visible', string='Is Visible')
    group_ids = fields.Many2many('res.groups', string='Visible Groups',
        groups='base.group_user',
        help="User needs to be at least in one of these groups to see the menu")
    is_mega_menu = fields.Boolean(compute='_compute_field_is_mega_menu', inverse='_inverse_field_is_mega_menu')
    mega_menu_content = fields.Html(translate=html_translate, sanitize=False, prefetch=True)
    mega_menu_classes = fields.Char()

    @api.depends('mega_menu_content')
    def _compute_field_is_mega_menu(self):
        for menu in self:
            menu.is_mega_menu = bool(menu.mega_menu_content)

    def _inverse_field_is_mega_menu(self):
        for menu in self:
            if menu.is_mega_menu:
                if not menu.mega_menu_content:
                    website = menu.website_id or self.env.website or self.env['website'].search([], limit=1)
                    menu.mega_menu_content = website.with_context(inherit_branding=False)._render_template('website.s_mega_menu_odoo_menu')
            else:
                menu.mega_menu_content = False
                menu.mega_menu_classes = False

    @api.depends('website_id')
    @api.depends_context('display_website')
    def _compute_display_name(self):
        if not self.env.context.get('display_website') and not self.env.user.has_group('website.group_multi_website'):
            return super()._compute_display_name()

        for menu in self:
            menu_name = menu.name or ""
            if menu.website_id:
                menu_name += f' [{menu.website_id.name}]'
            menu.display_name = menu_name

    @api.depends("page_id", "is_mega_menu", "child_id")
    def _compute_url(self):
        for menu in self:
            if menu.is_mega_menu or menu.child_id:
                menu.url = "#"
            else:
                menu.url = (menu.page_id.url if menu.page_id else menu.url) or "#"

    @api.constrains("parent_id", "child_id", "is_mega_menu", "mega_menu_content")
    def _validate_parent_menu(self):
        """
        Ensure valid menu hierarchy and mega menu constraints.

        Rules enforced:
        - Menus must not exceed two levels of nesting.
        - A mega menu must not have a parent or child.
        - Menus with children cannot be added as a submenu under another menu.
        """
        for record in self:
            parent_menu = record.parent_id.sudo() if record.parent_id else None

            # Check hierarchy level
            level = 0
            current_menu = parent_menu
            while current_menu:
                level += 1
                current_menu = current_menu.parent_id
                if level > 2:
                    raise UserError(_("Menus cannot have more than two levels of hierarchy."))

            if parent_menu:
                # Mega menu constraint
                if parent_menu.is_mega_menu or (record.is_mega_menu and (parent_menu.parent_id or record.child_id)):
                    raise UserError(_("A mega menu cannot have a parent or child menu."))

                # Submenu structure constraint
                if record.child_id and (parent_menu.parent_id or record.child_id.child_id):
                    raise UserError(_("Menus with child menus cannot be added as a submenu."))

    @api.constrains("mega_menu_content")
    def _validate_mega_menu_content(self):
        """
        Checks that there is no editing branding in the html content.
        """
        for record in self:
            if record.mega_menu_content and ' data-oe-model=' in record.mega_menu_content:
                raise UserError(_("Presence of publishing branding in html content is forbidden"))

    @api.model_create_multi
    def create(self, vals_list):
        self.env.transaction.invalidate_ormcache('templates')
        context_website_id = self.env.context.get('website_id')
        default_menu = self.env.ref('website.main_menu', raise_if_not_found=False)
        for vals in vals_list:
            if 'website_id' not in vals:
                if context_website_id:
                    vals['website_id'] = context_website_id
                if default_menu and not vals.get('parent_id'):
                    vals['parent_id'] = default_menu.id
        return super().create(vals_list)

    def _load_records(self, data_list, update=False):
        menus = super()._load_records(data_list, update)
        menus.filtered(lambda m: not m.website_id)._copy_menu_hierarchy()
        return menus

    def _copy_menu_hierarchy(self, websites=None):
        """Copy template menus (menus with no `website_id`) onto each
        website in `websites` (default: all websites).
        Duplicated menus receive an xml_id of the form:
        `<module_name>.<website_id>_<template_xmlid_name>`.
        These xml_ids are used to lookup parent menus thereby enabling
        multi-level menu creation.
        """
        template_menus = self.filtered(lambda m: not m.website_id)
        if not template_menus:
            return
        websites = websites or self.env['website'].search([])

        external_ids = template_menus.get_external_id()
        model_data = []
        for unnamed_menu in template_menus.filtered(lambda m: not external_ids.get(m.id)):
            xml_id = f'website.menu_{unnamed_menu.id}'
            external_ids[unnamed_menu.id] = xml_id
            model_data.append({
                'xml_id': xml_id,
                'record': unnamed_menu,
                'noupdate': True,
            })
        self.env['ir.model.data']._update_xmlids(model_data)
        parent_external_ids = template_menus.parent_id.get_external_id()

        data = []
        source_menus = []
        for menu in template_menus:
            for website in websites:
                site_xmlid = website._website_xmlid(external_ids[menu.id])
                if self.env.ref(site_xmlid, raise_if_not_found=False):
                    continue
                values = {**menu.copy_data()[0], 'website_id': website.id}
                if menu.parent_id:
                    parent_xmlid = parent_external_ids[menu.parent_id.id]
                    parent = self.env.ref(website._website_xmlid(parent_xmlid), raise_if_not_found=False)
                    values['parent_id'] = parent.id if parent else False
                data.append({'xml_id': site_xmlid, 'values': values, 'noupdate': True})
                source_menus.append(menu)
        new_menus = self._load_records(data)
        for source_menu, new_menu in zip(source_menus, new_menus):
            source_menu.copy_translations(new_menu)
        template_menus.child_id._copy_menu_hierarchy(websites)

    def write(self, vals):
        if any(self._ids):
            self.env.transaction.invalidate_ormcache('templates')
        res = super().write(vals)
        if 'group_ids' in vals and not self.env.context.get("adding_designer_group_to_menu"):
            self.filtered("group_ids").with_context(
                adding_designer_group_to_menu=True
            ).group_ids += self.env.ref("website.group_website_designer")
        return res

    def unlink(self):
        self.env.transaction.invalidate_ormcache('templates')
        default_menu = self.env.ref('website.main_menu', raise_if_not_found=False)
        menus_to_remove = self
        for menu in self.filtered(lambda m: default_menu and m.parent_id.id == default_menu.id):
            menus_to_remove |= self.env['website.menu'].search([('url', '=', menu.url),
                                                                ('website_id', '!=', False),
                                                                ('id', '!=', menu.id)])
        return super(WebsiteMenu, menus_to_remove).unlink()

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_tags(self):
        main_menu = self.env.ref('website.main_menu', raise_if_not_found=False)
        if main_menu and main_menu in self:
            raise UserError(_("You cannot delete this website menu as this serves as the default parent menu for new websites (e.g., /shop, /event, ...)."))

    def _compute_visible(self):
        for menu in self:
            visible = True
            if menu.page_id and not menu.env.user._is_internal():
                page_sudo = menu.page_id.sudo()
                if (not page_sudo.is_visible
                    or (not page_sudo.view_id._handle_visibility(do_raise=False)
                        and page_sudo.view_id._get_cached_visibility() != "password")):
                    visible = False

            if menu.controller_page_id and not menu.env.user._is_internal():
                controller_page_sudo = menu.controller_page_id.sudo()
                if (not controller_page_sudo.is_published
                    or (not controller_page_sudo.view_id._handle_visibility(do_raise=False)
                        and controller_page_sudo.view_id._get_cached_visibility() != "password")):
                    visible = False

            menu.is_visible = visible

    def _clean_url(self):
        # clean the url with heuristic
        url = self.url
        if url and not url.startswith('/') and url not in ('#top', '#bottom'):
            if "@" in self.url:
                if not self.url.startswith("mailto"):
                    url = "mailto:%s" % self.url
            elif not self.url.startswith("http"):
                url = "/%s" % self.url
        return url

    def _is_active(self):
        """ To be considered active, a menu should either:

        - have its URL matching the request's URL and have no children
        - or have a children menu URL matching the request's URL

        Matching an URL means, either:

        - be equal, eg ``/contact/on-site`` vs ``/contact/on-site``
        - be equal after unslug, eg ``/shop/1`` and ``/shop/my-super-product-1``

        Note that saving a menu URL with an anchor or a query string is
        considered a corner case, and the following applies:

        - anchor/fragment are ignored during the comparison (it would be
          impossible to compare anyway as the client is not sending the anchor
          to the server as per RFC)
        - query string parameters should be the same to be considered equal, as
          those could drasticaly alter a page result
        """
        if not request or self.is_mega_menu:
            # There is no notion of `active` if we don't have a request to
            # compare the url to.
            # Also, mega menu are never considered active.
            return False

        request_url = url_parse(request.httprequest.url)

        if not self.child_id:
            menu_url = url_parse(self._clean_url())
            unslug_url = self.env['ir.http']._unslug_url
            if unslug_url(menu_url.path) == unslug_url(request_url.path):
                # By default we compare the unslug version of the current URL
                # with the menu URL but if the menu is linked to a page we don't
                # consider it active if the paths don't match exactly.
                if self.page_id and menu_url.path != request_url.path:
                    return False
                if not (
                    set(menu_url.decode_query().items(multi=True))
                    <= set(request_url.decode_query().items(multi=True))
                ):
                    # correct path but query arguments does not match
                    return False
                if menu_url.netloc and menu_url.netloc != request_url.netloc:
                    # correct path but not correct domain
                    return False
                return True
        else:
            # Child match (dropdown menu), `self` is just a parent/container,
            # don't check its URL, consider only its children
            if any(child._is_active() for child in self.child_id):
                return True

        return False

    # would be better to take a menu_id as argument
    @api.model
    def get_tree(self, website_id, menu_id=None):
        website = self.env['website'].browse(website_id)

        def make_tree(node):
            menu_node = {
                'fields': {
                    'id': node.id,
                    'name': node.name,
                    'url': node.url,
                    'new_window': node.new_window,
                    'is_mega_menu': node.is_mega_menu,
                    'sequence': node.sequence,
                    'parent_id': node.parent_id.id,
                },
                'children': [],
                'is_homepage': node.url == (website.homepage_url or '/'),
            }
            for child in node.child_id:
                menu_node['children'].append(make_tree(child))
            return menu_node

        menu = menu_id and self.browse(menu_id) or website.menu_id
        return make_tree(menu)

    @api.model
    def save(self, website_id, data):
        WebsiteMenu = self.with_context(website_id=website_id)

        def replace_id(old_id, new_id):
            for menu in data['data']:
                if menu['id'] == old_id:
                    menu['id'] = new_id
                if menu['parent_id'] == old_id:
                    menu['parent_id'] = new_id
        to_delete = data.get('to_delete')
        if to_delete:
            WebsiteMenu.browse(to_delete).unlink()
        for menu in data['data']:
            mid = menu['id']
            # new menu are prefixed by new-
            if isinstance(mid, str):
                new_menu = WebsiteMenu.create({'name': menu['name'], 'website_id': website_id})
                replace_id(mid, new_menu.id)
        for menu in data['data']:
            menu_id = WebsiteMenu.browse(menu['id'])
            # Check if the url match a website.page (to set the m2o relation),
            # except if the menu url contains '#', we then unset the page_id
            if '#' in menu['url']:
                # Multiple case possible
                # 1. `#` => menu container (dropdown, ..)
                # 2. `#top` or `#bottom` => special anchors valid for any page
                # 3. `#anchor` => anchor on current page
                # 4. `/url#something` => valid internal URL
                # 5. https://google.com#smth => valid external URL
                if menu_id.page_id:
                    menu_id.page_id = None
                if request and menu['url'].startswith('#') and len(menu['url']) > 1 and \
                        menu['url'] not in ['#top', '#bottom']:
                    # Working on case 2.: prefix anchor with referer URL
                    referer_url = werkzeug.urls.url_parse(request.httprequest.headers.get('Referer', '')).path
                    menu['url'] = referer_url + menu['url']
            else:
                domain = WebsiteMenu.env["website"].browse(website_id).website_domain() & (
                    Domain("url", "=", menu["url"])
                    | Domain("url", "=", "/" + menu["url"])
                )
                page = WebsiteMenu.env["website.page"].search(domain, limit=1)
                if page:
                    menu['page_id'] = page.id
                    menu['url'] = page.url
                    if isinstance(menu.get('parent_id'), str):
                        # Avoid failure if parent_id is sent as a string from a customization.
                        menu['parent_id'] = int(menu['parent_id'])
                elif menu_id.page_id:
                    try:
                        # a page shouldn't have the same url as a controller
                        WebsiteMenu.env['ir.http']._match(menu['url'])
                        menu_id.page_id = None
                    except werkzeug.exceptions.NotFound:
                        menu_id.page_id.write({'url': menu['url']})
            menu_id.write(menu)

        return True
