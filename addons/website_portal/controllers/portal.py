# -*- coding: utf-8 -*-
from openerp import http
from openerp.addons.web.http import request


class portal(http.Controller):
    @http.route('/website_portal/portal', auth='public', website=True)
    def index(self, **kw):
        menu_obj = request.env()['ir.ui.menu']
        menu_data = menu_obj.load_menus()
        portal_obj = request.env()['ir.model.data']
        portal_menu_id = portal_obj.xmlid_to_res_id('portal.portal_menu')
        portal_menu = {}
        for menu in menu_data['children']:
            if menu['id'] == portal_menu_id:
                portal_menu['children'] = [menu]
        if not portal_menu:
            return request.render("website.403")
        return request.render("website.portal", qcontext={'portal_menu_data': portal_menu})
