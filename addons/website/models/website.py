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

    _name = "website"
    _description = "Website"

    @api.model
    def website_domain(self, website_id=False):
        return [('website_id', 'in', (False, website_id or self.id))]

    def _active_languages(self):
        return self.env['res.lang'].search([]).ids

    def _default_language(self):
        lang_code = self.env['ir.default'].get('res.partner', 'lang')
        def_lang = self.env['res.lang'].search([('code', '=', lang_code)], limit=1)
        return def_lang.id if def_lang else self._active_languages()[0]

    name = fields.Char('Website Name', required=True)
    domain = fields.Char('Website Domain')
    country_group_ids = fields.Many2many('res.country.group', 'website_country_group_rel', 'website_id', 'country_group_id',
                                         string='Country Groups', help='Used when multiple websites have the same domain.')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.ref('base.main_company').id, required=True)
    language_ids = fields.Many2many('res.lang', 'website_lang_rel', 'website_id', 'lang_id', 'Languages', default=_active_languages)
    default_lang_id = fields.Many2one('res.lang', string="Default Language", default=_default_language, required=True)
    default_lang_code = fields.Char("Default language code", related='default_lang_id.code', store=True, readonly=False)
    auto_redirect_lang = fields.Boolean('Autoredirect Language', default=True, help="Should users be redirected to their browser's language")

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

    def _default_social_instagram(self):
        return self.env.ref('base.main_company').social_instagram

    def _default_social_twitter(self):
        return self.env.ref('base.main_company').social_twitter

    social_twitter = fields.Char('Twitter Account', default=_default_social_twitter)
    social_facebook = fields.Char('Facebook Account', default=_default_social_facebook)
    social_github = fields.Char('GitHub Account', default=_default_social_github)
    social_linkedin = fields.Char('LinkedIn Account', default=_default_social_linkedin)
    social_youtube = fields.Char('Youtube Account', default=_default_social_youtube)
    social_googleplus = fields.Char('Google+ Account', default=_default_social_googleplus)
    social_instagram = fields.Char('Instagram Account', default=_default_social_instagram)
    social_default_image = fields.Binary(string="Default Social Share Image", attachment=True, help="If set, replaces the company logo as the default social share image.")

    google_analytics_key = fields.Char('Google Analytics Key')
    google_management_client_id = fields.Char('Google Client ID')
    google_management_client_secret = fields.Char('Google Client Secret')

    google_maps_api_key = fields.Char('Google Maps API Key')

    user_id = fields.Many2one('res.users', string='Public User', required=True)
    cdn_activated = fields.Boolean('Content Delivery Network (CDN)')
    cdn_url = fields.Char('CDN Base URL', default='')
    cdn_filters = fields.Text('CDN Filters', default=lambda s: '\n'.join(DEFAULT_CDN_FILTERS), help="URL matching those filters will be rewritten using the CDN Base URL")
    partner_id = fields.Many2one(related='user_id.partner_id', relation='res.partner', string='Public Partner', readonly=False)
    menu_id = fields.Many2one('website.menu', compute='_compute_menu', string='Main Menu')
    homepage_id = fields.Many2one('website.page', string='Homepage')
    favicon = fields.Binary(string="Website Favicon", help="This field holds the image used to display a favicon on the website.")
    theme_id = fields.Many2one('ir.module.module', help='Installed theme')

    specific_user_account = fields.Boolean('Specific User Account', help='If True, new accounts will be associated to the current website')
    auth_signup_uninvited = fields.Selection([
        ('b2b', 'On invitation'),
        ('b2c', 'Free sign up'),
    ], string='Customer Account', default='b2b')

    @api.onchange('language_ids')
    def _onchange_language_ids(self):
        if self.language_ids and self.default_lang_id not in self.language_ids:
            self.default_lang_id = self.language_ids[0]

    @api.multi
    def _compute_menu(self):
        Menu = self.env['website.menu']
        for website in self:
            website.menu_id = Menu.search([('parent_id', '=', False), ('website_id', '=', website.id)], order='id', limit=1).id

    @api.model
    def create(self, vals):
        if 'user_id' not in vals:
            company = self.env['res.company'].browse(vals.get('company_id'))
            vals['user_id'] = company._get_public_user().id if company else self.env.ref('base.public_user').id

        res = super(Website, self).create(vals)
        res._bootstrap_homepage()

        if not self.env.user.has_group('website.group_multi_website') and self.search_count([]) > 1:
            all_user_groups = 'base.group_portal,base.group_user,base.group_public'
            groups = self.env['res.groups'].concat(*(self.env.ref(it) for it in all_user_groups.split(',')))
            groups.write({'implied_ids': [(4, self.env.ref('website.group_multi_website').id)]})

        return res

    @api.multi
    def write(self, values):
        public_user_to_change_websites = self.env['website']
        self._get_languages.clear_cache(self)
        if 'company_id' in values and 'user_id' not in values:
            public_user_to_change_websites = self.filtered(lambda w: w.sudo().user_id.company_id.id != values['company_id'])
            if public_user_to_change_websites:
                company = self.env['res.company'].browse(values['company_id'])
                super(Website, public_user_to_change_websites).write(dict(values, user_id=company._get_public_user().id))

        result = super(Website, self - public_user_to_change_websites).write(values)
        if 'cdn_activated' in values or 'cdn_url' in values or 'cdn_filters' in values:
            # invalidate the caches from static node at compile time
            self.env['ir.qweb'].clear_caches()
        return result

    # ----------------------------------------------------------
    # Page Management
    # ----------------------------------------------------------
    def _bootstrap_homepage(self):
        standard_homepage = self.env.ref('website.homepage', raise_if_not_found=False)
        if not standard_homepage:
            return

        new_homepage_view = '''<t name="Homepage" t-name="website.homepage%s">
        <t t-call="website.layout">
            <t t-set="pageName" t-value="'homepage'"/>
            <div id="wrap" class="oe_structure oe_empty"/>
            </t>
        </t>''' % (self.id)
        standard_homepage.with_context(website_id=self.id).arch_db = new_homepage_view

        self.homepage_id = self.env['website.page'].search([('website_id', '=', self.id),
                                                            ('key', '=', standard_homepage.key)])
        # prevent /-1 as homepage URL
        self.homepage_id.url = '/'

        # Bootstrap default menu hierarchy, create a new minimalist one if no default
        default_menu = self.env.ref('website.main_menu')
        self.copy_menu_hierarchy(default_menu)

    def copy_menu_hierarchy(self, top_menu):
        def copy_menu(menu, t_menu):
            new_menu = menu.copy({
                'parent_id': t_menu.id,
                'website_id': self.id,
            })
            for submenu in menu.child_id:
                copy_menu(submenu, new_menu)
        for website in self:
            new_top_menu = top_menu.copy({
                'name': _('Top Menu for Website %s') % website.id,
                'website_id': website.id,
            })
            for submenu in top_menu.child_id:
                copy_menu(submenu, new_top_menu)

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

        website = self.get_current_website()
        if ispage:
            page = self.env['website.page'].create({
                'url': page_url,
                'website_id': website.id,  # remove it if only one webiste or not?
                'view_id': view.id,
            })
            result['view_id'] = view.id
        if add_menu:
            self.env['website.menu'].create({
                'name': name,
                'url': page_url,
                'parent_id': website.menu_id.id,
                'page_id': page.id,
                'website_id': website.id,
            })
        return result

    @api.model
    def guess_mimetype(self):
        return _guess_mimetype()

    def get_unique_path(self, page_url):
        """ Given an url, return that url suffixed by counter if it already exists
            :param page_url : the url to be checked for uniqueness
        """
        inc = 0
        # we only want a unique_path for website specific.
        # we need to be able to have /url for website=False, and /url for website=1
        # in case of duplicate, page manager will allow you to manage this case
        domain_static = [('website_id', '=', self.get_current_website().id)]  # .website_domain()
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
        if template_module:
            string = template_module + '.' + string
        else:
            if not string.startswith('website.'):
                string = 'website.' + string

        # Look for unique key
        key_copy = string
        inc = 0
        domain_static = self.get_current_website().website_domain()
        while self.env['website.page'].with_context(active_test=False).sudo().search([('key', '=', key_copy)] + domain_static):
            inc += 1
            key_copy = string + (inc and "-%s" % inc or "")
        return key_copy

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
        website = self.env['website'].browse(self._context.get('website_id'))
        url = page.url

        # search for website_page with link
        website_page_search_dom = [('view_id.arch_db', 'ilike', url)] + website.website_domain()
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
        page_search_dom = [('arch_db', 'ilike', url), ('id', 'not in', page_view_ids)] + website.website_domain()
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
        menu_search_dom = [('url', 'ilike', '%s' % url)] + website.website_domain()

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
        website = self.env['website'].browse(self._context.get('website_id'))
        key = page.key

        # search for website_page with link
        website_page_search_dom = [
            ('view_id.arch_db', 'ilike', key),
            ('id', '!=', page.id)
        ] + website.website_domain()
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
            ('arch_db', 'ilike', key), ('id', 'not in', page_view_ids),
            ('id', '!=', page.view_id.id),
        ] + website.website_domain()
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

    # ----------------------------------------------------------
    # Languages
    # ----------------------------------------------------------

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

    # ----------------------------------------------------------
    # Utilities
    # ----------------------------------------------------------

    @api.model
    def get_current_website(self, fallback=True):
        if request and request.session.get('force_website_id'):
            return self.browse(request.session['force_website_id'])

        website_id = self.env.context.get('website_id')
        if website_id:
            return self.browse(website_id)

        # The format of `httprequest.host` is `domain:port`
        domain_name = request and request.httprequest.host or ''

        country = request.session.geoip.get('country_code') if request and request.session.geoip else False
        country_id = False
        if country:
            country_id = self.env['res.country'].search([('code', '=', country)], limit=1).id

        website_id = self._get_current_website_id(domain_name, country_id, fallback=fallback)
        return self.browse(website_id)

    @tools.cache('domain_name', 'country_id', 'fallback')
    @api.model
    def _get_current_website_id(self, domain_name, country_id, fallback=True):
        """Get the current website id.

        First find all the websites for which the configured `domain` (after
        ignoring a potential scheme) is equal to the given
        `domain_name`. If there is only one result, return it immediately.

        If there are no website found for the given `domain_name`, either
        fallback to the first found website (no matter its `domain`) or return
        False depending on the `fallback` parameter.

        If there are multiple websites for the same `domain_name`, we need to
        filter them out by country. We return the first found website matching
        the given `country_id`. If no found website matching `domain_name`
        corresponds to the given `country_id`, the first found website for
        `domain_name` will be returned (no matter its country).

        :param domain_name: the domain for which we want the website.
            In regard to the `url_parse` method, only the `netloc` part should
            be given here, no `scheme`.
        :type domain_name: string

        :param country_id: id of the country for which we want the website
        :type country_id: int

        :param fallback: if True and no website is found for the specificed
            `domain_name`, return the first website (without filtering them)
        :type fallback: bool

        :return: id of the found website, or False if no website is found and
            `fallback` is False
        :rtype: int or False

        :raises: if `fallback` is True but no website at all is found
        """
        def _remove_port(domain_name):
            return (domain_name or '').split(':')[0]

        def _filter_domain(website, domain_name, ignore_port=False):
            """Ignore `scheme` from the `domain`, just match the `netloc` which
            is host:port in the version of `url_parse` we use."""
            # Here we add http:// to the domain if it's not set because
            # `url_parse` expects it to be set to correctly return the `netloc`.
            website_domain = urls.url_parse(website._get_http_domain()).netloc
            if ignore_port:
                website_domain = _remove_port(website_domain)
                domain_name = _remove_port(domain_name)
            return website_domain.lower() == (domain_name or '').lower()

        # Sort on country_group_ids so that we fall back on a generic website:
        # websites with empty country_group_ids will be first.
        found_websites = self.search([('domain', 'ilike', _remove_port(domain_name))]).sorted('country_group_ids')
        # Filter for the exact domain (to filter out potential subdomains) due
        # to the use of ilike.
        websites = found_websites.filtered(lambda w: _filter_domain(w, domain_name))
        # If there is no domain matching for the given port, ignore the port.
        websites = websites or found_websites.filtered(lambda w: _filter_domain(w, domain_name, ignore_port=True))

        if not websites:
            if not fallback:
                return False
            return self.search([], limit=1).id
        elif len(websites) == 1:
            return websites.id
        else:  # > 1 website with the same domain
            country_specific_websites = websites.filtered(lambda website: country_id in website.country_group_ids.mapped('country_ids').ids)
            return country_specific_websites[0].id if country_specific_websites else websites[0].id

    def _force(self):
        self._force_website(self.id)

    def _force_website(self, website_id):
        if request:
            request.session['force_website_id'] = website_id and str(website_id).isdigit() and int(website_id)

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
    def viewref(self, view_id, raise_if_not_found=True):
        ''' Given an xml_id or a view_id, return the corresponding view record.
            In case of website context, return the most specific one.

            If no website_id is in the context, it will return the generic view,
            instead of a random one like `get_view_id`.

            Look also for archived views, no matter the context.

            :param view_id: either a string xml_id or an integer view_id
            :param raise_if_not_found: should the method raise an error if no view found
            :return: The view record or empty recordset
        '''
        View = self.env['ir.ui.view']
        view = View
        if isinstance(view_id, pycompat.string_types):
            if 'website_id' in self._context:
                domain = [('key', '=', view_id)] + self.env['website'].website_domain(self._context.get('website_id'))
                order = 'website_id'
            else:
                domain = [('key', '=', view_id)]
                order = View._order
            views = View.with_context(active_test=False).search(domain, order=order)
            if views:
                view = views.filter_duplicate()
            else:
                # we handle the raise below
                view = self.env.ref(view_id, raise_if_not_found=False)
                # self.env.ref might return something else than an ir.ui.view (eg: a theme.ir.ui.view)
                if not view or view._name != 'ir.ui.view':
                    # make sure we always return a recordset
                    view = View
        elif isinstance(view_id, pycompat.integer_types):
            view = View.browse(view_id)
        else:
            raise ValueError('Expecting a string or an integer, not a %s.' % (type(view_id)))

        if not view and raise_if_not_found:
            raise ValueError('No record found for unique ID %s. It may have been deleted.' % (view_id))
        return view

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
        if not ('GET' in methods and
                endpoint.routing['type'] == 'http' and
                endpoint.routing['auth'] in ('none', 'public') and
                endpoint.routing.get('website', False) and
                all(hasattr(converter, 'generate') for converter in converters)):
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
                    query = i == len(convitems) - 1 and query_string
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
            # is_visible
            domain += [('website_published', '=', True), '|', ('date_publish', '=', False), ('date_publish', '<=', fields.Datetime.now())]

        if query_string:
            domain += [('url', 'like', query_string)]

        pages = self.get_website_pages(domain)

        for page in pages:
            record = {'loc': page['url'], 'id': page['id'], 'name': page['name']}
            if page.view_id and page.view_id.priority != 16:
                record['__priority'] = min(round(page.view_id.priority / 32.0, 1), 1)
            if page['write_date']:
                record['__lastmod'] = page['write_date'].date()
            yield record

    @api.multi
    def get_website_pages(self, domain=[], order='name', limit=None):
        domain += self.get_current_website().website_domain()
        pages = self.env['website.page'].search(domain, order='name', limit=limit)
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
        sha = hashlib.sha1(str(getattr(sudo_record, '__last_update')).encode('utf-8')).hexdigest()[0:7]
        size = '' if size is None else '/%s' % size
        return '/web/image/%s/%s/%s%s?unique=%s' % (record._name, record.id, field, size, sha)

    def get_cdn_url(self, uri):
        self.ensure_one()
        if not uri:
            return ''
        cdn_url = self.cdn_url
        cdn_filters = (self.cdn_filters or '').splitlines()
        for flt in cdn_filters:
            if flt and re.match(flt, uri):
                return urls.url_join(cdn_url, uri)
        return uri

    @api.model
    def action_dashboard_redirect(self):
        if self.env.user.has_group('base.group_system') or self.env.user.has_group('website.group_website_designer'):
            return self.env.ref('website.backend_dashboard').read()[0]
        return self.env.ref('website.action_website').read()[0]

    def button_go_website(self):
        self._force()
        return {
            'type': 'ir.actions.act_url',
            'url': '/',
            'target': 'self',
        }

    @api.multi
    def _get_http_domain(self):
        """Get the domain of the current website, prefixed by http if no
        scheme is specified.

        Empty string if no domain is specified on the website.
        """
        self.ensure_one()
        if not self.domain:
            return ''
        res = urls.url_parse(self.domain)
        return 'http://' + self.domain if not res.scheme else self.domain


