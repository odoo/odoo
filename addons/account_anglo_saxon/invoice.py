##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 
#    2004-2010 Tiny SPRL (<http://tiny.be>). 
#    2009-2010 Veritos (http://veritos.nl).
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

from openerp.osv import osv, fields
from openerp.tools.float_utils import float_round as round

class account_invoice_line(osv.osv):
    _inherit = "account.invoice.line"

    _columns = {
        'move_id': fields.many2one('stock.move', string="Move line", help="If the invoice was generated from a stock.picking, reference to the related move line."),
    }

    def move_line_get(self, cr, uid, invoice_id, context=None):
        res = super(account_invoice_line,self).move_line_get(cr, uid, invoice_id, context=context)
        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=context)
        if inv.type in ('out_invoice','out_refund'):
            for i_line in inv.invoice_line:
                res.extend(self._anglo_saxon_sale_move_lines(cr, uid, i_line, res, context=context))
        elif inv.type in ('in_invoice','in_refund'):
            for i_line in inv.invoice_line:
                res.extend(self._anglo_saxon_purchase_move_lines(cr, uid, i_line, res, context=context))
        return res


    def product_id_change(self, cr, uid, ids, product, uom_id, qty=0, name='', type='out_invoice', partner_id=False, fposition_id=False, price_unit=False, currency_id=False, company_id=None, context=None):
        fiscal_pool = self.pool.get('account.fiscal.position')
        res = super(account_invoice_line, self).product_id_change(cr, uid, ids, product, uom_id, qty, name, type, partner_id, fposition_id, price_unit, currency_id, company_id, context)
        if not product:
            return res
        if type in ('in_invoice','in_refund'):
            product_obj = self.pool.get('product.product').browse(cr, uid, product, context=context)
            oa = product_obj.property_stock_account_input and product_obj.property_stock_account_input.id
            if not oa:
                oa = product_obj.categ_id.property_stock_account_input_categ and product_obj.categ_id.property_stock_account_input_categ.id
            if oa:
                fpos = fposition_id and fiscal_pool.browse(cr, uid, fposition_id, context=context) or False
                a = fiscal_pool.map_account(cr, uid, fpos, oa)
                res['value'].update({'account_id':a})
        return res

    def _get_price(self, cr, uid, inv, company_currency, i_line, price_unit):
            cur_obj = self.pool.get('res.currency')
            decimal_precision = self.pool.get('decimal.precision')
            if inv.currency_id.id != company_currency:
                price = cur_obj.compute(cr, uid, company_currency, inv.currency_id.id, price_unit * i_line.quantity, context={'date': inv.date_invoice})
            else:
                price = price_unit * i_line.quantity
            return round(price, decimal_precision.precision_get(cr, uid, 'Account'))

    def _anglo_saxon_sale_move_lines(self, cr, uid, i_line, res, context=None):
        """Return the additional move lines for sales invoices and refunds.

        i_line: An account.invoice.line object.
        res: The move line entries produced so far by the parent move_line_get.
        """
        inv = i_line.invoice_id
        fiscal_pool = self.pool.get('account.fiscal.position')
        fpos = inv.fiscal_position or False
        company_currency = inv.company_id.currency_id.id

        if i_line.product_id.type != 'service' and i_line.product_id.valuation == 'real_time':
            # debit account dacc will be the output account
            # first check the product, if empty check the category
            dacc = i_line.product_id.property_stock_account_output and i_line.product_id.property_stock_account_output.id
            if not dacc:
                dacc = i_line.product_id.categ_id.property_stock_account_output_categ and i_line.product_id.categ_id.property_stock_account_output_categ.id
            # in both cases the credit account cacc will be the expense account
            # first check the product, if empty check the category
            cacc = i_line.product_id.property_account_expense and i_line.product_id.property_account_expense.id
            if not cacc:
                cacc = i_line.product_id.categ_id.property_account_expense_categ and i_line.product_id.categ_id.property_account_expense_categ.id
            if dacc and cacc:
                if i_line.move_id:
                    price_unit = i_line.move_id.price_unit
                else:
                    price_unit = i_line.product_id.standard_price
                from_unit = i_line.product_id.uom_id.id
                to_unit = i_line.uos_id.id
                price_unit = self.pool['product.uom']._compute_price(cr, uid, from_unit, price_unit, to_uom_id=to_unit)
                return [
                    {
                        'type':'src',
                        'name': i_line.name[:64],
                        'price_unit':price_unit,
                        'quantity':i_line.quantity,
                        'price':self._get_price(cr, uid, inv, company_currency, i_line, price_unit),
                        'account_id':dacc,
                        'product_id':i_line.product_id.id,
                        'uos_id':i_line.uos_id.id,
                        'account_analytic_id': False,
                        'taxes':i_line.invoice_line_tax_id,
                    },

                    {
                        'type':'src',
                        'name': i_line.name[:64],
                        'price_unit':price_unit,
                        'quantity':i_line.quantity,
                        'price': -1 * self._get_price(cr, uid, inv, company_currency, i_line, price_unit),
                        'account_id':fiscal_pool.map_account(cr, uid, fpos, cacc),
                        'product_id':i_line.product_id.id,
                        'uos_id':i_line.uos_id.id,
                        'account_analytic_id': False,
                        'taxes':i_line.invoice_line_tax_id,
                    },
                ]
        return []


    def _anglo_saxon_purchase_move_lines(self, cr, uid, i_line, res, context=None):
        """Return the additional move lines for purchase invoices and refunds.

        i_line: An account.invoice.line object.
        res: The move line entries produced so far by the parent move_line_get.
        """
        inv = i_line.invoice_id
        company_currency = inv.company_id.currency_id.id
        if i_line.product_id and i_line.product_id.valuation == 'real_time':
            if i_line.product_id.type != 'service':
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
                    oa = i_line.product_id.categ_id.property_stock_account_input_categ and i_line.product_id.categ_id.property_stock_account_input_categ.id
                if oa:
                    # get the fiscal position
                    fpos = i_line.invoice_id.fiscal_position or False
                    a = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, oa)
                diff_res = []
                decimal_precision = self.pool.get('decimal.precision')
                account_prec = decimal_precision.precision_get(cr, uid, 'Account')
                # calculate and write down the possible price difference between invoice price and product price
                for line in res:
                    if line.get('invl_id', 0) == i_line.id and a == line['account_id']:
                        uom = i_line.product_id.uos_id or i_line.product_id.uom_id
                        valuation_price_unit = self.pool.get('product.uom')._compute_price(cr, uid, uom.id, i_line.product_id.standard_price, i_line.uos_id.id)
                        if i_line.product_id.cost_method != 'standard' and i_line.purchase_line_id:
                            #for average/fifo/lifo costing method, fetch real cost price from incomming moves
                            stock_move_obj = self.pool.get('stock.move')
                            valuation_stock_move = stock_move_obj.search(cr, uid, [('purchase_line_id', '=', i_line.purchase_line_id.id)], limit=1, context=context)
                            if valuation_stock_move:
                                valuation_price_unit = stock_move_obj.browse(cr, uid, valuation_stock_move[0], context=context).price_unit
                        if inv.currency_id.id != company_currency:
                            valuation_price_unit = self.pool.get('res.currency').compute(cr, uid, company_currency, inv.currency_id.id, valuation_price_unit, context={'date': inv.date_invoice})
                        if valuation_price_unit != i_line.price_unit and line['price_unit'] == i_line.price_unit and acc:
                            # price with discount and without tax included
                            price_unit = self.pool['account.tax'].compute_all(cr, uid, line['taxes'],
                                i_line.price_unit * (1-(i_line.discount or 0.0)/100.0), line['quantity'])['total']
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
                                'uos_id': line['uos_id'],
                                'account_analytic_id': line['account_analytic_id'],
                                'taxes': line.get('taxes', []),
                                })
                return diff_res
        return []


class account_invoice(osv.osv):
    _inherit = "account.invoice"

    def _prepare_refund(self, cr, uid, invoice, date=None, period_id=None, description=None, journal_id=None, context=None):
        invoice_data = super(account_invoice, self)._prepare_refund(cr, uid, invoice, date, period_id,
                                                                    description, journal_id, context=context)
        if invoice.type == 'in_invoice':
            fiscal_position = self.pool.get('account.fiscal.position')
            for _, _, line_dict in invoice_data['invoice_line']:
                if line_dict.get('product_id'):
                    product = self.pool.get('product.product').browse(cr, uid, line_dict['product_id'], context=context)
                    counterpart_acct_id = product.property_stock_account_output and \
                            product.property_stock_account_output.id
                    if not counterpart_acct_id:
                        counterpart_acct_id = product.categ_id.property_stock_account_output_categ and \
                                product.categ_id.property_stock_account_output_categ.id
                    if counterpart_acct_id:
                        fpos = invoice.fiscal_position or False
                        line_dict['account_id'] = fiscal_position.map_account(cr, uid,
                                                                              fpos,
                                                                              counterpart_acct_id)
        return invoice_data

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
