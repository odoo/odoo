# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons import mrp


class ChangeProductionQty(mrp.ChangeProductionQty):

    @api.model
    def _need_quantity_propagation(self, move, qty):
        res = super()._need_quantity_propagation(move, qty)
        return res and not any(m.is_subcontract for m in move.move_dest_ids)
