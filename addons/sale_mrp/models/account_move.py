# -*- coding: utf-8 -*-

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _stock_account_get_anglo_saxon_price_unit(self):
        price_unit = super(AccountMoveLine, self)._stock_account_get_anglo_saxon_price_unit()

        so_line = self.sale_line_ids and self.sale_line_ids[-1] or False
        if so_line:
            bom = self.env['mrp.bom']._bom_find(products=so_line.product_id, company_id=so_line.company_id.id, bom_type='phantom')[so_line.product_id]
            if bom:
                is_line_reversing = self.move_id.move_type == 'out_refund'
                qty_to_invoice = self.product_uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
                posted_invoice_lines = so_line.invoice_lines.filtered(lambda l: l.move_id.state == 'posted' and bool(l.move_id.reversed_entry_id) == is_line_reversing)
                qty_invoiced = sum([x.product_uom_id._compute_quantity(x.quantity, x.product_id.uom_id) for x in posted_invoice_lines])
                moves = so_line.move_ids
                average_price_unit = 0
                components_qty = so_line._get_bom_component_qty(bom)
                storable_components = self.env['product.product'].search([('id', 'in', list(components_qty.keys())), ('type', '=', 'product')])
                for product in storable_components:
                    factor = components_qty[product.id]['qty']
                    prod_moves = moves.filtered(lambda m: m.product_id == product)
                    prod_qty_invoiced = factor * qty_invoiced
                    prod_qty_to_invoice = factor * qty_to_invoice
                    product = product.with_company(self.company_id)
                    average_price_unit += factor * product._compute_average_price(prod_qty_invoiced, prod_qty_to_invoice, prod_moves, is_returned=is_line_reversing)
                price_unit = average_price_unit / bom.product_qty or price_unit
                price_unit = self.product_id.uom_id._compute_price(price_unit, self.product_uom_id)
        return price_unit
