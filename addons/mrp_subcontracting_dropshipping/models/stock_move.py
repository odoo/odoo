# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _is_purchase_return(self):
        res = super()._is_purchase_return()
        return res or self._is_dropshipped_returned()

    def _is_dropshipped(self):
        res = super()._is_dropshipped()
        return (
            res
            # subcontractor -> customer
            or (
                self.partner_id.property_stock_subcontractor.parent_path
                and (
                    (
                        self.partner_id.property_stock_subcontractor.parent_path
                        in self.location_id.parent_path
                        and self.location_dest_id.usage == "customer"
                    )
                    # Vendor -> subcontractor location
                    or (
                        self.partner_id.property_stock_subcontractor.parent_path
                        in self.location_dest_id.parent_path
                        and self.location_id.usage == "supplier"
                    )
                )
            )
        )

    def _is_dropshipped_returned(self):
        res = super()._is_dropshipped_returned()
        return res or (
                self.location_id.usage == 'customer'
                and self.partner_id.property_stock_subcontractor.parent_path
                and self.partner_id.property_stock_subcontractor.parent_path in self.location_dest_id.parent_path
        )
