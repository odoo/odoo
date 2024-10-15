# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import point_of_sale


class PosConfig(point_of_sale.PosConfig):

    def _force_http(self):
        enforce_https = self.env['ir.config_parameter'].sudo().get_param('point_of_sale.enforce_https')
        if not enforce_https and self.payment_method_ids.filtered(lambda pm: pm.use_payment_terminal == 'six'):
            return True
        return super(PosConfig, self)._force_http()