class SeoMetadata(models.AbstractModel):

    _name = 'website.seo.metadata'
    _description = 'SEO metadata'

    is_seo_optimized = fields.Boolean("SEO optimized", compute='_compute_is_seo_optimized')
    website_meta_title = fields.Char("Website meta title", translate=True)
    website_meta_description = fields.Text("Website meta description", translate=True)
    website_meta_keywords = fields.Char("Website meta keywords", translate=True)
    website_meta_og_img = fields.Char("Website opengraph image")

    @api.multi
    def _compute_is_seo_optimized(self):
        for record in self:
            record.is_seo_optimized = record.website_meta_title and record.website_meta_description and record.website_meta_keywords

    def _default_website_meta(self):
        """ This method will return default meta information. It return the dict
            contains meta property as a key and meta content as a value.
            e.g. 'og:type': 'website'.

            Override this method in case you want to change default value
            from any model. e.g. change value of og:image to product specific
            images instead of default images
        """
        self.ensure_one()
        company = request.website.company_id.sudo()
        title = (request.website or company).name
        if 'name' in self:
            title = '%s | %s' % (self.name, title)
        if request.website.social_default_image:
            img = '/web/image/website/%s/social_default_image' % request.website.id
        else:
            img = '/web/image/res.company/%s/logo' % company.id
        # Default meta for OpenGraph
        default_opengraph = {
            'og:type': 'website',
            'og:title': title,
            'og:site_name': company.name,
            'og:url': request.httprequest.url,
            'og:image': img,
        }
        # Default meta for Twitter
        default_twitter = {
            'twitter:card': 'summary_large_image',
            'twitter:title': title,
            'twitter:image': img + '/300x300',
        }
        if company.social_twitter:
            default_twitter['twitter:site'] = "@%s" % company.social_twitter.split('/')[-1]

        return {
            'default_opengraph': default_opengraph,
            'default_twitter': default_twitter
        }

    def get_website_meta(self):
        """ This method will return final meta information. It will replace
            default values with user's custom value (if user modified it from
            the seo popup of fronted)

            This method is not meant for overridden. To customize meta values
            override `_default_website_meta` method instead of this method. This
            method only replaces user custom values in defaults.
        """
        root_url = request.httprequest.url_root.strip('/')
        default_meta = self._default_website_meta()
        opengraph_meta, twitter_meta = default_meta['default_opengraph'], default_meta['default_twitter']
        if self.website_meta_title:
            opengraph_meta['og:title'] = self.website_meta_title
            twitter_meta['twitter:title'] = self.website_meta_title
        if self.website_meta_description:
            opengraph_meta['og:description'] = self.website_meta_description
            twitter_meta['twitter:description'] = self.website_meta_description
        meta_image = self.website_meta_og_img or opengraph_meta['og:image']
        if meta_image.startswith('/'):
            meta_image = "%s%s" % (root_url, meta_image)
        opengraph_meta['og:image'] = meta_image
        twitter_meta['twitter:image'] = meta_image
        return {
            'opengraph_meta': opengraph_meta,
            'twitter_meta': twitter_meta
        }


