# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv.expression import OR
from odoo.addons.point_of_sale.models.pos_session import pos_loader


class PosSession(models.Model):
    _inherit = "pos.session"

    @pos_loader.info('gift.card')
    def _loader_info_gift_card(self):
        return {
            'fields': ["code", "initial_amount", "balance"],
            'domain': [],
        }

    def _get_product_product_domain(self):
        result = super(PosSession, self)._get_product_product_domain()
        if self.config_id.use_gift_card and self.config_id.gift_card_product_id:
            return OR([result, [("id", "=", self.config_id.gift_card_product_id.id)]])
        return result
