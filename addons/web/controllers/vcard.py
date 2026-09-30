# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import importlib.util
import io
import zipfile

import odoo.http as http

from odoo.exceptions import UserError
from odoo.http import request, content_disposition


class Partner(http.Controller):

    @http.route(['/web_enterprise/partner/<model("res.partner"):partner>/vcard',
                 '/web/partner/vcard'], type='http', auth="user")
    def download_vcard(self, partner_ids=None, partner=None, **kwargs):
        if importlib.util.find_spec('vobject') is None:
            raise UserError(self.env._('vobject library is not installed'))

        if partner_ids:
            partner_ids = list(filter(None, (int(pid) for pid in partner_ids.split(',') if pid.isdigit())))
            partners = request.env['res.partner'].browse(partner_ids)
            if len(partners) > 1:
                with io.BytesIO() as buffer:
                    with zipfile.ZipFile(buffer, 'w') as zipf:
                        for partner in partners:
                            filename = f"{partner.name or partner.email}.vcf"
                            content = partner._get_vcard_file()
                            zipf.writestr(filename, content)

                    return request.make_response(buffer.getvalue(), [
                        ('Content-Type', 'application/zip'),
                        ('Content-Length', len(content)),
                        ('Content-Disposition', content_disposition('Contacts.zip'))
                    ])

        if partner or partners:
            partner = partner or partners
            content = partner._get_vcard_file()
            return request.make_response(content, [
                ('Content-Type', 'text/vcard'),
                ('Content-Length', len(content)),
                ('Content-Disposition', content_disposition(f"{partner.name or partner.email}.vcf")),
            ])

        return request.not_found()
