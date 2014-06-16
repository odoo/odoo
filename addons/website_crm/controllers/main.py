# -*- coding: utf-8 -*-
import base64

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

    @http.route(['/page/website.contactus', '/page/contactus'], type='http', auth="public", website=True)
    def contact(self, **kwargs):
        values = {}
        for field in ['description', 'partner_name', 'phone', 'contact_name', 'email_from', 'name']:
            if kwargs.get(field):
                values[field] = kwargs.pop(field)
        values.update(kwargs=kwargs.items())
        return request.website.render("website.contactus", values)

    @http.route(['/crm/contactus'], type='http', auth="public", website=True)
    def contactus(self, description=None, partner_name=None, phone=None, contact_name=None, email_from=None, name=None, **kwargs):
        post = {
            'description': description,
            'partner_name': partner_name,
            'phone': phone,
            'contact_name': contact_name,
            'email_from': email_from,
            'name': name or contact_name,
        }

        # fields validation
        error = set(field for field in ['contact_name', 'email_from', 'description']
                    if not post.get(field))

        values = dict(post, error=error)
        if error:
            values.update(kwargs=kwargs.items())
            return request.website.render("website.contactus", values)

        try:
            post['channel_id'] = request.registry['ir.model.data'].get_object_reference(request.cr, SUPERUSER_ID, 'crm', 'crm_case_channel_website')[1]
        except ValueError:
            pass

        post['user_id'] = False
        environ = request.httprequest.headers.environ
        post['description'] = "%s\n-----------------------------\nIP: %s\nUSER_AGENT: %s\nACCEPT_LANGUAGE: %s\nREFERER: %s" % (
            post['description'],
            environ.get("REMOTE_ADDR"),
            environ.get("HTTP_USER_AGENT"),
            environ.get("HTTP_ACCEPT_LANGUAGE"),
            environ.get("HTTP_REFERER"))
        for field_name, field_value in kwargs.items():
            if not hasattr(field_value, 'filename'):
                post['description'] = "%s\n%s: %s" % (post['description'], field_name, field_value)

        post['section_id'] = request.registry['ir.model.data'].xmlid_to_res_id(request.cr, SUPERUSER_ID, 'website.salesteam_website_sales')
        lead_id = request.registry['crm.lead'].create(request.cr, SUPERUSER_ID, post, request.context)

        for field_name, field_value in kwargs.items():
            if hasattr(field_value, 'filename'):
                attachment_value = {
                    'name': field_value.filename,
                    'res_name': field_value.filename,
                    'res_model': 'crm.lead',
                    'res_id': lead_id,
                    'datas': base64.encodestring(field_value.read()),
                    'datas_fname': field_value.filename,
                }
                request.registry['ir.attachment'].create(request.cr, SUPERUSER_ID, attachment_value, context=request.context)

        company = request.website.company_id
        values = {
            'google_map_url': self.generate_google_map_url(company.street, company.city, company.zip, company.country_id and company.country_id.name_get()[0][1] or ''),
        }
        return request.website.render("website_crm.contactus_thanks", values)
