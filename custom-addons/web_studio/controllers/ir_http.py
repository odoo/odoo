# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super(IrHttp, self).session_info()

        if result['is_system']:
            # necessary keys for Studio
            result['dbuuid'] = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
            result['multi_lang'] = len(self.env['res.lang'].get_installed()) > 1

        return result
