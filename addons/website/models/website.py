# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import inspect
import logging
import hashlib
import requests
import re

from lxml import etree, html
from werkzeug import urls
from werkzeug.datastructures import OrderedMultiDict
from werkzeug.exceptions import NotFound

from odoo import api, fields, models, tools
from odoo.addons.http_routing.models.ir_http import slugify, _guess_mimetype, url_for
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.addons.portal.controllers.portal import pager
from odoo.addons.iap.tools import iap_tools
from odoo.exceptions import UserError, AccessError
from odoo.http import request
from odoo.modules.module import get_resource_path
from odoo.osv.expression import FALSE_DOMAIN
from odoo.tools.translate import _
from odoo.tools import pycompat

logger = logging.getLogger(__name__)


DEFAULT_CDN_FILTERS = [
    "^/[^/]+/static/",
    "^/web/(css|js)/",
    "^/web/image",
    "^/web/content",
    "^/web/assets",
    # retrocompatibility
    "^/website/image/",
]

DEFAULT_ENDPOINT = 'https://website.api.odoo.com'


class Website(models.Model):

    _name = "website"
    _description = "Website"
    _order = "sequence, id"

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
    sequence = fields.Integer(default=10)
    domain = fields.Char('Website Domain', help='E.g. https://www.mydomain.com')
    country_group_ids = fields.Many2many('res.country.group', 'website_country_group_rel', 'website_id', 'country_group_id',
                                         string='Country Groups', help='Used when multiple websites have the same domain.')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, required=True)
    language_ids = fields.Many2many('res.lang', 'website_lang_rel', 'website_id', 'lang_id', 'Languages', default=_active_languages)
    default_lang_id = fields.Many2one('res.lang', string="Default Language", default=_default_language, required=True)
    auto_redirect_lang = fields.Boolean('Autoredirect Language', default=True, help="Should users be redirected to their browser's language")
    cookies_bar = fields.Boolean('Cookies Bar', help="Display a customizable cookies bar on your website.")
    configurator_done = fields.Boolean(help='True if configurator has been completed or ignored')

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
        image_path = get_resource_path('website', 'static/src/img', 'website_logo.svg')
        with tools.file_open(image_path, 'rb') as f:
            return base64.b64encode(f.read())

    logo = fields.Binary('Website Logo', default=_default_logo, help="Display this logo on the website.")
    social_twitter = fields.Char('Twitter Account', default=_default_social_twitter)
    social_facebook = fields.Char('Facebook Account', default=_default_social_facebook)
    social_github = fields.Char('GitHub Account', default=_default_social_github)
    social_linkedin = fields.Char('LinkedIn Account', default=_default_social_linkedin)
    social_youtube = fields.Char('Youtube Account', default=_default_social_youtube)
    social_instagram = fields.Char('Instagram Account', default=_default_social_instagram)
    social_default_image = fields.Binary(string="Default Social Share Image", help="If set, replaces the website logo as the default social share image.")
    has_social_default_image = fields.Boolean(compute='_compute_has_social_default_image', store=True)

    google_analytics_key = fields.Char('Google Analytics Key')
    google_management_client_id = fields.Char('Google Client ID')
    google_management_client_secret = fields.Char('Google Client Secret')
    google_search_console = fields.Char(help='Google key, or Enable to access first reply')

    google_maps_api_key = fields.Char('Google Maps API Key')

    user_id = fields.Many2one('res.users', string='Public User', required=True)
    cdn_activated = fields.Boolean('Content Delivery Network (CDN)')
    cdn_url = fields.Char('CDN Base URL', default='')
    cdn_filters = fields.Text('CDN Filters', default=lambda s: '\n'.join(DEFAULT_CDN_FILTERS), help="URL matching those filters will be rewritten using the CDN Base URL")
    partner_id = fields.Many2one(related='user_id.partner_id', string='Public Partner', readonly=False)
    menu_id = fields.Many2one('website.menu', compute='_compute_menu', string='Main Menu')
    homepage_id = fields.Many2one('website.page', string='Homepage')
    custom_code_head = fields.Html('Custom <head> code', sanitize=False)
    custom_code_footer = fields.Html('Custom end of <body> code', sanitize=False)

    robots_txt = fields.Html('Robots.txt', translate=False, groups='website.group_website_designer', sanitize=False)

    def _default_favicon(self):
        img_path = get_resource_path('web', 'static/img/favicon.ico')
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

    @api.depends('social_default_image')
    def _compute_has_social_default_image(self):
        for website in self:
            website.has_social_default_image = bool(website.social_default_image)

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

            # prefetch every website.page and ir.ui.view at once
            menus.mapped('is_visible')

            top_menus = menus.filtered(lambda m: not m.parent_id)
            website.menu_id = top_menus and top_menus[0].id or False

    # self.env.uid for ir.rule groups on menu
    @tools.ormcache('self.env.uid', 'self.id')
    def _get_menu_ids(self):
        return self.env['website.menu'].search([('website_id', '=', self.id)]).ids

    @api.model
    def create(self, vals):
        self._handle_create_write(vals)

        if 'user_id' not in vals:
            company = self.env['res.company'].browse(vals.get('company_id'))
            vals['user_id'] = company._get_public_user().id if company else self.env.ref('base.public_user').id

        res = super(Website, self).create(vals)
        res.company_id._compute_website_id()
        res._bootstrap_homepage()

        if not self.env.user.has_group('website.group_multi_website') and self.search_count([]) > 1:
            all_user_groups = 'base.group_portal,base.group_user,base.group_public'
            groups = self.env['res.groups'].concat(*(self.env.ref(it) for it in all_user_groups.split(',')))
            groups.write({'implied_ids': [(4, self.env.ref('website.group_multi_website').id)]})

        return res

    def write(self, values):
        public_user_to_change_websites = self.env['website']
        original_company = self.company_id
        self._handle_create_write(values)

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

        # invalidate cache for `company.website_id` to be recomputed
        if 'sequence' in values or 'company_id' in values:
            (original_company | self.company_id)._compute_website_id()

        if 'cookies_bar' in values:
            existing_policy_page = self.env['website.page'].search([
                ('website_id', '=', self.id),
                ('url', '=', '/cookie-policy'),
            ])
            if not values['cookies_bar']:
                existing_policy_page.unlink()
            elif not existing_policy_page:
                cookies_view = self.env.ref('website.cookie_policy', raise_if_not_found=False)
                if cookies_view:
                    cookies_view.with_context(website_id=self.id).write({'website_id': self.id})
                    specific_cook_view = self.with_context(website_id=self.id).viewref('website.cookie_policy')
                    self.env['website.page'].create({
                        'is_published': True,
                        'website_indexed': False,
                        'url': '/cookie-policy',
                        'website_id': self.id,
                        'view_id': specific_cook_view.id,
                    })

        return result

    @api.model
    def _handle_create_write(self, vals):
        self._handle_favicon(vals)
        self._handle_domain(vals)

    @api.model
    def _handle_favicon(self, vals):
        if 'favicon' in vals:
            vals['favicon'] = tools.image_process(vals['favicon'], size=(256, 256), crop='center', output_format='ICO')

    @api.model
    def _handle_domain(self, vals):
        if 'domain' in vals and vals['domain']:
            if not vals['domain'].startswith('http'):
                vals['domain'] = 'https://%s' % vals['domain']
            vals['domain'] = vals['domain'].rstrip('/')

    @api.ondelete(at_uninstall=False)
    def _unlink_except_last_remaining_website(self):
        website = self.search([('id', 'not in', self.ids)], limit=1)
        if not website:
            raise UserError(_('You must keep at least one website.'))

    def unlink(self):
        # Do not delete invoices, delete what's strictly necessary
        attachments_to_unlink = self.env['ir.attachment'].search([
            ('website_id', 'in', self.ids),
            '|', '|',
            ('key', '!=', False),  # theme attachment
            ('url', 'ilike', '.custom.'),  # customized theme attachment
            ('url', 'ilike', '.assets\\_'),
        ])
        attachments_to_unlink.unlink()
        companies = self.company_id
        res = super(Website, self).unlink()
        companies._compute_website_id()
        return res

    def create_and_redirect_configurator(self):
        self._force()
        configurator_action_todo = self.env.ref('website.website_configurator_todo')
        return configurator_action_todo.action_launch()

    # ----------------------------------------------------------
    # Configurator
    # ----------------------------------------------------------
    def _website_api_rpc(self, route, params):
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        website_api_endpoint = IrConfigParameter.get_param('website.website_api_endpoint', DEFAULT_ENDPOINT)
        endpoint = website_api_endpoint + route
        return iap_tools.iap_jsonrpc(endpoint, params=params)

    def get_cta_data(self, website_purpose, website_type):
        return {'cta_btn_text': False, 'cta_btn_href': '/contactus'}

    @api.model
    def configurator_init(self):
        r = dict()
        company_id = self.get_current_website().company_id
        configurator_features = self.env['website.configurator.feature'].search([])
        r['features'] = [{
            'id': feature.id,
            'name': feature.name,
            'description': feature.description,
            'type': feature.type,
            'icon': feature.icon,
            'website_config_preselection': feature.website_config_preselection,
            'module_state': feature.module_id.state,
        } for feature in configurator_features]
        r['logo'] = False
        if company_id.logo and company_id.logo != company_id._get_logo():
            r['logo'] = company_id.logo.decode('utf-8')
        try:
            result = self._website_api_rpc('/api/website/1/configurator/industries', {'lang': self.env.user.lang})
            r['industries'] = result['industries']
        except AccessError as e:
            logger.warning(e.args[0])
        return r

    @api.model
    def configurator_recommended_themes(self, industry_id, palette):
        domain = [('name', '=like', 'theme%'), ('name', 'not in', ['theme_default', 'theme_common'])]
        client_themes = request.env['ir.module.module'].search(domain).mapped('name')
        params = {
            'palette': palette,
            'client_themes': client_themes,
        }
        return self._website_api_rpc('/api/website/1/configurator/recommended_themes/%s' % industry_id, params)

    @api.model
    def configurator_skip(self):
        website = self.get_current_website()
        website.configurator_done = True

    @api.model
    def configurator_apply(self, **kwargs):
        def set_colors(selected_palette):
            if isinstance(selected_palette, list):
                url = '/website/static/src/scss/options/colors/user_color_palette.scss'
                values = {f'o-color-{i}': color for i, color in enumerate(selected_palette, 1)}
            else:
                url = '/website/static/src/scss/options/user_values.scss'
                values = {'color-palettes-name': "'%s'" % selected_palette}
            self.env['web_editor.assets'].make_scss_customization(url, values)

        def set_features(selected_features):
            feature_ids = self.env['website.configurator.feature'].browse(selected_features)
            pages_views = {}
            modules = self.env['ir.module.module']
            for feature_id in feature_ids:
                if feature_id.type == 'app' and feature_id.module_id and feature_id.module_id.state != 'installed':
                    modules += feature_id.module_id
                if feature_id.type == 'page' and feature_id.page_view_id:
                    result = self.env['website'].new_page(name=feature_id.name, add_menu=True, template=feature_id.page_view_id.key)
                    pages_views[feature_id.iap_page_code] = result['view_id']

            modules.button_immediate_install()

            # Force to refresh env after install of modules
            self._cr.commit()
            api.Environment.reset()
            self.env = api.Environment(modules._cr, modules._uid, modules._context)
            return pages_views

        def configure_page(page_code, snippet_list, pages_views, cta_data):
            if page_code == 'homepage':
                page_view_id = website.homepage_id.view_id
            else:
                page_view_id = self.env['ir.ui.view'].browse(pages_views[page_code])
            rendered_snippets = []
            nb_snippets = len(snippet_list)
            for i, snippet in enumerate(snippet_list, start=1):
                try:
                    view_id = self.env['website'].with_context(website_id=website.id).viewref(snippet)
                    if view_id:
                        el = html.fromstring(view_id._render(values=cta_data))

                        # Add the data-snippet attribute to identify the snippet
                        # for compatibility code
                        el.attrib['data-snippet'] = snippet.split('.', 1)[-1]

                        # Tweak the shape of the first snippet to connect it
                        # properly with the header color in some themes
                        if i == 1:
                            shape_el = el.xpath("//*[hasclass('o_we_shape')]")
                            if shape_el:
                                shape_el[0].attrib['class'] += ' o_header_extra_shape_mapping'

                        # Tweak the shape of the last snippet to connect it
                        # properly with the footer color in some themes
                        if i == nb_snippets:
                            shape_el = el.xpath("//*[hasclass('o_we_shape')]")
                            if shape_el:
                                shape_el[0].attrib['class'] += ' o_footer_extra_shape_mapping'
                        rendered_snippet = pycompat.to_text(etree.tostring(el))
                        rendered_snippets.append(rendered_snippet)
                except ValueError as e:
                    logger.warning(e)
            page_view_id.save(value=''.join(rendered_snippets), xpath="(//div[hasclass('oe_structure')])[last()]")

        def set_images(images):
            for image in images:
                try:
                    response = requests.get(image['url'], timeout=3)
                    response.raise_for_status()
                except Exception as e:
                    logger.warning("Failed to download image: %s.\n%s", image['url'], e)
                else:
                    self.env['ir.attachment'].create({
                        'name': image['name'],
                        'website_id': website.id,
                        'key': image['name'],
                        'type': 'binary',
                        'raw': response.content,
                    })

        website = self.get_current_website()

        theme = self.env['ir.module.module'].search([('name', '=', kwargs['theme_name'])])
        url = theme.button_choose_theme()

        # Force to refresh env after install of module
        self._cr.commit()
        api.Environment.reset()
        self.env = api.Environment(theme._cr, theme._uid, theme._context)

        website.configurator_done = True

        # Enable tour
        tour_asset_id = self.env.ref('website.configurator_tour')
        tour_asset_id.copy({'key': tour_asset_id.key, 'website_id': website.id, 'active': True})

        # logo was generated as base64 url
        logo = kwargs.get('logo')
        if logo:
            website.logo = logo.split(',', 1)[1]

        # palette
        palette = kwargs.get('selected_palette')
        if palette:
            set_colors(palette)

        # modules
        pages_views = set_features(kwargs.get('selected_features'))
        # We need to refresh the environment of website because set_features installed some new module
        # and we need the overrides of these new menus e.g. for .get_cta_data()
        website = self.env['website'].browse(website.id)

        # Load suggestion from iap for selected pages
        requested_pages = list(pages_views.keys())
        requested_pages.append('homepage')
        params = {
            'theme': kwargs.get('theme_name'),
            'pages': requested_pages,
        }
        custom_resources = self._website_api_rpc('/api/website/1/configurator/custom_resources/%s' % kwargs.get('industry_id'), params)

        # Update CTA
        cta_data = website.get_cta_data(kwargs.get('website_purpose'), kwargs.get('website_type'))
        if cta_data['cta_btn_text']:
            xpath_view = 'website.snippets'
            parent_view = self.env['website'].with_context(website_id=website.id).viewref(xpath_view)
            self.env['ir.ui.view'].create({
                'name': parent_view.key + ' CTA',
                'key': parent_view.key + "_cta",
                'inherit_id': parent_view.id,
                'website_id': website.id,
                'type': 'qweb',
                'priority': 32,
                'arch_db': """
                    <data>
                        <xpath expr="//t[@t-set='cta_btn_href']" position="replace">
                            <t t-set="cta_btn_href">%s</t>
                        </xpath>
                        <xpath expr="//t[@t-set='cta_btn_text']" position="replace">
                            <t t-set="cta_btn_text">%s</t>
                        </xpath>
                    </data>
                """ % (cta_data['cta_btn_href'], cta_data['cta_btn_text'])
            })
            header_ids = [
                'website.template_header_default_oe_structure_header_default_1',
                'website.template_header_hamburger_oe_structure_header_hamburger_1',
                'website.template_header_slogan_oe_structure_header_slogan_2',
                'website.template_header_boxed_oe_structure_header_boxed_2',
                'website.template_header_image_oe_structure_header_image_2',
            ]
            for header_id in header_ids:
                try:
                    view_id = self.env['website'].viewref(header_id)
                    if view_id:
                        el = etree.fromstring(view_id.arch_db)
                        btn_cta_el = el.xpath("//a[hasclass('btn_cta')]")
                        if btn_cta_el:
                            btn_cta_el[0].attrib['href'] = cta_data['cta_btn_href']
                            btn_cta_el[0].text = cta_data['cta_btn_text']
                        view_id.with_context(website_id=website.id).write({'arch_db': etree.tostring(el)})
                except ValueError as e:
                    logger.warning(e)

        # Update pages
        pages = custom_resources.get('pages', {})
        for page_code, snippet_list in pages.items():
            configure_page(page_code, snippet_list, pages_views, cta_data)

        images = custom_resources.get('images', [])
        set_images(images)

        return url

    # ----------------------------------------------------------
    # Page Management
    # ----------------------------------------------------------
    def _bootstrap_homepage(self):
        Page = self.env['website.page']
        standard_homepage = self.env.ref('website.homepage', raise_if_not_found=False)
        if not standard_homepage:
            return

        # keep strange indentation in python file, to get it correctly in database
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
        home_menu = self.env['website.menu'].search([('website_id', '=', self.id), ('url', '=', '/')])
        home_menu.page_id = self.homepage_id

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
                'name': _('Top Menu for Website %s', website.id),
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
        result = {'url': page_url}

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
        result['view_id'] = view.id

        if view.arch_fs:
            view.arch_fs = False

        website = self.get_current_website()
        if ispage:
            page = self.env['website.page'].create({
                'url': page_url,
                'website_id': website.id,  # remove it if only one website or not?
                'view_id': view.id,
                'track': True,
            })
            result['page_id'] = page.id
        if add_menu:
            menu = self.env['website.menu'].create({
                'name': name,
                'url': page_url,
                'parent_id': website.menu_id.id,
                'page_id': page.id,
                'website_id': website.id,
            })
            result['menu_id'] = menu.id
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
                'text': _('Page <b>%s</b> contains a link to this page', page.url),
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
                'text': _('This page is in the menu <b>%s</b>', menu.name),
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
                'text': _('Page <b>%s</b> is calling this file', p.url),
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
        return request.env.user.id == request.website._get_cached('user_id')

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
        View = self.env['ir.ui.view'].sudo()
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

    @tools.ormcache_context(keys=('website_id',))
    def _cache_customize_show_views(self):
        views = self.env['ir.ui.view'].with_context(active_test=False).sudo().search([('customize_show', '=', True)])
        views = views.filter_duplicate()
        return {v.key: v.active for v in views}

    @tools.ormcache_context('key', keys=('website_id',))
    def is_view_active(self, key, raise_if_not_found=False):
        """
            Return True if active, False if not active, None if not found or not a customize_show view
        """
        views = self._cache_customize_show_views()
        view = key in views and views[key]
        if view is None and raise_if_not_found:
            raise ValueError('No view of type customize_show found for key %s' % key)
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
        return View.sudo().browse(view_id)

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
        sign = inspect.signature(endpoint.method.original_func)
        params = list(sign.parameters.values())[1:]  # skip self
        supported_kinds = (inspect.Parameter.POSITIONAL_ONLY,
                           inspect.Parameter.POSITIONAL_OR_KEYWORD)
        has_no_default = lambda p: p.default is inspect.Parameter.empty

        # check that all args have a converter
        return all(p.name in rule._converters for p in params
                   if p.kind in supported_kinds and has_no_default(p))

    def _enumerate_pages(self, query_string=None, force=False):
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
            if 'sitemap' in rule.endpoint.routing and rule.endpoint.routing['sitemap'] is not True:
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

            if 'sitemap' not in rule.endpoint.routing:
                logger.warning('No Sitemap value provided for controller %s (%s)' %
                               (rule.endpoint.method, ','.join(rule.endpoint.routing['routes'])))

            converters = rule._converters or {}
            if query_string and not converters and (query_string not in rule.build({}, append_unknown=False)[1]):
                continue

            values = [{}]
            # converters with a domain are processed after the other ones
            convitems = sorted(
                converters.items(),
                key=lambda x: (hasattr(x[1], 'domain') and (x[1].domain != '[]'), rule._trace.index((True, x[0]))))

            for (i, (name, converter)) in enumerate(convitems):
                if 'website_id' in self.env[converter.model]._fields and (not converter.domain or converter.domain == '[]'):
                    converter.domain = "[('website_id', 'in', (False, current_website_id))]"

                newval = []
                for val in values:
                    query = i == len(convitems) - 1 and query_string
                    if query:
                        r = "".join([x[1] for x in rule._trace[1:] if not x[0]])  # remove model converter from route
                        query = sitemap_qs2dom(query, r, self.env[converter.model]._rec_name)
                        if query == FALSE_DOMAIN:
                            continue

                    for rec in converter.generate(uid=self.env.uid, dom=query, args=val):
                        newval.append(val.copy())
                        newval[-1].update({name: rec})
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
            domain += [('website_indexed', '=', True), ('visibility', '=', False)]
            # is_visible
            domain += [
                ('website_published', '=', True), ('visibility', '=', False),
                '|', ('date_publish', '=', False), ('date_publish', '<=', fields.Datetime.now())
            ]

        if query_string:
            domain += [('url', 'like', query_string)]

        pages = self._get_website_pages(domain)

        for page in pages:
            record = {'loc': page['url'], 'id': page['id'], 'name': page['name']}
            if page.view_id and page.view_id.priority != 16:
                record['priority'] = min(round(page.view_id.priority / 32.0, 1), 1)
            if page['write_date']:
                record['lastmod'] = page['write_date'].date()
            yield record

    def _get_website_pages(self, domain=None, order='name', limit=None):
        if domain is None:
            domain = []
        domain += self.get_current_website().website_domain()
        pages = self.env['website.page'].sudo().search(domain, order=order, limit=limit)
        return pages

    def search_pages(self, needle=None, limit=None):
        name = slugify(needle, max_length=50, path=True)
        res = []
        for page in self._enumerate_pages(query_string=name, force=True):
            res.append(page)
            if len(res) == limit:
                break
        return res

    def get_suggested_controllers(self):
        """
            Returns a tuple (name, url, icon).
            Where icon can be a module name, or a path
        """
        suggested_controllers = [
            (_('Homepage'), url_for('/'), 'website'),
            (_('Contact Us'), url_for('/contactus'), 'website_crm'),
        ]
        return suggested_controllers

    @api.model
    def image_url(self, record, field, size=None):
        """ Returns a local url that points to the image field of a given browse record. """
        sudo_record = record.sudo()
        sha = hashlib.sha512(str(getattr(sudo_record, '__last_update')).encode('utf-8')).hexdigest()[:7]
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
            return self.env["ir.actions.actions"]._for_xml_id("website.backend_dashboard")
        return self.env["ir.actions.actions"]._for_xml_id("website.action_website")

    def button_go_website(self, path='/', mode_edit=False):
        self._force()
        if mode_edit:
            path += '?enable_editor=1'
        return {
            'type': 'ir.actions.act_url',
            'url': path,
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

    def _get_canonical_url_localized(self, lang, canonical_params):
        """Returns the canonical URL for the current request with translatable
        elements appropriately translated in `lang`.

        If `request.endpoint` is not true, returns the current `path` instead.

        `url_quote_plus` is applied on the returned path.
        """
        self.ensure_one()
        if request.endpoint:
            router = request.httprequest.app.get_db_router(request.db).bind('')
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

    @tools.ormcache('self.id')
    def _get_cached_values(self):
        self.ensure_one()
        return {
            'user_id': self.user_id.id,
            'company_id': self.company_id.id,
            'default_lang_id': self.default_lang_id.id,
        }

    def _get_cached(self, field):
        return self._get_cached_values()[field]
