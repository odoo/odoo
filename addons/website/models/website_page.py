# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os
import re
import time

from odoo.addons.base.models.ir_http import EXTENSION_TO_WEB_MIMETYPES
from odoo.addons.website.tools import text_from_html
from odoo import api, fields, models, tools, http
from odoo.fields import Domain
from odoo.tools import escape_psql, SQL
from odoo.tools.translate import _
from odoo.tools.safe_eval import safe_eval

logger = logging.getLogger(__name__)


class PageCanNotBeCached(Exception):
    def __init__(self, value=None):
        self.value = value
    pass


class WebsitePage(models.Model):
    _name = 'website.page'
    _inherits = {'ir.ui.view': 'view_id'}
    _inherit = [
        'website.published.multi.mixin',
        'website.searchable.mixin',
        'website.page_options.mixin',
    ]
    _description = 'Page'
    _order = 'website_id'

    url = fields.Char('Page URL', required=True)
    view_id = fields.Many2one('ir.ui.view', string='View', required=True, index=True, ondelete="cascade")

    view_write_uid = fields.Many2one('res.users', "Last Content Update by",
        related='view_id.write_uid')
    view_write_date = fields.Datetime("Last Content Update on",
        related='view_id.write_date')

    website_indexed = fields.Boolean('Is Indexed', default=True)
    date_publish = fields.Datetime('Publishing Date')
    menu_ids = fields.One2many('website.menu', 'page_id', 'Related Menus')
    is_in_menu = fields.Boolean(compute='_compute_website_menu')
    is_homepage = fields.Boolean(compute='_compute_is_homepage', string='Homepage')
    is_visible = fields.Boolean(compute='_compute_visible', string='Is Visible')
    is_new_page_template = fields.Boolean(string="New Page Template", help='Add this page to the "+New" page templates. It will be added to the "Custom" category.')

    # don't use mixin website_id but use website_id on ir.ui.view instead
    website_id = fields.Many2one(related='view_id.website_id', store=True, readonly=False, ondelete='cascade')
    arch = fields.Text(related='view_id.arch', readonly=False, depends_context=('website_id',))

    def _compute_is_homepage(self):
        website = self.env['website'].get_current_website()
        for page in self:
            page.is_homepage = page.url == (website.homepage_url or page.website_id == website and '/')

    def _compute_visible(self):
        for page in self:
            page.is_visible = page.website_published and (
                not page.date_publish or page.date_publish < fields.Datetime.now()
            )

    @api.depends('menu_ids')
    def _compute_website_menu(self):
        for page in self:
            page.is_in_menu = bool(page.menu_ids)

    # This update was added to make sure the mixin calculations are correct
    # (page.website_url > page.url).
    @api.depends('url')
    def _compute_website_url(self):
        for page in self:
            page.website_url = page.url

    @api.depends_context('uid')
    def _compute_can_publish(self):
        # Note: this `if`'s purpose it to optimize the way this is computed for
        # multiple records.
        if self.env.user.has_group('website.group_website_designer'):
            for record in self:
                record.can_publish = True
        else:
            super()._compute_can_publish()

    def _get_most_specific_pages(self):
        ''' Returns the most specific pages in self. '''
        ids = []
        previous_page = None
        page_keys = self.sudo().search(
            self.env['website'].browse(self.env.context.get('website_id')).website_domain()
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

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        if not default:
            return vals_list
        for page, vals in zip(self, vals_list):
            if not default.get('view_id'):
                new_view = page.view_id.copy({'website_id': default.get('website_id')})
                vals['view_id'] = new_view.id
                vals['key'] = new_view.key
            vals['url'] = default.get('url', self.env['website'].get_unique_path(page.url))
        return vals_list

    @api.model
    def clone_page(self, page_id, page_name=None, clone_menu=True):
        """ Clone a page, given its identifier
            :param page_id : website.page identifier
        """
        page = self.browse(int(page_id))
        copy_param = dict(name=page_name or page.name, website_id=self.env['website'].get_current_website().id)
        if page_name:
            url = '/' + self.env['ir.http']._slugify(page_name, max_length=1024, path=True)
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

        # Make sure website.is_menu_cache_disabled() will be recomputed
        if self:
            self.env.registry.clear_cache('templates')
        return super().unlink()

    def write(self, vals):
        for page in self:
            website_id = False
            if vals.get('website_id') or page.website_id:
                website_id = vals.get('website_id') or page.website_id.id

            # If URL has been edited, slug it
            if 'url' in vals:
                url = vals['url'] or ''
                url = '/' + self.env['ir.http']._slugify(url, max_length=1024, path=True)
                if page.url != url:
                    url = self.env['website'].with_context(website_id=website_id).get_unique_path(url)
                    page.menu_ids.write({'url': url})
                    # Sync website's homepage URL
                    website = self.env['website'].get_current_website()
                    page_url_normalized = {'homepage_url': page.url}
                    website._handle_homepage_url(page_url_normalized)
                    if website.homepage_url == page_url_normalized['homepage_url']:
                        website.homepage_url = url
                vals['url'] = url

            # If name has changed, check for key uniqueness
            if 'name' in vals and page.name != vals['name']:
                vals['key'] = self.env['website'].with_context(website_id=website_id).get_unique_key(self.env['ir.http']._slugify(vals['name'] or ''))
            if 'visibility' in vals:
                if vals['visibility'] != 'restricted_group':
                    vals['group_ids'] = False

        self.env.registry.clear_cache()  # write on page == write on view that invalid cache
        if 'url' in vals or 'visibility' in vals or 'group_ids' in vals:
            self.env.registry.clear_cache('templates')

        return super().write(vals)

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
        base_domain = Domain.AND(search_detail['base_domain'])
        domain = self._search_build_domain([base_domain], search, fields, search_detail.get('search_extra'))
        most_specific_pages = self.env['website']._get_website_pages(
            domain=base_domain, order=order
        )
        results = most_specific_pages.filtered_domain(domain)  # already sudo
        v_arch_db = self.env['ir.ui.view']._field_to_sql('v', 'arch_db')

        if with_description and search and most_specific_pages:
            # Perform search in translations
            # TODO Remove when domains will support xml_translate fields
            rows = self.env.execute_query(SQL(
                """
                SELECT DISTINCT %(table)s.id
                FROM %(table)s
                LEFT JOIN ir_ui_view v ON %(table)s.view_id = v.id
                WHERE (v.name ILIKE %(search)s
                OR %(v_arch_db)s ILIKE %(search)s)
                AND %(table)s.id IN %(ids)s
                LIMIT %(limit)s
                """,
                table=SQL.identifier(self._table),
                search=f"%{escape_psql(search)}%",
                v_arch_db=v_arch_db,
                ids=tuple(most_specific_pages.ids),
                limit=len(most_specific_pages.ids),
            ))
            ids = {row[0] for row in rows}
            if ids:
                ids.update(results.ids)
                domain = base_domain & Domain('id', 'in', ids)
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

    # website cache

    cache_time = fields.Integer(default=3600, help='Time to cache the page. (0 = no cache)')
    cache_key_expr = fields.Char(help='Expression (tuple) to evaluate the cached key. \nE.g.: "(request.params.get("currency"), )"')

    @api.model
    def _allow_to_use_cache(self, request):
        """ Can the future reponse and rendering come from the cache? """
        return (
            request.httprequest.method == "GET"
            and request.env.user._is_public()    # only cache for unlogged user
            and 'nocache' not in request.httprequest.args  # allow bypass cache / debug
        )

    @api.model
    def _allow_cache_insertion(self, layout):
        """ Will the rendering be added to the cache for all visitors and not
            contain any user information?
        """
        return True

    @api.model
    def _post_process_response_from_cache(self, request: http.Request, response: http.Response) -> None:
        # used for _register_website_track
        response._cached_view_id = self._get_page_info(request)['view_id']
        response._cached_page = self

    def _get_response(self, request):
        self.ensure_one()
        if self._allow_to_use_cache(request):
            try:
                response, cache_time = self._get_response_cached(request)
            except PageCanNotBeCached as notCache:
                if notCache.value:
                    return notCache.value[0]

            if response.time + cache_time > time.time():
                html = re.sub(r'csrf_token: "[^"]+"', f'csrf_token: {request.csrf_token(None)!r}', response.response[0])
                resp = http.Response(
                    headers=response.headers.copy(),
                    mimetype=response.mimetype,
                    content_type=response.content_type,
                    status=response.status,
                    response=[html],
                )
                self._post_process_response_from_cache(request, resp)
                return resp

        return self._get_response_raw(request)

    @api.model
    def _get_cache_key(self, request):
        # Always call me with super() AT THE END to have cache_key_expr appended as last element
        # It is the only way for end user to not use cache via expr.
        # E.g  (None if 'token' in request.params else 1,)  will bypass cache_time
        cache_key = (request.website.id, request.lang.code, request.httprequest.path, request.session.debug)
        cache_key_expr = self._get_page_info(request)['cache_key_expr']
        if cache_key_expr:  # e.g. (request.geoip.get('country_code'),)
            cache_key += safe_eval(cache_key_expr, {'request': request})
        return cache_key

    @tools.conditional(
        'xml' not in tools.config['dev_mode'],
        tools.ormcache('self._get_cache_key(request)', cache='templates.cached_values'),
    )
    def _get_response_cached(self, request) -> tuple[http.Response, int, str]:
        response = self._get_response_raw(request)
        result = (response, self.cache_time)

        if not response or not self.cache_time:
            raise PageCanNotBeCached(result)

        response.flatten()
        if not self._allow_cache_insertion(response.response[-1]):
            raise PageCanNotBeCached(result)

        return result

    def _get_response_raw(self, request) -> http.Response:
        req_page = request.httprequest.path

        # Force prefetch on all fetchable fields to get all data at once (e.g., 'website_meta').
        fields_to_fetch = [name for name, field in self._fields.items() if field.store and field.column_type]
        self.fetch(fields_to_fetch)

        # Force prefetch on all fetchable fields to get all data at once (e.g., 'website_meta').
        fields_to_fetch = [name for name, field in self.view_id._fields.items() if field.store and field.column_type]
        self.view_id.fetch(fields_to_fetch)

        if (
            (self.env.user.has_group('website.group_website_designer') or self.is_visible)
            and (
                # If a generic page (niche case) has been COWed and that COWed
                # page received a URL change, it should not let you access the
                # generic page anymore, despite having a different URL.
                self.website_id
                or self.view_id.id == self.env['ir.ui.view'].with_context(website_id=request.website.id)._get_cached_template_info(self.view_id.key)['id']
            )
        ):
            _, ext = os.path.splitext(req_page)
            response = request.render(self.view_id.id, {
                'main_object': self,
            }, mimetype=EXTENSION_TO_WEB_MIMETYPES.get(ext, 'text/html'))
            response.time = time.time()
            return response
        return False

    @api.model
    def _get_page_info(self, request) -> dict | None:
        if self._allow_to_use_cache(request):
            try:
                return self._get_page_info_cached(request)
            except PageCanNotBeCached:
                return None
        return self._get_page_info_raw(request)

    @tools.conditional(
        'xml' not in tools.config['dev_mode'],
        tools.ormcache('request.httprequest.path', cache='templates.cached_values'),
    )
    @api.model
    def _get_page_info_cached(self, request) -> dict | None:
        info = self._get_page_info_raw(request)
        if info is None:
            # Do not cache unknown page names.
            raise PageCanNotBeCached()
        return info

    @api.model
    def _get_page_info_raw(self, request) -> dict | None:
        req_page = request.httprequest.path

        # specific page first
        page_domain = Domain('url', '=', req_page) & request.website.website_domain()
        page = self.sudo().search_fetch(page_domain, order='website_id asc', limit=1)

        # case insensitive search
        if not page:
            page_domain = Domain('url', '=ilike', req_page) & request.website.website_domain()
            page = self.sudo().search_fetch(page_domain, order='website_id asc', limit=1)

        return page and {
            'id': page.id,
            'url': page.url,
            'cache_key_expr': page.cache_key_expr,
            'view_id': page.view_id.id,
        }
