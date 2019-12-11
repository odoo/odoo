# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import datetime
import json
import os
import logging
import pytz
import requests
import werkzeug.utils
import werkzeug.wrappers

from itertools import islice
from xml.etree import ElementTree as ET

import odoo

from odoo import http, models, fields, _
from odoo.http import request
from odoo.tools import OrderedSet
from odoo.addons.http_routing.models.ir_http import slug, _guess_mimetype
from odoo.addons.web.controllers.main import Binary
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.portal.controllers.web import Home

logger = logging.getLogger(__name__)

# Completely arbitrary limits
MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT = IMAGE_LIMITS = (1024, 768)
LOC_PER_SITEMAP = 45000
SITEMAP_CACHE_TIME = datetime.timedelta(hours=12)


class QueryURL(object):
    def __init__(self, path='', path_args=None, **args):
        self.path = path
        self.args = args
        self.path_args = OrderedSet(path_args or [])

    def __call__(self, path=None, path_args=None, **kw):
        path = path or self.path
        for key, value in self.args.items():
            kw.setdefault(key, value)
        path_args = OrderedSet(path_args or []) | self.path_args
        paths, fragments = {}, []
        for key, value in kw.items():
            if value and key in path_args:
                if isinstance(value, models.BaseModel):
                    paths[key] = slug(value)
                else:
                    paths[key] = u"%s" % value
            elif value:
                if isinstance(value, list) or isinstance(value, set):
                    fragments.append(werkzeug.url_encode([(key, item) for item in value]))
                else:
                    fragments.append(werkzeug.url_encode([(key, value)]))
        for key in path_args:
            value = paths.get(key)
            if value is not None:
                path += '/' + key + '/' + value
        if fragments:
            path += '?' + '&'.join(fragments)
        return path


