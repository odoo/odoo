# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import werkzeug

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.web import Home
from odoo.exceptions import UserError, ValidationError, AccessError, MissingError, AccessDenied


class WebsiteTest(Home):

    @http.route('/test_view', type='http', auth='public', website=True, sitemap=False)
    def test_view(self, **kwargs):
        return request.render('test_website.test_view')

    @http.route('/ignore_args/converteronly/<string:a>/', type='http', auth="public", website=True, sitemap=False)
    def test_ignore_args_converter_only(self, a):
        return request.make_response(json.dumps(dict(a=a, kw=None)))

    @http.route('/ignore_args/none', type='http', auth="public", website=True, sitemap=False)
    def test_ignore_args_none(self):
        return request.make_response(json.dumps(dict(a=None, kw=None)))

    @http.route('/ignore_args/a', type='http', auth="public", website=True, sitemap=False)
    def test_ignore_args_a(self, a):
        return request.make_response(json.dumps(dict(a=a, kw=None)))

    @http.route('/ignore_args/kw', type='http', auth="public", website=True, sitemap=False)
    def test_ignore_args_kw(self, a, **kw):
        return request.make_response(json.dumps(dict(a=a, kw=kw)))

    @http.route('/ignore_args/converter/<string:a>/', type='http', auth="public", website=True, sitemap=False)
    def test_ignore_args_converter(self, a, b='youhou', **kw):
        return request.make_response(json.dumps(dict(a=a, b=b, kw=kw)))

    @http.route('/ignore_args/converter/<string:a>/nokw', type='http', auth="public", website=True, sitemap=False)
    def test_ignore_args_converter_nokw(self, a, b='youhou'):
        return request.make_response(json.dumps(dict(a=a, b=b)))

    @http.route('/multi_company_website', type='http', auth="public", website=True, sitemap=False)
    def test_company_context(self):
        return request.make_response(json.dumps(request.context.get('allowed_company_ids')))

    # Test Session

    @http.route('/test_get_dbname', type='json', auth='public', website=True, sitemap=False)
    def test_get_dbname(self, **kwargs):
        return request.env.cr.dbname

    # Test Error

    @http.route('/test_error_view', type='http', auth='public', website=True, sitemap=False)
    def test_error_view(self, **kwargs):
        return request.render('test_website.test_error_view')

    @http.route('/test_user_error_http', type='http', auth='public', website=True, sitemap=False)
    def test_user_error_http(self, **kwargs):
        raise UserError("This is a user http test")

    @http.route('/test_user_error_json', type='json', auth='public', website=True, sitemap=False)
    def test_user_error_json(self, **kwargs):
        raise UserError("This is a user rpc test")

    @http.route('/test_validation_error_http', type='http', auth='public', website=True, sitemap=False)
    def test_validation_error_http(self, **kwargs):
        raise ValidationError("This is a validation http test")

    @http.route('/test_validation_error_json', type='json', auth='public', website=True, sitemap=False)
    def test_validation_error_json(self, **kwargs):
        raise ValidationError("This is a validation rpc test")

    @http.route('/test_access_error_json', type='json', auth='public', website=True, sitemap=False)
    def test_access_error_json(self, **kwargs):
        raise AccessError("This is an access rpc test")

    @http.route('/test_access_error_http', type='http', auth='public', website=True, sitemap=False)
    def test_access_error_http(self, **kwargs):
        raise AccessError("This is an access http test")

    @http.route('/test_missing_error_json', type='json', auth='public', website=True, sitemap=False)
    def test_missing_error_json(self, **kwargs):
        raise MissingError("This is a missing rpc test")

    @http.route('/test_missing_error_http', type='http', auth='public', website=True, sitemap=False)
    def test_missing_error_http(self, **kwargs):
        raise MissingError("This is a missing http test")

    @http.route('/test_internal_error_json', type='json', auth='public', website=True, sitemap=False)
    def test_internal_error_json(self, **kwargs):
        raise werkzeug.exceptions.InternalServerError()

    @http.route('/test_internal_error_http', type='http', auth='public', website=True, sitemap=False)
    def test_internal_error_http(self, **kwargs):
        raise werkzeug.exceptions.InternalServerError()

    @http.route('/test_access_denied_json', type='json', auth='public', website=True, sitemap=False)
    def test_denied_error_json(self, **kwargs):
        raise AccessDenied("This is an access denied rpc test")

    @http.route('/test_access_denied_http', type='http', auth='public', website=True, sitemap=False)
    def test_denied_error_http(self, **kwargs):
        raise AccessDenied("This is an access denied http test")

    @http.route(['/get'], type='http', auth="public", methods=['GET'], website=True)
    def get_method(self, **kw):
        return request.make_response('get')

    @http.route(['/post'], type='http', auth="public", methods=['POST'], website=True)
    def post_method(self, **kw):
        return request.make_response('post')

    @http.route(['/get_post'], type='http', auth="public", methods=['GET', 'POST'], website=True)
    def get_post_method(self, **kw):
        return request.make_response('get_post')

    @http.route(['/get_post_nomultilang'], type='http', auth="public", methods=['GET', 'POST'], website=True, multilang=False)
    def get_post_method_no_multilang(self, **kw):
        return request.make_response('get_post_nomultilang')
