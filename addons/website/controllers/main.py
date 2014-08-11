# -*- coding: utf-8 -*-
import cStringIO
import contextlib
import hashlib
import json
import xml.etree.ElementTree as ET

import logging
import os
import datetime

from sys import maxint

import psycopg2
import werkzeug
import werkzeug.exceptions
import werkzeug.utils
import urllib2
import werkzeug.wrappers
from PIL import Image

import openerp
from openerp.osv import fields
from openerp.addons.website.models import website
from openerp.addons.web import http
from openerp.addons.web.http import request, LazyResponse

logger = logging.getLogger(__name__)

# Completely arbitrary limits
MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT = IMAGE_LIMITS = (1024, 768)

class Website(openerp.addons.web.controllers.main.Home):
    #------------------------------------------------------
    # View
    #------------------------------------------------------
    @http.route('/', type='http', auth="public", website=True, multilang=True)
    def index(self, **kw):
        try:
            main_menu = request.registry['ir.model.data'].get_object(request.cr, request.uid, 'website', 'main_menu')
            first_menu = main_menu.child_id and main_menu.child_id[0]
            # Dont 302 loop on /
            if first_menu and not ((first_menu.url == '/') or first_menu.url.startswith('/#') or first_menu.url.startswith('/?')):
                return request.redirect(first_menu.url)
        except:
            pass
        return self.page("website.homepage")

    @http.route(website=True, auth="public", multilang=True)
    def web_login(self, *args, **kw):
        response = super(Website, self).web_login(*args, **kw)
        if isinstance(response, LazyResponse):
            values = dict(response.params['values'], disable_footer=True)
            response = request.website.render(response.params['template'], values)
        return response

    @http.route('/page/<page:page>', type='http', auth="public", website=True, multilang=True)
    def page(self, page, **opt):
        values = {
            'path': page,
        }
        # allow shortcut for /page/<website_xml_id>
        if '.' not in page:
            page = 'website.%s' % page

        try:
            request.website.get_template(page)
        except ValueError, e:
            # page not found
            if request.context['editable']:
                page = 'website.page_404'
            else:
                return request.registry['ir.http']._handle_exception(e, 404)

        return request.website.render(page, values)

    @http.route(['/robots.txt'], type='http', auth="public", website=True)
    def robots(self):
        response = request.website.render('website.robots', {'url_root': request.httprequest.url_root})
        response.mimetype = 'text/plain'
        return response

    @http.route('/sitemap', type='http', auth='public', website=True, multilang=True)
    def sitemap(self):
        return request.website.render('website.sitemap', {
            'pages': request.website.enumerate_pages()
        })

    @http.route('/sitemap.xml', type='http', auth="public", website=True)
    def sitemap_xml(self):
        response = request.website.render('website.sitemap_xml', {
            'pages': request.website.enumerate_pages()
        })
        response.headers['Content-Type'] = 'application/xml;charset=utf-8'
        return response

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
        url = "/page/" + xml_id
        if noredirect:
            return werkzeug.wrappers.Response(url, mimetype='text/plain')
        return werkzeug.utils.redirect(url)

    @http.route('/website/theme_change', type='http', auth="user", website=True)
    def theme_change(self, theme_id=False, **kwargs):
        imd = request.registry['ir.model.data']
        view = request.registry['ir.ui.view']

        view_model, view_option_id = imd.get_object_reference(
            request.cr, request.uid, 'website', 'theme')
        views = view.search(
            request.cr, request.uid, [('inherit_id', '=', view_option_id)],
            context=request.context)
        view.write(request.cr, request.uid, views, {'inherit_id': False},
                   context=request.context)

        if theme_id:
            module, xml_id = theme_id.split('.')
            view_model, view_id = imd.get_object_reference(
                request.cr, request.uid, module, xml_id)
            view.write(request.cr, request.uid, [view_id],
                       {'inherit_id': view_option_id}, context=request.context)

        return request.website.render('website.themes', {'theme_changed': True})

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

    @http.route('/website/customize_template_toggle', type='json', auth='user', website=True)
    def customize_template_set(self, view_id):
        view_obj = request.registry.get("ir.ui.view")
        view = view_obj.browse(request.cr, request.uid, int(view_id),
                               context=request.context)
        if view.inherit_id:
            value = False
        else:
            value = view.inherit_option_id and view.inherit_option_id.id or False
        view_obj.write(request.cr, request.uid, [view_id], {
            'inherit_id': value
        }, context=request.context)
        return True

    @http.route('/website/customize_template_get', type='json', auth='user', website=True)
    def customize_template_get(self, xml_id, optional=True):
        imd = request.registry['ir.model.data']
        view_model, view_theme_id = imd.get_object_reference(
            request.cr, request.uid, 'website', 'theme')

        user = request.registry['res.users'].browse(request.cr, request.uid, request.uid, request.context)
        group_ids = [g.id for g in user.groups_id]

        view = request.registry.get("ir.ui.view")
        views = view._views_get(request.cr, request.uid, xml_id, context=request.context)
        done = {}
        result = []
        for v in views:
            if v.groups_id and [g for g in v.groups_id if g.id not in group_ids]:
                continue
            if v.inherit_option_id and v.inherit_option_id.id != view_theme_id or not optional:
                if v.inherit_option_id.id not in done:
                    result.append({
                        'name': v.inherit_option_id.name,
                        'id': v.id,
                        'xml_id': v.xml_id,
                        'inherit_id': v.inherit_id.id,
                        'header': True,
                        'active': False
                    })
                    done[v.inherit_option_id.id] = True
                result.append({
                    'name': v.name,
                    'id': v.id,
                    'xml_id': v.xml_id,
                    'inherit_id': v.inherit_id.id,
                    'header': False,
                    'active': (v.inherit_id.id == v.inherit_option_id.id) or (not optional and v.inherit_id.id)
                })
        return result

    @http.route('/website/get_view_translations', type='json', auth='public', website=True)
    def get_view_translations(self, xml_id, lang=None):
        lang = lang or request.context.get('lang')
        views = self.customize_template_get(xml_id, optional=False)
        views_ids = [view.get('id') for view in views if view.get('active')]
        domain = [('type', '=', 'view'), ('res_id', 'in', views_ids), ('lang', '=', lang)]
        irt = request.registry.get('ir.translation')
        return irt.search_read(request.cr, request.uid, domain, ['id', 'res_id', 'value'], context=request.context)

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
                    irt.create(request.cr, request.uid, new_trans)
        return True

    @http.route('/website/attach', type='http', auth='user', methods=['POST'], website=True)
    def attach(self, func, upload):

        url = message = None
        try:
            image_data = upload.read()
            image = Image.open(cStringIO.StringIO(image_data))
            w, h = image.size
            if w*h > 42e6: # Nokia Lumia 1020 photo resolution
                raise ValueError(
                    u"Image size excessive, uploaded images must be smaller "
                    u"than 42 million pixel")

            Attachments = request.registry['ir.attachment']
            attachment_id = Attachments.create(request.cr, request.uid, {
                'name': upload.filename,
                'datas': image_data.encode('base64'),
                'datas_fname': upload.filename,
                'res_model': 'ir.ui.view',
            }, request.context)

            [attachment] = Attachments.read(
                request.cr, request.uid, [attachment_id], ['website_url'],
                context=request.context)
            url = attachment['website_url']
        except Exception, e:
            logger.exception("Failed to upload image to attachment")
            message = unicode(e)

        return """<script type='text/javascript'>
            window.parent['%s'](%s, %s);
        </script>""" % (func, json.dumps(url), json.dumps(message))

    @http.route(['/website/publish'], type='json', auth="public", website=True)
    def publish(self, id, object):
        _id = int(id)
        _object = request.registry[object]
        obj = _object.browse(request.cr, request.uid, _id)

        values = {}
        if 'website_published' in _object._all_columns:
            values['website_published'] = not obj.website_published
        if 'website_published_datetime' in _object._all_columns and values.get('website_published'):
            values['website_published_datetime'] = fields.datetime.now()
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
    @http.route(['/website/kanban/'], type='http', auth="public", methods=['POST'], website=True)
    def kanban(self, **post):
        return request.website.kanban_col(**post)

    def placeholder(self, response):
        # file_open may return a StringIO. StringIO can be closed but are
        # not context managers in Python 2 though that is fixed in 3
        with contextlib.closing(openerp.tools.misc.file_open(
                os.path.join('web', 'static', 'src', 'img', 'placeholder.png'),
                mode='rb')) as f:
            response.data = f.read()
            return response.make_conditional(request.httprequest)

    @http.route([
        '/website/image',
        '/website/image/<model>/<id>/<field>'
        ], auth="public", website=True)
    def website_image(self, model, id, field, max_width=maxint, max_height=maxint):
        Model = request.registry[model]

        response = werkzeug.wrappers.Response()

        id = int(id)

        ids = Model.search(request.cr, request.uid,
                           [('id', '=', id)], context=request.context) \
            or Model.search(request.cr, openerp.SUPERUSER_ID,
                            [('id', '=', id), ('website_published', '=', True)], context=request.context)

        if not ids:
            return self.placeholder(response)

        concurrency = '__last_update'
        [record] = Model.read(request.cr, openerp.SUPERUSER_ID, [id],
                              [concurrency, field], context=request.context)

        if concurrency in record:
            server_format = openerp.tools.misc.DEFAULT_SERVER_DATETIME_FORMAT
            try:
                response.last_modified = datetime.datetime.strptime(
                    record[concurrency], server_format + '.%f')
            except ValueError:
                # just in case we have a timestamp without microseconds
                response.last_modified = datetime.datetime.strptime(
                    record[concurrency], server_format)

        # Field does not exist on model or field set to False
        if not record.get(field):
            # FIXME: maybe a field which does not exist should be a 404?
            return self.placeholder(response)

        response.set_etag(hashlib.sha1(record[field]).hexdigest())
        response.make_conditional(request.httprequest)

        # conditional request match
        if response.status_code == 304:
            return response

        data = record[field].decode('base64')
        fit = int(max_width), int(max_height)

        buf = cStringIO.StringIO(data)

        image = Image.open(buf)
        image.load()
        response.mimetype = Image.MIME[image.format]

        w, h = image.size
        max_w, max_h = fit

        if w < max_w and h < max_h:
            response.data = data
        else:
            image.thumbnail(fit, Image.ANTIALIAS)
            image.save(response.stream, image.format)
            # invalidate content-length computed by make_conditional as writing
            # to response.stream does not do it (as of werkzeug 0.9.3)
            del response.headers['Content-Length']

        return response


# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
