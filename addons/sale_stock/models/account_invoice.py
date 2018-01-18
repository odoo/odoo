# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    incoterms_id = fields.Many2one('stock.incoterms', string="Incoterms",
        help="Incoterms are series of sales terms. They are used to divide transaction costs and responsibilities between buyer and seller and reflect state-of-the-art transportation practices.",
        readonly=True, states={'draft': [('readonly', False)]})

    def _get_related_stock_moves(self): # overridden from stock_account
        rslt = super(AccountInvoice, self)._get_related_stock_moves()

        if self.type in ('out_invoice', 'out_refund'):
            rslt += self.mapped('invoice_line_ids.sale_line_ids.order_id.picking_ids.move_lines').filtered(lambda x: x.state == 'done')

        return rslt

    def finalize_invoice_move_lines(self, move_lines):
        rslt = super(AccountInvoice, self).finalize_invoice_move_lines(move_lines)

        #TODO OCO si j'ai raison et que tout vient bien d'un bug dans stock_account, à priori, il ne faudra pas tout ceci.
        if self.type == 'out_invoice':
            products_valuation_map = {}
            for generated_line_tuple in rslt:
                generated_line = generated_line_tuple[2]
                line_product = generated_line['product_id'] and self.env['product.product'].browse(generated_line['product_id']) or False

                if not line_product:
                    continue

                interim_output_account = line_product.product_tmpl_id._get_product_accounts()['stock_output']

                if generated_line['account_id'] == interim_output_account.id:
                    line_qty = generated_line['quantity']
                    line_balance = generated_line['debit'] or -generated_line['credit']

                    line_data = products_valuation_map.get(line_product, None)
                    if  line_data != None:
                        line_qty += line_data[0]
                        line_balance += line_data[1]

                    products_valuation_map[line_product] = (line_qty, line_balance)

            for product, (product_qty, product_valuation) in products_valuation_map.items():
                shipped_qty = sum(self._get_related_stock_moves().mapped('product_qty'))

                # TODO OCO self.move_id.line_ids est vide car les aml ne sont pas postées ><
                #>> un iterable en plus en param, pas le choix :/
                #rslt += self.move_id.line_ids.get_aml_data_to_fully_reconcile_out_invoices_with_stock_valuation(interim_output_account, product, self.commercial_partner_id.id, shipped_qty, product_qty, product_valuation)

        return rslt



class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    def _get_anglo_saxon_price_unit(self):
        price_unit = super(AccountInvoiceLine,self)._get_anglo_saxon_price_unit()
        # in case of anglo saxon with a product configured as invoiced based on delivery, with perpetual
        # valuation and real price costing method, we must find the real price for the cost of good sold
        if self.product_id.invoice_policy == "delivery":
            for s_line in self.sale_line_ids:
                # qtys already invoiced
                qty_done = sum([x.uom_id._compute_quantity(x.quantity, x.product_id.uom_id) for x in s_line.invoice_lines if x.invoice_id.state in ('open', 'paid')])
                quantity = self.uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
                # Put moves in fixed order by date executed
                moves = self.env['stock.move']
                moves |= s_line.move_ids
                moves.sorted(lambda x: x.date)
                # Go through all the moves and do nothing until you get to qty_done
                # Beyond qty_done we need to calculate the average of the price_unit
                # on the moves we encounter.
                average_price_unit = self._compute_average_price(qty_done, quantity, moves)
                price_unit = average_price_unit or price_unit
                price_unit = self.product_id.uom_id._compute_price(price_unit, self.uom_id)
        return price_unit

    def _compute_average_price(self, qty_done, quantity, moves):
        average_price_unit = 0
        qty_delivered = 0
        invoiced_qty = 0
        for move in moves:
            if move.state != 'done':
                continue
            invoiced_qty += move.product_qty
            if invoiced_qty <= qty_done:
                continue
            qty_to_consider = move.product_qty
            if invoiced_qty - move.product_qty < qty_done:
                qty_to_consider = invoiced_qty - qty_done
            qty_to_consider = min(qty_to_consider, quantity - qty_delivered)
            qty_delivered += qty_to_consider
            average_price_unit = (average_price_unit * (qty_delivered - qty_to_consider) + (-1 * move.price_unit) * qty_to_consider) / qty_delivered
            if qty_delivered == quantity:
                break
        return average_price_unit
