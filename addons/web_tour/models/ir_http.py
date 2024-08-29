# -*- coding: utf-8 -*-
from odoo.addons import base
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrHttp(models.AbstractModel, base.IrHttp):

    def session_info(self):
        result = super().session_info()
        if result['is_admin']:
            demo_modules_count = self.env['ir.module.module'].sudo().search_count([('demo', '=', True)])
            result['web_tours'] = self.env['web_tour.tour'].get_consumed_tours()
            result['tour_disable'] = demo_modules_count > 0
        return result
