# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os
import traceback

import werkzeug
import werkzeug.routing
import werkzeug.utils

import odoo
from odoo import api, models
from odoo import SUPERUSER_ID
from odoo.http import request
from odoo.tools import config
from odoo.exceptions import QWebException
from odoo.tools.safe_eval import safe_eval

from odoo.addons.http_routing.models.ir_http import ModelConverter


logger = logging.getLogger(__name__)


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_converters(cls):
        """ Get the converters list for custom url pattern werkzeug need to
            match Rule. This override adds the website ones.
        """
        return dict(
            super(Http, cls)._get_converters(),
            model=ModelConverter,
            page=PageConverter,
        )

    @classmethod
    def _auth_method_public(cls):
        """ If no user logged, set the public user of current website, or default
            public user as request uid.
            After this method `request.env` can be called, since the `request.uid` is
            set. The `env` lazy property of `request` will be correct.
        """
        if not request.session.uid:
            env = api.Environment(request.cr, SUPERUSER_ID, request.context)
            website = env['website'].get_current_website()
            if website:
                request.uid = website.user_id.id
        if not request.uid:
            super(Http, cls)._auth_method_public()

    @classmethod
    def get_page_key(cls):
        return (cls._name, "cache", request.uid, request.lang, request.httprequest.full_path)

    @classmethod
    def _add_dispatch_parameters(cls, func):
        if request.is_frontend:
            context = dict(request.context)
            if not context.get('tz'):
                context['tz'] = request.session.get('geoip', {}).get('time_zone')

            request.website = request.env['website'].get_current_website()  # can use `request.env` since auth methods are called
            context['website_id'] = request.website.id

        super(Http, cls)._add_dispatch_parameters(func)

        if request.is_frontend and request.routing_iteration == 1:
            request.website = request.website.with_context(request.context)

    @classmethod
    def _get_languages(cls):
        if getattr(request, 'website', False):
            return request.website.language_ids
        return super(Http, cls)._get_languages()

    @classmethod
    def _get_language_codes(cls):
        if request.website:
            return request.website._get_languages()
        return super(Http, cls)._get_language_codes()

    @classmethod
    def _get_default_lang(cls):
        if getattr(request, 'website', False):
            return request.website.default_lang_id
        return super(Http, cls)._get_default_lang()

    @classmethod
    def _handle_exception(cls, exception, code=500):
        is_website_request = bool(getattr(request, 'is_frontend', False) and getattr(request, 'website', False))
        if not is_website_request:
            # Don't touch non website requests exception handling
            return super(Http, cls)._handle_exception(exception)
        else:
            try:
                response = super(Http, cls)._handle_exception(exception)
                if isinstance(response, Exception):
                    exception = response
                else:
                    # if parent excplicitely returns a plain response, then we don't touch it
                    return response
            except Exception as e:
                if 'werkzeug' in config['dev_mode'] and (not isinstance(exception, QWebException) or not exception.qweb.get('cause')):
                    raise
                exception = e

            values = dict(
                exception=exception,
                traceback=traceback.format_exc(),
            )

            if isinstance(exception, werkzeug.exceptions.HTTPException):
                if exception.code is None:
                    # Hand-crafted HTTPException likely coming from abort(),
                    # usually for a redirect response -> return it directly
                    return exception
                else:
                    code = exception.code

            if isinstance(exception, odoo.exceptions.AccessError):
                code = 403

            if isinstance(exception, QWebException):
                values.update(qweb_exception=exception)
                if isinstance(exception.qweb.get('cause'), odoo.exceptions.AccessError):
                    code = 403

            if code == 500:
                logger.error("500 Internal Server Error:\n\n%s", values['traceback'])
                if 'qweb_exception' in values:
                    view = request.env["ir.ui.view"]
                    views = view._views_get(exception.qweb['template'])
                    to_reset = views.filtered(lambda view: view.model_data_id.noupdate is True and not view.page)
                    values['views'] = to_reset
            elif code == 403:
                logger.warn("403 Forbidden:\n\n%s", values['traceback'])

            values.update(
                status_message=werkzeug.http.HTTP_STATUS_CODES[code],
                status_code=code,
            )

            if not request.uid:
                cls._auth_method_public()

            try:
                html = request.env['ir.ui.view'].render_template('website.%s' % code, values)
            except Exception:
                html = request.env['ir.ui.view'].render_template('website.http_error', values)
            return werkzeug.wrappers.Response(html, status=code, content_type='text/html;charset=utf-8')

    @classmethod
    def binary_content(cls, xmlid=None, model='ir.attachment', id=None, field='datas', unique=False, filename=None, filename_field='datas_fname', download=False, mimetype=None, default_mimetype='application/octet-stream', env=None):
        env = env or request.env
        obj = None
        if xmlid:
            obj = env.ref(xmlid, False)
        elif id and model in env:
            obj = env[model].browse(int(id))
        if obj and 'website_published' in obj._fields:
            if env[obj._name].sudo().search([('id', '=', obj.id), ('website_published', '=', True)]):
                env = env(user=SUPERUSER_ID)
        return super(Http, cls).binary_content(xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename, filename_field=filename_field, download=download, mimetype=mimetype, default_mimetype=default_mimetype, env=env)


class ModelConverter(ModelConverter):

    def generate(self, uid, query=None, args=None):
        Model = request.env[self.model].sudo(uid)
        domain = safe_eval(self.domain, (args or {}).copy())
        if query:
            domain.append((Model._rec_name, 'ilike', '%' + query + '%'))
        for record in Model.search_read(domain=domain, fields=['write_date', Model._rec_name]):
            if record.get(Model._rec_name, False):
                yield {'loc': (record['id'], record[Model._rec_name])}


class PageConverter(werkzeug.routing.PathConverter):
    """ Only point of this converter is to bundle pages enumeration logic """

    def generate(self, uid, query=None, args={}):
        View = request.env['ir.ui.view'].sudo(uid)
        domain = [('page', '=', True)]
        query = query and query.startswith('website.') and query[8:] or query
        if query:
            domain += [('key', 'like', query)]
        website = request.env['website'].get_current_website()
        domain += ['|', ('website_id', '=', website.id), ('website_id', '=', False)]

        views = View.search_read(domain, fields=['key', 'priority', 'write_date'], order='name')
        for view in views:
            xid = view['key'].startswith('website.') and view['key'][8:] or view['key']
            # the 'page/homepage' url is indexed as '/', avoid aving the same page referenced twice
            # when we will have an url mapping mechanism, replace this by a rule: page/homepage --> /
            if xid == 'homepage':
                continue
            record = {'loc': xid}
            if view['priority'] != 16:
                record['__priority'] = min(round(view['priority'] / 32.0, 1), 1)
            if view['write_date']:
                record['__lastmod'] = view['write_date'][:10]
            yield record
