# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models
from openerp.tools.float_utils import float_compare


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    purchase_id = fields.Many2one('purchase.order', string='Add Purchase Order',
        help='Encoding help. When selected, the associated purchase order lines are added to the vendor bill. Several PO can be selected.')

    @api.onchange('state', 'partner_id', 'invoice_line_ids')
    def _onchange_allowed_purchase_ids(self):
        '''
        The purpose of the method is to define a domain for the available
        purchase orders.
        '''
        result = {}

        # A PO can be selected only if at least one PO line is not already in the invoice
        purchase_line_ids = self.invoice_line_ids.mapped('purchase_line_id')
        purchase_ids = self.invoice_line_ids.mapped('purchase_id').filtered(lambda r: r.order_line <= purchase_line_ids)

        result['domain'] = {'purchase_id': [
            ('invoice_status', '=', 'to invoice'),
            ('partner_id', 'child_of', self.partner_id.id),
            ('id', 'not in', purchase_ids.ids),
            ]}
        return result

    # Load all unsold PO lines
    @api.onchange('purchase_id')
    def purchase_order_change(self):
        if not self.purchase_id:
            return {}
        if not self.partner_id:
            self.partner_id = self.purchase_id.partner_id.id

        new_lines = self.env['account.invoice.line']
        for line in self.purchase_id.order_line:
            # Load a PO line only once
            if line in self.invoice_line_ids.mapped('purchase_line_id'):
                continue
            if line.product_id.purchase_method == 'purchase':
                qty = line.product_qty - line.qty_invoiced
            else:
                qty = line.qty_received - line.qty_invoiced
            if float_compare(qty, 0.0, precision_rounding=line.product_uom.rounding) <= 0:
                qty = 0.0
            taxes = line.taxes_id or line.product_id.supplier_taxes_id
            invoice_line_tax_ids = self.purchase_id.fiscal_position_id.map_tax(taxes)
            data = {
                'purchase_line_id': line.id,
                'name': line.name,
                'origin': self.purchase_id.origin,
                'uom_id': line.product_uom.id,
                'product_id': line.product_id.id,
                'account_id': self.env['account.invoice.line'].with_context({'journal_id': self.journal_id.id, 'type': 'in_invoice'})._default_account(),
                'price_unit': line.order_id.currency_id.compute(line.price_unit, self.currency_id, round=False),
                'quantity': qty,
                'discount': 0.0,
                'account_analytic_id': line.account_analytic_id.id,
                'invoice_line_tax_ids': invoice_line_tax_ids.ids
            }
            account = new_lines.get_invoice_line_account('in_invoice', line.product_id, self.purchase_id.fiscal_position_id, self.env.user.company_id)
            if account:
                data['account_id'] = account.id
            new_line = new_lines.new(data)
            new_line._set_additional_fields(self)
            new_lines += new_line

        self.invoice_line_ids += new_lines
        self.purchase_id = False
        return {}

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        if self.currency_id:
            for line in self.invoice_line_ids.filtered(lambda r: r.purchase_line_id):
                line.price_unit = line.purchase_id.currency_id.compute(line.purchase_line_id.price_unit, self.currency_id, round=False)

    @api.onchange('invoice_line_ids')
    def _onchange_origin(self):
        purchase_ids = self.invoice_line_ids.mapped('purchase_id')
        if purchase_ids:
            self.origin = ', '.join(purchase_ids.mapped('name'))

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
                # get the fiscal position
                fpos = i_line.invoice_id.fiscal_position_id
                # get the price difference account at the product
                acc = i_line.product_id.property_account_creditor_price_difference
                if not acc:
                    # if not found on the product get the price difference account at the category
                    acc = i_line.product_id.categ_id.property_account_creditor_price_difference_categ
                acc = fpos.map_account(acc).id
                # reference_account_id is the stock input account
                reference_account_id = i_line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=fpos)['stock_input'].id
                diff_res = []
                account_prec = inv.company_id.currency_id.decimal_places
                product_prec = self.env['decimal.precision'].precision_get('Product Price')
                # calculate and write down the possible price difference between invoice price and product price
                for line in res:
                    if line.get('invl_id', 0) == i_line.id and reference_account_id == line['account_id']:
                        valuation_price_unit = self.env['product.uom']._compute_price(i_line.product_id.uom_id.id, i_line.product_id.standard_price, i_line.uom_id.id)
                        if i_line.product_id.cost_method != 'standard' and i_line.purchase_line_id:
                            #for average/fifo/lifo costing method, fetch real cost price from incomming moves
                            stock_move_obj = self.env['stock.move']
                            valuation_stock_move = stock_move_obj.search([('purchase_line_id', '=', i_line.purchase_line_id.id), ('state', '=', 'done')])
                            if valuation_stock_move:
                                valuation_price_unit_total = 0
                                valuation_total_qty = 0
                                for val_stock_move in valuation_stock_move:
                                    valuation_price_unit_total += val_stock_move.price_unit * val_stock_move.product_qty
                                    valuation_total_qty += val_stock_move.product_qty
                                valuation_price_unit = valuation_price_unit_total / valuation_total_qty
                        if inv.currency_id.id != company_currency.id:
                            valuation_price_unit = company_currency.with_context(date=inv.date_invoice).compute(valuation_price_unit, inv.currency_id, round=False)
                        if float_compare(valuation_price_unit, i_line.price_unit, precision_digits=product_prec) != 0\
                                and float_compare(line['price_unit'], i_line.price_unit, precision_digits=product_prec) == 0\
                                and acc:
                            # price with discount and without tax included
                            price_unit = i_line.price_unit * (1 - (i_line.discount or 0.0) / 100.0)
                            if line['tax_ids']:
                                #line['tax_ids'] is like [(4, tax_id, None), (4, tax_id2, None)...]
                                taxes = self.env['account.tax'].browse([x[1] for x in line['tax_ids']])
                                price_unit = taxes.with_context(round=False).compute_all(price_unit, currency=inv.currency_id, quantity=1.0)['total_excluded']
                            line.update({'price': round(valuation_price_unit * line['quantity'], account_prec)})
                            diff_res.append({
                                'type': 'src',
                                'name': i_line.name[:64],
                                'price_unit': round(price_unit - valuation_price_unit, product_prec),
                                'quantity': line['quantity'],
                                'price': round((price_unit - valuation_price_unit) * line['quantity'], account_prec),
                                'account_id': acc,
                                'product_id': line['product_id'],
                                'uom_id': line['uom_id'],
                                'account_analytic_id': line['account_analytic_id'],
                                })
                return diff_res
        return []


class AccountInvoiceLine(models.Model):
    """ Override AccountInvoice_line to add the link to the purchase order line it is related to"""
    _inherit = 'account.invoice.line'

    purchase_line_id = fields.Many2one('purchase.order.line', 'Purchase Order Line', ondelete='set null', select=True, readonly=True)
    purchase_id = fields.Many2one('purchase.order', related='purchase_line_id.order_id', string='Purchase Order', store=False, readonly=True,
        help='Associated Purchase Order. Filled in automatically when a PO is chosen on the vendor bill.')
