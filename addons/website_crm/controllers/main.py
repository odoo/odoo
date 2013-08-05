# -*- coding: utf-8 -*-

from openerp.addons.web import http
from openerp.addons.web.http import request

from urllib import quote_plus

class contactus(http.Controller):

    @http.route(['/crm/contactus'], type='http', auth="admin")
    def contactus(self, *arg, **post):
        website = request.registry['website']
        post['user_id'] = False
        request.registry['crm.lead'].create(request.cr, request.uid, post)
        values = website.get_rendering_context()
        company = values['res_company']
        values.update({
            'google_map_url': "http://maps.googleapis.com/maps/api/staticmap?center=%s&sensor=false&zoom=8&size=298x298" % quote_plus('%s, %s %s, %s' % (company.street, company.city, company.zip, company.country_id and company.country_id.name_get()[0][1] or ''))
        })
        return website.render("website_crm.thanks", values)

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
