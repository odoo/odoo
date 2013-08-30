# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.addons.web.http import request
import simplejson
import werkzeug.wrappers

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

    @http.route(['/crm/google_map/'], type='http', auth="admin")
    def google_map(self, *arg, **post):
        website = request.registry['website']
        values = website.get_rendering_context()
        values['partner_ids'] = post.get('partner_ids', "")
        return website.render("website_crm.google_map", values)

    @http.route(['/crm/google_map/partners.json'], type='http', auth="admin")
    def google_map_data(self, *arg, **post):
        website = request.registry['website']
        partner_obj = request.registry['res.partner']

        domain = [("id", "in", [int(p) for p in post.get('partner_ids', "").split(",") if p])]
        partner_ids = partner_obj.search(request.cr, openerp.SUPERUSER_ID, domain + [('website_published', '=', True)])
        if request.uid != website.get_public_user().id:
            partner_ids += partner_obj.search(request.cr, request.uid, domain)

        data = {
            "counter": len(partner_ids),
            "partners": []
            }
        for partner in partner_obj.browse(request.cr, openerp.SUPERUSER_ID, partner_ids, context={'show_address': True}):
            data["partners"].append({
                'id': partner.id,
                'name': partner.name,
                'address': '\n'.join(partner.name_get()[0][1].split('\n')[1:]),
                'type': "Silver Partners"
                })

        mime = 'application/json'
        body = "var data = " + "}, \n{".join(simplejson.dumps(data).split("}, {"))
        return werkzeug.wrappers.Response(body, headers=[('Content-Type', mime), ('Content-Length', len(body))])

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
