# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _get_subcontract_mo_confirmation_ctx(self):
        res = super()._get_subcontract_mo_confirmation_ctx()
        res['po_to_notify'] = self.move_ids.purchase_line_id.order_id
        return res
