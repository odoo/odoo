# -*- coding: utf-8 -*-

from openerp import http
from openerp.http import request


class WebsiteCertifiedPartners(http.Controller):

    @http.route(['/certifications',
                 '/certifications/<model("certification.type"):cert_type>'], type='http', auth='public',
                website=True)
    def certified_partners(self, cert_type=None, **post):
        domain = []
        if cert_type:
            domain.append(('type_id', '=', cert_type.id))

        data = {
            'certifications': request.env['certification.certification'].search(domain),
            'types': request.env['certification.type'].search([])
        }

        return request.website.render("website_certification.certified_partners", data)
