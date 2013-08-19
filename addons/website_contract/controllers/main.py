# -*- coding: utf-8 -*-

from openerp.addons.web import http
from openerp.addons.web.http import request

class website_contract(http.Controller):

    @http.route(['/references/'], type='http', auth="public")
    def blog(self, **post):
        website = request.registry['website']
        partner_obj = request.registry['res.partner']
        project_ids = partner_obj.search(request.cr, request.uid, [(1, "=", 1)])
        values = website.get_rendering_context({
            'partner_ids': partner_obj.browse(request.cr, request.uid, project_ids)
        })
        return website.render("website_contract.index", values)
