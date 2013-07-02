# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.controllers.main import template_values


class contactus(http.Controller):

    @http.route(['/crm/contactus'], type='http', auth="db")
    def contactus(self, *arg, **post):
        cr = request.cr
        uid = request.session._uid or openerp.SUPERUSER_ID
        post['user_id'] = False
        request.registry['crm.lead'].create(cr, uid, post)
        html = request.registry.get("ir.ui.view").render(cr, uid, "website_crm.thanks", template_values())
        return html

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
