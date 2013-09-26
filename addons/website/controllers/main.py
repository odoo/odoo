# -*- coding: utf-8 -*-
import base64
import cStringIO
import hashlib
import json
import logging
import os

import psycopg2
import werkzeug
import werkzeug.exceptions
import werkzeug.utils
import werkzeug.wrappers
from PIL import Image

import openerp
from openerp.addons.website import website
from openerp.addons.web import http
from openerp.addons.web.http import request

logger = logging.getLogger(__name__)


def auth_method_public():
    registry = openerp.modules.registry.RegistryManager.get(request.db)
    if not request.session.uid:
        request.uid = registry['website'].get_public_user().id
    else:
        request.uid = request.session.uid
http.auth_methods['public'] = auth_method_public

NOPE = object()
# PIL images have a type flag, but no MIME. Reverse type flag to MIME.
PIL_MIME_MAPPING = {'PNG': 'image/png', 'JPEG': 'image/jpeg', 'GIF': 'image/gif', }
# Completely arbitrary limits
MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT = IMAGE_LIMITS = (1024, 768)
class Website(openerp.addons.web.controllers.main.Home):
    @website.route('/', type='http', auth="admin")
    def index(self, **kw):
        return self.page("website.homepage")

    @http.route('/admin', type='http', auth="none")
    def admin(self, *args, **kw):
        return super(Website, self).index(*args, **kw)

     # FIXME: auth, if /pagenew known anybody can create new empty page
    @website.route('/pagenew/<path:path>', type='http', auth="admin")
    def pagenew(self, path, noredirect=NOPE):
        if '.' in path:
            module, idname = path.split('.', 1)
        else:
            module = 'website'
            idname = path
        xid = "%s.%s" % (module, idname)

        request.cr.execute('SAVEPOINT pagenew')
        imd = request.registry['ir.model.data']
        view = request.registry['ir.ui.view']
        view_model, view_id = imd.get_object_reference(
            request.cr, request.uid, 'website', 'default_page')
        newview_id = view.copy(
            request.cr, request.uid, view_id, context=request.context)
        newview = view.browse(
            request.cr, request.uid, newview_id, context=request.context)
        newview.write({
            'arch': newview.arch.replace("website.default_page", xid),
            'name': "page/%s" % path,
            'page': True,
        })
        # Fuck it, we're doing it live
        try:
            imd.create(request.cr, request.uid, {
                'name': idname,
                'module': module,
                'model': 'ir.ui.view',
                'res_id': newview_id,
                'noupdate': True
            }, context=request.context)
        except psycopg2.IntegrityError:
            request.cr.execute('ROLLBACK TO SAVEPOINT pagenew')
        else:
            request.cr.execute('RELEASE SAVEPOINT pagenew')
        url = "/page/%s" % path
        if noredirect is not NOPE:
            return werkzeug.wrappers.Response(url, mimetype='text/plain')
        return werkzeug.utils.redirect(url)

    @website.route('/website/theme_change', type='http', auth="admin")
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

    @website.route('/page/<path:path>', type='http', auth="admin")
    def page(self, path, **kwargs):
        values = {
            'path': path,
        }
        try:
            html = request.website.render(path, values)
        except ValueError:
            html = request.website.render('website.404', values)
        return html

    @website.route('/website/customize_template_toggle', type='json', auth='admin') # FIXME: auth
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

    @website.route('/website/customize_template_get', type='json', auth='admin') # FIXME: auth
    def customize_template_get(self, xml_id, optional=True):
        imd = request.registry['ir.model.data']
        view_model, view_theme_id = imd.get_object_reference(
            request.cr, request.uid, 'website', 'theme')

        view = request.registry.get("ir.ui.view")
        views = view._views_get(request.cr, request.uid, xml_id, request.context)
        done = {}
        result = []
        for v in views:
            if v.inherit_option_id and v.inherit_option_id.id != view_theme_id or not optional:
                if v.inherit_option_id.id not in done:
                    result.append({
                        'name': v.inherit_option_id.name,
                        'id': v.id,
                        'header': True,
                        'active': False
                    })
                    done[v.inherit_option_id.id] = True
                result.append({
                    'name': v.name,
                    'id': v.id,
                    'header': False,
                    'active': (v.inherit_id.id == v.inherit_option_id.id) or (not optional and v.inherit_id.id)
                })
        return result

    #  # FIXME: auth, anybody can upload an attachment if URL known/found
    @website.route('/website/attach', type='http', auth='admin')
    def attach(self, func, upload):
        req = request.httprequest
        if req.method != 'POST':
            return werkzeug.exceptions.MethodNotAllowed(valid_methods=['POST'])

        url = message = None
        try:
            attachment_id = request.registry['ir.attachment'].create(request.cr, request.uid, {
                'name': upload.filename,
                'datas': base64.encodestring(upload.read()),
                'datas_fname': upload.filename,
                'res_model': 'ir.ui.view',
            }, request.context)
            # FIXME: auth=user... no good.
            url = '/website/attachment/%d' % attachment_id
        except Exception, e:
            logger.exception("Failed to upload image to attachment")
            message = str(e)

        return """<script type='text/javascript'>
            window.parent['%s'](%s, %s);
        </script>""" % (func, json.dumps(url), json.dumps(message))

    @website.route('/website/attachment/<int:id>', type='http', auth="admin")
    def attachment(self, id):
        # TODO: provide actual thumbnails?
        # FIXME: can't use Binary.image because auth=user and website attachments need to be public
        attachment = request.registry['ir.attachment'].browse(
            request.cr, request.uid, id, request.context)

        buf = cStringIO.StringIO(base64.decodestring(attachment.datas))

        image = Image.open(buf)
        mime = PIL_MIME_MAPPING[image.format]

        w, h = image.size
        resized = w > MAX_IMAGE_WIDTH or h > MAX_IMAGE_HEIGHT

        # If saving unnecessary, just send the image buffer, don't go through
        # Image.save() (especially as it breaks animated gifs)
        if not resized:
            buf.seek(0)
            return werkzeug.wrappers.Response(buf, status=200, mimetype=mime)

        image.thumbnail(IMAGE_LIMITS, Image.ANTIALIAS)
        response = werkzeug.wrappers.Response(status=200, mimetype=mime)
        image.save(response.stream, image.format)
        return response

    @website.route('/website/image', type='http', auth="public")
    def image(self, model, id, field, **kw):
        last_update = '__last_update'
        Model = request.registry[model]
        headers = [('Content-Type', 'image/png')]
        etag = request.httprequest.headers.get('If-None-Match')
        hashed_session = hashlib.md5(request.session_id).hexdigest()
        retag = hashed_session
        try:
            ids = Model.read(request.cr, request.uid, [('id', '=', id)], request.context)
            if not ids:
                id = Model.read(request.cr, openerp.SUPERUSER_ID, [('id', '=', id), ('website_published', '=', True)], request.context)[0]

            if etag:
                date = Model.read(request.cr, openerp.SUPERUSER_ID, [id], [last_update], request.context)[0].get(last_update)
                if hashlib.md5(date).hexdigest() == etag:
                    return werkzeug.wrappers.Response(status=304)

            res = Model.read(request.cr, openerp.SUPERUSER_ID, [id], [last_update, field], request.context)[0]
            retag = hashlib.md5(res.get(last_update)).hexdigest()
            image_base64 = res.get(field)

            if kw.get('resize'):
                resize = kw.get('resize').split(',')
                if len(resize) == 2 and int(resize[0]) and int(resize[1]):
                    width = int(resize[0])
                    height = int(resize[1])
                    # resize maximum 500*500
                    if width > 500:
                        width = 500
                    if height > 500:
                        height = 500
                    image_base64 = openerp.tools.image_resize_image(base64_source=image_base64, size=(width, height), encoding='base64', filetype='PNG')

            image_data = base64.b64decode(image_base64)
        except Exception:
            image_data = open(os.path.join(http.addons_manifest['web']['addons_path'], 'web', 'static', 'src', 'img', 'placeholder.png'), 'rb').read()

        headers.append(('ETag', retag))
        headers.append(('Content-Length', len(image_data)))
        try:
            ncache = int(kw.get('cache'))
            headers.append(('Cache-Control', 'no-cache' if ncache == 0 else 'max-age=%s' % (ncache)))
        except:
            pass
        return request.make_response(image_data, headers)

    @website.route(['/website/publish'], type='json', auth="public")
    def publish(self, id, object):
        _id = int(id)
        _object = request.registry[object]

        obj = _object.browse(request.cr, request.uid, _id)
        _object.write(request.cr, request.uid, [_id],
                      {'website_published': not obj.website_published},
                      context=request.context)
        obj = _object.browse(request.cr, request.uid, _id)
        return obj.website_published and True or False

    @website.route(['/website/kanban/'], type='http', auth="public")
    def kanban(self, **post):
        return request.website.kanban_col(**post)

    @website.route(['/robots.txt'], type='http', auth="public")
    def robots(self):
        return request.website.render('website.robots', {'url_root': request.httprequest.url_root})

    @website.route(['/sitemap.xml'], type='http', auth="public")
    def sitemap(self):
        return request.website.render('website.sitemap', {'pages': request.website.list_pages()})

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
