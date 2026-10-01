# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_subcontract_partner(self):
        """Use the PO vendor as subcontractor instead of picking.partner_id.

        For Dropship Subcontracting POs with a dest_address_id different from
        the vendor, secondary pickings (one per unique date_planned) inherit
        partner_id from the move (= dest_address_id) via _get_new_picking_values().
        The PO vendor is the correct subcontractor for BoM lookup and location
        resolution.
        """
        if self.purchase_line_id:
            return self.purchase_line_id.order_id.partner_id
        return super()._get_subcontract_partner()

    def _is_purchase_return(self):
        res = super()._is_purchase_return()
        return res or self._is_subcontract_return()
