# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import datetime
import os
import logging
import re
import requests
import werkzeug.urls
import werkzeug.utils
import werkzeug.wrappers
import zipfile

from hashlib import md5
from io import BytesIO
from itertools import islice
from lxml import etree, html
from markupsafe import escape as markup_escape
from textwrap import shorten
from werkzeug.exceptions import NotFound
from xml.etree import ElementTree as ET

import odoo

from odoo import http, models, fields, tools, _
from odoo.exceptions import AccessError, UserError
from odoo.fields import Domain
from odoo.http import request, SessionExpiredException
from odoo.tools import OrderedSet, escape_psql, html_escape as escape, py_to_js_locale
from odoo.tools.translate import LazyTranslate
from odoo.addons.base.models.ir_http import EXTENSION_TO_WEB_MIMETYPES
from odoo.addons.base.models.ir_qweb import QWebException
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.portal.controllers.web import Home
from odoo.addons.web.controllers.binary import Binary
from odoo.addons.web.controllers.session import Session
from odoo.addons.website.tools import get_base_domain
from odoo.tools.json import scriptsafe as json

_lt = LazyTranslate(__name__)
logger = logging.getLogger(__name__)

# Completely arbitrary limits
MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT = IMAGE_LIMITS = (1024, 768)
LOC_PER_SITEMAP = 45000
SITEMAP_CACHE_TIME = datetime.timedelta(hours=12)
MAX_FONT_FILE_SIZE = 10 * 1024 * 1024
SUPPORTED_FONT_EXTENSIONS = ['ttf', 'woff', 'woff2', 'otf']


class QueryURL:
    def __init__(self, path='', path_args=None, **args):
        self.path = path
        self.args = args
        self.path_args = OrderedSet(path_args or [])

    def __call__(self, path=None, path_args=None, **kw):
        path_prefix = path or self.path
        path = ''
        for key, value in self.args.items():
            kw.setdefault(key, value)
        slug = request.env['ir.http']._slug
        path_args = OrderedSet(path_args or []) | self.path_args
        paths, fragments = {}, []
        for key, value in kw.items():
            if value and key in path_args:
                if isinstance(value, models.BaseModel):
                    paths[key] = slug(value)
                else:
                    paths[key] = "%s" % value
            elif value:
                if isinstance(value, (list, set)):
                    fragments.append(
                        werkzeug.urls.url_encode([(key, item) for item in value if item])
                    )
                else:
                    fragments.append(werkzeug.urls.url_encode([(key, value)]))
        for key in path_args:
            value = paths.get(key)
            if value is not None:
                path += '/' + key + '/' + value
        if fragments:
            path += '?' + '&'.join(fragments)
        if not path.startswith(path_prefix):
            path = path_prefix + path
        return path


