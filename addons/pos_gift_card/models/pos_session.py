# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv.expression import OR


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        if self.config_id.use_gift_card and self.config_id.gift_card_product_id:
            result['search_params']['domain'] = OR([result['search_params']['domain'], [('id', '=', self.config_id.gift_card_product_id.id)]])
        return result
