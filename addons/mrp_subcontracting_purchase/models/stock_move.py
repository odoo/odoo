# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import mrp_subcontracting, purchase_mrp


class StockMove(mrp_subcontracting.StockMove, purchase_mrp.StockMove):

    def _is_purchase_return(self):
        res = super()._is_purchase_return()
        return res or self._is_subcontract_return()