class WebsiteMultiMixin(models.AbstractModel):

    _name = 'website.multi.mixin'
    _description = 'Multi Website Mixin'

    website_id = fields.Many2one('website', string='Website', help='Restrict publishing to this website.')

    @api.multi
    def can_access_from_current_website(self, website_id=False):
        can_access = True
        for record in self:
            if (website_id or record.website_id.id) not in (False, request.website.id):
                can_access = False
                continue
        return can_access


class WebsitePublishedMixin(models.AbstractModel):

    _name = "website.published.mixin"
    _description = 'Website Published Mixin'

    website_published = fields.Boolean('Visible on current website', related='is_published', readonly=False)
    is_published = fields.Boolean('Is published', copy=False)
    website_url = fields.Char('Website URL', compute='_compute_website_url', help='The full URL to access the document through the website.')

    @api.multi
    def _compute_website_url(self):
        for record in self:
            record.website_url = '#'

    @api.multi
    def website_publish_button(self):
        self.ensure_one()
        if self.env.user.has_group('website.group_website_publisher') and self.website_url != '#':
            # Force website to land on record's website to publish/unpublish it
            if 'website_id' in self and self.env.user.has_group('website.group_multi_website'):
                self.website_id._force()
            return self.open_website_url()
        return self.write({'website_published': not self.website_published})

    def open_website_url(self):
        return {
            'type': 'ir.actions.act_url',
            'url': self.website_url,
            'target': 'self',
        }

    def create_and_get_website_url(self, **kwargs):
        return self.create(kwargs).website_url


