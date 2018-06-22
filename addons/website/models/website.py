# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import inspect
import logging
import hashlib
import re

from werkzeug import urls
from werkzeug.exceptions import NotFound

from odoo import api, fields, models, tools
from odoo.addons.http_routing.models.ir_http import slugify, _guess_mimetype
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.addons.portal.controllers.portal import pager
from odoo.tools import pycompat
from odoo.http import request
from odoo.osv import expression
from odoo.osv.expression import FALSE_DOMAIN
from odoo.tools.translate import _

logger = logging.getLogger(__name__)


DEFAULT_CDN_FILTERS = [
    "^/[^/]+/static/",
    "^/web/(css|js)/",
    "^/web/image",
    "^/web/content",
    # retrocompatibility
    "^/website/image/",
]


class Website(models.Model):

    _name = "website"  # Avoid website.website convention for conciseness (for new api). Got a special authorization from xmo and rco
    _description = "Website"

    def _active_languages(self):
        return self.env['res.lang'].search([]).ids

    def _default_language(self):
        lang_code = self.env['ir.default'].get('res.partner', 'lang')
        def_lang = self.env['res.lang'].search([('code', '=', lang_code)], limit=1)
        return def_lang.id if def_lang else self._active_languages()[0]

    def _default_social_twitter(self):
        return self.env.ref('base.main_company').social_twitter

    def _default_social_facebook(self):
        return self.env.ref('base.main_company').social_facebook

    def _default_social_github(self):
        return self.env.ref('base.main_company').social_github

    def _default_social_linkedin(self):
        return self.env.ref('base.main_company').social_linkedin

    def _default_social_youtube(self):
        return self.env.ref('base.main_company').social_youtube

    def _default_social_googleplus(self):
        return self.env.ref('base.main_company').social_googleplus

    name = fields.Char('Website Name')
    domain = fields.Char('Website Domain')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.ref('base.main_company').id)
    language_ids = fields.Many2many('res.lang', 'website_lang_rel', 'website_id', 'lang_id', 'Languages', default=_active_languages)
    default_lang_id = fields.Many2one('res.lang', string="Default Language", default=_default_language, required=True)
    default_lang_code = fields.Char(related='default_lang_id.code', string="Default language code", store=True)
    auto_redirect_lang = fields.Boolean('Autoredirect Language', default=True, help="Should users be redirected to their browser's language")

    social_twitter = fields.Char('Twitter Account', default=_default_social_twitter)
    social_facebook = fields.Char('Facebook Account', default=_default_social_facebook)
    social_github = fields.Char('GitHub Account', default=_default_social_github)
    social_linkedin = fields.Char('LinkedIn Account', default=_default_social_linkedin)
    social_youtube = fields.Char('Youtube Account', default=_default_social_youtube)
    social_googleplus = fields.Char('Google+ Account', default=_default_social_googleplus)

    google_analytics_key = fields.Char('Google Analytics Key')
    google_management_client_id = fields.Char('Google Client ID')
    google_management_client_secret = fields.Char('Google Client Secret')

    user_id = fields.Many2one('res.users', string='Public User', required=True, default=lambda self: self.env.ref('base.public_user').id)
    cdn_activated = fields.Boolean('Activate CDN for assets')
    cdn_url = fields.Char('CDN Base URL', default='')
    cdn_filters = fields.Text('CDN Filters', default=lambda s: '\n'.join(DEFAULT_CDN_FILTERS), help="URL matching those filters will be rewritten using the CDN Base URL")
    partner_id = fields.Many2one(related='user_id.partner_id', relation='res.partner', string='Public Partner')
    menu_id = fields.Many2one('website.menu', compute='_compute_menu', string='Main Menu')
    homepage_id = fields.Many2one('website.page', string='Homepage')
    favicon = fields.Binary(string="Website Favicon", help="This field holds the image used to display a favicon on the website.")
    installed_theme_id = fields.Many2one('ir.module.module')
    theme_ids = fields.Many2many('ir.module.module', 'website_theme', 'website_id', 'ir_module_module_id')
    auth_signup_uninvited = fields.Selection([
        ('b2b', 'On invitation (B2B)'),
        ('b2c', 'Free sign up (B2C)'),
    ], string='Customer Account', default='b2b')

    @api.multi
    def _compute_menu(self):
        Menu = self.env['website.menu']
        for website in self:
            website.menu_id = Menu.search([('parent_id', '=', False), ('website_id', 'in', (website.id, False))], order='id', limit=1).id

    # cf. Wizard hack in website_views.xml
    def noop(self, *args, **kwargs):
        pass

    @api.model
    def create(self, vals):
        res = super(Website, self).create(vals)

        # publish default homepage on new website so people can login
        default_homepage = self.env.ref('website.homepage_page', raise_if_not_found=False)
        if default_homepage:
            default_homepage.website_ids |= res

        return res

    @api.multi
    def write(self, values):
        self._get_languages.clear_cache(self)
        return super(Website, self).write(values)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.social_twitter = self.company_id.social_twitter
        self.social_facebook = self.company_id.social_facebook
        self.social_github = self.company_id.social_github
        self.social_linkedin = self.company_id.social_linkedin
        self.social_youtube = self.company_id.social_youtube
        self.social_googleplus = self.company_id.social_googleplus

    #----------------------------------------------------------
    # Page Management
    #----------------------------------------------------------
    @api.model
    def new_page(self, name=False, add_menu=False, template='website.default_page', ispage=True, namespace=None):
        """ Create a new website page, and assign it a xmlid based on the given one
            :param name : the name of the page
            :param template : potential xml_id of the page to create
            :param namespace : module part of the xml_id if none, the template module name is used
        """
        if namespace:
            template_module = namespace
        else:
            template_module, _ = template.split('.')
        page_url = '/' + slugify(name, max_length=1024, path=True)
        page_url = self.get_unique_path(page_url)
        page_key = slugify(name)
        result = dict({'url': page_url, 'view_id': False})

        if not name:
            name = 'Home'
            page_key = 'home'

        template_record = self.env.ref(template)
        website_id = self._context.get('website_id')
        key = self.get_unique_key(page_key, template_module)
        view = template_record.copy({'website_id': website_id, 'key': key})

        view.with_context(lang=None).write({
            'arch': template_record.arch.replace(template, key),
            'name': name,
        })

        if view.arch_fs:
            view.arch_fs = False

        if ispage:
            page = self.env['website.page'].create({
                'url': page_url,
                'website_ids': [(6, None, [self.get_current_website().id])],
                'view_id': view.id
            })
            result['view_id'] = view.id
        if add_menu:
            self.env['website.menu'].create({
                'name': name,
                'url': page_url,
                'parent_id': self.get_current_website().menu_id.id,
                'page_id': page.id,
                'website_id': self.get_current_website().id,
            })
        return result

    @api.model
    def guess_mimetype(self):
        return _guess_mimetype()

    def get_unique_path(self, page_url):
        """ Given an url, return that url suffixed by counter if it already exists
            :param page_url : the url to be checked for uniqueness
        """
        website_id = self.get_current_website().id
        inc = 0
        domain_static = ['|', ('website_ids', '=', False), ('website_ids', 'in', website_id)]
        page_temp = page_url
        while self.env['website.page'].with_context(active_test=False).sudo().search([('url', '=', page_temp)] + domain_static):
            inc += 1
            page_temp = page_url + (inc and "-%s" % inc or "")
        return page_temp

    def get_unique_key(self, string, template_module=False):
        """ Given a string, return an unique key including module prefix.
            It will be suffixed by a counter if it already exists to garantee uniqueness.
            :param string : the key to be checked for uniqueness, you can pass it with 'website.' or not
            :param template_module : the module to be prefixed on the key, if not set, we will use website
        """
        website_id = self.get_current_website().id
        if template_module:
            string = template_module + '.' + string
        else:
            if not string.startswith('website.'):
                string = 'website.' + string

        #Look for unique key
        key_copy = string
        inc = 0
        domain_static = ['|', ('website_ids', '=', False), ('website_ids', 'in', website_id)]
        while self.env['website.page'].with_context(active_test=False).sudo().search([('key', '=', key_copy)] + domain_static):
            inc += 1
            key_copy = string + (inc and "-%s" % inc or "")
        return key_copy

    def key_to_view_id(self, view_id):
        return self.env['ir.ui.view'].search([
            ('id', '=', view_id),
            '|', ('website_id', '=', self._context.get('website_id')), ('website_id', '=', False),
            ('type', '=', 'qweb')
        ])

    @api.model
    def page_search_dependencies(self, page_id=False):
        """ Search dependencies just for information. It will not catch 100%
            of dependencies and False positive is more than possible
            Each module could add dependences in this dict
            :returns a dictionnary where key is the 'categorie' of object related to the given
                view, and the value is the list of text and link to the resource using given page
        """
        dependencies = {}
        if not page_id:
            return dependencies

        page = self.env['website.page'].browse(int(page_id))
        website_id = self._context.get('website_id')
        url = page.url

        # search for website_page with link
        website_page_search_dom = [
            '|', ('website_ids', 'in', website_id), ('website_ids', '=', False), ('view_id.arch_db', 'ilike', url)
        ]
        pages = self.env['website.page'].search(website_page_search_dom)
        page_key = _('Page')
        if len(pages) > 1:
            page_key = _('Pages')
        page_view_ids = []
        for page in pages:
            dependencies.setdefault(page_key, [])
            dependencies[page_key].append({
                'text': _('Page <b>%s</b> contains a link to this page') % page.url,
                'item': page.name,
                'link': page.url,
            })
            page_view_ids.append(page.view_id.id)

        # search for ir_ui_view (not from a website_page) with link
        page_search_dom = [
            '|', ('website_id', '=', website_id), ('website_id', '=', False),
            ('arch_db', 'ilike', url), ('id', 'not in', page_view_ids)
        ]
        views = self.env['ir.ui.view'].search(page_search_dom)
        view_key = _('Template')
        if len(views) > 1:
            view_key = _('Templates')
        for view in views:
            dependencies.setdefault(view_key, [])
            dependencies[view_key].append({
                'text': _('Template <b>%s (id:%s)</b> contains a link to this page') % (view.key or view.name, view.id),
                'link': '/web#id=%s&view_type=form&model=ir.ui.view' % view.id,
                'item': _('%s (id:%s)') % (view.key or view.name, view.id),
            })
        # search for menu with link
        menu_search_dom = [
            '|', ('website_id', '=', website_id), ('website_id', '=', False), ('url', 'ilike', '%s' % url)
        ]

        menus = self.env['website.menu'].search(menu_search_dom)
        menu_key = _('Menu')
        if len(menus) > 1:
            menu_key = _('Menus')
        for menu in menus:
            dependencies.setdefault(menu_key, []).append({
                'text': _('This page is in the menu <b>%s</b>') % menu.name,
                'link': '/web#id=%s&view_type=form&model=website.menu' % menu.id,
                'item': menu.name,
            })

        return dependencies

    @api.model
    def page_search_key_dependencies(self, page_id=False):
        """ Search dependencies just for information. It will not catch 100%
            of dependencies and False positive is more than possible
            Each module could add dependences in this dict
            :returns a dictionnary where key is the 'categorie' of object related to the given
                view, and the value is the list of text and link to the resource using given page
        """
        dependencies = {}
        if not page_id:
            return dependencies

        page = self.env['website.page'].browse(int(page_id))
        website_id = self._context.get('website_id')
        key = page.key

        # search for website_page with link
        website_page_search_dom = [
            '|', ('website_ids', 'in', website_id), ('website_ids', '=', False), ('view_id.arch_db', 'ilike', key),
            ('id', '!=', page.id),
        ]
        pages = self.env['website.page'].search(website_page_search_dom)
        page_key = _('Page')
        if len(pages) > 1:
            page_key = _('Pages')
        page_view_ids = []
        for p in pages:
            dependencies.setdefault(page_key, [])
            dependencies[page_key].append({
                'text': _('Page <b>%s</b> is calling this file') % p.url,
                'item': p.name,
                'link': p.url,
            })
            page_view_ids.append(p.view_id.id)

        # search for ir_ui_view (not from a website_page) with link
        page_search_dom = [
            '|', ('website_id', '=', website_id), ('website_id', '=', False),
            ('arch_db', 'ilike', key), ('id', 'not in', page_view_ids),
            ('id', '!=', page.view_id.id),
        ]
        views = self.env['ir.ui.view'].search(page_search_dom)
        view_key = _('Template')
        if len(views) > 1:
            view_key = _('Templates')
        for view in views:
            dependencies.setdefault(view_key, [])
            dependencies[view_key].append({
            'text': _('Template <b>%s (id:%s)</b> is calling this file') % (view.key or view.name, view.id),
            'item': _('%s (id:%s)') % (view.key or view.name, view.id),
            'link': '/web#id=%s&view_type=form&model=ir.ui.view' % view.id,
            })

        return dependencies

    @api.model
    def page_exists(self, name, module='website'):
        try:
            name = (name or "").replace("/website.", "").replace("/", "")
            if not name:
                return False
            return self.env.ref('%s.%s' % module, name)
        except Exception:
            return False

    #----------------------------------------------------------
    # Languages
    #----------------------------------------------------------

    @api.multi
    def get_languages(self):
        self.ensure_one()
        return self._get_languages()

    @tools.cache('self.id')
    def _get_languages(self):
        return [(lg.code, lg.name) for lg in self.language_ids]

    @api.multi
    def get_alternate_languages(self, req=None):
        langs = []
        if req is None:
            req = request.httprequest
        default = self.get_current_website().default_lang_code
        shorts = []

        def get_url_localized(router, lang):
            arguments = dict(request.endpoint_arguments)
            for key, val in list(arguments.items()):
                if isinstance(val, models.BaseModel):
                    arguments[key] = val.with_context(lang=lang)
            return router.build(request.endpoint, arguments)

        router = request.httprequest.app.get_db_router(request.db).bind('')
        for code, dummy in self.get_languages():
            lg_path = ('/' + code) if code != default else ''
            lg_codes = code.split('_')
            shorts.append(lg_codes[0])
            uri = get_url_localized(router, code) if request.endpoint else request.httprequest.path
            if req.query_string:
                uri += u'?' + req.query_string.decode('utf-8')
            lang = {
                'hreflang': ('-'.join(lg_codes)).lower(),
                'short': lg_codes[0],
                'href': req.url_root[0:-1] + lg_path + uri,
            }
            langs.append(lang)
        for lang in langs:
            if shorts.count(lang['short']) == 1:
                lang['hreflang'] = lang['short']
        return langs

    #----------------------------------------------------------
    # Utilities
    #----------------------------------------------------------

    @api.model
    def get_current_website(self):
        domain_name = request and request.httprequest.environ.get('HTTP_HOST', '').split(':')[0] or None
        website_id = self._get_current_website_id(domain_name)
        if request:
            request.context = dict(request.context, website_id=website_id)
        return self.browse(website_id)

    def _get_current_website_id(self, domain_name):
        forced_website_id = self.env['ir.config_parameter'].sudo().get_param('website_multi.force_website_id', '')
        # todo jov public user
        website = False
        if forced_website_id.isdigit():
            website = request.env['website'].browse(int(forced_website_id))
            logger.debug('forcing website %s (ID: %s)', website.name, website.id)

        if not website:
            website = self.search([('domain', '=', domain_name)], limit=1)
            if not website:
                website = self.search([], limit=1)

        return website.id

    @api.model
    def is_publisher(self):
        return self.env['ir.model.access'].check('ir.ui.view', 'write', False)

    @api.model
    def is_user(self):
        return self.env['ir.model.access'].check('ir.ui.menu', 'read', False)

    @api.model
    def is_public_user(self):
        return request.env.user.id == request.website.user_id.id

    @api.model
    def get_template(self, template):
        View = self.env['ir.ui.view']
        if isinstance(template, pycompat.integer_types):
            view_id = template
        else:
            if '.' not in template:
                template = 'website.%s' % template
            view_id = View.get_view_id(template)
        if not view_id:
            raise NotFound
        return View.browse(view_id)

    @api.model
    def pager(self, url, total, page=1, step=30, scope=5, url_args=None):
        return pager(url, total, page=page, step=step, scope=scope, url_args=url_args)

    def rule_is_enumerable(self, rule):
        """ Checks that it is possible to generate sensible GET queries for
            a given rule (if the endpoint matches its own requirements)
            :type rule: werkzeug.routing.Rule
            :rtype: bool
        """
        endpoint = rule.endpoint
        methods = endpoint.routing.get('methods') or ['GET']

        converters = list(rule._converters.values())
        if not ('GET' in methods
            and endpoint.routing['type'] == 'http'
            and endpoint.routing['auth'] in ('none', 'public')
            and endpoint.routing.get('website', False)
            and all(hasattr(converter, 'generate') for converter in converters)
            and endpoint.routing.get('website')):
            return False

        # dont't list routes without argument having no default value or converter
        spec = inspect.getargspec(endpoint.method.original_func)

        # remove self and arguments having a default value
        defaults_count = len(spec.defaults or [])
        args = spec.args[1:(-defaults_count or None)]

        # check that all args have a converter
        return all((arg in rule._converters) for arg in args)

    @api.multi
    def enumerate_pages(self, query_string=None, force=False):
        """ Available pages in the website/CMS. This is mostly used for links
            generation and can be overridden by modules setting up new HTML
            controllers for dynamic pages (e.g. blog).
            By default, returns template views marked as pages.
            :param str query_string: a (user-provided) string, fetches pages
                                     matching the string
            :returns: a list of mappings with two keys: ``name`` is the displayable
                      name of the resource (page), ``url`` is the absolute URL
                      of the same.
            :rtype: list({name: str, url: str})
        """

        router = request.httprequest.app.get_db_router(request.db)
        # Force enumeration to be performed as public user
        url_set = set()

        sitemap_endpoint_done = set()

        for rule in router.iter_rules():
            if 'sitemap' in rule.endpoint.routing:
                if rule.endpoint in sitemap_endpoint_done:
                    continue
                sitemap_endpoint_done.add(rule.endpoint)

                func = rule.endpoint.routing['sitemap']
                if func is False:
                    continue
                for loc in func(self.env, rule, query_string):
                    yield loc
                continue

            if not self.rule_is_enumerable(rule):
                continue

            converters = rule._converters or {}
            if query_string and not converters and (query_string not in rule.build([{}], append_unknown=False)[1]):
                continue
            values = [{}]
            # converters with a domain are processed after the other ones
            convitems = sorted(
                converters.items(),
                key=lambda x: (hasattr(x[1], 'domain') and (x[1].domain != '[]'), rule._trace.index((True, x[0]))))

            for (i, (name, converter)) in enumerate(convitems):
                newval = []
                for val in values:
                    query = i == len(convitems)-1 and query_string
                    if query:
                        r = "".join([x[1] for x in rule._trace[1:] if not x[0]])  # remove model converter from route
                        query = sitemap_qs2dom(query, r, self.env[converter.model]._rec_name)
                        if query == FALSE_DOMAIN:
                            continue
                    for value_dict in converter.generate(uid=self.env.uid, dom=query, args=val):
                        newval.append(val.copy())
                        value_dict[name] = value_dict['loc']
                        del value_dict['loc']
                        newval[-1].update(value_dict)
                values = newval

            for value in values:
                domain_part, url = rule.build(value, append_unknown=False)
                if not query_string or query_string.lower() in url.lower():
                    page = {'loc': url}
                    for key, val in value.items():
                        if key.startswith('__'):
                            page[key[2:]] = val
                    if url in ('/sitemap.xml',):
                        continue
                    if url in url_set:
                        continue
                    url_set.add(url)

                    yield page

        # '/' already has a http.route & is in the routing_map so it will already have an entry in the xml
        domain = [('url', '!=', '/')]
        if not force:
            domain += [('website_indexed', '=', True)]
            #is_visible
            domain += [('website_published', '=', True), '|', ('date_publish', '=', False), ('date_publish', '<=', fields.Datetime.now())]

        if query_string:
            domain += [('url', 'like', query_string)]

        pages = self.get_website_pages(domain)

        for page in pages:
            record = {'loc': page['url'], 'id': page['id'], 'name': page['name']}
            if page.view_id and page.view_id.priority != 16:
                record['__priority'] = min(round(page.view_id.priority / 32.0, 1), 1)
            if page['write_date']:
                record['__lastmod'] = page['write_date'][:10]
            yield record

    @api.multi
    def get_website_pages(self, domain=[], order='name', limit=None):
        domain += ['|', ('website_ids', 'in', self.get_current_website().id), ('website_ids', '=', False)]
        pages = request.env['website.page'].search(domain, order='name', limit=limit)
        return pages

    @api.multi
    def search_pages(self, needle=None, limit=None):
        name = slugify(needle, max_length=50, path=True)
        res = []
        for page in self.enumerate_pages(query_string=name, force=True):
            res.append(page)
            if len(res) == limit:
                break
        return res

    @api.model
    def image_url(self, record, field, size=None):
        """ Returns a local url that points to the image field of a given browse record. """
        sudo_record = record.sudo()
        sha = hashlib.sha1(getattr(sudo_record, '__last_update').encode('utf-8')).hexdigest()[0:7]
        size = '' if size is None else '/%s' % size
        return '/web/image/%s/%s/%s%s?unique=%s' % (record._name, record.id, field, size, sha)

    @api.model
    def get_cdn_url(self, uri):
        # Currently only usable in a website_enable request context
        if request and request.website and not request.debug and request.website.user_id.id == request.uid:
            cdn_url = request.website.cdn_url
            cdn_filters = (request.website.cdn_filters or '').splitlines()
            for flt in cdn_filters:
                if flt and re.match(flt, uri):
                    return urls.url_join(cdn_url, uri)
        return uri

    @api.model
    def action_dashboard_redirect(self):
        if self.env.user.has_group('base.group_system') or self.env.user.has_group('website.group_website_designer'):
            return self.env.ref('website.backend_dashboard').read()[0]
        return self.env.ref('website.action_website').read()[0]


