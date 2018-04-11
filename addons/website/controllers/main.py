# -*- coding: utf-8 -*-
import datetime
from itertools import islice
import json
import xml.etree.ElementTree as ET

import logging
import re

import werkzeug.utils
import urllib2
import werkzeug.wrappers

import openerp
from openerp.addons.base.ir.ir_qweb import AssetsBundle
from openerp.addons.web.controllers.main import WebClient, Binary
from openerp.addons.web import http
from openerp.http import request

logger = logging.getLogger(__name__)

# Completely arbitrary limits
MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT = IMAGE_LIMITS = (1024, 768)
LOC_PER_SITEMAP = 45000
SITEMAP_CACHE_TIME = datetime.timedelta(hours=12)

class Website(openerp.addons.web.controllers.main.Home):
    #------------------------------------------------------
    # View
    #------------------------------------------------------
    @http.route('/', type='http', auth="public", website=True)
    def index(self, **kw):
        page = 'homepage'
        try:
            main_menu = request.env.ref('website.main_menu')
        except Exception:
            pass
        else:
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
            if request.registry['res.users'].has_group(request.cr, request.uid, 'base.group_user'):
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
            'deletable': True, # used to add 'delete this page' in content menu
        }
        # /page/website.XXX --> /page/XXX
        if page.startswith('website.'):
            url = '/page/' + page[8:]
            if request.httprequest.query_string:
                url += '?' + request.httprequest.query_string
            return request.redirect(url, code=301)
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
                return request.registry['ir.http']._handle_exception(e, 404)

        return request.render(page, values)

    @http.route(['/robots.txt'], type='http', auth="public")
    def robots(self):
        return request.render('website.robots', {'url_root': request.httprequest.url_root}, mimetype='text/plain')

    @http.route('/sitemap.xml', type='http', auth="public", website=True)
    def sitemap_xml_index(self):
        current_website = request.website
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        ira = request.registry['ir.attachment']
        iuv = request.registry['ir.ui.view']
        mimetype ='application/xml;charset=utf-8'
        content = None

        def create_sitemap(url, content):
            return ira.create(cr, uid, dict(
                datas=content.encode('base64'),
                mimetype=mimetype,
                type='binary',
                name=url,
                url=url,
            ), context=context)
        dom = [('url', '=' , '/sitemap-%d.xml' % current_website.id), ('type', '=', 'binary')]
        sitemap = ira.search_read(cr, uid, dom, ('datas', 'create_date'), context=context)
        if sitemap:
            # Check if stored version is still valid
            server_format = openerp.tools.misc.DEFAULT_SERVER_DATETIME_FORMAT
            create_date = datetime.datetime.strptime(sitemap[0]['create_date'], server_format)
            delta = datetime.datetime.now() - create_date
            if delta < SITEMAP_CACHE_TIME:
                content = sitemap[0]['datas'].decode('base64')

        if not content:
            # Remove all sitemaps in ir.attachments as we're going to regenerated them
            dom = [('type', '=', 'binary'), '|', ('url', '=like' , '/sitemap-%d-%%.xml' % current_website.id),
                   ('url', '=' , '/sitemap-%d.xml' % current_website.id)]
            sitemap_ids = ira.search(cr, uid, dom, context=context)
            if sitemap_ids:
                ira.unlink(cr, uid, sitemap_ids, context=context)

            pages = 0
            locs = request.website.sudo(user=request.website.user_id.id).enumerate_pages()
            while True:
                values = {
                    'locs': islice(locs, 0, LOC_PER_SITEMAP),
                    'url_root': request.httprequest.url_root[:-1],
                }
                urls = iuv.render(cr, uid, 'website.sitemap_locs', values, context=context)
                if urls.strip():
                    content = iuv.render(cr, uid, 'website.sitemap_xml', dict(content=urls), context=context)
                    pages += 1
                    last = create_sitemap('/sitemap-%d-%d.xml' % (current_website.id, pages), content)
                else:
                    break
            if not pages:
                return request.not_found()
            elif pages == 1:
                # rename the -id-page.xml => -id.xml
                ira.write(cr, uid, last, dict(url="/sitemap-%d.xml" % current_website.id, name="/sitemap-%d.xml" % current_website.id), context=context)
            else:
                # TODO: in master/saas-15, move current_website_id in template directly
                pages_with_website = map(lambda p: "%d-%d" % (current_website.id, p), range(1, pages + 1))

                # Sitemaps must be split in several smaller files with a sitemap index
                content = iuv.render(cr, uid, 'website.sitemap_index_xml', dict(
                    pages=pages_with_website,
                    url_root=request.httprequest.url_root,
                ), context=context)
                create_sitemap('/sitemap-%d.xml' % current_website.id, content)

        return request.make_response(content, [('Content-Type', mimetype)])

    @http.route('/website/info', type='http', auth="public", website=True)
    def website_info(self):
        try:
            request.website.get_template('website.info').name
        except Exception, e:
            return request.registry['ir.http']._handle_exception(e, 404)
        irm = request.env['ir.module.module'].sudo()
        apps = irm.search([('state','=','installed'),('application','=',True)])
        modules = irm.search([('state','=','installed'),('application','=',False)])
        values = {
            'apps': apps,
            'modules': modules,
            'version': openerp.service.common.exp_version()
        }
        return request.render('website.info', values)

    #------------------------------------------------------
    # Edit
    #------------------------------------------------------
    @http.route('/website/add/<path:path>', type='http', auth="user", website=True)
    def pagenew(self, path, noredirect=False, add_menu=None, template=False):
        if template:
            xml_id = request.registry['website'].new_page(request.cr, request.uid, path, template=template, context=request.context)
        else:
            xml_id = request.registry['website'].new_page(request.cr, request.uid, path, context=request.context)
        if add_menu:
            request.registry['website.menu'].create(
                request.cr, request.uid, {
                    'name': path,
                    'url': "/page/" + xml_id[8:],
                    'parent_id': request.website.menu_id.id,
                    'website_id': request.website.id,
                }, context=request.context)
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
            view = request.registry['ir.ui.view'].browse(request.cr, request.uid, int(temp_id), context=request.context)
            if view.page:
                continue
            view.model_data_id.write({
                'noupdate': False
            })
            if view.model_data_id.module not in modules_to_update:
                modules_to_update.append(view.model_data_id.module)

        if modules_to_update:
            module_obj = request.env['ir.module.module'].sudo()
            modules = module_obj.search([('name', 'in', modules_to_update)])
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
        return request.registry["ir.ui.view"].customize_template_get(
            request.cr, request.uid, key, full=full, bundles=bundles,
            context=request.context)

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
        _object = request.registry[object]
        obj = _object.browse(request.cr, request.uid, _id)

        values = {}
        if 'website_published' in _object._fields:
            values['website_published'] = not obj.website_published
        _object.write(request.cr, request.uid, [_id],
                      values, context=request.context)

        obj = _object.browse(request.cr, request.uid, _id)
        return bool(obj.website_published)

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
        imd = request.registry['ir.model.data']
        for xml_id in xml_ids:
            if "." in xml_id:
                xml = xml_id.split(".")
                view_model, id = imd.get_object_reference(request.cr, request.uid, xml[0], xml[1])
            else:
                id = int(xml_id)
            ids.append(id)
        return ids

    @http.route(['/website/theme_customize_get'], type='json', auth="public", website=True)
    def theme_customize_get(self, xml_ids):
        view = request.registry["ir.ui.view"]
        enable = []
        disable = []
        ids = self.get_view_ids(xml_ids)
        context = dict(request.context or {}, active_test=True)
        for v in view.browse(request.cr, request.uid, ids, context=context):
            if v.active:
                enable.append(v.xml_id)
            else:
                disable.append(v.xml_id)
        return [enable, disable]

    @http.route(['/website/theme_customize'], type='json', auth="public", website=True)
    def theme_customize(self, enable, disable, get_bundle=False):
        """ enable or Disable lists of ``xml_id`` of the inherit templates
        """
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        view = pool["ir.ui.view"]
        context = dict(request.context or {}, active_test=True)

        def set_active(ids, active):
            if ids:
                view.write(cr, uid, self.get_view_ids(ids), {'active': active}, context=context)

        set_active(disable, False)
        set_active(enable, True)

        if get_bundle:
            bundle = AssetsBundle('website.assets_frontend', cr=http.request.cr, uid=http.request.uid, context={}, registry=http.request.registry)
            return bundle.to_html()

        return True

    @http.route(['/website/theme_customize_reload'], type='http', auth="public", website=True)
    def theme_customize_reload(self, href, enable, disable):
        self.theme_customize(enable and enable.split(",") or [],disable and disable.split(",") or [])
        return request.redirect(href + ("&theme=true" if "#" in href else "#theme=true"))

    @http.route(['/website/multi_render'], type='json', auth="public", website=True)
    def multi_render(self, ids_or_xml_ids, values=None):
        res = {}
        for id_or_xml_id in ids_or_xml_ids:
            res[id_or_xml_id] = request.registry["ir.ui.view"].render(request.cr, request.uid, id_or_xml_id, values=values, engine='ir.qweb', context=request.context)
        return res

    #------------------------------------------------------
    # Server actions
    #------------------------------------------------------
    @http.route([
        '/website/action/<path_or_xml_id_or_id>',
        '/website/action/<path_or_xml_id_or_id>/<path:path>',
        ], type='http', auth="public", website=True)
    def actions_server(self, path_or_xml_id_or_id, **post):
        cr, uid, context = request.cr, request.uid, request.context
        res, action_id, action = None, None, None
        ServerActions = request.registry['ir.actions.server']

        # find the action_id: either an xml_id, the path, or an ID
        if isinstance(path_or_xml_id_or_id, basestring) and '.' in path_or_xml_id_or_id:
            action_id = request.registry['ir.model.data'].xmlid_to_res_id(request.cr, request.uid, path_or_xml_id_or_id, raise_if_not_found=False)
        if not action_id:
            action_ids = ServerActions.search(cr, uid, [('website_path', '=', path_or_xml_id_or_id), ('website_published', '=', True)], context=context)
            action_id = action_ids and action_ids[0] or None
        if not action_id:
            try:
                action_id = int(path_or_xml_id_or_id)
            except ValueError:
                pass

        # check it effectively exists
        if action_id:
            action_ids = ServerActions.exists(cr, uid, [action_id], context=context)
            action_id = action_ids and action_ids[0] or None
        # run it, return only if we got a Response object
        if action_id:
            action = ServerActions.browse(cr, uid, action_id, context=context)
            if action.state == 'code' and action.website_published:
                action_res = ServerActions.run(cr, uid, [action_id], context=context)
                if isinstance(action_res, werkzeug.wrappers.Response):
                    res = action_res
        if res:
            return res
        return request.redirect('/')


#------------------------------------------------------
# Retrocompatibility routes
#------------------------------------------------------
class WebsiteBinary(openerp.http.Controller):
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
