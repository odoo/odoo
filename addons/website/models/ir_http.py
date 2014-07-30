# -*- coding: utf-8 -*-
import logging
import re
import traceback

import werkzeug
import werkzeug.routing

import openerp
from openerp.addons.base import ir
from openerp.addons.base.ir import ir_qweb
from openerp.addons.website.models.website import slug
from openerp.http import request
from openerp.osv import orm

logger = logging.getLogger(__name__)

class RequestUID(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)

class ir_http(orm.AbstractModel):
    _inherit = 'ir.http'

    rerouting_limit = 10

    def _get_converters(self):
        return dict(
            super(ir_http, self)._get_converters(),
            model=ModelConverter,
            page=PageConverter,
        )

    def _dispatch(self):
        first_pass = not hasattr(request, 'website')
        request.website = None
        func = None
        try:
            func, arguments = self._find_handler()
            request.website_enabled = func.routing.get('website', False)
        except werkzeug.exceptions.NotFound:
            # either we have a language prefixed route, either a real 404
            # in all cases, website processes them
            request.website_enabled = True

        if request.website_enabled:
            if func:
                self._authenticate(func.routing['auth'])
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
        return super(ir_http, self)._dispatch()

    def reroute(self, path):
        if not hasattr(request, 'rerouting'):
            request.rerouting = [request.httprequest.path]
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

    def _postprocess_args(self, arguments):
        if hasattr(request, 'rerouting'):
            url = request.rerouting[0]
        else:
            url = request.httprequest.url
        original_url = url
        for arg in arguments.itervalues():
            if isinstance(arg, orm.browse_record) and isinstance(arg._uid, RequestUID):
                placeholder = arg._uid
                arg._uid = request.uid
                try:
                    good_slug = slug(arg)
                    if str(arg.id) != placeholder.value and placeholder.value != good_slug:
                        # TODO: properly recompose the url instead of using replace()
                        url = url.replace(placeholder.value, good_slug)
                except KeyError, e:
                    return self._handle_exception(e, code=404)
        if url != original_url:
            werkzeug.exceptions.abort(werkzeug.utils.redirect(url))

    def _handle_exception(self, exception, code=500):
        is_website_request = bool(getattr(request, 'website_enabled', False) and request.website)
        if not is_website_request:
            # Don't touch non website requests exception handling
            return super(ir_http, self)._handle_exception(exception)
        else:
            try:
                response = super(ir_http, self)._handle_exception(exception)
                if isinstance(response, Exception):
                    exception = response
                else:
                    # if parent excplicitely returns a plain response, then we don't touch it
                    return response
            except Exception, e:
                exception = e

            values = dict(
                exception=exception,
                traceback=traceback.format_exc(exception),
            )
            code = getattr(exception, 'code', code)

            if isinstance(exception, openerp.exceptions.AccessError):
                code = 403

            if isinstance(exception, ir_qweb.QWebException):
                values.update(qweb_exception=exception)
                if isinstance(exception.qweb.get('cause'), openerp.exceptions.AccessError):
                    code = 403

            if isinstance(exception, werkzeug.exceptions.HTTPException) and code is None:
                # Hand-crafted HTTPException likely coming from abort(),
                # usually for a redirect response -> return it directly
                return exception

            if code == 500:
                logger.error("500 Internal Server Error:\n\n%s", values['traceback'])
                if 'qweb_exception' in values:
                    view = request.registry.get("ir.ui.view")
                    views = view._views_get(request.cr, request.uid, exception.qweb['template'], request.context)
                    to_reset = [v for v in views if v.model_data_id.noupdate is True and not v.page]
                    values['views'] = to_reset
            elif code == 403:
                logger.warn("403 Forbidden:\n\n%s", values['traceback'])

            values.update(
                status_message=werkzeug.http.HTTP_STATUS_CODES[code],
                status_code=code,
            )

            if not request.uid:
                self._auth_method_public()

            try:
                html = request.website._render('website.%s' % code, values)
            except Exception:
                html = request.website._render('website.http_error', values)
            return werkzeug.wrappers.Response(html, status=code, content_type='text/html;charset=utf-8')

class ModelConverter(ir.ir_http.ModelConverter):
    def __init__(self, url_map, model=False):
        super(ModelConverter, self).__init__(url_map, model)
        self.regex = r'(?:[A-Za-z0-9-_]+?-)?(\d+)(?=$|/)'

    def to_url(self, value):
        return slug(value)

    def to_python(self, value):
        m = re.match(self.regex, value)
        _uid = RequestUID(value=value, match=m, converter=self)
        return request.registry[self.model].browse(
            request.cr, _uid, int(m.group(1)), context=request.context)

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
            if xid and (not query or query.lower() in xid.lower()):
                yield xid
