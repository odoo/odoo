# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

import logging

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.model
    def invoice_line_move_line_get(self):
        res = super(AccountInvoice, self).invoice_line_move_line_get()
        if self.company_id.anglo_saxon_accounting and self.type in ('out_invoice', 'out_refund'):
            for i_line in self.invoice_line_ids:
                res.extend(self._anglo_saxon_sale_move_lines(i_line))
        return res

    @api.model
    def _anglo_saxon_sale_move_lines(self, i_line):
        """Return the additional move lines for sales invoices and refunds.

        i_line: An account.invoice.line object.
        res: The move line entries produced so far by the parent move_line_get.
        """
        inv = i_line.invoice_id
        company_currency = inv.company_id.currency_id

        if i_line.product_id.type == 'product' and i_line.product_id.valuation == 'real_time':
            fpos = i_line.invoice_id.fiscal_position_id
            accounts = i_line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=fpos)
            # debit account dacc will be the output account
            dacc = accounts['stock_output'].id
            # credit account cacc will be the expense account
            cacc = accounts['expense'].id
            if dacc and cacc:
                price_unit = i_line._get_anglo_saxon_price_unit()
                if inv.currency_id != company_currency:
                    currency_id = inv.currency_id.id
                    amount_currency = i_line._get_price(company_currency, price_unit)
                else:
                    currency_id = False
                    amount_currency = False
                return [
                    {
                        'type': 'src',
                        'name': i_line.name[:64],
                        'price_unit': price_unit,
                        'quantity': i_line.quantity,
                        'price': price_unit * i_line.quantity,
                        'currency_id': currency_id,
                        'amount_currency': amount_currency,
                        'account_id':dacc,
                        'product_id':i_line.product_id.id,
                        'uom_id':i_line.uom_id.id,
                        'account_analytic_id': i_line.account_analytic_id.id,
                        'analytic_tag_ids': i_line.analytic_tag_ids.ids and [(6, 0, i_line.analytic_tag_ids.ids)] or False,
                    },

                    {
                        'type': 'src',
                        'name': i_line.name[:64],
                        'price_unit': price_unit,
                        'quantity': i_line.quantity,
                        'price': -1 * price_unit * i_line.quantity,
                        'currency_id': currency_id,
                        'amount_currency': -1 * amount_currency,
                        'account_id':cacc,
                        'product_id':i_line.product_id.id,
                        'uom_id':i_line.uom_id.id,
                        'account_analytic_id': i_line.account_analytic_id.id,
                        'analytic_tag_ids': i_line.analytic_tag_ids.ids and [(6, 0, i_line.analytic_tag_ids.ids)] or False,
                    },
                ]
        return []

    def _get_related_stock_moves(self):
        """ To be overridden for customer invoices and vendor bills in order to
        return the stock moves related to this invoice.
        """
        return self.env['stock.move']

    def _get_products_set(self):
        """ Returns a recordset of the products contained in this invoice's lines
        """
        return self.mapped('invoice_line_ids.product_id')

    def _get_anglosaxon_interim_account(self, product):
        """ Return the interim account used in anglosaxon accounting for
        this invoice"""
        if self.type in ('out_invoice', 'out_refund'):
            return product.product_tmpl_id._get_product_accounts()['stock_output']
        elif self.type in ('in_invoice', 'in_refund'):
            return product.product_tmpl_id.get_product_accounts()['stock_input']

        return None

    def invoice_validate(self):
        super(AccountInvoice, self).invoice_validate()
        self.anglo_saxon_reconcile_valuation()

    def anglo_saxon_reconcile_valuation(self):
        """ Reconciles the entries made in the interim accounts in anglosaxon accounting,
        reconciling stock valuation move lines with the invoice's.
        """
        for invoice in self:
            if invoice.company_id.anglo_saxon_accounting:
                invoice_stock_moves_id_list = self._get_related_stock_moves().ids
                for product in self._get_products_set():
                    if product.valuation == 'real_time' and product.cost_method == 'real':
                        # We first get the invoice's move lines ...
                        product_interim_account = invoice._get_anglosaxon_interim_account(product)
                        to_reconcile = self.env['account.move.line'].search([('move_id','=',invoice.move_id.id), ('product_id','=',product.id), ('account_id','=',product_interim_account.id), ('reconciled','=',False)])

                        # And then the stock valuation ones.
                        product_stock_moves = self.env['stock.move'].search([('id','in',invoice_stock_moves_id_list), ('product_id','=',product.id)])

                        for valuation_line in product_stock_moves.mapped('stock_account_valuation_account_move_id.line_ids'):
                            if valuation_line.account_id == product_interim_account and not valuation_line.reconciled:
                                to_reconcile += valuation_line

                        if to_reconcile:
                            to_reconcile.reconcile()

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    def _get_anglo_saxon_price_unit(self):
        self.ensure_one()
        price = self.product_id.standard_price
        if not self.uom_id or self.product_id.uom_id == self.uom_id:
            return price
        else:
            return self.product_id.uom_id._compute_price(price, self.uom_id)

    def _get_price(self, company_currency, price_unit):
        if self.invoice_id.currency_id.id != company_currency.id:
            price = company_currency.with_context(date=self.invoice_id.date_invoice).compute(price_unit * self.quantity, self.invoice_id.currency_id)
        else:
            price = price_unit * self.quantity
        return self.invoice_id.currency_id.round(price)

    def get_invoice_line_account(self, type, product, fpos, company):
        if company.anglo_saxon_accounting and type in ('in_invoice', 'in_refund') and product and product.type == 'product':
            accounts = product.product_tmpl_id.get_product_accounts(fiscal_pos=fpos)
            if product.categ_id.property_valuation != 'manual_periodic' and accounts['stock_input']:
                return accounts['stock_input']
        return super(AccountInvoiceLine, self).get_invoice_line_account(type, product, fpos, company)