class SeoMetadata(models.AbstractModel):

    _name = 'website.seo.metadata'
    _description = 'SEO metadata'

    website_meta_title = fields.Char("Website meta title", translate=True)
    website_meta_description = fields.Text("Website meta description", translate=True)
    website_meta_keywords = fields.Char("Website meta keywords", translate=True)


class WebsitePublishedMixin(models.AbstractModel):

    _name = "website.published.mixin"

    website_published = fields.Boolean('Visible on current website',
                                       compute='_compute_website_published',
                                       inverse='_inverse_website_published',
                                       search='_search_website_published')
    website_ids = fields.Many2many('website', string='Published on Websites', help='Determines on what websites this record will be visible.')
    website_url = fields.Char('Website URL', compute='_compute_website_url', help='The full URL to access the document through the website.')

    @api.multi
    def _compute_website_published(self):
        for record in self:
            current_website_id = self._context.get('website_id')
            if current_website_id:
                record.website_published = current_website_id in record.website_ids.ids
            else:  # should be in the backend, return things that are published anywhere
                record.website_published = bool(record.website_ids)

    @api.multi
    def _inverse_website_published(self):
        for record in self:
            current_website_id = self._context.get('website_id')
            if current_website_id:
                current_website = self.env['website'].browse(current_website_id)

                if record.website_published:
                    record.website_ids |= current_website
                else:
                    record.website_ids -= current_website

            else:  # this happens during e.g. demo data installation -> publish on all websites
                record.website_ids = self.env['website'].search([])

    def _search_website_published(self, operator, value):
        if not isinstance(value, bool) or operator not in ('=', '!='):
            logger.warning('unsupported search on website_published: %s, %s', operator, value)
            return [()]

        if operator in expression.NEGATIVE_TERM_OPERATORS:
            value = not value

        current_website_id = self._context.get('website_id')
        if current_website_id:
            return [('website_ids', 'in' if value is True else 'not in', current_website_id)]
        else:  # should be in the backend, return things that are published anywhere
            return [('website_ids', '!=' if value is True else '=', False)]

    @api.multi
    def _compute_website_url(self):
        for record in self:
            record.website_url = '#'

    @api.multi
    def website_publish_button(self):
        self.ensure_one()
        if self.env['website'].search_count([]) <= 1:
            return super(WebsitePublishedMixin, self).website_publish_button()
        else:
            # Some models using the mixin put the base url in the
            # website_url (e.g. website_slides' slide.slide), other
            # ones use a relative url (e.g. website_sale's
            # product.template). Since we are going to construct the
            # urls ourselves filter that out.
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            self.website_url = self.website_url.replace(base_url, '')

            wizard = self.env['website.urls.wizard'].create({
                'path': self.website_url,
                'record_id': self.id,
                'model_name': self._name,
            })
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'website.urls.wizard',
                'view_mode': 'form',
                'res_id': wizard.id,
                'target': 'new',
            }

    @api.multi
    def toggle_publish(self):
        for record in self:
            record.website_published = not record.website_published

    def open_website_url(self):
        return {
            'type': 'ir.actions.act_url',
            'url': self.website_url,
            'target': 'self',
        }


