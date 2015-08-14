# -*- coding: utf-8 -*-
import cStringIO
import datetime
from itertools import islice
import json
import xml.etree.ElementTree as ET

import logging
import re

import werkzeug.utils
import urllib2
import werkzeug.wrappers
from PIL import Image

import openerp
from openerp.addons.web.controllers.main import WebClient
from openerp.addons.web import http
from openerp.http import request, STATIC_CACHE
from openerp.tools import image_save_for_web

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
            main_menu = request.registry['ir.model.data'].get_object(request.cr, request.uid, 'website', 'main_menu')
        except Exception:
            pass
        else:
            first_menu = main_menu.child_id and main_menu.child_id[0]
            if first_menu:
                if not (first_menu.url.startswith(('/page/', '/?', '/#')) or (first_menu.url=='/')):
                    return request.redirect(first_menu.url)
                if first_menu.url.startswith('/page/'):
                    return request.registry['ir.http'].reroute(first_menu.url)
        return self.page(page)

    @http.route(website=True, auth="public")
    def web_login(self, *args, **kw):
        # TODO: can't we just put auth=public, ... in web client ?
        return super(Website, self).web_login(*args, **kw)

    @http.route('/website/lang/<lang>', type='http', auth="public", website=True, multilang=False)
    def change_lang(self, lang, r='/', **kwargs):
        if lang == 'default':
            lang = request.website.default_lang_code
            r = '/%s%s' % (lang, r or '/')
        redirect = werkzeug.utils.redirect(r or ('/%s' % lang), 303)
        redirect.set_cookie('website_lang', lang)
        return redirect

    @http.route('/page/<page:page>', type='http', auth="public", website=True)
    def page(self, page, **opt):
        values = {
            'path': page,
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
                page = 'website.page_404'
            else:
                return request.registry['ir.http']._handle_exception(e, 404)

        return request.render(page, values)

    @http.route(['/robots.txt'], type='http', auth="public")
    def robots(self):
        return request.render('website.robots', {'url_root': request.httprequest.url_root}, mimetype='text/plain')

    @http.route('/sitemap.xml', type='http', auth="public", website=True)
    def sitemap_xml_index(self):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        ira = request.registry['ir.attachment']
        iuv = request.registry['ir.ui.view']
        mimetype ='application/xml;charset=utf-8'
        content = None

        def create_sitemap(url, content):
            ira.create(cr, uid, dict(
                datas=content.encode('base64'),
                mimetype=mimetype,
                type='binary',
                name=url,
                url=url,
            ), context=context)

        sitemap = ira.search_read(cr, uid, [('url', '=' , '/sitemap.xml'), ('type', '=', 'binary')], ('datas', 'create_date'), context=context)
        if sitemap:
            # Check if stored version is still valid
            server_format = openerp.tools.misc.DEFAULT_SERVER_DATETIME_FORMAT
            create_date = datetime.datetime.strptime(sitemap[0]['create_date'], server_format)
            delta = datetime.datetime.now() - create_date
            if delta < SITEMAP_CACHE_TIME:
                content = sitemap[0]['datas'].decode('base64')

        if not content:
            # Remove all sitemaps in ir.attachments as we're going to regenerated them
            sitemap_ids = ira.search(cr, uid, [('url', '=like' , '/sitemap%.xml'), ('type', '=', 'binary')], context=context)
            if sitemap_ids:
                ira.unlink(cr, uid, sitemap_ids, context=context)

            pages = 0
            first_page = None
            locs = request.website.sudo(user=request.website.user_id.id).enumerate_pages()
            while True:
                start = pages * LOC_PER_SITEMAP
                values = {
                    'locs': islice(locs, start, start + LOC_PER_SITEMAP),
                    'url_root': request.httprequest.url_root[:-1],
                }
                urls = iuv.render(cr, uid, 'website.sitemap_locs', values, context=context)
                if urls.strip():
                    page = iuv.render(cr, uid, 'website.sitemap_xml', dict(content=urls), context=context)
                    if not first_page:
                        first_page = page
                    pages += 1
                    create_sitemap('/sitemap-%d.xml' % pages, page)
                else:
                    break
            if not pages:
                return request.not_found()
            elif pages == 1:
                content = first_page
            else:
                # Sitemaps must be split in several smaller files with a sitemap index
                content = iuv.render(cr, uid, 'website.sitemap_index_xml', dict(
                    pages=range(1, pages + 1),
                    url_root=request.httprequest.url_root,
                ), context=context)
            create_sitemap('/sitemap.xml', content)

        return request.make_response(content, [('Content-Type', mimetype)])

    @http.route('/website/info', type='http', auth="public", website=True)
    def website_info(self):
        try:
            request.website.get_template('website.info').name
        except Exception, e:
            return request.registry['ir.http']._handle_exception(e, 404)
        irm = request.env()['ir.module.module'].sudo()
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
    def pagenew(self, path, noredirect=False, add_menu=None):
        xml_id = request.registry['website'].new_page(request.cr, request.uid, path, context=request.context)
        if add_menu:
            model, id  = request.registry["ir.model.data"].get_object_reference(request.cr, request.uid, 'website', 'main_menu')
            request.registry['website.menu'].create(request.cr, request.uid, {
                    'name': path,
                    'url': "/page/" + xml_id,
                    'parent_id': id,
                }, context=request.context)
        # Reverse action in order to allow shortcut for /page/<website_xml_id>
        url = "/page/" + re.sub(r"^website\.", '', xml_id)

        if noredirect:
            return werkzeug.wrappers.Response(url, mimetype='text/plain')
        return werkzeug.utils.redirect(url)

    @http.route('/website/theme_change', type='http', auth="user", website=True)
    def theme_change(self, theme_id=False, **kwargs):
        imd = request.registry['ir.model.data']
        Views = request.registry['ir.ui.view']

        _, theme_template_id = imd.get_object_reference(
            request.cr, request.uid, 'website', 'theme')
        views = Views.search(request.cr, request.uid, [
            ('inherit_id', '=', theme_template_id),
        ], context=request.context)
        Views.write(request.cr, request.uid, views, {
            'active': False,
        }, context=dict(request.context or {}, active_test=True))

        if theme_id:
            module, xml_id = theme_id.split('.')
            _, view_id = imd.get_object_reference(
                request.cr, request.uid, module, xml_id)
            Views.write(request.cr, request.uid, [view_id], {
                'active': True
            }, context=dict(request.context or {}, active_test=True))

        return request.render('website.themes', {'theme_changed': True})

    @http.route(['/website/snippets'], type='json', auth="public", website=True)
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
            module_obj = request.registry['ir.module.module']
            module_ids = module_obj.search(request.cr, request.uid, [('name', 'in', modules_to_update)], context=request.context)
            if module_ids:
                module_obj.button_immediate_upgrade(request.cr, request.uid, module_ids, context=request.context)
        return request.redirect(redirect)

    @http.route('/website/customize_template_get', type='json', auth='user', website=True)
    def customize_template_get(self, xml_id, full=False):
        return request.registry["ir.ui.view"].customize_template_get(
            request.cr, request.uid, xml_id, full=full, context=request.context)

    @http.route('/website/get_view_translations', type='json', auth='public', website=True)
    def get_view_translations(self, xml_id, lang=None):
        lang = lang or request.context.get('lang')
        return request.registry["ir.ui.view"].get_view_translations(
            request.cr, request.uid, xml_id, lang=lang, context=request.context)

    @http.route('/website/set_translations', type='json', auth='public', website=True)
    def set_translations(self, data, lang):
        irt = request.registry.get('ir.translation')
        for view_id, trans in data.items():
            view_id = int(view_id)
            for t in trans:
                initial_content = t['initial_content'].strip()
                new_content = t['new_content'].strip()
                tid = t['translation_id']
                if not tid:
                    old_trans = irt.search_read(
                        request.cr, request.uid,
                        [
                            ('type', '=', 'view'),
                            ('res_id', '=', view_id),
                            ('lang', '=', lang),
                            ('src', '=', initial_content),
                        ])
                    if old_trans:
                        tid = old_trans[0]['id']
                if tid:
                    vals = {'value': new_content}
                    irt.write(request.cr, request.uid, [tid], vals)
                else:
                    new_trans = {
                        'name': 'website',
                        'res_id': view_id,
                        'lang': lang,
                        'type': 'view',
                        'source': initial_content,
                        'value': new_content,
                    }
                    if t.get('gengo_translation'):
                        new_trans['gengo_translation'] = t.get('gengo_translation')
                        new_trans['gengo_comment'] = t.get('gengo_comment')
                    irt.create(request.cr, request.uid, new_trans)
        return True

    @http.route('/website/translations', type='json', auth="public", website=True)
    def get_website_translations(self, lang):
        module_obj = request.registry['ir.module.module']
        module_ids = module_obj.search(request.cr, request.uid, [('name', 'ilike', 'website'), ('state', '=', 'installed')], context=request.context)
        modules = [x['name'] for x in module_obj.read(request.cr, request.uid, module_ids, ['name'], context=request.context)]
        return WebClient().translations(mods=modules, lang=lang)

    @http.route('/website/attach', type='http', auth='user', methods=['POST'], website=True)
    def attach(self, func, upload=None, url=None, disable_optimization=None):
        Attachments = request.registry['ir.attachment']

        website_url = message = None
        if not upload:
            website_url = url
            name = url.split("/").pop()
            attachment_id = Attachments.create(request.cr, request.uid, {
                'name': name,
                'type': 'url',
                'url': url,
                'res_model': 'ir.ui.view',
            }, request.context)
        else:
            try:
                image_data = upload.read()
                image = Image.open(cStringIO.StringIO(image_data))
                w, h = image.size
                if w*h > 42e6: # Nokia Lumia 1020 photo resolution
                    raise ValueError(
                        u"Image size excessive, uploaded images must be smaller "
                        u"than 42 million pixel")

                if not disable_optimization and image.format in ('PNG', 'JPEG'):
                    image_data = image_save_for_web(image)

                attachment_id = Attachments.create(request.cr, request.uid, {
                    'name': upload.filename,
                    'datas': image_data.encode('base64'),
                    'datas_fname': upload.filename,
                    'res_model': 'ir.ui.view',
                }, request.context)

                [attachment] = Attachments.read(
                    request.cr, request.uid, [attachment_id], ['website_url'],
                    context=request.context)
                website_url = attachment['website_url']
            except Exception, e:
                logger.exception("Failed to upload image to attachment")
                message = unicode(e)

        return """<script type='text/javascript'>
            window.parent['%s'](%s, %s);
        </script>""" % (func, json.dumps(website_url), json.dumps(message))

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

    @http.route(['/website/seo_suggest/<keywords>'], type='http', auth="public", website=True)
    def seo_suggest(self, keywords):
        url = "http://google.com/complete/search"
        try:
            req = urllib2.Request("%s?%s" % (url, werkzeug.url_encode({
                'ie': 'utf8', 'oe': 'utf8', 'output': 'toolbar', 'q': keywords})))
            request = urllib2.urlopen(req)
        except (urllib2.HTTPError, urllib2.URLError):
            return []
        xmlroot = ET.fromstring(request.read())
        return json.dumps([sugg[0].attrib['data'] for sugg in xmlroot if len(sugg) and sugg[0].attrib['data']])

    #------------------------------------------------------
    # Helpers
    #------------------------------------------------------
    @http.route(['/website/kanban'], type='http', auth="public", methods=['POST'], website=True)
    def kanban(self, **post):
        return request.website.kanban_col(**post)

    def placeholder(self, response):
        return request.registry['website']._image_placeholder(response)

    @http.route([
        '/website/image',
        '/website/image/<model>/<id>/<field>',
        '/website/image/<model>/<id>/<field>/<int:max_width>x<int:max_height>'
        ], auth="public", website=True)
    def website_image(self, model, id, field, max_width=None, max_height=None):
        """ Fetches the requested field and ensures it does not go above
        (max_width, max_height), resizing it if necessary.

        If the record is not found or does not have the requested field,
        returns a placeholder image via :meth:`~.placeholder`.

        Sets and checks conditional response parameters:
        * :mailheader:`ETag` is always set (and checked)
        * :mailheader:`Last-Modified is set iif the record has a concurrency
          field (``__last_update``)

        The requested field is assumed to be base64-encoded image data in
        all cases.
        """
        try:
            idsha = id.split('_')
            id = idsha[0]
            response = werkzeug.wrappers.Response()
            return request.registry['website']._image(
                request.cr, request.uid, model, id, field, response, max_width, max_height,
                cache=STATIC_CACHE if len(idsha) > 1 else None)
        except Exception:
            logger.exception("Cannot render image field %r of record %s[%s] at size(%s,%s)",
                             field, model, id, max_width, max_height)
            response = werkzeug.wrappers.Response()
            return self.placeholder(response)

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

