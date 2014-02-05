# -*- coding: utf-8 -*-

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp import SUPERUSER_ID

import werkzeug.urls


class contactus(http.Controller):

    def generate_google_map_url(self, street, city, city_zip, country_name):
        url = "http://maps.googleapis.com/maps/api/staticmap?center=%s&sensor=false&zoom=8&size=298x298" % werkzeug.url_quote_plus(
            '%s, %s %s, %s' % (street, city, city_zip, country_name)
        )
        return url

    @http.route(['/crm/contactus'], type='http', auth="public", website=True, multilang=True)
    def contactus(self, description=None, partner_name=None, phone=None, contact_name=None, email_from=None, name=None):
        post = {}
        post['description'] = description
        post['partner_name'] = partner_name
        post['phone'] = phone
        post['contact_name'] = contact_name
        post['email_from'] = email_from
        post['name'] = name

        required_fields = ['contact_name', 'email_from', 'description']
        error = set()
        values = dict((key, post.get(key)) for key in post)
        values['error'] = error

        # fields validation
        for field in required_fields:
            if not post.get(field):
                error.add(field)
        if error:
            return request.website.render("website.contactus", values)

        # if not given: subject is contact name
        if not post.get('name'):
            post['name'] = post.get('contact_name')
            
        post['user_id'] = False

        try:
            post['channel_id'] = request.registry['ir.model.data'].get_object_reference(request.cr, SUPERUSER_ID, 'crm', 'crm_case_channel_website')[1]
        except ValueError:
            pass

        request.registry['crm.lead'].create(request.cr, SUPERUSER_ID, post, request.context)
        company = request.website.company_id
        values = {
            'google_map_url': self.generate_google_map_url(company.street, company.city, company.zip, company.country_id and company.country_id.name_get()[0][1] or '')
        }
        return request.website.render("website_crm.contactus_thanks", values)
