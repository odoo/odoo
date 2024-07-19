# -*- coding: utf-8 -*-

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _stock_account_get_anglo_saxon_price_unit(self):
        price_unit = super(AccountMoveLine, self)._stock_account_get_anglo_saxon_price_unit()

        so_line = self.sale_line_ids and self.sale_line_ids[-1] or False
        if so_line:
            # We give preference to the bom in the stock moves for the sale order lines
            # If there are changes in BOMs between the stock moves creation and the
            # invoice validation a wrong price will be taken
            moves = so_line.move_ids
            bom = moves.filtered(lambda m: m.state != 'cancel').bom_line_id.bom_id.filtered(lambda b: b.type == 'phantom')[:1]
            # In the case of nested kits, the above method doesn't allow us to go back to the "root" bom,
            # Since we lost the relevant information we have to fallback to another method for finding an appropriate bom
            # This bom may be technically incorrect in the sense that
            # it's possibly not the one that was actually used for this operation
            if bom and bom.product_tmpl_id != so_line.product_template_id:
                bom = self.env['mrp.bom']._bom_find(
                    products=so_line.product_id, company_id=so_line.company_id.id,
                    picking_type=moves.picking_type_id, bom_type='phantom',
                )[so_line.product_id]
            if bom:
                is_line_reversing = self.move_id.move_type == 'out_refund'
                qty_to_invoice = self.product_uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
                account_moves = so_line.invoice_lines.move_id.filtered(lambda m: m.state == 'posted' and bool(m.reversed_entry_id) == is_line_reversing)
                posted_invoice_lines = account_moves.line_ids.filtered(lambda l: l.display_type == 'cogs' and l.product_id == self.product_id and l.balance > 0)
                qty_invoiced = sum([x.product_uom_id._compute_quantity(x.quantity, x.product_id.uom_id) for x in posted_invoice_lines])
                reversal_cogs = posted_invoice_lines.move_id.reversal_move_id.line_ids.filtered(lambda l: l.display_type == 'cogs' and l.product_id == self.product_id and l.balance > 0)
                qty_invoiced -= sum([line.product_uom_id._compute_quantity(line.quantity, line.product_id.uom_id) for line in reversal_cogs])

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
