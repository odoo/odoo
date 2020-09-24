# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields

import logging

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.model
    def invoice_line_move_line_get(self):
        res = super(AccountInvoice, self).invoice_line_move_line_get()
        if self.company_id.anglo_saxon_accounting and self.type in ('out_invoice', 'out_refund'):
            for i_line in self.invoice_line_ids:
                if not i_line._get_sale_move_owner():
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
        price_unit = i_line._get_anglo_saxon_price_unit()
        if inv.currency_id != company_currency:
            currency = inv.currency_id
            amount_currency = i_line._get_price(company_currency, price_unit)
        else:
            currency = False
            amount_currency = False

        product = i_line.product_id.with_context(force_company=self.company_id.id)
        return self.env['product.product']._anglo_saxon_sale_move_lines(i_line.name, product, i_line.uom_id, i_line.quantity, price_unit, currency=currency, amount_currency=amount_currency, fiscal_position=inv.fiscal_position_id, account_analytic=i_line.account_analytic_id, analytic_tags=i_line.analytic_tag_ids)

    def _get_last_step_stock_moves(self):
        """ To be overridden for customer invoices and vendor bills in order to
        return the stock moves related to the invoices in self.
        """
        return self.env['stock.move']

    def _get_products_set(self):
        """ Returns a recordset of the products contained in this invoice's lines """
        return self.mapped('invoice_line_ids.product_id')

    def _get_anglosaxon_interim_account(self, product):
        """ Returns the interim account used in anglosaxon accounting for
        this invoice"""
        if self.type in ('out_invoice', 'out_refund'):
            return product.product_tmpl_id._get_product_accounts()['stock_output']
        return product.product_tmpl_id.get_product_accounts()['stock_input']

    def invoice_validate(self):
        res = super(AccountInvoice, self).invoice_validate()
        self.filtered(lambda i: i.company_id.anglo_saxon_accounting)._anglo_saxon_reconcile_valuation()
        return res

    def _anglo_saxon_reconcile_valuation(self, product=False):
        """ Reconciles the entries made in the interim accounts in anglosaxon accounting,
        reconciling stock valuation move lines with the invoice's.
        """
        for invoice in self:
            if invoice.company_id.anglo_saxon_accounting:
                stock_moves = invoice._get_last_step_stock_moves()
                product_set = product or invoice._get_products_set()
                for prod in product_set:
                    product_interim_account = invoice._get_anglosaxon_interim_account(prod)
                    if prod.valuation == 'real_time' and stock_moves and product_interim_account.reconcile:
                        # We first get the invoices move lines (taking the invoice and the previous ones into account)...
                        to_reconcile = self.env['account.move.line'].search([
                            ('move_id', '=', invoice.move_id.id),
                            ('product_id', '=', prod.id),
                            ('account_id','=', product_interim_account.id),
                            ('reconciled','=', False)
                        ])

                        # And then the stock valuation ones.
                        product_stock_moves = stock_moves.filtered(lambda s: s.product_id.id == prod.id)
                        for valuation_line in product_stock_moves.mapped('account_move_ids.line_ids'):
                            if valuation_line.account_id == product_interim_account and not valuation_line.reconciled:
                                to_reconcile += valuation_line

                        if to_reconcile:
                            to_reconcile.reconcile()


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    def _get_anglo_saxon_price_unit(self):
        self.ensure_one()
        if not self.product_id:
            return self.price_unit
        return self.product_id._get_anglo_saxon_price_unit(uom=self.uom_id)

    def _get_price(self, company_currency, price_unit):
        if self.invoice_id.currency_id.id != company_currency.id:
            price = company_currency._convert(
                price_unit * self.quantity,
                self.invoice_id.currency_id,
                self.invoice_id.company_id,
                self.invoice_id.date_invoice or fields.Date.today())
        else:
            price = price_unit * self.quantity
        return self.invoice_id.currency_id.round(price)

    def _get_sale_move_owner(self):
        # to override in sale_stock
        self.ensure_one()
        return False

    def _get_purchase_move_owner(self):
        # to override in purchase_stock
        return False

    def get_invoice_line_account(self, type, product, fpos, company):
        if company.anglo_saxon_accounting and type in ('in_invoice', 'in_refund') and product and (product.type == 'product' or product.type == 'consu' and product._is_phantom_bom()) and not self._get_purchase_move_owner():
            accounts = product.product_tmpl_id.get_product_accounts(fiscal_pos=fpos)
            if accounts['stock_input']:
                return accounts['stock_input']
        return super(AccountInvoiceLine, self).get_invoice_line_account(type, product, fpos, company)