class WebsitePublishedMultiMixin(WebsitePublishedMixin):

    _name = 'website.published.multi.mixin'
    _inherit = ['website.published.mixin', 'website.multi.mixin']
    _description = 'Multi Website Published Mixin'

    website_published = fields.Boolean(compute='_compute_website_published',
                                       inverse='_inverse_website_published',
                                       search='_search_website_published',
                                       related=False, readonly=False)

    @api.multi
    @api.depends('is_published', 'website_id')
    def _compute_website_published(self):
        current_website_id = self._context.get('website_id')
        for record in self:
            if current_website_id:
                record.website_published = record.is_published and (not record.website_id or record.website_id.id == current_website_id)
            else:
                record.website_published = record.is_published

    @api.multi
    def _inverse_website_published(self):
        for record in self:
            record.is_published = record.website_published

    def _search_website_published(self, operator, value):
        if not isinstance(value, bool) or operator not in ('=', '!='):
            logger.warning('unsupported search on website_published: %s, %s', operator, value)
            return [()]

        if operator in expression.NEGATIVE_TERM_OPERATORS:
            value = not value

        current_website_id = self._context.get('website_id')
        is_published = [('is_published', '=', value)]
        if current_website_id:
            on_current_website = self.env['website'].website_domain(current_website_id)
            return (['!'] if value is False else []) + expression.AND([is_published, on_current_website])
        else:  # should be in the backend, return things that are published anywhere
            return is_published


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

    @api.multi
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
                'type': data['redirect_type'],
                'url_from': original_url,
                'url_to': url,
                'website_id': website.id,
            })

        return url

    @api.multi
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

    @api.multi
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

    @api.multi
    def write(self, vals):
        if 'url' in vals and not vals['url'].startswith('/'):
            vals['url'] = '/' + vals['url']
        return super(Page, self).write(vals)

    def get_website_meta(self):
        self.ensure_one()
        return self.view_id.get_website_meta()


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
    def name_get(self):
        res = []
        for menu in self:
            website_suffix = '%s - %s' % (menu.name, menu.website_id.name)
            res.append((menu.id, website_suffix if menu.website_id and self.env.user.has_group('website.group_multi_website') else menu.name))
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

    @api.multi
    def unlink(self):
        default_menu = self.env.ref('website.main_menu', raise_if_not_found=False)
        menus_to_remove = self
        for menu in self.filtered(lambda m: default_menu and m.parent_id.id == default_menu.id):
            menus_to_remove |= self.env['website.menu'].search([('url', '=', menu.url),
                                                                ('website_id', '!=', False),
                                                                ('id', '!=', menu.id)])
        return super(Menu, menus_to_remove).unlink()

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
            for child in node.child_id:
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

    type = fields.Selection([('301', 'Moved permanently (301)'), ('302', 'Moved temporarily (302)')], string='Redirection Type', required=True, default='301')
    url_from = fields.Char('Redirect From', required=True)
    url_to = fields.Char('Redirect To', required=True)
    website_id = fields.Many2one('website', 'Website')
    active = fields.Boolean(default=True)
    sequence = fields.Integer()
