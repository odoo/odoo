# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import traceback
import os
import unittest

import pytz
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
from odoo.osv.expression import FALSE_DOMAIN, OR

from odoo.addons.http_routing.models.ir_http import ModelConverter, _guess_mimetype
from odoo.addons.portal.controllers.portal import _build_url_w_params

logger = logging.getLogger(__name__)


def sitemap_qs2dom(qs, route, field='name'):
    """ Convert a query_string (can contains a path) to a domain"""
    dom = []
    if qs and qs.lower() not in route:
        needles = qs.strip('/').split('/')
        # needles will be altered and keep only element which one is not in route
        # diff(from=['shop', 'product'], to=['shop', 'product', 'product']) => to=['product']
        unittest.util.unorderable_list_difference(route.strip('/').split('/'), needles)
        if len(needles) == 1:
            dom = [(field, 'ilike', needles[0])]
        else:
            dom = FALSE_DOMAIN
    return dom


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
            if website and website.user_id:
                request.uid = website.user_id.id
        if not request.uid:
            super(Http, cls)._auth_method_public()

    @classmethod
    def _add_dispatch_parameters(cls, func):

        # Force website with query string paramater, typically set from website selector in frontend navbar
        force_website_id = request.httprequest.args.get('fw')
        if (force_website_id and request.session.get('force_website_id') != force_website_id and
                request.env.user.has_group('website.group_multi_website') and
                request.env.user.has_group('website.group_website_publisher')):
            request.env['website']._force_website(request.httprequest.args.get('fw'))

        context = {}
        if not request.context.get('tz'):
            context['tz'] = request.session.get('geoip', {}).get('time_zone')
            try:
                pytz.timezone(context['tz'] or '')
            except pytz.UnknownTimeZoneError:
                context.pop('tz')

        request.website = request.env['website'].get_current_website()  # can use `request.env` since auth methods are called
        context['website_id'] = request.website.id

        # modify bound context
        request.context = dict(request.context, **context)

        super(Http, cls)._add_dispatch_parameters(func)

        if request.routing_iteration == 1:
            request.website = request.website.with_context(request.context)

    @classmethod
    def _get_languages(cls):
        if getattr(request, 'website', False):
            return request.website.language_ids
        return super(Http, cls)._get_languages()

    @classmethod
    def _get_language_codes(cls):
        if getattr(request, 'website', False):
            return request.website._get_languages()
        return super(Http, cls)._get_language_codes()

    @classmethod
    def _get_default_lang(cls):
        if getattr(request, 'website', False):
            return request.website.default_lang_id
        return super(Http, cls)._get_default_lang()

    @classmethod
    def _get_translation_frontend_modules_domain(cls):
        domain = super(Http, cls)._get_translation_frontend_modules_domain()
        return OR([domain, [('name', 'ilike', 'website')]])

    @classmethod
    def _serve_page(cls):
        req_page = request.httprequest.path
        page_domain = [('url', '=', req_page)] + request.website.website_domain()

        published_domain = page_domain
        # need to bypass website_published, to apply is_most_specific
        # filter later if not publisher
        pages = request.env['website.page'].sudo().search(published_domain, order='website_id')
        pages = pages.filtered(pages._is_most_specific_page)

        if not request.website.is_publisher():
            pages = pages.filtered('is_visible')

        mypage = pages[0] if pages else False
        _, ext = os.path.splitext(req_page)
        if mypage:
            return request.render(mypage.get_view_identifier(), {
                # 'path': req_page[1:],
                'deletable': True,
                'main_object': mypage,
            }, mimetype=_guess_mimetype(ext))
        return False

    @classmethod
    def _serve_redirect(cls):
        req_page = request.httprequest.path
        domain = [('url_from', '=', req_page)] + request.website.website_domain()
        return request.env['website.redirect'].search(domain, limit=1)

    @classmethod
    def _serve_fallback(cls, exception):
        # serve attachment before
        parent = super(Http, cls)._serve_fallback(exception)
        if parent:  # attachment
            return parent

        website_page = cls._serve_page()
        if website_page:
            return website_page

        redirect = cls._serve_redirect()
        if redirect:
            return request.redirect(_build_url_w_params(redirect.url_to, request.params), code=redirect.type)

        return False

    @classmethod
    def _handle_exception(cls, exception):
        code = 500  # default code
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
                    raise e
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
                    to_reset = views.filtered(lambda view: view.model_data_id.noupdate is True and view.arch_fs)
                    values['views'] = to_reset
            elif code == 403:
                logger.warn("403 Forbidden:\n\n%s", values['traceback'])

            values.update(
                status_message=werkzeug.http.HTTP_STATUS_CODES[code],
                status_code=code,
            )

            view_id = code
            if request.website.is_publisher() and isinstance(exception, werkzeug.exceptions.NotFound):
                view_id = 'page_404'
                values['path'] = request.httprequest.path[1:]

            if not request.uid:
                cls._auth_method_public()

            try:
                html = request.env['ir.ui.view'].render_template('website.%s' % view_id, values)
            except Exception:
                html = request.env['ir.ui.view'].render_template('website.http_error', values)
            return werkzeug.wrappers.Response(html, status=code, content_type='text/html;charset=utf-8')

    def binary_content(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                       unique=False, filename=None, filename_field='datas_fname', download=False,
                       mimetype=None, default_mimetype='application/octet-stream',
                       access_token=None):
        obj = None
        if xmlid:
            obj = self._xmlid_to_obj(self.env, xmlid)
        elif id and model in self.env:
            obj = self.env[model].browse(int(id))
        if obj and 'website_published' in obj._fields:
            if self.env[obj._name].sudo().search([('id', '=', obj.id), ('website_published', '=', True)]):
                self.sudo()
        return super(Http, self).binary_content(
            xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename,
            filename_field=filename_field, download=download, mimetype=mimetype,
            default_mimetype=default_mimetype, access_token=access_token)

    @classmethod
    def _xmlid_to_obj(cls, env, xmlid):
        website_id = env['website'].get_current_website()
        if website_id and website_id.theme_id:
            obj = env['ir.attachment'].search([('key', '=', xmlid), ('website_id', '=', website_id.id)])
            if obj:
                return obj[0]

        return super(Http, cls)._xmlid_to_obj(env, xmlid)


class ModelConverter(ModelConverter):

    def generate(self, uid, dom=None, args=None):
        Model = request.env[self.model].sudo(uid)
        # Allow to current_website_id directly in route domain
        args.update(current_website_id=request.env['website'].get_current_website().id)
        domain = safe_eval(self.domain, (args or {}).copy())
        if dom:
            domain += dom
        for record in Model.search_read(domain=domain, fields=['write_date', Model._rec_name]):
            if record.get(Model._rec_name, False):
                yield {'loc': (record['id'], record[Model._rec_name])}
