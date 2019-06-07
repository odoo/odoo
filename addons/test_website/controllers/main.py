# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.web import Home
import json


class WebsiteTest(Home):

    @http.route('/test_view', type='http', auth="public", website=True)
    def test_view(self, **kw):
        return request.render('test_website.test_view')

    @http.route('/ignore_args/converteronly/<string:a>/', type='http', auth="public", website=True)
    def test_ignore_args_converter_only(self, a):
        return request.make_response(json.dumps(dict(a=a, kw=None)))

    @http.route('/ignore_args/none', type='http', auth="public", website=True)
    def test_ignore_args_none(self):
        return request.make_response(json.dumps(dict(a=None, kw=None)))

    @http.route('/ignore_args/a', type='http', auth="public", website=True)
    def test_ignore_args_a(self, a):
        return request.make_response(json.dumps(dict(a=a, kw=None)))

    @http.route('/ignore_args/kw', type='http', auth="public", website=True)
    def test_ignore_args_kw(self, a, **kw):
        return request.make_response(json.dumps(dict(a=a, kw=kw)))

    @http.route('/ignore_args/converter/<string:a>/', type='http', auth="public", website=True)
    def test_ignore_args_converter(self, a, b='youhou', **kw):
        return request.make_response(json.dumps(dict(a=a, b=b, kw=kw)))

    @http.route('/ignore_args/converter/<string:a>/nokw', type='http', auth="public", website=True)
    def test_ignore_args_converter_nokw(self, a, b='youhou'):
        return request.make_response(json.dumps(dict(a=a, b=b)))
