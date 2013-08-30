# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.addons.web.http import request
import simplejson
import werkzeug.wrappers
from datetime import datetime

class google_map(http.Controller):

    @http.route(['/google_map/'], type='http', auth="admin")
    def google_map(self, *arg, **post):
        website = request.registry['website']
        values = website.get_rendering_context()
        values['partner_ids'] = post.get('partner_ids', "")
        values['width'] = post.get('width', 900)
        values['height'] = post.get('height', 460)
        values['partner_url'] = post.get('partner_url')
        return website.render("website_google_map.google_map", values)

    @http.route(['/google_map/partners.json'], type='http', auth="admin")
    def google_map_data(self, *arg, **post):
        website = request.registry['website']
        partner_obj = request.registry['res.partner']

        domain = [("id", "in", [int(p) for p in post.get('partner_ids', "").split(",") if p])]
        partner_ids = partner_obj.search(request.cr, openerp.SUPERUSER_ID, domain + [('website_published', '=', True)])
        if request.uid != website.get_public_user().id:
            partner_ids += partner_obj.search(request.cr, request.uid, domain)
            partner_ids = list(set(partner_ids))

        data = {
            "counter": len(partner_ids),
            "partners": []
            }
        for partner in partner_obj.browse(request.cr, openerp.SUPERUSER_ID, partner_ids, context={'show_address': True}):
            data["partners"].append({
                'id': partner.id,
                'name': partner.name,
                'address': '\n'.join(partner.name_get()[0][1].split('\n')[1:]),
                'type': partner.grade_id.name,
                'latitude': partner.partner_latitude,
                'longitude': partner.partner_longitude,
                })

        mime = 'application/json'
        body = "var data = " + "}, \n{".join(simplejson.dumps(data).split("}, {"))
        return werkzeug.wrappers.Response(body, headers=[('Content-Type', mime), ('Content-Length', len(body))])

    @http.route(['/google_map/set_partner_position/'], type='http', auth="admin")
    def google_map_set_partner_position(self, *arg, **post):
        website = request.registry['website']
        partner_obj = request.registry['res.partner']

        partner_id = post.get('partner_id') and int(post['partner_id'])
        latitude = post.get('latitude') and float(post['latitude'])
        longitude = post.get('longitude') and float(post['longitude'])

        if request.uid != website.get_public_user().id and partner_id and (latitude or longitude):
            values = {
                'partner_latitude': latitude,
                'partner_longitude': longitude,
                'date_localization': datetime.now().strftime('%Y-%m-%d'),
                }
            partner_obj.write(request.cr, request.uid, [partner_id], values)


# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