class Page(models.Model):
    _name = 'website.page'
    _inherits = {'ir.ui.view': 'view_id'}
    _inherit = 'website.published.mixin'
    _description = 'Page'
    _order = 'specificity'

    url = fields.Char('Page URL')
    view_id = fields.Many2one('ir.ui.view', string='View', required=True, ondelete="cascade")
    website_indexed = fields.Boolean('Page Indexed', default=True)
    date_publish = fields.Datetime('Publishing Date')
    # This is needed to be able to display if page is a menu in /website/pages
    menu_ids = fields.One2many('website.menu', 'page_id', 'Related Menus')
    is_homepage = fields.Boolean(compute='_compute_homepage', inverse='_set_homepage', string='Homepage')
    is_visible = fields.Boolean(compute='_compute_visible', string='Is Visible')
    specificity = fields.Integer(compute='_compute_specifity', store=True,
                             help='''Used to order pages from most specific (i.e. belonging to 1 website)
                             to least specific (i.e. not belonging to a website.). Note that this is defined
                             in ascending order, so a specificity of 0 is a page for 1 website (i.e. most specific).''')

    @api.one
    def _compute_homepage(self):
        self.is_homepage = self == self.env['website'].get_current_website().homepage_id

    @api.one
    def _set_homepage(self):
        website = self.env['website'].get_current_website()
        if self.is_homepage:
            if website.homepage_id != self:
                website.write({'homepage_id': self.id})
        else:
            if website.homepage_id == self:
                website.write({'homepage_id': None})

    @api.one
    def _compute_visible(self):
        self.is_visible = self.website_published and (not self.date_publish or self.date_publish < fields.Datetime.now())

    @api.multi
    @api.depends('website_ids', 'view_id.website_id')
    def _compute_specifity(self):
        '''This defines a specificity as follows:

        |--------------------+-------------|
        | amount of websites | specificity |
        |--------------------+-------------|
        |                  1 |           0 |
        |                  2 |           1 |
        |                ... |         ... |
        |                  0 |         MAX |
        |--------------------+-------------|

        So when there are multiple pages for a given url, the most
        specific one will be chosen.
        '''
        for page in self:
            if page.view_id.website_id:
                page.specificity = 0
            elif page.website_ids:
                page.specificity = len(page.website_ids) - 1
            else:
                # This is an arbitrary maximum, the important thing is
                # that this should always be greater than #websites - 1.
                # Presumably noone is going to create >1024 websites...
                page.specificity = 1024

    @api.multi
    def _is_most_specific_page(self, page_to_test):
        '''This will test if page_to_test is the most specific page in self.'''
        pages_for_url = self.filtered(lambda page: page.url == page_to_test.url)

        # this works because pages are _order'ed by specificity
        most_specific_page = pages_for_url[0]

        return most_specific_page == page_to_test

    @api.model
    def get_page_info(self, id, website_id):
        domain = ['|', ('website_ids', 'in', website_id), ('website_ids', '=', False), ('id', '=', id)]
        item = self.search_read(domain, fields=['id', 'name', 'url', 'website_published', 'website_indexed', 'date_publish', 'menu_ids', 'is_homepage'], limit=1)
        return item

    @api.multi
    def get_view_identifier(self):
        """ Get identifier of this page view that may be used to render it """
        return self.view_id.id

    @api.model
    def save_page_info(self, website_id, data):
        website = self.env['website'].browse(website_id)
        page = self.browse(int(data['id']))

        #If URL has been edited, slug it
        original_url = page.url
        url = data['url']
        if not url.startswith('/'):
            url = '/' + url
        if page.url != url:
            url = '/' + slugify(url, max_length=1024, path=True)
            url = self.env['website'].get_unique_path(url)

        #If name has changed, check for key uniqueness
        if page.name != data['name']:
            page_key = self.env['website'].get_unique_key(slugify(data['name']))
        else:
            page_key = page.key

        menu = self.env['website.menu'].search([('page_id', '=', int(data['id']))])
        if not data['is_menu']:
            #If the page is no longer in menu, we should remove its website_menu
            if menu:
                menu.unlink()
        else:
            #The page is now a menu, check if has already one
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

        page.write({
            'key': page_key,
            'name': data['name'],
            'url': url,
            'website_published': data['website_published'],
            'website_indexed': data['website_indexed'],
            'date_publish': data['date_publish'] or None,
            'is_homepage': data['is_homepage'],
        })

        # Create redirect if needed
        if data['create_redirect']:
            self.env['website.redirect'].create({
                'type': data['redirect_type'],
                'url_from': original_url,
                'url_to': url,
                'website_id': website.id,
            })

        return url

    @api.multi
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default and not default.get('view_id'):
            view = self.env['ir.ui.view'].browse(self.view_id.id)
            # website.page's ir.ui.view should have a different key than the one it
            # is copied from.
            # (eg: website_version: an ir.ui.view record with the same key is
            # expected to be the same ir.ui.view but from another version)
            new_view = view.copy({'key': view.key + '.copy', 'name': '%s %s' % (view.name,  _('(copy)'))})
            default = {
                'name': '%s %s' % (self.name,  _('(copy)')),
                'url': self.env['website'].get_unique_path(self.url),
                'view_id': new_view.id,
            }
        return super(Page, self).copy(default=default)

    @api.model
    def clone_page(self, page_id, clone_menu=True):
        """ Clone a page, given its identifier
            :param page_id : website.page identifier
        """
        page = self.browse(int(page_id))
        new_page = page.copy()
        if clone_menu:
            menu = self.env['website.menu'].search([('page_id', '=', page_id)], limit=1)
            if menu:
                # If the page being cloned has a menu, clone it too
                new_menu = menu.copy()
                new_menu.write({'url': new_page.url, 'name': '%s %s' % (menu.name,  _('(copy)')), 'page_id': new_page.id})

        return new_page.url + '?enable_editor=1'

    @api.multi
    def unlink(self):
        """ When a website_page is deleted, the ORM does not delete its ir_ui_view.
            So we got to delete it ourself, but only if the ir_ui_view is not used by another website_page.
        """
        # Handle it's ir_ui_view
        for page in self:
            # Other pages linked to the ir_ui_view of the page being deleted (will it even be possible?)
            pages_linked_to_iruiview = self.search(
                [('view_id', '=', page.view_id.id), ('id', '!=', page.id)]
            )
            if len(pages_linked_to_iruiview) == 0:
                # If there is no other pages linked to that ir_ui_view, we can delete the ir_ui_view
                self.env['ir.ui.view'].search([('id', '=', page.view_id.id)]).unlink()
        # And then delete the website_page itself
        return super(Page, self).unlink()

    @api.model
    def delete_page(self, page_id):
        """ Delete a page, given its identifier
            :param page_id : website.page identifier
        """
        # If we are deleting a page (that could possibly be a menu with a page)
        page = self.env['website.page'].browse(int(page_id))
        if page:
            # Check if it is a menu with a page and also delete menu if so
            menu = self.env['website.menu'].search([('page_id', '=', page.id)], limit=1)
            if menu:
                menu.unlink()
            page.unlink()

    @api.multi
    def write(self, vals):
        if 'url' in vals and not vals['url'].startswith('/'):
            vals['url'] = '/' + vals['url']
        return super(Page, self).write(vals)


