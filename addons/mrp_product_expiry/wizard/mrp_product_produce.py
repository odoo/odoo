# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MrpProductProduce(models.TransientModel):
    _inherit = 'mrp.product.produce'

    def do_produce(self):
        confirm_expired_lots = self._check_expired_lots()
        if confirm_expired_lots:
            return confirm_expired_lots
        return super(MrpProductProduce, self).do_produce()

    def _get_expired_context(self, expired_lot_ids):
        context = super(MrpProductProduce, self)._get_expired_context(expired_lot_ids)
        context['default_produce_id'] = self.id
        return context
