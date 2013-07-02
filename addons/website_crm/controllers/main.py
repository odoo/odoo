# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.controllers.main import template_values


class contactus(http.Controller):

    @http.route(['/crm/contactus'], type='http', auth="db")
    def contactus(self, *arg, **kwarg):
        values = template_values()
        cr = request.cr
        uid = request.session._uid or openerp.SUPERUSER_ID

        html = request.registry.get("ir.ui.view").render(cr, uid, "website_crm.contactus", self.get_values())
        return html

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
