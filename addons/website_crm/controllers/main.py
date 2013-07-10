# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.controllers.main import template_values

from urllib import quote_plus

class contactus(http.Controller):

    @http.route(['/crm/contactus'], type='http', auth="admin")
    def contactus(self, *arg, **post):
        post['user_id'] = False
        request.registry['crm.lead'].create(request.cr, request.uid, post)
        values = template_values()
        company = request.registry['res.company'].browse(request.cr, request.uid, 1)
        values.update({
            'res_company': company,
            'google_map_url': "http://maps.googleapis.com/maps/api/staticmap?center=%s&sensor=false&zoom=8&size=298x298" % quote_plus('%s, %s %s, %s' % (company.street, company.city, company.zip, company.country_id and company.country_id.name_get()[0][1] or ''))
        })
        html = request.registry.get("ir.ui.view").render(request.cr, request.uid, "website_crm.thanks", values)
        return html


# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
