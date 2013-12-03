# -*- coding: utf-8 -*-
import logging
import traceback

import werkzeug.routing

import openerp
from openerp.addons.base import ir
from openerp.addons.website.models.website import slug
from openerp.http import request
from openerp.osv import orm

logger = logging.getLogger(__name__)

class ir_http(orm.AbstractModel):
    _inherit = 'ir.http'

    rerouting_limit = 10

    def _get_converters(self):
        return dict(
            super(ir_http, self)._get_converters(),
            model=ModelConverter,
            page=PageConverter,
        )

    def _auth_method_public(self):
        if not request.session.uid:
            request.uid = request.registry['website'].get_public_user(
                request.cr, openerp.SUPERUSER_ID, request.context)
        else:
            request.uid = request.session.uid

    def _dispatch(self):
        first_pass = not hasattr(request, 'website')
        request.website = None
        func = None
        try:
            func, arguments = self._find_handler()
            request.cms = getattr(func, 'cms', False)
        except werkzeug.exceptions.NotFound:
            # either we have a language prefixed route, either a real 404
            # in all cases, website processes them
            request.cms = True

        if request.cms:
            if func:
                self._authenticate(getattr(func, 'auth', None))
            else:
                self._auth_method_public()
            request.website = request.registry['website'].get_current_website(request.cr, request.uid, context=request.context)
            if first_pass:
                request.lang = request.website.default_lang_code
            request.context['lang'] = request.lang
            request.website.preprocess_request(request)
            if not func:
                path = request.httprequest.path.split('/')
                langs = [lg[0] for lg in request.website.get_languages()]
                if path[1] in langs:
                    request.lang = request.context['lang'] = path.pop(1)
                    path = '/'.join(path) or '/'
                    return self.reroute(path)
                return self._handle_404()
        return super(ir_http, self)._dispatch()

    def reroute(self, path):
        if not hasattr(request, 'rerouting'):
            request.rerouting = []
        if path in request.rerouting:
            raise Exception("Rerouting loop is forbidden")
        request.rerouting.append(path)
        if len(request.rerouting) > self.rerouting_limit:
            raise Exception("Rerouting limit exceeded")
        request.httprequest.environ['PATH_INFO'] = path
        # void werkzeug cached_property. TODO: find a proper way to do this
        for key in ('path', 'full_path', 'url', 'base_url'):
            request.httprequest.__dict__.pop(key, None)

        return self._dispatch()

    def _handle_403(self, exception):
        if getattr(request, 'cms', False) and request.website:
            logger.warn("403 Forbidden:\n\n%s", traceback.format_exc(exception))
            self._auth_method_public()
            return self._render_error(403, {
                'error': exception.message
            })
        raise exception

    def _handle_404(self, exception=None):
        if getattr(request, 'cms', False) and request.website:
            return self._render_error(404)
        raise request.not_found()

    def _handle_500(self, exception):
        if getattr(request, 'cms', False) and request.website:
            logger.error("500 Internal Server Error:\n\n%s", traceback.format_exc(exception))
            return self._render_error(500, {
                'exception': exception,
                'traceback': traceback.format_exc(),
                'qweb_template': getattr(exception, 'qweb_template', None),
                'qweb_node': getattr(exception, 'qweb_node', None),
                'qweb_eval': getattr(exception, 'qweb_eval', None),
            })
        raise exception

    def _render_error(self, code, values=None):
        return werkzeug.wrappers.Response(
            request.website._render('website.%s' % code, values),
            status=code,
            content_type='text/html;charset=utf-8')

class ModelConverter(ir.ir_http.ModelConverter):
    def __init__(self, url_map, model=False):
        super(ModelConverter, self).__init__(url_map, model)
        self.regex = r'(?:[A-Za-z0-9-_]+?-)?(\d+)(?=$|/)'

    def to_url(self, value):
        return slug(value)

    def generate(self, cr, uid, query=None, context=None):
        return request.registry[self.model].name_search(
            cr, uid, name=query or '', context=context)

class PageConverter(werkzeug.routing.PathConverter):
    """ Only point of this converter is to bundle pages enumeration logic

    Sads got: no way to get the view's human-readable name even if one exists
    """
    def generate(self, cr, uid, query=None, context=None):
        View = request.registry['ir.ui.view']
        views = View.search_read(
            cr, uid, [['page', '=', True]],
            fields=[], order='name', context=context)
        xids = View.get_external_id(
            cr, uid, [view['id'] for view in views], context=context)

        for view in views:
            xid = xids[view['id']]
            if xid and (not query or query in xid):
                yield xid
