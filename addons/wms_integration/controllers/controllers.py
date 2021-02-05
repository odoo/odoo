#-*- coding: utf-8 -*-
from odoo import http


class WmsIntegration(http.Controller):
    @http.route('/wms_integration/wms_integration/', auth='public')
    def index(self, **kw):
        return "Hello, world"

    @http.route('/wms_integration/wms_integration/objects/', auth='public')
    def list(self, **kw):
        return http.request.render('wms_integration.listing', {
            'root': '/wms_integration/wms_integration',
            'objects': http.request.env['wms_integration.wms_integration'].search([]),
        })

    @http.route('/wms_integration/wms_integration/objects/<model("wms_integration.wms_integration"):obj>/', auth='public')
    def object(self, obj, **kw):
        return http.request.render('wms_integration.object', {
            'object': obj
        })
