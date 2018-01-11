# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from openerp.addons.web import http
from openerp.addons.web.http import request


class WebsiteCertifiedPartners(http.Controller):

    @http.route(['/certifications',
                 '/certifications/<model("certification.type"):cert_type>'], type='http', auth='public',
                website=True)
    def certified_partners(self, cert_type=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        certification_obj = request.registry['certification.certification']
        cert_type_obj = request.registry['certification.type']

        domain = []
        if cert_type:
            domain.append(('type_id', '=', cert_type.id))

        certifications_ids = certification_obj.search(cr, uid, domain, context=context)
        certifications = certification_obj.browse(cr, uid, certifications_ids, context=context)
        types = cert_type_obj.browse(cr, uid, cert_type_obj.search(cr, uid, [], context=context), context=context)
        data = {
            'certifications': certifications,
            'types': types
        }

        return request.website.render("website_certification.certified_partners", data)
