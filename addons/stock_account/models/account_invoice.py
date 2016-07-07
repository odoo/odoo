# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api
from openerp.osv import osv

import logging

_logger = logging.getLogger(__name__)


class account_invoice(osv.osv):
    _inherit = "account.invoice"

    @api.model
    def invoice_line_move_line_get(self):
        res = super(account_invoice,self).invoice_line_move_line_get()
        if self.company_id.anglo_saxon_accounting:
            if self.type in ('out_invoice','out_refund'):
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
        company_currency = inv.company_id.currency_id.id

        if i_line.product_id.type  == 'product' and i_line.product_id.valuation == 'real_time':
            fpos = i_line.invoice_id.fiscal_position_id
            accounts = i_line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=fpos)
            # debit account dacc will be the output account
            dacc = accounts['stock_output'].id
            # credit account cacc will be the expense account
            cacc = accounts['expense'].id
            if dacc and cacc:
                price_unit = i_line._get_anglo_saxon_price_unit()
                return [
                    {
                        'type':'src',
                        'name': i_line.name[:64],
                        'price_unit': price_unit,
                        'quantity': i_line.quantity,
                        'price': i_line._get_price(company_currency, price_unit),
                        'account_id':dacc,
                        'product_id':i_line.product_id.id,
                        'uom_id':i_line.uom_id.id,
                        'account_analytic_id': False,
                    },

                    {
                        'type':'src',
                        'name': i_line.name[:64],
                        'price_unit': price_unit,
                        'quantity': i_line.quantity,
                        'price': -1 * i_line._get_price(company_currency, price_unit),
                        'account_id':cacc,
                        'product_id':i_line.product_id.id,
                        'uom_id':i_line.uom_id.id,
                        'account_analytic_id': False,
                    },
                ]
        return []


class account_invoice_line(osv.osv):
    _inherit = "account.invoice.line"

    def _get_anglo_saxon_price_unit(self):
        self.ensure_one()
        return self.product_id.standard_price

    def _get_price(self, cr, uid, ids, company_currency, price_unit, context=None):
        line = self.browse(cr, uid, ids, context=context)[0]
        cur_obj = self.pool.get('res.currency')
        if line.invoice_id.currency_id.id != company_currency:
            price = cur_obj.compute(cr, uid, company_currency, line.invoice_id.currency_id.id, price_unit * line.quantity, context={'date': line.invoice_id.date_invoice})
        else:
            price = price_unit * line.quantity
        return round(price, line.invoice_id.currency_id.decimal_places)

    def get_invoice_line_account(self, type, product, fpos, company):
        if company.anglo_saxon_accounting and type in ('in_invoice', 'in_refund') and product and product.type == 'product':
            accounts = product.product_tmpl_id.get_product_accounts(fiscal_pos=fpos)
            return accounts['stock_input']
        return super(account_invoice_line, self).get_invoice_line_account(type, product, fpos, company)