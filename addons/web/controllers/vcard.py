# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.http as http

from odoo.http import request, content_disposition


class Partner(http.Controller):

    @http.route('/web/partner/<model("res.partner"):partner>/vcard', type='http', auth="user")
    def download_vcard(self, partner, **kwargs):
        content = partner._get_vcard_file()
        if not content:
            return request.not_found()
        return request.make_response(content, [
            ('Content-Type', 'text/vcard'),
            ('Content-Length', len(content)),
            ('Content-Disposition', content_disposition('%s.vcf' % partner.name))
        ])
