# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv.expression import OR


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _load_data_params(self, config_id):
        params = super(PosSession, self)._load_data_params(config_id)
        if self.config_id.module_pos_discount:
            curr_domain = params['product.product']['domain']
            params['product.product']['domain'] = OR([curr_domain, [('id', '=', self.config_id.discount_product_id.id)]])
        return params
