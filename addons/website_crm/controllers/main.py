# -*- coding: utf-8 -*-

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models import website

from urllib import quote_plus


class contactus(http.Controller):

    def generate_google_map_url(self, street, city, city_zip, country_name):
        url = "http://maps.googleapis.com/maps/api/staticmap?center=%s&sensor=false&zoom=8&size=298x298" % quote_plus(
            '%s, %s %s, %s' % (street, city, city_zip, country_name)
        )
        return url

    @website.route(['/crm/contactus'], type='http', auth="admin", multilang=True)
    def contactus(self, *arg, **post):
        required_fields = ['contact_name', 'email_from', 'description']
        post['user_id'] = False
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

        request.registry['crm.lead'].create(request.cr, request.uid,
                                            post, request.context)
        company = request.website.company_id
        values = {
            'google_map_url': self.generate_google_map_url(company.street, company.city, company.zip, company.country_id and company.country_id.name_get()[0][1] or '')
        }
        return request.website.render("website_crm.contactus_thanks", values)
