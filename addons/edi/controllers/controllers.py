# -*- coding: utf-8 -*-
from odoo import http


class Edi(http.Controller):
    @http.route('/edi/edi', auth='public')
    def index(self, **kw):
        return "Hello, world"

    @http.route('/edi/edi/objects', auth='public')
    def list(self, **kw):
        return http.request.render('edi.list', {
            'root': '/edi/edi',
            'objects': http.request.env['edi.partner'].search([]),
        })

    @http.route('/edi/edi/objects/<model("edi.partner"):obj>', auth='public')
    def object(self, obj, **kw):
        return http.request.render('edi.object', {
            'object': obj
        })