# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import inspect
import logging
import hashlib
import re


from werkzeug import urls
from werkzeug.datastructures import OrderedMultiDict
from werkzeug.exceptions import NotFound

from odoo import api, fields, models, tools, http
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
from odoo.addons.http_routing.models.ir_http import slugify, _guess_mimetype
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.addons.portal.controllers.portal import pager
from odoo.exceptions import UserError
from odoo.http import request
from odoo.modules.module import get_resource_path
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
        def_lang_id = self.env['res.lang']._lang_get_id(lang_code)
        return def_lang_id or self._active_languages()[0]

    name = fields.Char('Website Name', required=True)
    domain = fields.Char('Website Domain',
        help='Will be prefixed by http in canonical URLs if no scheme is specified')
    country_group_ids = fields.Many2many('res.country.group', 'website_country_group_rel', 'website_id', 'country_group_id',
                                         string='Country Groups', help='Used when multiple websites have the same domain.')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, required=True)
    language_ids = fields.Many2many('res.lang', 'website_lang_rel', 'website_id', 'lang_id', 'Languages', default=_active_languages)
    default_lang_id = fields.Many2one('res.lang', string="Default Language", default=_default_language, required=True)
    auto_redirect_lang = fields.Boolean('Autoredirect Language', default=True, help="Should users be redirected to their browser's language")

    def _default_social_facebook(self):
        return self.env.ref('base.main_company').social_facebook

    def _default_social_github(self):
        return self.env.ref('base.main_company').social_github

    def _default_social_linkedin(self):
        return self.env.ref('base.main_company').social_linkedin

    def _default_social_youtube(self):
        return self.env.ref('base.main_company').social_youtube

    def _default_social_instagram(self):
        return self.env.ref('base.main_company').social_instagram

    def _default_social_twitter(self):
        return self.env.ref('base.main_company').social_twitter

    def _default_logo(self):
        image_path = get_resource_path('website', 'static/src/img', 'website_logo.png')
        with tools.file_open(image_path, 'rb') as f:
            return base64.b64encode(f.read())

    logo = fields.Binary('Website Logo', default=_default_logo, help="Display this logo on the website.")
    social_twitter = fields.Char('Twitter Account', default=_default_social_twitter)
    social_facebook = fields.Char('Facebook Account', default=_default_social_facebook)
    social_github = fields.Char('GitHub Account', default=_default_social_github)
    social_linkedin = fields.Char('LinkedIn Account', default=_default_social_linkedin)
    social_youtube = fields.Char('Youtube Account', default=_default_social_youtube)
    social_instagram = fields.Char('Instagram Account', default=_default_social_instagram)
    social_default_image = fields.Binary(string="Default Social Share Image", help="If set, replaces the company logo as the default social share image.")

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

    def _default_favicon(self):
        img_path = get_resource_path('web', 'static/src/img/favicon.ico')
        with tools.file_open(img_path, 'rb') as f:
            return base64.b64encode(f.read())

    favicon = fields.Binary(string="Website Favicon", help="This field holds the image used to display a favicon on the website.", default=_default_favicon)
    theme_id = fields.Many2one('ir.module.module', help='Installed theme')

    specific_user_account = fields.Boolean('Specific User Account', help='If True, new accounts will be associated to the current website')
    auth_signup_uninvited = fields.Selection([
        ('b2b', 'On invitation'),
        ('b2c', 'Free sign up'),
    ], string='Customer Account', default='b2b')

    @api.onchange('language_ids')
    def _onchange_language_ids(self):
        language_ids = self.language_ids._origin
        if language_ids and self.default_lang_id not in language_ids:
            self.default_lang_id = language_ids[0]

    def _compute_menu(self):
        for website in self:
            menus = self.env['website.menu'].browse(website._get_menu_ids())

            # use field parent_id (1 query) to determine field child_id (2 queries by level)"
            for menu in menus:
                menu._cache['child_id'] = ()
            for menu in menus:
                # don't add child menu if parent is forbidden
                if menu.parent_id and menu.parent_id in menus:
                    menu.parent_id._cache['child_id'] += (menu.id,)

            top_menus = menus.filtered(lambda m: not m.parent_id)
            website.menu_id = top_menus and top_menus[0].id or False

    # self.env.uid for ir.rule groups on menu
    @tools.ormcache('self.env.uid', 'self.id')
    def _get_menu_ids(self):
        return self.env['website.menu'].search([('website_id', '=', self.id)]).ids

    @api.model
    def create(self, vals):
        self._handle_favicon(vals)

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

    def write(self, values):
        public_user_to_change_websites = self.env['website']
        self._handle_favicon(values)

        self.clear_caches()

        if 'company_id' in values and 'user_id' not in values:
            public_user_to_change_websites = self.filtered(lambda w: w.sudo().user_id.company_id.id != values['company_id'])
            if public_user_to_change_websites:
                company = self.env['res.company'].browse(values['company_id'])
                super(Website, public_user_to_change_websites).write(dict(values, user_id=company and company._get_public_user().id))

        result = super(Website, self - public_user_to_change_websites).write(values)
        if 'cdn_activated' in values or 'cdn_url' in values or 'cdn_filters' in values:
            # invalidate the caches from static node at compile time
            self.env['ir.qweb'].clear_caches()
        return result

    @api.model
    def _handle_favicon(self, vals):
        if 'favicon' in vals:
            vals['favicon'] = tools.image_process(vals['favicon'], size=(256, 256), crop='center', output_format='ICO')

    def unlink(self):
        if not self.env.context.get(MODULE_UNINSTALL_FLAG, False):
            website = self.search([('id', 'not in', self.ids)], limit=1)
            if not website:
                raise UserError(_('You must keep at least one website.'))

        # Do not delete invoices, delete what's strictly necessary
        attachments_to_unlink = self.env['ir.attachment'].search([
            ('website_id', 'in', self.ids),
            '|', '|',
            ('key', '!=', False),  # theme attachment
            ('url', 'ilike', '.custom.'),  # customized theme attachment
            ('url', 'ilike', '.assets\\_'),
        ])
        attachments_to_unlink.unlink()
        return super(Website, self).unlink()

    # ----------------------------------------------------------
    # Page Management
    # ----------------------------------------------------------
    def _bootstrap_homepage(self):
        Page = self.env['website.page']
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

        homepage_page = Page.search([
            ('website_id', '=', self.id),
            ('key', '=', standard_homepage.key),
        ], limit=1)
        if not homepage_page:
            homepage_page = Page.create({
                'website_published': True,
                'url': '/',
                'view_id': self.with_context(website_id=self.id).viewref('website.homepage').id,
            })
        # prevent /-1 as homepage URL
        homepage_page.url = '/'
        self.homepage_id = homepage_page

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
                'website_id': website.id,  # remove it if only one website or not?
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

    def _get_alternate_languages(self, canonical_params):
        self.ensure_one()

        if not self._is_canonical_url(canonical_params=canonical_params):
            # no hreflang on non-canonical pages
            return []

        languages = self.language_ids
        if len(languages) <= 1:
            # no hreflang if no alternate language
            return []

        langs = []
        shorts = []

        for lg in languages:
            lg_codes = lg.code.split('_')
            short = lg_codes[0]
            shorts.append(short)
            langs.append({
                'hreflang': ('-'.join(lg_codes)).lower(),
                'short': short,
                'href': self._get_canonical_url_localized(lang=lg, canonical_params=canonical_params),
            })

        # if there is only one region for a language, use only the language code
        for lang in langs:
            if shorts.count(lang['short']) == 1:
                lang['hreflang'] = lang['short']

        # add the default
        langs.append({
            'hreflang': 'x-default',
            'href': self._get_canonical_url_localized(lang=self.default_lang_id, canonical_params=canonical_params),
        })

        return langs

    # ----------------------------------------------------------
    # Utilities
    # ----------------------------------------------------------

    @api.model
    def get_current_website(self, fallback=True):
        if request and request.session.get('force_website_id'):
            website_id = self.browse(request.session['force_website_id']).exists()
            if not website_id:
                # Don't crash is session website got deleted
                request.session.pop('force_website_id')
            else:
                return website_id

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
        if isinstance(view_id, str):
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
        elif isinstance(view_id, int):
            view = View.browse(view_id)
        else:
            raise ValueError('Expecting a string or an integer, not a %s.' % (type(view_id)))

        if not view and raise_if_not_found:
            raise ValueError('No record found for unique ID %s. It may have been deleted.' % (view_id))
        return view

    @api.model
    def get_template(self, template):
        View = self.env['ir.ui.view']
        if isinstance(template, int):
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

        router = http.root.get_db_router(request.db)
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
            if query_string and not converters and (query_string not in rule.build({}, append_unknown=False)[1]):
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
                record['priority'] = min(round(page.view_id.priority / 32.0, 1), 1)
            if page['write_date']:
                record['lastmod'] = page['write_date'].date()
            yield record

    def get_website_pages(self, domain=[], order='name', limit=None):
        domain += self.get_current_website().website_domain()
        pages = self.env['website.page'].search(domain, order='name', limit=limit)
        return pages

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

    def get_base_url(self):
        self.ensure_one()
        return self._get_http_domain() or super(BaseModel, self).get_base_url()

    def _get_canonical_url_localized(self, lang, canonical_params):
        """Returns the canonical URL for the current request with translatable
        elements appropriately translated in `lang`.

        If `request.endpoint` is not true, returns the current `path` instead.

        `url_quote_plus` is applied on the returned path.
        """
        self.ensure_one()
        if request.endpoint:
            router = http.root.get_db_router(request.db).bind('')
            arguments = dict(request.endpoint_arguments)
            for key, val in list(arguments.items()):
                if isinstance(val, models.BaseModel):
                    if val.env.context.get('lang') != lang.code:
                        arguments[key] = val.with_context(lang=lang.code)
            path = router.build(request.endpoint, arguments)
        else:
            # The build method returns a quoted URL so convert in this case for consistency.
            path = urls.url_quote_plus(request.httprequest.path, safe='/')
        lang_path = ('/' + lang.url_code) if lang != self.default_lang_id else ''
        canonical_query_string = '?%s' % urls.url_encode(canonical_params) if canonical_params else ''
        return self.get_base_url() + lang_path + path + canonical_query_string

    def _get_canonical_url(self, canonical_params):
        """Returns the canonical URL for the current request."""
        self.ensure_one()
        return self._get_canonical_url_localized(lang=request.lang, canonical_params=canonical_params)

    def _is_canonical_url(self, canonical_params):
        """Returns whether the current request URL is canonical."""
        self.ensure_one()
        # Compare OrderedMultiDict because the order is important, there must be
        # only one canonical and not params permutations.
        params = request.httprequest.args
        canonical_params = canonical_params or OrderedMultiDict()
        if params != canonical_params:
            return False
        # Compare URL at the first rerouting iteration (if available) because
        # it's the one with the language in the path.
        # It is important to also test the domain of the current URL.
        current_url = request.httprequest.url_root[:-1] + (hasattr(request, 'rerouting') and request.rerouting[0] or request.httprequest.path)
        canonical_url = self._get_canonical_url_localized(lang=request.lang, canonical_params=None)
        # A request path with quotable characters (such as ",") is never
        # canonical because request.httprequest.base_url is always unquoted,
        # and canonical url is always quoted, so it is never possible to tell
        # if the current URL is indeed canonical or not.
        return current_url == canonical_url

    def _get_relative_url(self, url):
        return urls.url_parse(url).replace(scheme='', netloc='').to_url()


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def get_base_url(self):
        """
        Returns baseurl about one given record.
        If a website_id field exists in the current record we use the url
        from this website as base url.

        :return: the base url for this record
        :rtype: string

        """
        self.ensure_one()
        if 'website_id' in self and self.website_id.domain:
            return self.website_id._get_http_domain()
        else:
            return super(BaseModel, self).get_base_url()
