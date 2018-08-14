# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare

from odoo.exceptions import UserError

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    purchase_id = fields.Many2one(
        comodel_name='purchase.order',
        string='Add Purchase Order',
        readonly=True, states={'draft': [('readonly', False)]},
        help='Encoding help. When selected, the associated purchase order lines are added to the vendor bill. Several PO can be selected.'
    )

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

        domain = [('invoice_status', '=', 'to invoice')]
        if self.partner_id:
            domain += [('partner_id', 'child_of', self.partner_id.id)]
        if purchase_ids:
            domain += [('id', 'not in', purchase_ids.ids)]
        result['domain'] = {'purchase_id': domain}
        return result

    def _prepare_invoice_line_from_po_line(self, line):
        if line.product_id.purchase_method == 'purchase':
            qty = line.product_qty - line.qty_invoiced
        else:
            qty = line.qty_received - line.qty_invoiced
        if float_compare(qty, 0.0, precision_rounding=line.product_uom.rounding) <= 0:
            qty = 0.0
        taxes = line.taxes_id
        invoice_line_tax_ids = line.order_id.fiscal_position_id.map_tax(taxes, line.product_id, line.order_id.partner_id)
        invoice_line = self.env['account.invoice.line']
        data = {
            'purchase_line_id': line.id,
            'name': line.order_id.name+': '+line.name,
            'origin': line.order_id.origin,
            'uom_id': line.product_uom.id,
            'product_id': line.product_id.id,
            'account_id': invoice_line.with_context({'journal_id': self.journal_id.id, 'type': 'in_invoice'})._default_account(),
            'price_unit': line.order_id.currency_id.with_context(date=self.date or self.date_invoice).compute(line.price_unit, self.currency_id, round=False),
            'quantity': qty,
            'discount': 0.0,
            'account_analytic_id': line.account_analytic_id.id,
            'analytic_tag_ids': line.analytic_tag_ids.ids,
            'invoice_line_tax_ids': invoice_line_tax_ids.ids
        }
        account = invoice_line.get_invoice_line_account('in_invoice', line.product_id, line.order_id.fiscal_position_id, self.env.user.company_id)
        if account:
            data['account_id'] = account.id
        return data

    def _onchange_product_id(self):
        domain = super(AccountInvoice, self)._onchange_product_id()
        if self.purchase_id:
            # Use the purchase uom by default
            self.uom_id = self.product_id.uom_po_id
        return domain

    # Load all unsold PO lines
    @api.onchange('purchase_id')
    def purchase_order_change(self):
        if not self.purchase_id:
            return {}
        if not self.partner_id:
            self.partner_id = self.purchase_id.partner_id.id

        if not self.invoice_line_ids:
            #as there's no invoice line yet, we keep the currency of the PO
            self.currency_id = self.purchase_id.currency_id
        new_lines = self.env['account.invoice.line']
        for line in self.purchase_id.order_line - self.invoice_line_ids.mapped('purchase_line_id'):
            data = self._prepare_invoice_line_from_po_line(line)
            new_line = new_lines.new(data)
            new_line._set_additional_fields(self)
            new_lines += new_line

        self.invoice_line_ids += new_lines
        self.payment_term_id = self.purchase_id.payment_term_id
        self.env.context = dict(self.env.context, from_purchase_order_change=True)
        self.purchase_id = False
        return {}

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        if self.currency_id:
            for line in self.invoice_line_ids.filtered(lambda r: r.purchase_line_id):
                line.price_unit = line.purchase_id.currency_id.with_context(date=self.date or self.date_invoice).compute(line.purchase_line_id.price_unit, self.currency_id, round=False)

    @api.onchange('invoice_line_ids')
    def _onchange_origin(self):
        purchase_ids = self.invoice_line_ids.mapped('purchase_id')
        if purchase_ids:
            self.origin = ', '.join(purchase_ids.mapped('name'))

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        payment_term_id = self.env.context.get('from_purchase_order_change') and self.payment_term_id or False
        res = super(AccountInvoice, self)._onchange_partner_id()
        if payment_term_id:
            self.payment_term_id = payment_term_id
        if not self.env.context.get('default_journal_id') and self.partner_id and self.currency_id and\
                self.type in ['in_invoice', 'in_refund'] and\
                self.currency_id != self.partner_id.property_purchase_currency_id and\
                self.partner_id.property_purchase_currency_id.id:
            journal_domain = [
                ('type', '=', 'purchase'),
                ('company_id', '=', self.company_id.id),
                ('currency_id', '=', self.partner_id.property_purchase_currency_id.id),
            ]
            default_journal_id = self.env['account.journal'].search(journal_domain, limit=1)
            if default_journal_id:
                self.journal_id = default_journal_id
            if self.env.context.get('default_currency_id'):
                self.currency_id = self.env.context['default_currency_id']
        return res

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
        if i_line.product_id and i_line.product_id.valuation == 'real_time' and i_line.product_id.type == 'product':
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
            # calculate and write down the possible price difference between invoice price and product price
            for line in res:
                if line.get('invl_id', 0) == i_line.id and reference_account_id == line['account_id']:
                    # valuation_price unit is always expressed in invoice currency, so that it can always be computed with the good rate
                    valuation_price_unit = company_currency.compute(i_line.product_id.uom_id._compute_price(i_line.product_id.standard_price, i_line.uom_id), inv.currency_id, round=False)
                    line_quantity = line['quantity']

                    if i_line.product_id.cost_method != 'standard' and i_line.purchase_line_id:
                        po_currency = i_line.purchase_id.currency_id
                        #for average/fifo/lifo costing method, fetch real cost price from incomming moves
                        valuation_price_unit = po_currency.with_context(date=inv.date or inv.date_invoice).compute(i_line.purchase_line_id.product_uom._compute_price(i_line.purchase_line_id.price_unit, i_line.uom_id), inv.currency_id, round=False)
                        stock_move_obj = self.env['stock.move']
                        valuation_stock_move = stock_move_obj.search([
                            ('purchase_line_id', '=', i_line.purchase_line_id.id),
                            ('state', '=', 'done'), ('product_qty', '!=', 0.0)
                        ])
                        if self.type == 'in_refund':
                            valuation_stock_move = valuation_stock_move.filtered(lambda m: m._is_out())
                        elif self.type == 'in_invoice':
                            valuation_stock_move = valuation_stock_move.filtered(lambda m: m._is_in())

                        if valuation_stock_move:
                            valuation_price_unit_total = 0
                            valuation_total_qty = 0
                            for val_stock_move in valuation_stock_move:
                                # In case val_stock_move is a return move, its valuation entries have been made with the
                                # currency rate corresponding to the original stock move
                                valuation_date = val_stock_move.origin_returned_move_id.date or val_stock_move.date_expected
                                valuation_price_unit_total += company_currency.with_context(date=valuation_date).compute(abs(val_stock_move.price_unit) * val_stock_move.product_qty, inv.currency_id, round=False)
                                valuation_total_qty += val_stock_move.product_qty
                            valuation_price_unit = valuation_price_unit_total / valuation_total_qty
                            valuation_price_unit = i_line.product_id.uom_id._compute_price(valuation_price_unit, i_line.uom_id)
                            line_quantity = valuation_total_qty

                        elif i_line.product_id.cost_method == 'fifo':
                            # In this condition, we have a real price-valuated product which has not yet been received
                            valuation_price_unit = po_currency.with_context(date=inv.date or inv.date_invoice).compute(i_line.purchase_line_id.price_unit, inv.currency_id, round=False)

                    interim_account_price = valuation_price_unit * line_quantity
                    invoice_cur_prec = inv.currency_id.decimal_places

                    if float_compare(valuation_price_unit, i_line.price_unit, precision_digits=invoice_cur_prec) != 0 and float_compare(line['price_unit'], i_line.price_unit, precision_digits=invoice_cur_prec) == 0:

                        # price with discount and without tax included
                        price_unit = i_line.price_unit * (1 - (i_line.discount or 0.0) / 100.0)
                        tax_ids = []
                        if line['tax_ids']:
                            #line['tax_ids'] is like [(4, tax_id, None), (4, tax_id2, None)...]
                            taxes = self.env['account.tax'].browse([x[1] for x in line['tax_ids']])
                            price_unit = taxes.compute_all(price_unit, currency=inv.currency_id, quantity=1.0)['total_excluded']
                            for tax in taxes:
                                tax_ids.append((4, tax.id, None))
                                for child in tax.children_tax_ids:
                                    if child.type_tax_use != 'none':
                                        tax_ids.append((4, child.id, None))

                        price_before = line.get('price', 0.0)
                        price_unit_val_dif = price_unit - valuation_price_unit

                        price_val_dif = price_before - interim_account_price
                        if inv.currency_id.compare_amounts(i_line.price_unit, valuation_price_unit) != 0 and acc:
                            # If the unit prices have not changed and we have a
                            # valuation difference, it means this difference is due to exchange rates,
                            # so we don't create anything, the exchange rate entries will
                            # be processed automatically by the rest of the code.
                            diff_res.append({
                                'type': 'src',
                                'name': i_line.name[:64],
                                'price_unit': inv.currency_id.round(price_unit_val_dif),
                                'quantity': line_quantity,
                                'price': inv.currency_id.round(price_val_dif),
                                'account_id': acc,
                                'product_id': line['product_id'],
                                'uom_id': line['uom_id'],
                                'account_analytic_id': line['account_analytic_id'],
                                'tax_ids': tax_ids,
                                })
            return diff_res
        return []

    @api.model
    def create(self, vals):
        invoice = super(AccountInvoice, self).create(vals)
        purchase = invoice.invoice_line_ids.mapped('purchase_line_id.order_id')
        if purchase and not invoice.refund_invoice_id:
            message = _("This vendor bill has been created from: %s") % (",".join(["<a href=# data-oe-model=purchase.order data-oe-id="+str(order.id)+">"+order.name+"</a>" for order in purchase]))
            invoice.message_post(body=message)
        return invoice

    @api.multi
    def write(self, vals):
        result = True
        for invoice in self:
            purchase_old = invoice.invoice_line_ids.mapped('purchase_line_id.order_id')
            result = result and super(AccountInvoice, invoice).write(vals)
            purchase_new = invoice.invoice_line_ids.mapped('purchase_line_id.order_id')
            #To get all po reference when updating invoice line or adding purchase order reference from vendor bill.
            purchase = (purchase_old | purchase_new) - (purchase_old & purchase_new)
            if purchase:
                message = _("This vendor bill has been modified from: %s") % (",".join(["<a href=# data-oe-model=purchase.order data-oe-id="+str(order.id)+">"+order.name+"</a>" for order in purchase]))
                invoice.message_post(body=message)
        return result

    def _get_last_step_stock_moves(self):
        """ Overridden from stock_account.
        Returns the stock moves associated to this invoice."""
        rslt = super(AccountInvoice, self)._get_last_step_stock_moves()
        for invoice in self.filtered(lambda x: x.type == 'in_invoice'):
            rslt += invoice.mapped('invoice_line_ids.purchase_line_id.move_ids').filtered(lambda x: x.state == 'done' and x.location_id.usage == 'supplier')
        for invoice in self.filtered(lambda x: x.type == 'in_refund'):
            rslt += invoice.mapped('invoice_line_ids.purchase_line_id.move_ids').filtered(lambda x: x.state == 'done' and x.location_dest_id.usage == 'supplier')
        return rslt


class AccountInvoiceLine(models.Model):
    """ Override AccountInvoice_line to add the link to the purchase order line it is related to"""
    _inherit = 'account.invoice.line'

    purchase_line_id = fields.Many2one('purchase.order.line', 'Purchase Order Line', ondelete='set null', index=True, readonly=True)
    purchase_id = fields.Many2one('purchase.order', related='purchase_line_id.order_id', string='Purchase Order', store=False, readonly=True, related_sudo=False,
        help='Associated Purchase Order. Filled in automatically when a PO is chosen on the vendor bill.')