class Menu(models.Model):

    _name = "website.menu"
    _description = "Website Menu"

    _parent_store = True
    _order = "sequence, id"

    def _default_sequence(self):
        menu = self.search([], limit=1, order="sequence DESC")
        return menu.sequence or 0

    name = fields.Char('Menu', required=True, translate=True)
    url = fields.Char('Url', default='')
    page_id = fields.Many2one('website.page', 'Related Page', ondelete='cascade')
    new_window = fields.Boolean('New Window')
    sequence = fields.Integer(default=_default_sequence)
    website_id = fields.Many2one('website', 'Website')
    parent_id = fields.Many2one('website.menu', 'Parent Menu', index=True, ondelete="cascade")
    child_id = fields.One2many('website.menu', 'parent_id', string='Child Menus')
    parent_path = fields.Char(index=True)
    is_visible = fields.Boolean(compute='_compute_visible', string='Is Visible')

    @api.multi
    def write(self, vals):
        '''COW for ir.ui.view. This way editing websites does not
        impact other websites and so that newly created websites will
        only contain the default views.
        '''
        current_website_id = self._context.get('website_id')

        # if generic menu in multi-website context
        if current_website_id and not self.website_id and not self._context.get('no_cow') and self.env['website'].search_count([]) > 1:
            new_website_specific_menu = self.copy({'website_id': current_website_id})

            for child in self.child_id:
                child.write({'parent_id': new_website_specific_menu.id})

            return new_website_specific_menu.write(vals)

        return super(Menu, self).write(vals)

    @api.one
    def _compute_visible(self):
        visible = True
        if self.page_id and not self.page_id.sudo().is_visible and not self.user_has_groups('base.group_user'):
            visible = False
        self.is_visible = visible

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

    def get_children_for_current_website(self):
        most_specific_child_menus = self.env['website.menu']
        website_id = self._context.get('website_id')

        if not website_id:
            return self.child_id

        for child in self.child_id:
            if child.website_id and child.website_id.id == website_id:
                most_specific_child_menus |= child
            elif not child.website_id and not any(child.clean_url() == child2.clean_url() and child2.website_id.id == website_id for child2 in self.child_id):
                most_specific_child_menus |= child

        return most_specific_child_menus

    # would be better to take a menu_id as argument
    @api.model
    def get_tree(self, website_id, menu_id=None):
        def make_tree(node):
            page_id = node.page_id.id if node.page_id else None
            is_homepage = page_id and self.env['website'].browse(website_id).homepage_id.id == page_id
            menu_node = dict(
                id=node.id,
                name=node.name,
                url=node.page_id.url if page_id else node.url,
                new_window=node.new_window,
                sequence=node.sequence,
                parent_id=node.parent_id.id,
                children=[],
                is_homepage=is_homepage,
            )
            for child in node.get_children_for_current_website():
                menu_node['children'].append(make_tree(child))
            return menu_node
        if menu_id:
            menu = self.browse(menu_id)
        else:
            menu = self.env['website'].browse(website_id).menu_id
        return make_tree(menu)

    @api.model
    def save(self, website_id, data):
        def replace_id(old_id, new_id):
            for menu in data['data']:
                if menu['id'] == old_id:
                    menu['id'] = new_id
                if menu['parent_id'] == old_id:
                    menu['parent_id'] = new_id
        to_delete = data['to_delete']
        if to_delete:
            self.browse(to_delete).unlink()
        for menu in data['data']:
            mid = menu['id']
            # new menu are prefixed by new-
            if isinstance(mid, pycompat.string_types):
                new_menu = self.create({'name': menu['name']})
                replace_id(mid, new_menu.id)
        for menu in data['data']:
            menu_id = self.browse(menu['id'])
            # if the url match a website.page, set the m2o relation
            # except if the menu url is '#', meaning it will be used as a menu container, most likely for a dropdown
            if menu['url'] == '#':
                if menu_id.page_id:
                    menu_id.page_id = None
            else:
                page = self.env['website.page'].search(['|', ('url', '=', menu['url']), ('url', '=', '/' + menu['url'])], limit=1)
                if page:
                    menu['page_id'] = page.id
                    menu['url'] = page.url
                elif menu_id.page_id:
                    menu_id.page_id.write({'url': menu['url']})
            menu_id.write(menu)

        return True


class WebsiteRedirect(models.Model):
    _name = "website.redirect"
    _description = "Website Redirect"
    _order = "sequence, id"
    _rec_name = 'url_from'

    type = fields.Selection([('301', 'Moved permanently (301)'), ('302', 'Moved temporarily (302)')], string='Redirection Type', required=True)
    url_from = fields.Char('Redirect From', required=True)
    url_to = fields.Char('Redirect To', required=True)
    website_id = fields.Many2one('website', 'Website')
    active = fields.Boolean(default=True)
    sequence = fields.Integer()
