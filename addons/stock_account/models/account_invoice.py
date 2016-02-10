# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    def _get_anglo_saxon_price_unit(self):
        self.ensure_one()
        return self.product_id.standard_price

    def _get_price(self, invoice, company_currency, price_unit):
        self.ensure_one()
        if invoice.currency_id != company_currency:
            price = company_currency.with_context({'date': invoice.date_invoice}).compute(price_unit * self.quantity, invoice.currency_id)
        else:
            price = price_unit * self.quantity
        return round(price, invoice.currency_id.decimal_places)

    @api.model
    def get_invoice_line_account(self, inv_type, product, fpos, company):
        if company.anglo_saxon_accounting and inv_type in ('in_invoice', 'in_refund') and product and product.type == 'product':
            accounts = product.product_tmpl_id.get_product_accounts(fiscal_pos=fpos)
            return accounts['stock_input']
        return super(AccountInvoiceLine, self).get_invoice_line_account(inv_type, product, fpos, company)


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.model
    def invoice_line_move_line_get(self):
        res = super(AccountInvoice,self).invoice_line_move_line_get()
        if self.company_id.anglo_saxon_accounting and self.type in ('out_invoice', 'out_refund'):
            res.extend(self._anglo_saxon_sale_move_lines(self.invoice_line_ids))
        return res

    def _anglo_saxon_sale_move_lines(self, i_lines):
        """Return the additional move lines for sales invoices and refunds.

        i_lines: An account.invoice.line object.
        res: The move line entries produced so far by the parent move_line_get.
        """
        res = []
        for i_line in i_lines.filtered(lambda i: i.product_id.type == 'product' and i.product_id.valuation == 'real_time'):
            invoice = i_line.invoice_id
            accounts = i_line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=invoice.fiscal_position_id)
            # debit account debit_acc will be the output account
            debit_acc = accounts.get('stock_output')
            # credit account credit_acc will be the expense account
            credit_acc = accounts.get('expense')
            if debit_acc and credit_acc:
                price_unit = i_line._get_anglo_saxon_price_unit()
                price = i_line._get_price(invoice, invoice.company_id.currency_id, price_unit)
                res.extend([{
                    'type': 'src',
                    'name': i_line.name[:64],
                    'price_unit': price_unit,
                    'quantity': i_line.quantity,
                    'price': price,
                    'account_id': debit_acc.id,
                    'product_id': i_line.product_id.id,
                    'uom_id': i_line.uom_id.id,
                    'account_analytic_id': False
                }, {
                    'type': 'src',
                    'name': i_line.name[:64],
                    'price_unit': price_unit,
                    'quantity': i_line.quantity,
                    'price': -1 * price,
                    'account_id': credit_acc.id,
                    'product_id': i_line.product_id.id,
                    'uom_id': i_line.uom_id.id,
                    'account_analytic_id': False
                }])
        return res