class Website(Home):

    @http.route('/', auth="public", website=True, sitemap=True)
    def index(self, **kw):
        """ The goal of this controller is to make sure we don't serve a 404 as
        the website homepage. As this is the website entry point, serving a 404
        is terrible.
        There is multiple fallback mechanism to prevent that:
        - If homepage URL is set (empty by default), serve the website.page
        matching it
        - If homepage URL is set (empty by default), serve the controller
        matching it
        - If homepage URL is not set, serve the `/` website.page
        - Serve the first accessible menu as last resort. It should be relevant
        content, at least better than a 404
        - Serve 404
        Most DBs will just have a website.page with '/' as URL and keep the
        homepage_url setting empty.
        """
        # prefetch all menus (it will prefetch website.page too)
        top_menu = request.website.menu_id

        homepage_url = request.website._get_cached('homepage_url')
        if homepage_url and homepage_url != '/':
            request.reroute(homepage_url)

        # Check for page
        website_page = request.env['ir.http']._serve_page()
        if website_page:
            return website_page

        # Check for controller
        if homepage_url and homepage_url != '/':
            try:
                rule, args = request.env['ir.http']._match(homepage_url)
                return request._serve_ir_http(rule, args)
            except (AccessError, NotFound, SessionExpiredException):
                pass

        # Fallback on first accessible menu
        def is_reachable(menu):
            return menu.is_visible and menu.url not in ('/', '', '#') and not menu.url.startswith(('/?', '/#', ' '))

        reachable_menus = top_menu.child_id.filtered(is_reachable)
        if reachable_menus:
            return request.redirect(reachable_menus[0].url)

        raise request.not_found()

    @http.route('/website/force/<int:website_id>', type='http', auth="user", website=True, sitemap=False, multilang=False, readonly=True)
    def website_force(self, website_id, path='/', isredir=False, **kw):
        """ To switch from a website to another, we need to force the website in
        session, AFTER landing on that website domain (if set) as this will be a
        different session.
        """
        if not (request.env.user.has_group('website.group_multi_website')
           and request.env.user.has_group('website.group_website_restricted_editor')):
            # The user might not be logged in on the forced website, so he won't
            # have rights. We just redirect to the path as the user is already
            # on the domain (basically a no-op as it won't change domain or
            # force website).
            # Website 1 : 127.0.0.1 (admin)
            # Website 2 : 127.0.0.2 (not logged in)
            # Click on "Website 2" from Website 1
            return request.redirect(path)

        website = request.env['website'].browse(website_id)

        if not isredir and website.domain:
            domain_from = request.httprequest.environ.get('HTTP_HOST', '')
            domain_to = get_base_domain(website.domain)
            if domain_from != domain_to:
                # redirect to correct domain for a correct routing map
                url_to = tools.urls.urljoin(
                    website.domain,
                    '/website/force/%s?isredir=1&path=%s' % (website.id, path),
                )
                return request.redirect(url_to)
        website._force()
        return request.redirect(path)

    @http.route(['/@/', '/@/<path:path>'], type='http', auth='public', website=True, sitemap=False, multilang=False, readonly=True)
    def client_action_redirect(self, path='', **kw):
        """ Redirect internal users to the backend preview of the requested path
        URL (client action iframe).
        Non internal users will be redirected to the regular frontend version of
        that URL.
        """
        path = '/' + path
        mode_edit = bool(kw.pop('enable_editor', False))
        if kw:
            path += '?' + werkzeug.urls.url_encode(kw)

        if request.env.user._is_internal():
            path = request.website.get_client_action_url(path, mode_edit)

        return request.redirect(path)

    # ------------------------------------------------------
    # Login - overwrite of the web login so that regular users are redirected to the backend
    # while portal users are redirected to the frontend by default
    # ------------------------------------------------------

    def _login_redirect(self, uid, redirect=None):
        """ Redirect regular users (employees) to the backend) and others to
        the frontend
        """
        if not redirect and request.params.get('login_success'):
            if request.env['res.users'].browse(uid)._is_internal():
                redirect = '/odoo?' + request.httprequest.query_string.decode()
            else:
                redirect = '/my'
        return super()._login_redirect(uid, redirect=redirect)

    # Force website=True + auth='public', required for login form layout
    @http.route(website=True, auth="public", sitemap=False)
    def web_login(self, *args, **kw):
        return super().web_login(*args, **kw)

    # ------------------------------------------------------
    # Business
    # ------------------------------------------------------

    @http.route('/website/get_languages', type='jsonrpc', auth="user", website=True, readonly=True)
    def website_languages(self, **kwargs):
        return [(py_to_js_locale(lg.code), lg.url_code, lg.name) for lg in request.website.language_ids]

    @http.route('/website/lang/<lang>', type='http', auth="public", website=True, multilang=False)
    def change_lang(self, lang, r='/', **kwargs):
        """ :param lang: supposed to be value of `url_code` field """
        if lang == 'default':
            lang = request.website.default_lang_id.url_code
            r = '/%s%s' % (lang, r or '/')
        lang_code = request.env['res.lang']._get_data(url_code=lang).code or lang
        # replace context with correct lang, to avoid that the url_for of request.redirect remove the
        # default lang in case we switch from /fr -> /en with /en as default lang.
        request.update_context(lang=lang_code)
        redirect = request.redirect(r or ('/%s' % lang))
        redirect.set_cookie('frontend_lang', lang_code)
        return redirect

    @http.route(['/website/country_infos/<model("res.country"):country>'], type='jsonrpc', auth="public", methods=['POST'], website=True, readonly=True)
    def country_infos(self, country, **kw):
        fields = country.get_address_fields()
        return dict(fields=fields, states=[(st.id, st.name, st.code) for st in country.state_ids], phone_code=country.phone_code)

    @http.route(['/robots.txt'], type='http', auth="public", website=True, multilang=False, sitemap=False)
    def robots(self, **kwargs):
        # Don't use `request.website.domain` here, the template is in charge of
        # detecting if the current URL is the domain one and add a `Disallow: /`
        # if it's not the case to prevent the crawler to continue.
        return request.render('website.robots', {
            'allowed_routes': self._get_allowed_robots_routes(),
            'url_root': request.httprequest.url_root,
        }, mimetype='text/plain')

    @http.route('/sitemap.xml', type='http', auth="public", website=True, multilang=False, sitemap=False)
    def sitemap_xml_index(self, **kwargs):
        current_website = request.website
        Attachment = request.env['ir.attachment'].sudo()
        View = request.env['ir.ui.view'].sudo()
        mimetype = 'application/xml;charset=utf-8'
        content = None
        url_root = request.httprequest.url_root
        # For a same website, each domain has its own sitemap (cache)
        hashed_url_root = md5(url_root.encode()).hexdigest()[:8]
        sitemap_base_url = '/sitemap-%d-%s' % (current_website.id, hashed_url_root)

        def create_sitemap(url, content):
            return Attachment.create({
                'raw': content.encode(),
                'mimetype': mimetype,
                'type': 'binary',
                'name': url,
                'url': url,
            })
        dom = [('url', '=', '%s.xml' % sitemap_base_url), ('type', '=', 'binary')]
        sitemap = Attachment.search(dom, limit=1)
        if sitemap:
            # Check if stored version is still valid
            create_date = fields.Datetime.from_string(sitemap.create_date)
            delta = datetime.datetime.now() - create_date
            if delta < SITEMAP_CACHE_TIME:
                content = base64.b64decode(sitemap.datas)

        if not content:
            # Remove all sitemaps in ir.attachments as we're going to regenerated them
            dom = [('type', '=', 'binary'), '|', ('url', '=like', '%s-%%.xml' % sitemap_base_url),
                   ('url', '=', '%s.xml' % sitemap_base_url)]
            sitemaps = Attachment.search(dom)
            sitemaps.unlink()

            pages = 0
            locs = request.website.with_user(request.website.user_id)._enumerate_pages()
            while True:
                values = {
                    'locs': islice(locs, 0, LOC_PER_SITEMAP),
                    'url_root': url_root[:-1],
                }
                urls = View._render_template('website.sitemap_locs', values)
                if urls.strip():
                    content = View._render_template('website.sitemap_xml', {'content': urls})
                    pages += 1
                    last_sitemap = create_sitemap('%s-%d.xml' % (sitemap_base_url, pages), content)
                else:
                    break

            if not pages:
                return request.not_found()
            elif pages == 1:
                # rename the -id-page.xml => -id.xml
                last_sitemap.write({
                    'url': "%s.xml" % sitemap_base_url,
                    'name': "%s.xml" % sitemap_base_url,
                })
            else:
                # TODO: in master/saas-15, move current_website_id in template directly
                pages_with_website = ["%d-%s-%d" % (current_website.id, hashed_url_root, p) for p in range(1, pages + 1)]

                # Sitemaps must be split in several smaller files with a sitemap index
                content = View._render_template('website.sitemap_index_xml', {
                    'pages': pages_with_website,
                    # URLs inside the sitemap index have to be on the same
                    # domain as the sitemap index itself
                    'url_root': url_root,
                })
                create_sitemap('%s.xml' % sitemap_base_url, content)

        return request.make_response(content, [('Content-Type', mimetype)])

    # if not icon provided in DOM, browser tries to access /favicon.ico, eg when
    # opening an order pdf
    @http.route(['/favicon.ico'], type='http', auth='public', website=True, multilang=False, sitemap=False, readonly=True)
    def favicon(self, **kw):
        website = request.website
        response = request.redirect(website.image_url(website, 'favicon'), code=301)
        response.headers['Cache-Control'] = 'public, max-age=%s' % http.STATIC_CACHE_LONG
        return response

    def sitemap_website_info(env, rule, qs):
        website = env['website'].get_current_website()
        if not (
            website.is_view_active('website.website_info')
            and website.is_view_active('website.show_website_info')
        ):
            # avoid 404 or blank page in sitemap
            return False

        if not qs or qs.lower() in '/website/info':
            yield {'loc': '/website/info'}

    @http.route('/website/info', type='http', auth="public", website=True, sitemap=sitemap_website_info, readonly=True, list_as_website_content=_lt("Website Information"))
    def website_info(self, **kwargs):
        Module = request.env['ir.module.module'].sudo()
        apps = Module.search([('state', '=', 'installed'), ('application', '=', True)])
        l10n = Module.search([('state', '=', 'installed'), ('name', '=like', 'l10n_%')])
        values = {
            'apps': apps,
            'l10n': l10n,
            'version': odoo.service.common.exp_version()
        }
        return request.render('website.website_info', values)

    @http.route(['/website/configurator', '/website/configurator/<int:step>'], type='http', auth="user", website=True, multilang=False)
    def website_configurator(self, step=1, **kwargs):
        if not request.env.user.has_group('website.group_website_designer'):
            raise werkzeug.exceptions.NotFound()
        if request.website.configurator_done:
            return request.redirect('/')
        if request.env.lang != request.website.default_lang_id.code:
            return request.redirect('/%s%s' % (request.website.default_lang_id.url_code, request.httprequest.path))
        action_url = f"/odoo/action-website.website_configurator?menu_id={request.env.ref('website.menu_website_configuration').id}"
        if step > 1:
            action_url += '&step=' + str(step)
        return request.redirect(action_url)

    @http.route(['/website/social/<string:social>'], type='http', auth="public", website=True, sitemap=False)
    def social(self, social, **kwargs):
        url = getattr(request.website, 'social_%s' % social, False)
        if not url:
            raise werkzeug.exceptions.NotFound()
        return request.redirect(url, local=False)

    @http.route('/website/get_suggested_links', type='jsonrpc', auth="user", website=True, readonly=True)
    def get_suggested_link(self, needle, limit=10):
        current_website = request.website

        matching_pages = []
        for page in current_website.search_pages(needle, limit=int(limit)):
            matching_pages.append({
                'value': page['loc'],
                'label': 'name' in page and '%s (%s)' % (page['loc'], page['name']) or page['loc'],
            })
        matching_urls = {match['value'] for match in matching_pages}

        matching_last_modified = []
        last_modified_pages = current_website._get_website_pages(order='write_date desc', limit=5)
        for url, name in last_modified_pages.mapped(lambda p: (p.url, p.name)):
            if needle.lower() in name.lower() or needle.lower() in url.lower() and url not in matching_urls:
                matching_last_modified.append({
                    'value': url,
                    'label': '%s (%s)' % (url, name),
                })

        suggested_controllers = []
        for name, url, mod in current_website.get_suggested_controllers():
            if needle.lower() in name.lower() or needle.lower() in url.lower():
                module_sudo = mod and request.env.ref('base.module_%s' % mod, False).sudo()
                icon = mod and '%s' % (module_sudo and module_sudo.icon or mod) or ''
                suggested_controllers.append({
                    'value': url,
                    'icon': icon,
                    'label': '%s (%s)' % (url, name),
                })

        return {
            'matching_pages': sorted(matching_pages, key=lambda o: o['label']),
            'others': [
                dict(title=_('Last modified pages'), values=matching_last_modified),
                dict(title=_('Apps url'), values=suggested_controllers),
            ]
        }

    @http.route('/website/save_session_layout_mode', type='jsonrpc', auth='public', website=True, readonly=True)
    def save_session_layout_mode(self, layout_mode, view_id):
        assert layout_mode in ('grid', 'list'), "Invalid layout mode"
        request.session[f'website_{view_id}_layout_mode'] = layout_mode

    @http.route('/website/snippet/filters', type='jsonrpc', auth='public', website=True, readonly=True)
    def get_dynamic_filter(self, filter_id, **kwargs):
        dynamic_filter_sudo = request.env['website.snippet.filter'].sudo()
        if filter_id:
            dynamic_filter_sudo = dynamic_filter_sudo.search(
                Domain('id', '=', filter_id) & request.website.website_domain()
            )
        return dynamic_filter_sudo._render(**kwargs) or []

    @http.route('/website/snippet/options_filters', type='jsonrpc', auth='user', website=True, readonly=True)
    def get_dynamic_snippet_filters(self, model_name=None, search_domain=None):
        if not request.env.user.has_group('website.group_website_restricted_editor'):
            raise werkzeug.exceptions.NotFound()
        domain = request.website.website_domain()
        if search_domain:
            search_domain = Domain(search_domain)
            assert all(condition.field_expr in request.env['website.snippet.filter']._fields for condition in search_domain.iter_conditions())
            domain &= search_domain
        if model_name:
            domain &= (
                Domain('filter_id.model_id', '=', model_name)
                | Domain('action_server_id.model_id.model', '=', model_name)
            )
        dynamic_filter = request.env['website.snippet.filter'].sudo().search_read(
            domain, ['id', 'name', 'limit', 'model_name', 'help'], order='id asc'
        )
        return dynamic_filter

    @http.route('/website/snippet/filter_templates', type='jsonrpc', auth='public', website=True, readonly=True)
    def get_dynamic_snippet_templates(self, filter_name=False):
        domain = [['key', 'ilike', '.dynamic_filter_template_'], ['type', '=', 'qweb']]
        if filter_name:
            domain.append(['key', 'ilike', escape_psql('_%s_' % filter_name)])
        templates = request.env['ir.ui.view'].sudo().search_read(domain, ['key', 'name', 'arch_db'])

        for t in templates:
            children = etree.fromstring(t.pop('arch_db')).getchildren()
            attribs = children and children[0].attrib or {}
            t['numOfEl'] = attribs.get('data-number-of-elements')
            t['numOfElSm'] = attribs.get('data-number-of-elements-sm')
            t['numOfElFetch'] = attribs.get('data-number-of-elements-fetch')
            t['rowPerSlide'] = attribs.get('data-row-per-slide')
            t['arrowPosition'] = attribs.get('data-arrow-position')
            t['extraClasses'] = attribs.get('data-extra-classes')
            t['extraSnippetClasses'] = attribs.get('data-extra-snippet-classes')
            t['containerClasses'] = attribs.get('data-container-classes')
            t['contentClasses'] = attribs.get('data-content-classes')
            t['columnClasses'] = attribs.get('data-column-classes')
            t['thumb'] = attribs.get('data-thumb')
        return templates

    @http.route('/website/get_current_currency', type='jsonrpc', auth="public", website=True, readonly=True)
    def get_current_currency(self, **kwargs):
        return {
            'id': request.website.company_id.currency_id.id,
            'symbol': request.website.company_id.currency_id.symbol,
            'position': request.website.company_id.currency_id.position,
        }

    # --------------------------------------------------------------------------
    # Search Bar
    # --------------------------------------------------------------------------

    def _get_search_order(self, order):
        # OrderBy will be parsed in orm and so no direct sql injection
        # id is added to be sure that order is a unique sort key
        order = order or 'name ASC'
        return 'is_published desc, %s, id desc' % order

    @http.route('/website/snippet/autocomplete', type='jsonrpc', auth='public', website=True, readonly=True)
    def autocomplete(self, search_type=None, term=None, order=None, limit=5, max_nb_chars=999, options=None):
        """
        Returns list of results according to the term and options

        :param str search_type: indicates what to search within, 'all' matches all available types
        :param str term: search term written by the user
        :param str order:
        :param int limit: number of results to consider, defaults to 5
        :param int max_nb_chars: max number of characters for text fields
        :param dict options: options map containing
            allowFuzzy: enables the fuzzy matching when truthy
            fuzzy (boolean): True when called after finding a name through fuzzy matching

        :returns: dict (or False if no result) containing
            - 'results' (list): results (only their needed field values)
                    note: the monetary fields will be strings properly formatted and
                    already containing the currency
            - 'results_count' (int): the number of results in the database
                    that matched the search query
            - 'parts' (dict): presence of fields across all results
            - 'fuzzy_search': search term used instead of requested search
        """
        order = self._get_search_order(order)
        options = options or {}
        results_count, search_results, fuzzy_term = request.website._search_with_fuzzy(search_type, term, limit, order, options)
        if not results_count:
            return {
                'results': [],
                'results_count': 0,
                'parts': {},
            }
        term = fuzzy_term or term
        search_results = request.website._search_render_results(search_results, limit)

        mappings = []
        results_data = []
        for search_result in search_results:
            results_data += search_result['results_data']
            mappings.append(search_result['mapping'])
        if search_type == 'all':
            # Only supported order for 'all' is on name
            results_data.sort(key=lambda r: r.get('name', ''), reverse='name desc' in order)
        results_data = results_data[:limit]
        result = []
        for record in results_data:
            mapping = record['_mapping']
            mapped = {
                '_fa': record.get('_fa'),
            }
            for mapped_name, field_meta in mapping.items():
                value = record.get(field_meta.get('name'))
                if not value:
                    mapped[mapped_name] = ''
                    continue
                field_type = field_meta.get('type')
                if field_type == 'text':
                    if value and field_meta.get('truncate', True):
                        value = shorten(value, max_nb_chars, placeholder='...')
                    if field_meta.get('match') and value and term:
                        pattern = '|'.join(map(re.escape, term.split()))
                        if pattern:
                            parts = re.split(f'({pattern})', value, flags=re.IGNORECASE)
                            if len(parts) > 1:
                                value = request.env['ir.ui.view'].sudo()._render_template(
                                    "website.search_text_with_highlight",
                                    {'parts': parts}
                                )
                                field_type = 'html'

                if field_type not in ('image', 'binary') and ('ir.qweb.field.%s' % field_type) in request.env:
                    opt = {}
                    if field_type == 'monetary':
                        opt['display_currency'] = options['display_currency']
                    value = request.env[('ir.qweb.field.%s' % field_type)].value_to_html(value, opt)
                mapped[mapped_name] = escape(value)
            result.append(mapped)

        return {
            'results': result,
            'results_count': results_count,
            'parts': {key: True for mapping in mappings for key in mapping},
            'fuzzy_search': fuzzy_term,
        }

    def _get_page_search_options(self, **post):
        return {
            'displayDescription': False,
            'displayDetail': False,
            'displayExtraDetail': False,
            'displayExtraLink': False,
            'displayImage': False,
            'allowFuzzy': not post.get('noFuzzy'),
        }

    @http.route(['/pages', '/pages/page/<int:page>'], type='http', auth="public", website=True, sitemap=False, readonly=True)
    def pages_list(self, page=1, search='', **kw):
        options = self._get_page_search_options(**kw)
        step = 50
        pages_count, details, fuzzy_search_term = request.website._search_with_fuzzy(
            "pages", search, limit=page * step, order='name asc, website_id desc, id',
            options=options)
        pages = details[0].get('results', request.env['website.page'])

        pager = portal_pager(
            url="/pages",
            url_args={'search': search},
            total=pages_count,
            page=page,
            step=step
        )

        pages = pages[(page - 1) * step:page * step]

        values = {
            'pager': pager,
            'pages': pages,
            'search': fuzzy_search_term or search,
            'search_count': pages_count,
            'original_search': fuzzy_search_term and search,
        }
        return request.render("website.list_website_public_pages", values)

    def _get_hybrid_search_options(self, **post):
        return {
            'displayDescription': True,
            'displayDetail': True,
            'displayExtraDetail': True,
            'displayExtraLink': True,
            'displayImage': True,
            'allowFuzzy': not post.get('noFuzzy'),
        }

    @http.route([
        '/website/search',
        '/website/search/page/<int:page>',
        '/website/search/<string:search_type>',
        '/website/search/<string:search_type>/page/<int:page>',
    ], type='http', auth="public", website=True, sitemap=False, readonly=True)
    def hybrid_list(self, page=1, search='', search_type='all', **kw):
        if not search:
            return request.render("website.list_hybrid")

        options = self._get_hybrid_search_options(**kw)
        data = self.autocomplete(search_type=search_type, term=search, order='name asc', limit=500, max_nb_chars=200, options=options)

        results = data.get('results', [])
        search_count = len(results)
        parts = data.get('parts', {})

        step = 50
        pager = portal_pager(
            url="/website/search/%s" % search_type,
            url_args={'search': search},
            total=search_count,
            page=page,
            step=step
        )

        results = results[(page - 1) * step:page * step]

        values = {
            'pager': pager,
            'results': results,
            'parts': parts,
            'search': search,
            'fuzzy_search': data.get('fuzzy_search'),
            'search_count': search_count,
        }
        return request.render("website.list_hybrid", values)

    # ------------------------------------------------------
    # Edit
    # ------------------------------------------------------

    @http.route(['/website/add', '/website/add/<path:path>'], type='http', auth="user", website=True, methods=['POST'])
    def pagenew(self, path="", add_menu=False, template=False, redirect=False, **kwargs):
        # for supported mimetype, get correct default template
        _, ext = os.path.splitext(path)
        ext_special_case = ext != '.html' and ext in EXTENSION_TO_WEB_MIMETYPES

        if not template and ext_special_case:
            default_templ = 'website.default_%s' % ext.lstrip('.')
            if request.env.ref(default_templ, False):
                template = default_templ

        template = template and dict(template=template) or {}
        website_id = kwargs.get('website_id')
        if website_id:
            website = request.env['website'].browse(int(website_id))
            website._force()
        page = request.env['website'].new_page(path, add_menu=add_menu, sections_arch=kwargs.get('sections_arch'), **template)
        url = page['url']
        # In case the page is created through the 404 "Create Page" button, the
        # URL may use special characters which are slugified on page creation.
        # If that URL is also a menu, we update it accordingly.
        # NB: we don't want to slugify on menu creation as it could redirect
        # towards files (with spaces, apostrophes, etc.).
        menu = request.env['website.menu'].search([('url', '=', '/' + path)])
        if menu:
            menu.page_id = page['page_id']

        if redirect:
            if ext_special_case:  # redirect non html pages to backend to edit
                return request.redirect(f"/odoo/ir.ui.view/{page.get('view_id')}")
            return request.redirect(request.env['website'].get_client_action_url(url, True))

        if ext_special_case:
            return json.dumps({'view_id': page.get('view_id')})
        return json.dumps({'url': url})

    @http.route('/website/get_new_page_templates', type='jsonrpc', auth='user', website=True, readonly=True)
    def get_new_page_templates(self, **kw):
        View = request.env['ir.ui.view']
        result = []
        groups_html = View._render_template("website.new_page_template_groups")
        groups_el = etree.fromstring(f'<data>{groups_html}</data>')
        for group_el in groups_el.getchildren():
            group = {
                'id': group_el.attrib['id'],
                'title': group_el.text,
                'templates': [],
            }
            if group_el.attrib['id'] == 'custom':
                for page in request.website._get_website_pages(domain=[('is_new_page_template', '=', True)]):
                    html_tree = html.fromstring(View.with_context(inherit_branding=False)._render_template(
                        page.key,
                    ))
                    wrap_el = html_tree.xpath('//div[@id="wrap"]')[0]
                    group['templates'].append({
                        'key': page.key,
                        'template': html.tostring(wrap_el),
                        'name': page.name,
                    })
                group['is_custom'] = True
                result.append(group)
                continue
            for template in View.search([
                ('mode', '=', 'primary'),
                ('key', 'like', escape_psql(f'new_page_template_sections_{group["id"]}_')),
            ], order='key'):
                try:
                    html_tree = html.fromstring(View.with_context(inherit_branding=False)._render_template(
                        template.key,
                    ))
                    for section_el in html_tree.xpath("//section[@data-snippet]"):
                        # data-snippet must be the short general name
                        snippet = section_el.attrib['data-snippet']
                        # Because the templates are generated from specific
                        # t-snippet-calls such as:
                        # "website.new_page_template_about_0_s_text_block",
                        # the generated data-snippet looks like:
                        # "new_page_template_about_0_s_text_block"
                        # while it should be "s_text_block" only.
                        if '_s_' in snippet:
                            section_el.attrib['data-snippet'] = f's_{snippet.split("_s_")[-1]}'

                    group['templates'].append({
                        'key': template.key,
                        'template': html.tostring(html_tree),
                    })
                except QWebException as qe:
                    # Do not fail if theme is not compatible.
                    logger.warning("Theme not compatible with template %r: %s", template.key, qe)
            if group['templates']:
                result.append(group)
        return result

    @http.route('/website/save_xml', type='jsonrpc', auth='user', website=True)
    def save_xml(self, view_id, arch):
        request.env['ir.ui.view'].browse(view_id).with_context(lang=request.website.default_lang_id.code).arch = arch

    @http.route("/website/get_switchable_related_views", type="jsonrpc", auth="user", website=True, readonly=True)
    def get_switchable_related_views(self, key):
        views = request.env["ir.ui.view"].get_related_views(key, bundles=False).filtered(lambda v: v.customize_show)
        views = views.sorted(key=lambda v: (v.inherit_id.id, v.name))
        return views.with_context(display_website=False).read(['name', 'id', 'key', 'xml_id', 'active', 'inherit_id'])

    @http.route('/website/reset_template', type='jsonrpc', auth='user', methods=['POST'])
    def reset_template(self, view_id, mode='soft', **kwargs):
        """ This method will try to reset a broken view.
        Given the mode, the view can either be:
        - Soft reset: restore to previous architecture.
        - Hard reset: it will read the original `arch` from the XML file if the
        view comes from an XML file (arch_fs).
        """
        view = request.env['ir.ui.view'].browse(int(view_id))
        # Deactivate COW to not fix a generic view by creating a specific
        view.with_context(website_id=None).reset_arch(mode)
        return True

    @http.route(['/website/seo_suggest'], type='jsonrpc', auth="user", website=True, readonly=True)
    def seo_suggest(self, keywords=None, lang=None):
        """
        Suggests search keywords based on a given input using Google's
        autocomplete API.

        This method takes in a `keywords` string and an optional `lang`
        parameter that defines the language and geographical region for
        tailoring search suggestions. It sends a request to Google's
        autocomplete service and returns the search suggestions in JSON format.

        :param str keywords: the keyword string for which suggestions
            are needed.
        :param str lang: a string representing the language and geographical
            location, formatted as:
            - `language_territory@modifier`, where:
                - `language`: 2-letter ISO language code (e.g., "en" for
                  English).
                - `territory`: Optional, 2-letter country code (e.g., "US" for
                  United States).
                - `modifier`: Optional, generally script variant (e.g.,
                  "latin").
            If `lang` is not provided or does not match the expected format, the
            default language is set to English (`en`) and the territory to the
            United States (`US`).

        :returns: JSON list of strings
            A list of suggested keywords returned by Google's autocomplete
            service. If no suggestions are found or if there's an error (e.g.,
            connection issues), an empty list is returned.
        """
        pattern = r'^([a-zA-Z]+)(?:_(\w+))?(?:@(\w+))?$'
        match = re.match(pattern, lang)
        language = [match.group(1), match.group(2) or ''] if match else ['en', 'US']
        url = "http://google.com/complete/search"
        try:
            req = requests.get(url, params={
                'ie': 'utf8', 'oe': 'utf8', 'output': 'toolbar', 'q': keywords, 'hl': language[0], 'gl': language[1]})
            req.raise_for_status()
            response = req.content
        except OSError:
            return []
        xmlroot = ET.fromstring(response)
        return json.dumps([sugg[0].attrib['data'] for sugg in xmlroot if len(sugg) and sugg[0].attrib['data']])

    @http.route(['/website/get_alt_images'], type='jsonrpc', auth="user", website=True)
    def get_alt_images(self, models):
        result = []
        for model in models:
            record = request.env[model['model']].browse(model['id'])
            model['field'] = 'arch_db' if model['field'] == 'arch' else model['field']
            tree = html.fromstring(str(record[model['field']]))
            for index, el in enumerate(tree.xpath('//img')):
                role = el.get('role')
                decorative = role == "presentation"
                alt = el.get('alt')
                if not decorative or alt is None:
                    result.append({
                        "src": el.get("src"),
                        "alt": alt or "",
                        "decorative": False,
                        "updated": False,
                        "res_model": model['model'],
                        "res_id": model['id'],
                        "id": f"{model['model']}-{model['id']}-{index}",
                        "field": model.get('field'),
                    })
        return json.dumps(result)

    @http.route(['/website/update_alt_images'], type='jsonrpc', auth="user", website=True)
    def update_alt_images(self, imgs):
        if not request.env.user.has_group('website.group_website_restricted_editor'):
            raise werkzeug.exceptions.Forbidden()
        for img in imgs:
            record = request.env[img['res_model']].browse(img['res_id'])
            if not record.has_access('write'):
                continue
            img['field'] = 'arch_db' if img['field'] == 'arch' else img['field']
            tree = html.fromstring(str(record[img['field']]))
            modified = False
            for index, element in enumerate(tree.xpath('//img')):
                imgId = f"{img['res_model']}-{img['res_id']}-{index!s}"
                if imgId == img['id']:
                    if (img['decorative']):
                        element.set('alt', '')
                        element.set('role', 'presentation')
                    else:
                        element.set('alt', markup_escape(img['alt']))
                        element.attrib.pop('role', None)
                    modified = True
            if modified:
                new_html_content = html.tostring(tree, encoding='unicode', method='html')
                record.write({img['field']: new_html_content})

    @http.route(['/website/update_broken_links'], type='jsonrpc', auth="user", website=True)
    def update_broken_links(self, links):
        if not request.env.user.has_group('website.group_website_restricted_editor'):
            raise werkzeug.exceptions.Forbidden()
        for link in links:
            record = request.env[link['res_model']].browse(link['res_id'])
            if not record.has_access('write'):
                continue
            link['field'] = 'arch_db' if link['field'] == 'arch' else link['field']
            tree = html.fromstring(str(record[link['field']]))
            modified = False
            for element in tree.xpath('//a'):
                href = element.get('href')
                if href and (link['oldLink'] == href or link['oldLink'] == href + '/'):
                    if link['remove']:
                        element.drop_tag()
                    else:
                        element.set('href', markup_escape(link['newLink']))
                    modified = True
            if modified:
                new_html_content = html.tostring(tree, encoding='unicode', method='html')
                record.write({link['field']: new_html_content})

    @http.route(['/website/get_seo_data'], type='jsonrpc', auth="user", website=True, readonly=True)
    def get_seo_data(self, res_id, res_model):
        if not request.env.user.has_group('website.group_website_restricted_editor'):
            # Still ok if user can access the record anyway.
            try:
                record = request.env[res_model].browse(res_id)
                record.check_access('write')
            except AccessError:
                raise werkzeug.exceptions.Forbidden()

        fields = ['website_meta_title', 'website_meta_description', 'website_meta_keywords', 'website_meta_og_img']
        res = {'can_edit_seo': True}
        record = request.env[res_model].browse(res_id)
        if res_model == 'website.page':
            fields.extend(['website_indexed', 'website_id'])
            res["website_is_published"] = record.website_published

        try:
            request.website._check_user_can_modify(record)
        except AccessError:
            res['can_edit_seo'] = False
        if request.env.user.has_group('website.group_website_restricted_editor'):
            record = record.sudo()

        res.update(record.read(fields)[0])
        res['has_social_default_image'] = request.website.has_social_default_image

        if res_model not in ('website.page', 'ir.ui.view') and 'seo_name' in record:  # allow custom slugify
            res['seo_name_default'] = request.env['ir.http']._slugify(record.display_name or '')  # default slug, if seo_name become empty
            res['seo_name'] = record.seo_name and request.env['ir.http']._slugify(record.seo_name) or ''

        return res

    @http.route(['/website/check_can_modify_any'], type='jsonrpc', auth="user", website=True, readonly=True)
    def check_can_modify_any(self, records):
        if not request.env.user.has_group('website.group_website_restricted_editor'):
            raise werkzeug.exceptions.Forbidden()
        first_error = None
        for rec in records:
            try:
                record = request.env[rec['res_model']].browse(rec['res_id'])
                request.website._check_user_can_modify(record)
                return True
            except AccessError as e:
                if not first_error:
                    first_error = e
                continue
        raise first_error

    @http.route(['/google<string(length=16):key>.html'], type='http', auth="public", website=True, sitemap=False, readonly=True)
    def google_console_search(self, key, **kwargs):
        if not request.website.google_search_console:
            logger.warning('Google Search Console not enable')
            raise werkzeug.exceptions.NotFound()
        gsc = request.website.google_search_console
        trusted = gsc[gsc.startswith('google') and len('google'):gsc.endswith('.html') and -len('.html') or None]

        if key != trusted:
            if key.startswith(trusted):
                request.website.sudo().google_search_console = "google%s.html" % key
            else:
                logger.warning('Google Search Console %s not recognize' % key)
                raise werkzeug.exceptions.NotFound()

        return request.make_response("google-site-verification: %s" % request.website.google_search_console)

    @http.route('/website/google_maps_api_key', type='jsonrpc', auth='public', website=True, readonly=True)
    def google_maps_api_key(self):
        return json.dumps({
            'google_maps_api_key': request.website.google_maps_api_key or ''
        })

    # ------------------------------------------------------
    # Themes
    # ------------------------------------------------------

    @http.route('/website/google_font_metadata', type='jsonrpc', auth='user', website=True)
    def google_font_metadata(self):
        """ Avoid CORS by caching google fonts metadata on server """
        Attachment = request.env['ir.attachment']
        metadata = Attachment.search([
            ('name', '=', 'googleFontMetadata'),
            ('public', '=', True),
        ], limit=1)
        yesterday = fields.Datetime.add(fields.Datetime.now(), days=-1)
        if not metadata or metadata.write_date < yesterday:
            req = requests.get('https://fonts.google.com/metadata/fonts', timeout=5)
            if req.status_code != requests.codes.ok:
                return {
                    'familyMetadataList': [],
                }
            json_content = req.content
            if metadata:
                metadata.raw = json_content
            else:
                metadata = Attachment.create({
                    'public': True,
                    'name': 'googleFontMetadata',
                    'type': 'binary',
                    'mimetype': 'application/json',
                    'raw': json_content,
                })
        return json.loads(metadata.raw)

    def _get_customize_data(self, keys, is_view_data):
        model = 'ir.ui.view' if is_view_data else 'ir.asset'
        Model = request.env[model].with_context(active_test=False)
        domain = Domain("key", "in", keys) & request.website.website_domain()
        return Model.search(domain).filter_duplicate()

    @http.route(['/website/theme_customize_data_get'], type='jsonrpc', auth='user', website=True, readonly=True)
    def theme_customize_data_get(self, keys, is_view_data):
        records = self._get_customize_data(keys, is_view_data)
        return records.filtered('active').mapped('key')

    @http.route(['/website/theme_customize_data'], type='jsonrpc', auth='user', website=True)
    def theme_customize_data(self, is_view_data, enable=None, disable=None, reset_view_arch=False):
        """
        Enables and/or disables views/assets according to list of keys.

        :param is_view_data: True = "ir.ui.view", False = "ir.asset"
        :param enable: list of views/assets keys to enable
        :param disable: list of views/assets keys to disable
        :param reset_view_arch: restore the default template after disabling
        """
        if disable:
            records = self._get_customize_data(disable, is_view_data).filtered('active')
            if reset_view_arch:
                records.reset_arch(mode='hard')
            records.write({'active': False})

        if enable:
            records = self._get_customize_data(enable, is_view_data)
            records.filtered(lambda x: not x.active).write({'active': True})

    @http.route(['/website/theme_customize_bundle_reload'], type='jsonrpc', auth='user', website=True, readonly=True)
    def theme_customize_bundle_reload(self):
        """
        Reloads asset bundles and returns their unique URLs.
        """
        return {
            'web.assets_frontend': request.env['ir.qweb']._get_asset_link_urls('web.assets_frontend', request.session.debug),
        }

    @http.route(['/website/update_footer_template'], type='jsonrpc', auth='user', website=True)
    def update_footer_template(self, template_key, possible_values):
        """ Enables the footer template and its corresponding copyright template
            on template change. The goal is to ensure that the content width of
            the copyright aligns with the footer.
        """

        # Define templates views to enable/disable
        views_enable = [template_key]
        views_disable = self.theme_customize_data_get(possible_values, is_view_data=True)

        # Define the possible footer classes and corresponding views
        width_views = {
            'container-fluid': 'website.footer_copyright_content_width_fluid',
            'o_container_small': 'website.footer_copyright_content_width_small',
        }

        # Parse new footer template and get the content width
        new_template = self._get_customize_data([template_key], is_view_data=True)
        if not new_template or not new_template[0].arch:
            return

        tree = etree.HTML(new_template[0].arch)
        container_classes = ['container', 'container-fluid', 'o_container_small']
        classes_selector = ' or '.join([f"hasclass('{c}')" for c in container_classes])
        res = tree.xpath(f"//div[{classes_selector}]")

        # Define copyright views to enable/disable
        if res:
            classes = res[0].get('class').split()
            width = next((c for c in container_classes if c in classes), False)
            if width:
                view = width_views.get(width)
                if view is not None:
                    views_enable += [view]
                views_disable += [v for k, v in width_views.items() if k != width]

        # Activate/Deactivate the computed views
        self.theme_customize_data(is_view_data=True,
                                  enable=views_enable,
                                  disable=views_disable,
                                  reset_view_arch=False)

    # ------------------------------------------------------
    # Server actions
    # ------------------------------------------------------

    @http.route(['/website/theme_upload_font'], type='jsonrpc', auth='user', website=True)
    def theme_upload_font(self, name, data):
        """
        Uploads font binary data and returns metadata about accessing individual fonts.
        :param name: name of the uploaded file
        :param data: binary content of the uploaded file
        :return: list of dict describing each contained font with:
            - name
            - mimetype
            - attachment id
            - attachment URL
        """
        def check_content(filename, data):
            """ Returns True only if data matches the font extension. """
            # Do not pollute general guess_mimetype with this.
            ext = filename.rsplit('.')[-1].lower()
            if ext == 'otf':
                return data.startswith(b'OTTO')
            elif ext == 'woff':
                return data.startswith(b'wOFF')
            elif ext == 'woff2':
                return data.startswith(b'wOF2')
            elif ext == 'ttf':
                # Based on https://docs.fileformat.com/font/ttf/#true-type-file-format-specifications
                TOC_OFFSET = 12
                TOC_ENTRY_LENGTH = 16
                table_size = int.from_bytes(data[4:6], 'big') * TOC_ENTRY_LENGTH
                if TOC_OFFSET + table_size > len(data):
                    return False
                mandatory_tags = {b'cmap', b'glyf', b'head', b'hhea', b'hmtx', b'loca', b'maxp', b'name', b'post'}
                for offset in range(TOC_OFFSET, TOC_OFFSET + table_size, TOC_ENTRY_LENGTH):
                    tag = data[offset:offset + 4]
                    mandatory_tags.discard(tag)
                return not mandatory_tags
            return False

        def create_attachment(font, data):
            """ Creates font attachments right away to avoid keeping
            several extracted contents in memory. """
            ext = font['name'].rsplit('.')[-1].lower()
            font['mimetype'] = f'font/{ext}'
            attachment = request.env['ir.attachment'].create({
                'name': font['name'],
                'mimetype': font['mimetype'],
                'raw': data,
                'public': True,
            })
            font['id'] = attachment.id
            font['url'] = f"/web/content/{attachment.id}/{font['name']}"
            return font

        result = []
        binary_data = base64.b64decode(data, validate=True)
        readable_data = BytesIO(binary_data)
        if zipfile.is_zipfile(readable_data):
            with zipfile.ZipFile(readable_data, "r") as zip_file:
                for entry in zip_file.infolist():
                    if entry.file_size > MAX_FONT_FILE_SIZE:
                        raise UserError(_("File '%s' exceeds maximum allowed file size", entry.filename))
                    if entry.filename.rsplit('.', 1)[-1].lower() not in SUPPORTED_FONT_EXTENSIONS \
                            or entry.filename.startswith('__MACOSX') \
                            or '/.' in entry.filename:
                        continue
                    data = zip_file.read(entry)
                    if not check_content(entry.filename, data):
                        continue
                    result.append(create_attachment({
                        'name': f'{name}-{entry.filename.replace("/", "-")}',
                    }, data))
        elif name.rsplit('.', 1)[-1].lower() in SUPPORTED_FONT_EXTENSIONS and check_content(name, binary_data):
            result.append(create_attachment({
                'name': name,
            }, binary_data))
        if not result:
            raise UserError(_("File '%s' is not recognized as a font", name))
        return result

    @http.route([
        '/website/action/<path_or_xml_id_or_id>',
        '/website/action/<path_or_xml_id_or_id>/<path:path>',
    ], type='http', auth="public", website=True)
    def actions_server(self, path_or_xml_id_or_id, **post):
        ServerActions = request.env['ir.actions.server']
        action = action_id = None

        # find the action_id: either an xml_id, the path, or an ID
        if isinstance(path_or_xml_id_or_id, str) and '.' in path_or_xml_id_or_id:
            action = request.env.ref(path_or_xml_id_or_id, raise_if_not_found=False).sudo()
        if not action:
            action = ServerActions.sudo().search(
                [('website_path', '=', path_or_xml_id_or_id), ('website_published', '=', True)], limit=1)
        if not action:
            try:
                action_id = int(path_or_xml_id_or_id)
                action = ServerActions.sudo().browse(action_id).exists()
            except ValueError:
                pass

        # run it, return only if we got a Response object
        if action:
            if action.state == 'code' and action.website_published:
                # use main session env for execution
                action_res = ServerActions.browse(action.id).run()
                if isinstance(action_res, werkzeug.wrappers.Response):
                    return action_res

        return request.redirect('/')


class WebsiteSession(Session):

    # Force auth='public', required for logout
    @http.route(auth="public")
    def logout(self, *args, **kw):
        return super().logout(*args, **kw)


class WebsiteBinary(Binary):

    # Backward compatibility routes
    @http.route([
        '/website/image',
        '/website/image/<xmlid>',
        '/website/image/<xmlid>/<int:width>x<int:height>',
        '/website/image/<xmlid>/<field>',
        '/website/image/<xmlid>/<field>/<int:width>x<int:height>',
        '/website/image/<model>/<id>/<field>',
        '/website/image/<model>/<id>/<field>/<int:width>x<int:height>'
    ], type='http', auth="public", website=False, multilang=False, readonly=True)
    def website_content_image(self, id=None, max_width=0, max_height=0, **kw):  # noqa: A002
        if max_width:
            kw['width'] = max_width
        if max_height:
            kw['height'] = max_height
        if id:
            identifier, _, unique = id.partition('_')
            kw['id'] = int(identifier)
            if unique:
                kw['unique'] = unique
        return self.content_image(**kw)
