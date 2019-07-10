# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.http_routing.models.ir_http import slugify
from odoo import api, fields, models


class Page(models.Model):
    _name = 'website.page'
    _inherits = {'ir.ui.view': 'view_id'}
    _inherit = 'website.published.multi.mixin'
    _description = 'Page'
    _order = 'website_id'

    url = fields.Char('Page URL')
    view_id = fields.Many2one('ir.ui.view', string='View', required=True, ondelete="cascade")
    website_indexed = fields.Boolean('Page Indexed', default=True)
    date_publish = fields.Datetime('Publishing Date')
    # This is needed to be able to display if page is a menu in /website/pages
    menu_ids = fields.One2many('website.menu', 'page_id', 'Related Menus')
    is_homepage = fields.Boolean(compute='_compute_homepage', inverse='_set_homepage', string='Homepage')
    is_visible = fields.Boolean(compute='_compute_visible', string='Is Visible')

    # Page options
    header_overlay = fields.Boolean()
    header_color = fields.Char()

    # don't use mixin website_id but use website_id on ir.ui.view instead
    website_id = fields.Many2one(related='view_id.website_id', store=True, readonly=False)

    def _compute_homepage(self):
        for page in self:
            page.is_homepage = page == self.env['website'].get_current_website().homepage_id

    def _set_homepage(self):
        for page in self:
            website = self.env['website'].get_current_website()
            if page.is_homepage:
                if website.homepage_id != page:
                    website.write({'homepage_id': page.id})
            else:
                if website.homepage_id == page:
                    website.write({'homepage_id': None})

    def _compute_visible(self):
        for page in self:
            page.is_visible = page.website_published and (
                not page.date_publish or page.date_publish < fields.Datetime.now()
            )

    def _is_most_specific_page(self, page_to_test):
        '''This will test if page_to_test is the most specific page in self.'''
        pages_for_url = self.sorted(key=lambda p: not p.website_id).filtered(lambda page: page.url == page_to_test.url)

        # this works because pages are _order'ed by website_id
        most_specific_page = pages_for_url[0]

        return most_specific_page == page_to_test

    @api.model
    def get_page_info(self, id):
        return self.browse(id).read(
            ['id', 'name', 'url', 'website_published', 'website_indexed', 'date_publish', 'menu_ids', 'is_homepage', 'website_id'],
        )

    def get_view_identifier(self):
        """ Get identifier of this page view that may be used to render it """
        return self.view_id.id

    @api.model
    def save_page_info(self, website_id, data):
        website = self.env['website'].browse(website_id)
        page = self.browse(int(data['id']))

        # If URL has been edited, slug it
        original_url = page.url
        url = data['url']
        if not url.startswith('/'):
            url = '/' + url
        if page.url != url:
            url = '/' + slugify(url, max_length=1024, path=True)
            url = self.env['website'].get_unique_path(url)

        # If name has changed, check for key uniqueness
        if page.name != data['name']:
            page_key = self.env['website'].get_unique_key(slugify(data['name']))
        else:
            page_key = page.key

        menu = self.env['website.menu'].search([('page_id', '=', int(data['id']))])
        if not data['is_menu']:
            # If the page is no longer in menu, we should remove its website_menu
            if menu:
                menu.unlink()
        else:
            # The page is now a menu, check if has already one
            if menu:
                menu.write({'url': url})
            else:
                self.env['website.menu'].create({
                    'name': data['name'],
                    'url': url,
                    'page_id': data['id'],
                    'parent_id': website.menu_id.id,
                    'website_id': website.id,
                })

        # Edits via the page manager shouldn't trigger the COW
        # mechanism and generate new pages. The user manages page
        # visibility manually with is_published here.
        w_vals = {
            'key': page_key,
            'name': data['name'],
            'url': url,
            'is_published': data['website_published'],
            'website_indexed': data['website_indexed'],
            'date_publish': data['date_publish'] or None,
            'is_homepage': data['is_homepage'],
        }
        page.with_context(no_cow=True).write(w_vals)

        # Create redirect if needed
        if data['create_redirect']:
            self.env['website.redirect'].create({
                'redirect_type': data['redirect_type'],
                'url_from': original_url,
                'url_to': url,
                'website_id': website.id,
            })

        return url

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default:
            if not default.get('view_id'):
                view = self.env['ir.ui.view'].browse(self.view_id.id)
                new_view = view.copy({'website_id': default.get('website_id')})
                default['view_id'] = new_view.id

            default['url'] = default.get('url', self.env['website'].get_unique_path(self.url))
        return super(Page, self).copy(default=default)

    @api.model
    def clone_page(self, page_id, clone_menu=True):
        """ Clone a page, given its identifier
            :param page_id : website.page identifier
        """
        page = self.browse(int(page_id))
        new_page = page.copy(dict(name=page.name, website_id=self.env['website'].get_current_website().id))
        # Should not clone menu if the page was cloned from one website to another
        # Eg: Cloning a generic page (no website) will create a page with a website, we can't clone menu (not same container)
        if clone_menu and new_page.website_id == page.website_id:
            menu = self.env['website.menu'].search([('page_id', '=', page_id)], limit=1)
            if menu:
                # If the page being cloned has a menu, clone it too
                menu.copy({'url': new_page.url, 'name': menu.name, 'page_id': new_page.id})

        return new_page.url + '?enable_editor=1'

    def unlink(self):
        # When a website_page is deleted, the ORM does not delete its
        # ir_ui_view. So we got to delete it ourself, but only if the
        # ir_ui_view is not used by another website_page.
        for page in self:
            # Other pages linked to the ir_ui_view of the page being deleted (will it even be possible?)
            pages_linked_to_iruiview = self.search(
                [('view_id', '=', page.view_id.id), ('id', '!=', page.id)]
            )
            if not pages_linked_to_iruiview and not page.view_id.inherit_children_ids:
                # If there is no other pages linked to that ir_ui_view, we can delete the ir_ui_view
                page.view_id.unlink()
        return super(Page, self).unlink()

    def write(self, vals):
        if 'url' in vals and not vals['url'].startswith('/'):
            vals['url'] = '/' + vals['url']
        return super(Page, self).write(vals)

    def get_website_meta(self):
        self.ensure_one()
        return self.view_id.get_website_meta()
