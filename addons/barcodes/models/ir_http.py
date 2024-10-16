# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import web


class IrHttp(web.IrHttp):

    def session_info(self):
        res = super(IrHttp, self).session_info()
        if self.env.user._is_internal():
            res['max_time_between_keys_in_ms'] = int(
                self.env['ir.config_parameter'].sudo().get_param('barcode.max_time_between_keys_in_ms', default='150'))
        return res
