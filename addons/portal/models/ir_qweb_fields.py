# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import urllib.parse
from odoo import models
from odoo.http import request


class Image(models.AbstractModel):
    _inherit = 'ir.qweb.field.image'

    def _get_src_urls(self, record, field_name, options):
        src, src_zoom = super()._get_src_urls(record, field_name, options)
        if isinstance(record, self.env.registry['portal.mixin']) and request and request.params.get('access_token'):
            attachment = self.sudo().env['ir.attachment'].search([('res_model', '=', record._name), ('res_id', '=', record.id), ('res_field', '=', field_name)])
            attachment.generate_access_token()
            url = urllib.parse.urlsplit(src)
            query = urllib.parse.parse_qs(url.query)
            query['access_token'] = [attachment.access_token]
            new_url = url._replace(query=urllib.parse.urlencode(query, doseq=True))
            src = urllib.parse.urlunsplit(new_url)
        return src, src_zoom
