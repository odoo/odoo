# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv.expression import OR


class PosSession(models.Model):
    _inherit = "pos.session"

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        result.append("gift.card")
        return result

    def _loader_info_gift_card(self):
        return {
            'fields': ["code", "initial_amount", "balance"],
            'domain': [],
        }

    def _get_pos_ui_gift_card(self, params):
        return self.env["gift.card"].search_read(params["domain"], params["fields"])

    def _get_product_product_domain(self):
        result = super(PosSession, self)._get_product_product_domain()
        if self.config_id.use_gift_card and self.config_id.gift_card_product_id:
            return OR([result, [("id", "=", self.config_id.gift_card_product_id.id)]])
        return result
