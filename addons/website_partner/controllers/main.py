# -*- coding: utf-8 -*-

import werkzeug

from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request

def get_partner_template_value(partner_id):
    partner = request.registry['res.partner'].browse(request.cr, SUPERUSER_ID, partner_id, context=request.context)
    if not partner.exists() or not partner.website_published:
        return None
    return {
        'partner': partner,
    }

class WebsitePartner(http.Controller):
    @http.route(['/partners/<int:partner_id>', '/partners/<partner_name>-<int:partner_id>'], type='http', auth="public", website=True, multilang=True)
    def partner(self, partner_id, partner_name='', **post):
        """ Route for displaying a single partner / customer. """
        values = get_partner_template_value(partner_id)
        if not values:
            raise werkzeug.exceptions.NotFound()

        return request.website.render("website_partner.partner_page", values)
