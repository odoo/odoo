# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models import website
import werkzeug


def get_partner_template_value(partner):
    ctx = dict(request.context, show_address=True)
    partner_obj = request.registry['res.partner']
    partner_id = partner.id
    partner_ids = partner_obj.search(request.cr, request.uid, [('id', '=', partner_id)], context=request.context)
    if not partner.exists() or not partner_ids:
        partner = None

    partner_data = partner_obj.read(
            request.cr, openerp.SUPERUSER_ID, [partner_id], request.website.get_partner_white_list_fields(), context=ctx)[0]

    if not partner_data["website_published"]:
        return None

    partner_data['name_get'] = partner_obj.name_get(request.cr, openerp.SUPERUSER_ID, [partner_id],context=request.context)[0]

    partner_data['address'] = '<br/>'.join(partner_obj.name_get(
            request.cr, openerp.SUPERUSER_ID, [partner_id],context=ctx)[0][1].split('\n')[1:])

    values = {
        'partner': partner,
        'partner_data': partner_data,
    }
    return values

class WebsitePartner(http.Controller):
    @website.route(['/partners/<model("res.partner"):partner>/'], type='http', auth="public", multilang=True)
    def partner(self, partner, **post):
        """ Route for displaying a single partner / customer. """
        values = get_partner_template_value(partner)
        if not values:
            raise werkzeug.exceptions.NotFound
        return request.website.render("website_partner.partner_detail", values)
