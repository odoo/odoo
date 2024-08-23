# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.http import request


class Image(models.AbstractModel):
    _inherit = 'ir.qweb.field.image'

    def _get_src_urls(self, record, field_name, options):
        src, src_zoom = super()._get_src_urls(record, field_name, options)
        if isinstance(record, self.env.registry['portal.mixin']) and request and request.params.get('access_token'):
            src += '&access_token=' + request.params.get('access_token')
        return src, src_zoom
