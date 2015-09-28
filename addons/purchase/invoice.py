# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.tools.float_utils import float_compare


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    purchase_id = fields.Many2one('purchase.order', string='Purchase Order', domain=[('invoice_status', '=', 'to invoice')])

    # Load all unsold PO lines
    @api.onchange('purchase_id')
    def purchase_order_change(self):
        result = []
        if not self.purchase_id:
            return {}
        if not self.partner_id:
            self.partner_id = self.purchase_id.partner_id.id

        # Keep existing lines. We want to be able to add several PO on the same invoice.
        for line in self.invoice_line_ids:
            result.append({
                'purchase_line_id': line.purchase_line_id.id,
                'name': line.name,
                'origin': line.origin,
                'uom_id': line.uom_id.id,
                'product_id': line.product_id.id,
                'account_id': line.account_id.id,
                'price_unit': line.price_unit,
                'quantity': line.quantity,
                'discount': line.discount,
                'account_analytic_id': line.account_analytic_id.id,
                'invoice_line_tax_ids': line.invoice_line_tax_ids.ids,
            })

        for line in self.purchase_id.order_line:
            if line.product_id.purchase_method == 'purchase':
                qty = line.product_qty - line.qty_invoiced
            else:
                qty = line.qty_received - line.qty_invoiced
            if float_compare(qty, 0.0, precision_rounding=line.product_uom.rounding) <= 0:
                qty = 0.0
            account = self.env['account.invoice.line'].get_invoice_line_account('in_invoice', line.product_id, self.purchase_id.fiscal_position_id, self.env.user.company_id)
            taxes = line.taxes_id or line.product_id.supplier_taxes_id
            invoice_line_tax_ids = self.purchase_id.fiscal_position_id.map_tax(taxes)
            result.append({
                'purchase_line_id': line.id,
                'name': line.name,
                'origin': self.purchase_id.origin,
                'uom_id': line.product_uom.id,
                'product_id': line.product_id.id,
                'account_id': account.id,
                'price_unit': line.price_unit,
                'quantity': qty,
                'discount': 0.0,
                'account_analytic_id': line.account_analytic_id.id,
                'invoice_line_tax_ids': invoice_line_tax_ids.ids
            })
        self.invoice_line_ids = result
        return {}

    @api.model
    def invoice_line_move_line_get(self):
        res = super(AccountInvoice, self).invoice_line_move_line_get()

        if self.env.user.company_id.anglo_saxon_accounting:
            if self.type in ['in_invoice', 'in_refund']:
                for i_line in self.invoice_line_ids:
                    res.extend(self._anglo_saxon_purchase_move_lines(i_line, res))
        return res

    @api.model
    def _anglo_saxon_purchase_move_lines(self, i_line, res):
        """Return the additional move lines for purchase invoices and refunds.

        i_line: An account.invoice.line object.
        res: The move line entries produced so far by the parent move_line_get.
        """
        inv = i_line.invoice_id
        company_currency = inv.company_id.currency_id
        if i_line.product_id and i_line.product_id.valuation == 'real_time':
            if i_line.product_id.type in ('product', 'consu'):
                # get the price difference account at the product
                acc = i_line.product_id.property_account_creditor_price_difference and i_line.product_id.property_account_creditor_price_difference.id
                if not acc:
                    # if not found on the product get the price difference account at the category
                    acc = i_line.product_id.categ_id.property_account_creditor_price_difference_categ and i_line.product_id.categ_id.property_account_creditor_price_difference_categ.id
                a = None

                # oa will be the stock input account
                # first check the product, if empty check the category
                oa = i_line.product_id.property_stock_account_input and i_line.product_id.property_stock_account_input.id
                if not oa:
                    oa = i_line.product_id.categ_id.property_stock_account_input_categ_id and i_line.product_id.categ_id.property_stock_account_input_categ_id.id
                if oa:
                    # get the fiscal position
                    fpos = i_line.invoice_id.fiscal_position_id
                    a = fpos.map_account(oa)
                diff_res = []
                account_prec = inv.company_id.currency_id.decimal_places
                # calculate and write down the possible price difference between invoice price and product price
                for line in res:
                    if line.get('invl_id', 0) == i_line.id and a == line['account_id']:
                        uom = i_line.product_id.uom_id
                        valuation_price_unit = uom._compute_price(i_line.product_id.standard_price, i_line.uom_id.id)
                        if i_line.product_id.cost_method != 'standard' and i_line.purchase_line_id:
                            #for average/fifo/lifo costing method, fetch real cost price from incomming moves
                            stock_move_obj = self.env['stock.move']
                            valuation_stock_move = stock_move_obj.search([('purchase_line_id', '=', i_line.purchase_line_id.id)], limit=1)
                            if valuation_stock_move:
                                valuation_price_unit = valuation_stock_move[0].price_unit
                        if inv.currency_id.id != company_currency.id:
                            valuation_price_unit = company_currency.compute(inv.currency_id, valuation_price_unit, context={'date': inv.date_invoice})
                        if valuation_price_unit != i_line.price_unit and line['price_unit'] == i_line.price_unit and acc:
                            # price with discount and without tax included
                            price_unit = self.env['account.tax'].compute_all(line['taxes'], i_line.price_unit * (1-(i_line.discount or 0.0)/100.0),\
                                inv.currency_id.id, line['quantity'])['total_excluded']
                            price_line = round(valuation_price_unit * line['quantity'], account_prec)
                            price_diff = round(price_unit - price_line, account_prec)
                            line.update({'price': price_line})
                            diff_res.append({
                                'type': 'src',
                                'name': i_line.name[:64],
                                'price_unit': round(price_diff / line['quantity'], account_prec),
                                'quantity': line['quantity'],
                                'price': price_diff,
                                'account_id': acc,
                                'product_id': line['product_id'],
                                'uom_id': line['uom_id'],
                                'account_analytic_id': line['account_analytic_id'],
                                'taxes': line.get('taxes', []),
                                })
                return diff_res
        return []


class AccountInvoiceLine(models.Model):
    """ Override AccountInvoice_line to add the link to the purchase order line it is related to"""
    _inherit = 'account.invoice.line'
    purchase_line_id = fields.Many2one('purchase.order.line', 'Purchase Order Line', ondelete='set null', select=True, readonly=True)

