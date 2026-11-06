# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _is_purchase_return(self):
        res = super()._is_purchase_return()
        return res or self._is_subcontract_return()

    def _get_related_invoices(self):
        rslt = super()._get_related_invoices()
        # subcontracted move valuations are linked to the MO finished move, not the PO move
        subcontracted_moves = self.move_dest_ids.filtered(lambda m: m.is_subcontract)
        if subcontracted_moves:
            rslt |= subcontracted_moves._get_related_invoices()
        return rslt
