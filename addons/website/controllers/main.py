# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
import json
import logging
import re
import urllib2
import werkzeug.utils
import werkzeug.wrappers

from itertools import islice
import xml.etree.ElementTree as ET

from odoo import fields, http, service, tools
from odoo.http import request
from odoo.addons.base.ir.ir_qweb import AssetsBundle
from odoo.addons.web.controllers.main import Binary, Home, WebClient

logger = logging.getLogger(__name__)

# Completely arbitrary limits
MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT = IMAGE_LIMITS = (1024, 768)
LOC_PER_SITEMAP = 45000
SITEMAP_CACHE_TIME = datetime.timedelta(hours=12)

class Website(Home):
    #------------------------------------------------------
    # View
    #------------------------------------------------------
    @http.route('/', type='http', auth="public", website=True)
    def index(self, **kw):
        page = 'homepage'
        main_menu = request.env.ref('website.main_menu', raise_if_not_found=False)
        if main_menu:
            first_menu = main_menu.child_id and main_menu.child_id[0]
            if first_menu:
                if first_menu.url and (not (first_menu.url.startswith(('/page/', '/?', '/#')) or (first_menu.url == '/'))):
                    return request.redirect(first_menu.url)
                if first_menu.url and first_menu.url.startswith('/page/'):
                    return request.registry['ir.http'].reroute(first_menu.url)
        return self.page(page)

    #------------------------------------------------------
    # Login - overwrite of the web login so that regular users are redirected to the backend
    # while portal users are redirected to the frontend by default
    #------------------------------------------------------
    @http.route(website=True, auth="public")
    def web_login(self, redirect=None, *args, **kw):
        r = super(Website, self).web_login(redirect=redirect, *args, **kw)
        if not redirect and request.params['login_success']:
            if request.env.user.has_group('base.group_user'):
                redirect = '/web?' + request.httprequest.query_string
            else:
                redirect = '/'
            return http.redirect_with_hash(redirect)
        return r

    @http.route('/website/lang/<lang>', type='http', auth="public", website=True, multilang=False)
    def change_lang(self, lang, r='/', **kwargs):
        if lang == 'default':
            lang = request.website.default_lang_code
            r = '/%s%s' % (lang, r or '/')
        redirect = werkzeug.utils.redirect(r or ('/%s' % lang), 303)
        redirect.set_cookie('website_lang', lang)
        return redirect

    @http.route('/page/<page:page>', type='http', auth="public", website=True, cache=300)
    def page(self, page, **opt):
        values = {
            'path': page,
            'deletable': True,  # used to add 'delete this page' in content menu
        }
        # /page/website.XXX --> /page/XXX
        if page.startswith('website.'):
            return request.redirect('/page/' + page[8:], code=301)
        elif '.' not in page:
            page = 'website.%s' % page

        try:
            request.website.get_template(page)
        except ValueError, e:
            # page not found
            if request.website.is_publisher():
                values.pop('deletable')
                page = 'website.page_404'
            else:
                return request.env['ir.http']._handle_exception(e, 404)

        return request.render(page, values)

    @http.route(['/robots.txt'], type='http', auth="public")
    def robots(self):
        return request.render('website.robots', {'url_root': request.httprequest.url_root}, mimetype='text/plain')

    @http.route('/sitemap.xml', type='http', auth="public", website=True)
    def sitemap_xml_index(self):
        Attachment_sudo = request.env['ir.attachment'].sudo()
        mimetype = 'application/xml;charset=utf-8'
        content = None

        def create_sitemap(url, content):
            return Attachment_sudo.create(dict(
                datas=content.encode('base64'),
                mimetype=mimetype,
                type='binary',
                name=url,
                url=url,
            ))

        sitemap = Attachment_sudo.search_read([('url', '=', '/sitemap.xml'), ('type', '=', 'binary')], ('datas', 'create_date'))
        if sitemap:
            # Check if stored version is still valid
            create_date = fields.Datetime.from_string(sitemap[0]['create_date'])
            delta = datetime.datetime.now() - create_date
            if delta < SITEMAP_CACHE_TIME:
                content = sitemap[0]['datas'].decode('base64')

        if not content:
            sitemap = Attachment_sudo.search([('url', '=like', '/sitemap%.xml'), ('type', '=', 'binary')])
            # Remove all sitemaps in ir.attachments as we're going to regenerated them
            sitemap.unlink()

            pages = 0
            locs = request.website.sudo(user=request.website.user_id.id).enumerate_pages()
            while True:
                values = {
                    'locs': islice(locs, 0, LOC_PER_SITEMAP),
                    'url_root': request.httprequest.url_root[:-1],
                }
                sitemap_locs = request.env.ref('website.sitemap_locs')
                urls = sitemap_locs.render(values)
                if urls.strip():
                    sitemap_xml = request.env.ref('website.sitemap_xml')
                    content = sitemap_xml.render(dict(content=urls))
                    pages += 1
                    attachment = create_sitemap('/sitemap-%d.xml' % pages, content)
                else:
                    break
            if not pages:
                return request.not_found()
            elif pages == 1:
                attachment.write(dict(url="/sitemap.xml", name="/sitemap.xml"))
            else:
                # Sitemaps must be split in several smaller files with a sitemap index
                view = request.env.ref('website.sitemap_index_xml')
                content = view.render(dict(
                    pages=range(1, pages + 1),
                    url_root=request.httprequest.url_root))
                create_sitemap('/sitemap.xml', content)

        return request.make_response(content, [('Content-Type', mimetype)])

    @http.route('/website/info', type='http', auth="public", website=True)
    def website_info(self):
        try:
            request.website.get_template('website.info').name
        except Exception, e:
            return request.env['ir.http']._handle_exception(e, 404)
        IrModule = request.env['ir.module.module'].sudo()
        apps = IrModule.search([('state', '=', 'installed'), ('application', '=', True)])
        modules = IrModule.search([('state', '=', 'installed'), ('application', '=', False)])
        values = {
            'apps': apps,
            'modules': modules,
            'version': service.common.exp_version()
        }
        return request.render('website.info', values)

    #------------------------------------------------------
    # Edit
    #------------------------------------------------------
    @http.route('/website/add/<path:path>', type='http', auth="user", website=True)
    def pagenew(self, path, noredirect=False, add_menu=None, template=False):
        if template:
            xml_id = request.env['website'].new_page(path, template=template)
        else:
            xml_id = request.env['website'].new_page(path)
        if add_menu:
            request.env['website.menu'].create({
                    'name': path,
                    'url': "/page/" + xml_id[8:],
                    'parent_id': request.website.menu_id.id,
                    'website_id': request.website.id,
                })
        # Reverse action in order to allow shortcut for /page/<website_xml_id>
        url = "/page/" + re.sub(r"^website\.", '', xml_id)

        if noredirect:
            return werkzeug.wrappers.Response(url, mimetype='text/plain')
        return werkzeug.utils.redirect(url + "?enable_editor=1")

    @http.route(['/website/snippets'], type='json', auth="user", website=True)
    def snippets(self):
        return request.website._render('website.snippets')

    @http.route('/website/reset_templates', type='http', auth='user', methods=['POST'], website=True)
    def reset_template(self, templates, redirect='/'):
        templates = request.httprequest.form.getlist('templates')
        modules_to_update = []
        for temp_id in templates:
            view = request.env['ir.ui.view'].browse(int(temp_id))
            if view.page:
                continue
            view.model_data_id.write({
                'noupdate': False
            })
            if view.model_data_id.module not in modules_to_update:
                modules_to_update.append(view.model_data_id.module)

        if modules_to_update:
            Module = request.env['ir.module.module'].sudo()
            modules = Module.search([('name', 'in', modules_to_update)])
            if modules:
                modules.button_immediate_upgrade()
        return request.redirect(redirect)

    @http.route('/website/customize_template_get', type='json', auth='user', website=True)
    def customize_template_get(self, key, full=False, bundles=False):
        """ Get inherit view's informations of the template ``key``. By default, only
        returns ``customize_show`` templates (which can be active or not), if
        ``full=True`` returns inherit view's informations of the template ``key``.
        ``bundles=True`` returns also the asset bundles
        """
        return request.env["ir.ui.view"].customize_template_get(key, full=full, bundles=bundles)

    @http.route('/website/translations', type='json', auth="public", website=True)
    def get_website_translations(self, lang, mods=None):
        Modules = request.env['ir.module.module'].sudo()
        modules = Modules.search([
            ('name', 'ilike', 'website'),
            ('state', '=', 'installed')
        ]).mapped('name')
        if mods:
            modules += mods
        return WebClient().translations(mods=modules, lang=lang)

    @http.route(['/website/publish'], type='json', auth="public", website=True)
    def publish(self, id, object):
        _id = int(id)
        Model = request.env[object]
        model = Model.browse(_id)

        if 'website_published' in Model._fields:
            model.website_published = not model.website_published

        return bool(model.website_published)

    @http.route(['/website/seo_suggest'], type='json', auth="user", website=True)
    def seo_suggest(self, keywords=None, lang=None):
        language = lang.split("_")
        url = "http://google.com/complete/search"
        try:
            req = urllib2.Request("%s?%s" % (url, werkzeug.url_encode({
                'ie': 'utf8', 'oe': 'utf8', 'output': 'toolbar', 'q': keywords, 'hl': language[0], 'gl': language[1]})))
            request = urllib2.urlopen(req)
        except (urllib2.HTTPError, urllib2.URLError):
            return []
        xmlroot = ET.fromstring(request.read())
        return json.dumps([sugg[0].attrib['data'] for sugg in xmlroot if len(sugg) and sugg[0].attrib['data']])

    #------------------------------------------------------
    # Themes
    #------------------------------------------------------

    def get_view_ids(self, xml_ids):
        ids = []
        IrModelData = request.env['ir.model.data']
        for xml_id in xml_ids:
            if "." in xml_id:
                xml = xml_id.split(".")
                view_model, _id = IrModelData.get_object_reference(xml[0], xml[1])
            else:
                _id = int(xml_id)
            ids.append(_id)
        return ids

    @http.route(['/website/theme_customize_get'], type='json', auth="public", website=True)
    def theme_customize_get(self, xml_ids):
        IrView = request.env["ir.ui.view"]
        enable = []
        disable = []
        ids = self.get_view_ids(xml_ids)
        for view in IrView.with_context(active_test=True).browse(ids):
            if view.active:
                enable.append(view.xml_id)
            else:
                disable.append(view.xml_id)
        return [enable, disable]

    @http.route(['/website/theme_customize'], type='json', auth="public", website=True)
    def theme_customize(self, enable, disable, get_bundle=False):
        """ enable or Disable lists of ``xml_id`` of the inherit templates
        """
        IrView = request.env["ir.ui.view"]

        def set_active(ids, active):
            if ids:
                view_ids = self.get_view_ids(ids)
                views = IrView.browse(view_ids)
                views.with_context(active_test=True).write({'active': active})

        set_active(disable, False)
        set_active(enable, True)

        if get_bundle:
            bundle = AssetsBundle('web.assets_frontend', env=request.env(context={}))
            return bundle.to_html()

        return True

    @http.route(['/website/theme_customize_reload'], type='http', auth="public", website=True)
    def theme_customize_reload(self, href, enable, disable):
        self.theme_customize(enable and enable.split(",") or [], disable and disable.split(",") or [])
        return request.redirect(href + ("&theme=true" if "#" in href else "#theme=true"))

    @http.route(['/website/multi_render'], type='json', auth="public", website=True)
    def multi_render(self, ids_or_xml_ids, values=None):
        View = request.env['ir.ui.view']
        res = {}
        for id_or_xml_id in ids_or_xml_ids:
            res[id_or_xml_id] = View.render_template(id_or_xml_id, values)
        return res

    #------------------------------------------------------
    # Server actions
    #------------------------------------------------------
    @http.route([
        '/website/action/<path_or_xml_id_or_id>',
        '/website/action/<path_or_xml_id_or_id>/<path:path>',
        ], type='http', auth="public", website=True)
    def actions_server(self, path_or_xml_id_or_id, **post):
        action, action_id = None, None
        ServerActions = request.env['ir.actions.server']

        # find the action: either an xml_id, the path, or an ID
        if isinstance(path_or_xml_id_or_id, basestring) and '.' in path_or_xml_id_or_id:
            action = request.env.ref(path_or_xml_id_or_id, raise_if_not_found=False)
        if not action:
            action = ServerActions.search([('website_path', '=', path_or_xml_id_or_id), ('website_published', '=', True)], limit=1)
        if not action:
            with tools.ignore(Exception):
                action_id = int(path_or_xml_id_or_id)

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


#------------------------------------------------------
# Retrocompatibility routes
#------------------------------------------------------
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