class Website(Home):

    @http.route('/', type='http', auth="public", website=True)
    def index(self, **kw):
        homepage = request.website.homepage_id
        if homepage and (homepage.sudo().is_visible or request.env.user.has_group('base.group_user')) and homepage.url != '/':
            return request.env['ir.http'].reroute(homepage.url)

        website_page = request.env['ir.http']._serve_page()
        if website_page:
            return website_page
        else:
            top_menu = request.website.menu_id
            first_menu = top_menu and top_menu.child_id and top_menu.child_id.filtered(lambda menu: menu.is_visible)
            if first_menu and first_menu[0].url not in ('/', '', '#') and (not (first_menu[0].url.startswith(('/?', '/#', ' ')))):
                return request.redirect(first_menu[0].url)

        raise request.not_found()

    @http.route('/website/force_website', type='json', auth="user")
    def force_website(self, website_id):
        request.env['website']._force_website(website_id)
        return True

    # ------------------------------------------------------
    # Login - overwrite of the web login so that regular users are redirected to the backend
    # while portal users are redirected to the frontend by default
    # ------------------------------------------------------

    @http.route(website=True, auth="public", sitemap=False)
    def web_login(self, redirect=None, *args, **kw):
        response = super(Website, self).web_login(redirect=redirect, *args, **kw)
        if not redirect and request.params['login_success']:
            if request.env['res.users'].browse(request.uid).has_group('base.group_user'):
                redirect = b'/web?' + request.httprequest.query_string
            else:
                redirect = '/my'
            return http.redirect_with_hash(redirect)
        return response

    # ------------------------------------------------------
    # Business
    # ------------------------------------------------------

    @http.route('/website/get_languages', type='json', auth="user", website=True)
    def website_languages(self, **kwargs):
        return [(lg.code, lg.url_code, lg.name) for lg in request.website.language_ids]

    @http.route('/website/lang/<lang>', type='http', auth="public", website=True, multilang=False)
    def change_lang(self, lang, r='/', **kwargs):
        """ :param lang: supposed to be value of `url_code` field """
        if lang == 'default':
            lang = request.website.default_lang_id.url_code
            r = '/%s%s' % (lang, r or '/')
        redirect = werkzeug.utils.redirect(r or ('/%s' % lang), 303)
        lang_code = request.env['res.lang']._lang_get_code(lang)
        redirect.set_cookie('frontend_lang', lang_code)
        return redirect

    @http.route(['/website/country_infos/<model("res.country"):country>'], type='json', auth="public", methods=['POST'], website=True)
    def country_infos(self, country, **kw):
        fields = country.get_address_fields()
        return dict(fields=fields, states=[(st.id, st.name, st.code) for st in country.state_ids], phone_code=country.phone_code)

    @http.route(['/robots.txt'], type='http', auth="public")
    def robots(self, **kwargs):
        return request.render('website.robots', {'url_root': request.httprequest.url_root}, mimetype='text/plain')

    @http.route('/sitemap.xml', type='http', auth="public", website=True, multilang=False, sitemap=False)
    def sitemap_xml_index(self, **kwargs):
        current_website = request.website
        Attachment = request.env['ir.attachment'].sudo()
        View = request.env['ir.ui.view'].sudo()
        mimetype = 'application/xml;charset=utf-8'
        content = None

        def create_sitemap(url, content):
            return Attachment.create({
                'datas': base64.b64encode(content),
                'mimetype': mimetype,
                'type': 'binary',
                'name': url,
                'url': url,
            })
        dom = [('url', '=', '/sitemap-%d.xml' % current_website.id), ('type', '=', 'binary')]
        sitemap = Attachment.search(dom, limit=1)
        if sitemap:
            # Check if stored version is still valid
            create_date = fields.Datetime.from_string(sitemap.create_date)
            delta = datetime.datetime.now() - create_date
            if delta < SITEMAP_CACHE_TIME:
                content = base64.b64decode(sitemap.datas)

        if not content:
            # Remove all sitemaps in ir.attachments as we're going to regenerated them
            dom = [('type', '=', 'binary'), '|', ('url', '=like', '/sitemap-%d-%%.xml' % current_website.id),
                   ('url', '=', '/sitemap-%d.xml' % current_website.id)]
            sitemaps = Attachment.search(dom)
            sitemaps.unlink()

            pages = 0
            locs = request.website.with_user(request.website.user_id).enumerate_pages()
            while True:
                values = {
                    'locs': islice(locs, 0, LOC_PER_SITEMAP),
                    'url_root': request.httprequest.url_root[:-1],
                }
                urls = View.render_template('website.sitemap_locs', values)
                if urls.strip():
                    content = View.render_template('website.sitemap_xml', {'content': urls})
                    pages += 1
                    last_sitemap = create_sitemap('/sitemap-%d-%d.xml' % (current_website.id, pages), content)
                else:
                    break

            if not pages:
                return request.not_found()
            elif pages == 1:
                # rename the -id-page.xml => -id.xml
                last_sitemap.write({
                    'url': "/sitemap-%d.xml" % current_website.id,
                    'name': "/sitemap-%d.xml" % current_website.id,
                })
            else:
                # TODO: in master/saas-15, move current_website_id in template directly
                pages_with_website = ["%d-%d" % (current_website.id, p) for p in range(1, pages + 1)]

                # Sitemaps must be split in several smaller files with a sitemap index
                content = View.render_template('website.sitemap_index_xml', {
                    'pages': pages_with_website,
                    'url_root': request.httprequest.url_root,
                })
                create_sitemap('/sitemap-%d.xml' % current_website.id, content)

        return request.make_response(content, [('Content-Type', mimetype)])

    @http.route('/website/info', type='http', auth="public", website=True)
    def website_info(self, **kwargs):
        try:
            request.website.get_template('website.website_info').name
        except Exception as e:
            return request.env['ir.http']._handle_exception(e, 404)
        Module = request.env['ir.module.module'].sudo()
        apps = Module.search([('state', '=', 'installed'), ('application', '=', True)])
        l10n = Module.search([('state', '=', 'installed'), ('name', '=like', 'l10n_%')])
        values = {
            'apps': apps,
            'l10n': l10n,
            'version': odoo.service.common.exp_version()
        }
        return request.render('website.website_info', values)

    # ------------------------------------------------------
    # Edit
    # ------------------------------------------------------

    @http.route(['/website/pages', '/website/pages/page/<int:page>'], type='http', auth="user", website=True)
    def pages_management(self, page=1, sortby='url', search='', **kw):
        # only website_designer should access the page Management
        if not request.env.user.has_group('website.group_website_designer'):
            raise werkzeug.exceptions.NotFound()

        Page = request.env['website.page']
        searchbar_sortings = {
            'url': {'label': _('Sort by Url'), 'order': 'url'},
            'name': {'label': _('Sort by Name'), 'order': 'name'},
        }
        # default sortby order
        sort_order = searchbar_sortings.get(sortby, 'url')['order'] + ', website_id desc, id'

        domain = request.website.website_domain()
        if search:
            domain += ['|', ('name', 'ilike', search), ('url', 'ilike', search)]

        pages = Page.search(domain, order=sort_order)
        if sortby != 'url' or not request.env.user.has_group('website.group_multi_website'):
            pages = pages.filtered(pages._is_most_specific_page)
        pages_count = len(pages)

        step = 50
        pager = portal_pager(
            url="/website/pages",
            url_args={'sortby': sortby},
            total=pages_count,
            page=page,
            step=step
        )

        pages = pages[(page - 1) * step:page * step]

        values = {
            'pager': pager,
            'pages': pages,
            'search': search,
            'sortby': sortby,
            'searchbar_sortings': searchbar_sortings,
        }
        return request.render("website.list_website_pages", values)

    @http.route(['/website/add/', '/website/add/<path:path>'], type='http', auth="user", website=True)
    def pagenew(self, path="", noredirect=False, add_menu=False, template=False, **kwargs):
        # for supported mimetype, get correct default template
        _, ext = os.path.splitext(path)
        ext_special_case = ext and ext in _guess_mimetype() and ext != '.html'

        if not template and ext_special_case:
            default_templ = 'website.default_%s' % ext.lstrip('.')
            if request.env.ref(default_templ, False):
                template = default_templ

        template = template and dict(template=template) or {}
        page = request.env['website'].new_page(path, add_menu=add_menu, **template)
        url = page['url']
        if noredirect:
            return werkzeug.wrappers.Response(url, mimetype='text/plain')

        if ext_special_case:  # redirect non html pages to backend to edit
            return werkzeug.utils.redirect('/web#id=' + str(page.get('view_id')) + '&view_type=form&model=ir.ui.view')
        return werkzeug.utils.redirect(url + "?enable_editor=1")

    @http.route("/website/get_switchable_related_views", type="json", auth="user", website=True)
    def get_switchable_related_views(self, key):
        views = request.env["ir.ui.view"].get_related_views(key, bundles=False).filtered(lambda v: v.customize_show)
        views = views.sorted(key=lambda v: (v.inherit_id.id, v.name))
        return views.read(['name', 'id', 'key', 'xml_id', 'arch', 'active', 'inherit_id'])

    @http.route('/website/toggle_switchable_view', type='json', auth='user', website=True)
    def toggle_switchable_view(self, view_key):
        request.website.viewref(view_key).toggle()

    @http.route('/website/reset_template', type='http', auth='user', methods=['POST'], website=True, csrf=False)
    def reset_template(self, view_id, mode='soft', redirect='/', **kwargs):
        """ This method will try to reset a broken view.
        Given the mode, the view can either be:
        - Soft reset: restore to previous architeture.
        - Hard reset: it will read the original `arch` from the XML file if the
        view comes from an XML file (arch_fs).
        """
        view = request.env['ir.ui.view'].browse(int(view_id))
        # Deactivate COW to not fix a generic view by creating a specific
        view.with_context(website_id=None).reset_arch(mode)
        return request.redirect(redirect)

    @http.route(['/website/publish'], type='json', auth="public", website=True)
    def publish(self, id, object):
        Model = request.env[object]
        record = Model.browse(int(id))

        values = {}
        if 'website_published' in Model._fields:
            values['website_published'] = not record.website_published
        record.write(values)
        return bool(record.website_published)

    @http.route(['/website/seo_suggest'], type='json', auth="user", website=True)
    def seo_suggest(self, keywords=None, lang=None):
        language = lang.split("_")
        url = "http://google.com/complete/search"
        try:
            req = requests.get(url, params={
                'ie': 'utf8', 'oe': 'utf8', 'output': 'toolbar', 'q': keywords, 'hl': language[0], 'gl': language[1]})
            req.raise_for_status()
            response = req.content
        except IOError:
            return []
        xmlroot = ET.fromstring(response)
        return json.dumps([sugg[0].attrib['data'] for sugg in xmlroot if len(sugg) and sugg[0].attrib['data']])

    # ------------------------------------------------------
    # Themes
    # ------------------------------------------------------

    def _get_customize_views(self, xml_ids):
        View = request.env["ir.ui.view"].with_context(active_test=False)
        if not xml_ids:
            return View
        domain = [("key", "in", xml_ids)] + request.website.website_domain()
        return View.search(domain).filter_duplicate()

    @http.route(['/website/theme_customize_get'], type='json', auth="public", website=True)
    def theme_customize_get(self, xml_ids):
        views = self._get_customize_views(xml_ids)
        return {
            'enabled': views.filtered('active').mapped('key'),
            'names': {view.key: view.name for view in views},
        }

    @http.route(['/website/theme_customize'], type='json', auth="public", website=True)
    def theme_customize(self, enable=None, disable=None, get_bundle=False):
        """ enable or Disable lists of ``xml_id`` of the inherit templates """

        self._get_customize_views(disable).write({'active': False})
        self._get_customize_views(enable).write({'active': True})

        if get_bundle:
            context = dict(request.context)
            return {
                'web.assets_common': request.env['ir.qweb']._get_asset_link_urls('web.assets_common', options=context),
                'web.assets_frontend': request.env['ir.qweb']._get_asset_link_urls('web.assets_frontend', options=context),
                'website.assets_editor': request.env['ir.qweb']._get_asset_link_urls('website.assets_editor', options=context),
            }

        return True

    @http.route(['/website/theme_customize_reload'], type='http', auth="public", website=True)
    def theme_customize_reload(self, href, enable, disable, tab=0, **kwargs):
        self.theme_customize(enable and enable.split(",") or [], disable and disable.split(",") or [])
        return request.redirect(href + ("&theme=true" if "#" in href else "#theme=true") + ("&tab=" + tab))

    @http.route(['/website/make_scss_custo'], type='json', auth='user', website=True)
    def make_scss_custo(self, url, values):
        """
        Params:
            url (str):
                the URL of the scss file to customize (supposed to be a variable
                file which will appear in the assets_common bundle)

            values (dict):
                key,value mapping to integrate in the file's map (containing the
                word hook). If a key is already in the file's map, its value is
                overridden.

        Returns:
            boolean
        """
        request.env['web_editor.assets'].make_scss_customization(url, values)
        return True

    @http.route(['/website/multi_render'], type='json', auth="public", website=True)
    def multi_render(self, ids_or_xml_ids, values=None):
        View = request.env['ir.ui.view']
        res = {}
        for id_or_xml_id in ids_or_xml_ids:
            res[id_or_xml_id] = View.render_template(id_or_xml_id, values)
        return res

    @http.route(['/website/update_visitor_timezone'], type='json', auth="public", website=True)
    def update_visitor_timezone(self, timezone):
        visitor_sudo = request.env['website.visitor']._get_visitor_from_request()
        if visitor_sudo:
            if timezone in pytz.all_timezones:
                visitor_sudo.write({'timezone': timezone})
                return True
        return False

    # ------------------------------------------------------
    # Server actions
    # ------------------------------------------------------

    @http.route([
        '/website/action/<path_or_xml_id_or_id>',
        '/website/action/<path_or_xml_id_or_id>/<path:path>',
    ], type='http', auth="public", website=True)
    def actions_server(self, path_or_xml_id_or_id, **post):
        ServerActions = request.env['ir.actions.server']
        action = action_id = None

        # find the action_id: either an xml_id, the path, or an ID
        if isinstance(path_or_xml_id_or_id, str) and '.' in path_or_xml_id_or_id:
            action = request.env.ref(path_or_xml_id_or_id, raise_if_not_found=False)
        if not action:
            action = ServerActions.search([('website_path', '=', path_or_xml_id_or_id), ('website_published', '=', True)], limit=1)
        if not action:
            try:
                action_id = int(path_or_xml_id_or_id)
            except ValueError:
                pass

        # check it effectively exists
        if action_id:
            action = ServerActions.browse(action_id).exists()
        # run it, return only if we got a Response object
        if action:
            if action.state == 'code' and action.website_published:
                action_res = action.run()
                if isinstance(action_res, werkzeug.wrappers.Response):
                    return action_res

        return request.redirect('/')


# ------------------------------------------------------
# Retrocompatibility routes
# ------------------------------------------------------
class WebsiteBinary(http.Controller):

    @http.route([
        '/website/image',
        '/website/image/<xmlid>',
        '/website/image/<xmlid>/<int:width>x<int:height>',
        '/website/image/<xmlid>/<field>',
        '/website/image/<xmlid>/<field>/<int:width>x<int:height>',
        '/website/image/<model>/<id>/<field>',
        '/website/image/<model>/<id>/<field>/<int:width>x<int:height>'
    ], type='http', auth="public", website=False, multilang=False)
    def content_image(self, id=None, max_width=0, max_height=0, **kw):
        if max_width:
            kw['width'] = max_width
        if max_height:
            kw['height'] = max_height
        if id:
            id, _, unique = id.partition('_')
            kw['id'] = int(id)
            if unique:
                kw['unique'] = unique
        return Binary().content_image(**kw)

    @http.route(['/favicon.ico'], type='http', auth='public', website=True, multilang=False, sitemap=False)
    def favicon(self, **kw):
        # when opening a pdf in chrome, chrome tries to open the default favicon url
        return self.content_image(model='website', id=str(request.website.id), field='favicon', **kw)
