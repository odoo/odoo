# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import sql
import re

from odoo.addons.http_routing.models.ir_http import slugify
from odoo.addons.website.tools import text_from_html
from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools import escape_psql
from odoo.tools.translate import _


class Page(models.Model):
    _name = 'website.page'
    _inherits = {'ir.ui.view': 'view_id'}
    _inherit = [
        'website.published.multi.mixin',
        'website.searchable.mixin',
    ]
    _description = 'Page'
    _order = 'website_id'

    url = fields.Char('Page URL', required=True)
    view_id = fields.Many2one('ir.ui.view', string='View', required=True, ondelete="cascade")
    website_indexed = fields.Boolean('Is Indexed', default=True)
    date_publish = fields.Datetime('Publishing Date')
    menu_ids = fields.One2many('website.menu', 'page_id', 'Related Menus')
    # This is needed to be able to control if page is a menu in page properties.
    # TODO this should be reviewed entirely so that we use a transient model.
    is_in_menu = fields.Boolean(compute='_compute_website_menu', inverse='_inverse_website_menu')
    is_homepage = fields.Boolean(compute='_compute_is_homepage', inverse='_set_is_homepage', string='Homepage')
    is_visible = fields.Boolean(compute='_compute_visible', string='Is Visible')

    # Page options
    header_overlay = fields.Boolean()
    header_color = fields.Char()
    header_text_color = fields.Char()
    header_visible = fields.Boolean(default=True)
    footer_visible = fields.Boolean(default=True)

    # don't use mixin website_id but use website_id on ir.ui.view instead
    website_id = fields.Many2one(related='view_id.website_id', store=True, readonly=False, ondelete='cascade')
    arch = fields.Text(related='view_id.arch', readonly=False, depends_context=('website_id',))

    def _compute_is_homepage(self):
        website = self.env['website'].get_current_website()
        for page in self:
            page.is_homepage = page.url == (website.homepage_url or page.website_id == website and '/')

    def _set_is_homepage(self):
        website = self.env['website'].get_current_website()
        for page in self:
            if page.is_homepage:
                if website.homepage_url != page.url:
                    website.homepage_url = page.url
            else:
                if website.homepage_url == page.url:
                    website.homepage_url = ''

    def _compute_visible(self):
        for page in self:
            page.is_visible = page.website_published and (
                not page.date_publish or page.date_publish < fields.Datetime.now()
            )

    @api.depends('menu_ids')
    def _compute_website_menu(self):
        for page in self:
            page.is_in_menu = bool(page.menu_ids)

    def _inverse_website_menu(self):
        for page in self:
            if page.is_in_menu:
                if not page.menu_ids:
                    self.env['website.menu'].create({
                        'name': page.name,
                        'url': page.url,
                        'page_id': page.id,
                        'parent_id': page.website_id.menu_id.id,
                        'website_id': page.website_id.id,
                    })
            elif page.menu_ids:
                # If the page is no longer in menu, we should remove its website_menu
                page.menu_ids.unlink()

    # This update was added to make sure the mixin calculations are correct
    # (page.website_url > page.url).
    @api.depends('url')
    def _compute_website_url(self):
        for page in self:
            page.website_url = page.url

    def _get_most_specific_pages(self):
        ''' Returns the most specific pages in self. '''
        ids = []
        previous_page = None
        page_keys = self.sudo().search(
            self.env['website'].website_domain(website_id=self._context.get('website_id'))
        ).mapped('key')
        # Iterate a single time on the whole list sorted on specific-website first.
        for page in self.sorted(key=lambda p: (p.url, not p.website_id)):
            if (
                (not previous_page or page.url != previous_page.url)
                # If a generic page (niche case) has been COWed and that COWed
                # page received a URL change, it should not let you access the
                # generic page anymore, despite having a different URL.
                and (page.website_id or page_keys.count(page.key) == 1)
            ):
                ids.append(page.id)
            previous_page = page
        return self.browse(ids)

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
    def clone_page(self, page_id, page_name=None, clone_menu=True):
        """ Clone a page, given its identifier
            :param page_id : website.page identifier
        """
        page = self.browse(int(page_id))
        copy_param = dict(name=page_name or page.name, website_id=self.env['website'].get_current_website().id)
        if page_name:
            url = '/' + slugify(page_name, max_length=1024, path=True)
            copy_param['url'] = self.env['website'].get_unique_path(url)

        new_page = page.copy(copy_param)
        # Should not clone menu if the page was cloned from one website to another
        # Eg: Cloning a generic page (no website) will create a page with a website, we can't clone menu (not same container)
        if clone_menu and new_page.website_id == page.website_id:
            menu = self.env['website.menu'].search([('page_id', '=', page_id)], limit=1)
            if menu:
                # If the page being cloned has a menu, clone it too
                menu.copy({'url': new_page.url, 'name': new_page.name, 'page_id': new_page.id})

        return new_page.url

    def unlink(self):
        # When a website_page is deleted, the ORM does not delete its
        # ir_ui_view. So we got to delete it ourself, but only if the
        # ir_ui_view is not used by another website_page.
        views_to_delete = self.view_id.filtered(
            lambda v: v.page_ids <= self and not v.inherit_children_ids
        )
        # Rebind self to avoid unlink already deleted records from `ondelete="cascade"`
        self = self - views_to_delete.page_ids
        views_to_delete.unlink()

        # Make sure website._get_menu_ids() will be recomputed
        self.env.registry.clear_cache()
        return super().unlink()

    def write(self, vals):
        for page in self:
            website_id = False
            if vals.get('website_id') or page.website_id:
                website_id = vals.get('website_id') or page.website_id.id

            # If URL has been edited, slug it
            if 'url' in vals:
                url = vals['url'] or ''
                redirect_old_url = redirect_type = None
                # TODO This should be done another way after the backend/frontend merge
                if isinstance(url, dict):
                    redirect_old_url = url.get('redirect_old_url')
                    redirect_type = url.get('redirect_type')
                    url = url.get('url')
                url = '/' + slugify(url, max_length=1024, path=True)
                if page.url != url:
                    url = self.env['website'].with_context(website_id=website_id).get_unique_path(url)
                    page.menu_ids.write({'url': url})
                    if redirect_old_url:
                        self.env['website.rewrite'].create({
                            'name': vals.get('name') or page.name,
                            'redirect_type': redirect_type,
                            'url_from': page.url,
                            'url_to': url,
                            'website_id': website_id,
                        })
                    # Sync website's homepage URL
                    website = self.env['website'].get_current_website()
                    page_url_normalized = {'homepage_url': page.url}
                    website._handle_homepage_url(page_url_normalized)
                    if website.homepage_url == page_url_normalized['homepage_url']:
                        website.homepage_url = url
                vals['url'] = url

            # If name has changed, check for key uniqueness
            if 'name' in vals and page.name != vals['name']:
                vals['key'] = self.env['website'].with_context(website_id=website_id).get_unique_key(slugify(vals['name']))
            if 'visibility' in vals:
                if vals['visibility'] != 'restricted_group':
                    vals['groups_id'] = False
        self.env.registry.clear_cache()  # write on page == write on view that invalid cache
        return super(Page, self).write(vals)

    def get_website_meta(self):
        self.ensure_one()
        return self.view_id.get_website_meta()

    @api.model
    def _search_get_detail(self, website, order, options):
        with_description = options['displayDescription']
        # Read access on website.page requires sudo.
        requires_sudo = True
        domain = [website.website_domain()]
        if not self.env.user.has_group('website.group_website_designer'):
            # Rule must be reinforced because of sudo.
            domain.append([('website_published', '=', True)])

        search_fields = ['name', 'url']
        fetch_fields = ['id', 'name', 'url']
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
            'website_url': {'name': 'url', 'type': 'text', 'truncate': False},
        }
        if with_description:
            search_fields.append('arch_db')
            fetch_fields.append('arch')
            mapping['description'] = {'name': 'arch', 'type': 'text', 'html': True, 'match': True}
        return {
            'model': 'website.page',
            'base_domain': domain,
            'requires_sudo': requires_sudo,
            'search_fields': search_fields,
            'fetch_fields': fetch_fields,
            'mapping': mapping,
            'icon': 'fa-file-o',
        }

    @api.model
    def _search_fetch(self, search_detail, search, limit, order):
        with_description = 'description' in search_detail['mapping']
        # Cannot rely on the super's _search_fetch because the search must be
        # performed among the most specific pages only.
        fields = search_detail['search_fields']
        base_domain = search_detail['base_domain']
        domain = self._search_build_domain(base_domain, search, fields, search_detail.get('search_extra'))
        most_specific_pages = self.env['website']._get_website_pages(
            domain=expression.AND(base_domain), order=order
        )
        results = most_specific_pages.filtered_domain(domain)  # already sudo

        if with_description and search and most_specific_pages:
            # Perform search in translations
            # TODO Remove when domains will support xml_translate fields
            query = sql.SQL("""
                SELECT DISTINCT {table}.id
                FROM {table}
                LEFT JOIN ir_ui_view v ON {table}.view_id = v.id
                WHERE (v.name ILIKE {search}
                OR COALESCE(v.arch_db->>{lang}, v.arch_db->>'en_US') ILIKE {search})
                AND {table}.id IN {ids}
                LIMIT {limit}
            """).format(
                table=sql.Identifier(self._table),
                search=sql.Placeholder('search'),
                lang=sql.Literal(self.env.lang or 'en_US'),
                ids=sql.Placeholder('ids'),
                limit=sql.Placeholder('limit'),
            )
            self.env.cr.execute(query, {
                'search': '%%%s%%' % escape_psql(search),
                'ids': tuple(most_specific_pages.ids),
                'limit': len(most_specific_pages.ids),
            })
            ids = {row[0] for row in self.env.cr.fetchall()}
            if ids:
                ids.update(results.ids)
                domains = search_detail['base_domain'].copy()
                domains.append([('id', 'in', list(ids))])
                domain = expression.AND(domains)
                model = self.sudo() if search_detail.get('requires_sudo') else self
                results = model.search(
                    domain,
                    limit=len(ids),
                    order=search_detail.get('order', order)
                )

        def filter_page(search, page, all_pages):
            # Search might have matched words in the xml tags and parameters therefore we make
            # sure the terms actually appear inside the text.
            text = '%s %s %s' % (page.name, page.url, text_from_html(page.arch))
            pattern = '|'.join([re.escape(search_term) for search_term in search.split()])
            return re.findall('(%s)' % pattern, text, flags=re.I) if pattern else False
        if search and with_description:
            results = results.filtered(lambda result: filter_page(search, result, results))
        return results[:limit], len(results)

    def action_page_debug_view(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.ui.view',
            'res_id': self.view_id.id,
            'view_mode': 'form',
            'view_id': self.env.ref('website.view_view_form_extend').id,
        }


# this is just a dummy function to be used as ormcache key
def _cached_response():
    pass
