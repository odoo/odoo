# -*- coding: utf-8 -*-

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _stock_account_get_anglo_saxon_price_unit(self):
        price_unit = super(AccountMoveLine, self)._stock_account_get_anglo_saxon_price_unit()

        so_line = self.sale_line_ids and self.sale_line_ids[-1] or False
        if so_line:
            boms = self.sale_line_ids.move_ids.bom_line_id.bom_id
            bom = boms.filtered(lambda bom: bom.type == "phantom" and (bom.product_id == so_line.product_id
                                            or (not bom.product_id and bom.product_tmpl_id == so_line.product_template_id)))
            if bom:
                qty_to_invoice = self.product_uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
                qty_invoiced = sum([x.product_uom_id._compute_quantity(x.quantity, x.product_id.uom_id) for x in so_line.invoice_lines if x.move_id.state == 'posted'])
                moves = so_line.move_ids
                average_price_unit = 0
                components = so_line._get_bom_component_qty(bom)
                for product_id in components:
                    product = self.env['product.product'].browse(product_id)
                    factor = components[product_id]['qty']
                    prod_moves = moves.filtered(lambda m: m.product_id == product)
                    prod_qty_invoiced = factor * qty_invoiced
                    prod_qty_to_invoice = factor * qty_to_invoice
                    average_price_unit += factor * product._compute_average_price(prod_qty_invoiced, prod_qty_to_invoice, prod_moves)
                price_unit = average_price_unit or price_unit
                price_unit = self.product_id.uom_id._compute_price(price_unit, self.product_uom_id)
        return price_unit

