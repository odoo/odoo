# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
from operator import itemgetter
from itertools import groupby

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import tools
from openerp.tools import float_compare, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)


#----------------------------------------------------------
# Stock Location
#----------------------------------------------------------

class stock_location(osv.osv):
    _inherit = "stock.location"

    _columns = {
        'valuation_in_account_id': fields.many2one('account.account', 'Stock Valuation Account (Incoming)', domain = [('type','=','other')],
                                                   help="Used for real-time inventory valuation. When set on a virtual location (non internal type), "
                                                        "this account will be used to hold the value of products being moved from an internal location "
                                                        "into this location, instead of the generic Stock Output Account set on the product. "
                                                        "This has no effect for internal locations."),
        'valuation_out_account_id': fields.many2one('account.account', 'Stock Valuation Account (Outgoing)', domain = [('type','=','other')],
                                                   help="Used for real-time inventory valuation. When set on a virtual location (non internal type), "
                                                        "this account will be used to hold the value of products being moved out of this location "
                                                        "and into an internal location, instead of the generic Stock Output Account set on the product. "
                                                        "This has no effect for internal locations."),
    }

#----------------------------------------------------------
# Quants
#----------------------------------------------------------

class stock_quant(osv.osv):
    _inherit = "stock.quant"


    def _get_inventory_value(self, cr, uid, line, prodbrow, context=None):
        #TODO: what in case of partner_id
        if prodbrow[(line.company_id.id, line.product_id.id)].cost_method in ('real'):
            return line.cost * line.qty
        return super(stock_quant, self)._get_inventory_value(cr, uid, line, prodbrow, context=context)


    # FP Note: this is where we should post accounting entries for adjustment
    def _price_update(self, cr, uid, quant, newprice, context=None):
        super(stock_quant, self)._price_update(cr, uid, quant, newprice, context=context)
        # TODO: generate accounting entries

    """
    Accounting Valuation Entries

    location_from: can be None if it's a new quant
    """
    def _account_entry_move(self, cr, uid, quant, location_from, location_to, move, context=None):
        if context is None:
            context = {}
        if quant.product_id.valuation != 'real_time':
            return False
        if quant.lot_id and quant.lot_id.partner_id:
            #if the quant isn't owned by the company, we don't make any valuation entry
            return False
        if quant.qty <= 0 or quant.propagated_from_id:
            #we don't make any stock valuation for negative quants because we may not know the real cost price.
            #The valuation will be made at the time of the reconciliation of the negative quant.
            return False
        company_from = self._location_owner(cr, uid, quant, location_from, context=context)
        company_to = self._location_owner(cr, uid, quant, location_to, context=context)
        if company_from == company_to:
            return False

        # Create Journal Entry for products arriving in the company
        if company_to:
            ctx = context.copy()
            ctx['force_company'] = company_to.id
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation(cr, uid, move, context=ctx)
            if location_from and location_from.usage == 'customer':
                #goods returned from customer
                self._create_account_move_line(cr, uid, quant, move, acc_dest, acc_valuation, journal_id, context=ctx)
            else:
                self._create_account_move_line(cr, uid, quant, move, acc_src, acc_valuation, journal_id, context=ctx)

        # Create Journal Entry for products leaving the company
        if company_from:
            ctx = context.copy()
            ctx['force_company'] = company_from.id
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation(cr, uid, move, context=ctx)
            if location_to and location_to.usage == 'supplier':
                #goods returned to supplier
                self._create_account_move_line(cr, uid, quant, move, acc_valuation, acc_src, journal_id, context=ctx)
            else:
                self._create_account_move_line(cr, uid, quant, move, acc_valuation, acc_dest, journal_id, context=ctx)

    def move_single_quant(self, cr, uid, quant, qty, move, context=None):
        location_from = quant and quant.location_id or False
        quant = super(stock_quant, self).move_single_quant(cr, uid, quant, qty, move, context=context)
        quant.refresh()
        self._account_entry_move(cr, uid, quant, location_from, quant.location_id, move, context=context)
        return quant

    def _get_accounting_data_for_valuation(self, cr, uid, move, context=None):
        """
        Return the accounts and journal to use to post Journal Entries for the real-time
        valuation of the quant.

        :param context: context dictionary that can explicitly mention the company to consider via the 'force_company' key
        :returns: journal_id, source account, destination account, valuation account
        :raise: osv.except_osv() is any mandatory account or journal is not defined.
        """
        product_obj = self.pool.get('product.product')
        accounts = product_obj.get_product_accounts(cr, uid, move.product_id.id, context)
        if move.location_id.valuation_out_account_id:
            acc_src = move.location_id.valuation_out_account_id.id
        else:
            acc_src = accounts['stock_account_input']

        if move.location_dest_id.valuation_in_account_id:
            acc_dest = move.location_dest_id.valuation_in_account_id.id
        else:
            acc_dest = accounts['stock_account_output']

        acc_valuation = accounts.get('property_stock_valuation_account_id', False)
        journal_id = accounts['stock_journal']

        if not all([acc_src, acc_dest, acc_valuation, journal_id]):
            raise osv.except_osv(_('Error!'), _('''One of the following information is missing on the product or product category and prevents the accounting valuation entries to be created:
    Stock Input Account: %s
    Stock Output Account: %s
    Stock Valuation Account: %s
    Stock Journal: %s
    ''') % (acc_src, acc_dest, acc_valuation, journal_id))
        return journal_id, acc_src, acc_dest, acc_valuation

    def _prepare_account_move_line(self, cr, uid, quant, move, credit_account_id, debit_account_id, context=None):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given quant.
        """
        valuation_amount = quant.product_id.cost_method == 'real' and quant.cost or quant.product_id.standard_price
        partner_id = (move.picking_id.partner_id and self.pool.get('res.partner')._find_accounting_partner(move.picking_id.partner_id).id) or False
        debit_line_vals = {
                    'name': move.name,
                    'product_id': quant.product_id.id,
                    'quantity': quant.qty,
                    'product_uom_id': quant.product_id.uom_id.id, 
                    'ref': move.picking_id and move.picking_id.name or False,
                    'date': time.strftime('%Y-%m-%d'),
                    'partner_id': partner_id,
                    'debit': valuation_amount * quant.qty,
                    'account_id': debit_account_id,
        }
        credit_line_vals = {
                    'name': move.name,
                    'product_id': quant.product_id.id,
                    'quantity': quant.qty,
                    'product_uom_id': quant.product_id.uom_id.id, 
                    'ref': move.picking_id and move.picking_id.name or False,
                    'date': time.strftime('%Y-%m-%d'),
                    'partner_id': partner_id,
                    'credit': valuation_amount * quant.qty,
                    'account_id': credit_account_id,
        }
        res = [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
        return res

    def _create_account_move_line(self, cr, uid, quant, move, credit_account_id, debit_account_id, journal_id, context=None):
        move_obj = self.pool.get('account.move')
        move_lines = self._prepare_account_move_line(cr, uid, quant, move, credit_account_id, debit_account_id, context=context)
        return move_obj.create(cr, uid, {'journal_id': journal_id,
                                  'line_id': move_lines,
                                  'ref': move.picking_id and move.picking_id.name}, context=context)


#----------------------------------------------------------
# Stock Picking
#----------------------------------------------------------

class stock_picking(osv.osv):
    _inherit = "stock.picking"

    _columns = {
        'invoice_state': fields.selection([
            ("invoiced", "Invoiced"),
            ("2binvoiced", "To Be Invoiced"),
            ("none", "Not Applicable")], "Invoice Control",
            select=True, required=True, readonly=True, track_visibility='onchange', states={'draft': [('readonly', False)]}),
    }
    _defaults = {
        'invoice_state': 'none',
    }

    #TODO update standard price on product after do_partial()

    #TODO: we don't need to change invoice_state on cancelation, do we?
    #def action_cancel(self, cr, uid, ids, context=None):
    #    """ Changes picking state to cancel.
    #    @return: True
    #    """
    #    for pick in self.browse(cr, uid, ids, context=context):
    #        ids2 = [move.id for move in pick.move_lines]
    #        self.pool.get('stock.move').action_cancel(cr, uid, ids2, context)
    #    self.write(cr, uid, ids, {'state': 'cancel', 'invoice_state': 'none'})
    #    return True

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        picking_obj = self.browse(cr, uid, id, context=context)
        if 'invoice_state' not in default and picking_obj.invoice_state == 'invoiced':
            default['invoice_state'] = '2binvoiced'
        return super(stock_picking, self).copy(cr, uid, id, default, context)


    def get_currency_id(self, cr, uid, picking):
        return False

    def _get_partner_to_invoice(self, cr, uid, picking, context=None):
        """ Gets the partner that will be invoiced
            Note that this function is inherited in the sale and purchase modules
            @param picking: object of the picking for which we are selecting the partner to invoice
            @return: object of the partner to invoice
        """
        return picking.partner_id and picking.partner_id.id

    def _get_comment_invoice(self, cr, uid, picking):
        """
        @return: comment string for invoice
        """
        return picking.note or ''

    def _get_price_unit_invoice(self, cr, uid, move_line, type, context=None):
        """ Gets price unit for invoice
        @param move_line: Stock move lines
        @param type: Type of invoice
        @return: The price unit for the move line
        """
        if context is None:
            context = {}

        if type in ('in_invoice', 'in_refund'):
            # Take the user company and pricetype
            context['currency_id'] = move_line.company_id.currency_id.id
            amount_unit = move_line.product_id.price_get('standard_price', context=context)[move_line.product_id.id]
            return amount_unit
        else:
            return move_line.product_id.list_price

    def _get_discount_invoice(self, cr, uid, move_line):
        '''Return the discount for the move line'''
        return 0.0

    def _get_taxes_invoice(self, cr, uid, move_line, type):
        """ Gets taxes on invoice
        @param move_line: Stock move lines
        @param type: Type of invoice
        @return: Taxes Ids for the move line
        """
        if type in ('in_invoice', 'in_refund'):
            taxes = move_line.product_id.supplier_taxes_id
        else:
            taxes = move_line.product_id.taxes_id

        if move_line.picking_id and move_line.picking_id.partner_id and move_line.picking_id.partner_id.id:
            return self.pool.get('account.fiscal.position').map_tax(
                cr,
                uid,
                move_line.picking_id.partner_id.property_account_position,
                taxes
            )
        else:
            return map(lambda x: x.id, taxes)

    def _get_account_analytic_invoice(self, cr, uid, picking, move_line):
        return False

    def _invoice_line_hook(self, cr, uid, move_line, invoice_line_id):
        '''Call after the creation of the invoice line'''
        return

    def _invoice_hook(self, cr, uid, picking, invoice_id):
        '''Call after the creation of the invoice'''
        return

    def _get_invoice_type(self, pick):
        src_usage = dest_usage = None
        inv_type = None
        if pick.invoice_state == '2binvoiced':
            if pick.move_lines:
                src_usage = pick.move_lines[0].location_id.usage
                dest_usage = pick.move_lines[0].location_dest_id.usage
            if pick.type == 'out' and dest_usage == 'supplier':
                inv_type = 'in_refund'
            elif pick.type == 'out' and dest_usage == 'customer':
                inv_type = 'out_invoice'
            elif pick.type == 'in' and src_usage == 'supplier':
                inv_type = 'in_invoice'
            elif pick.type == 'in' and src_usage == 'customer':
                inv_type = 'out_refund'
            else:
                inv_type = 'out_invoice'
        return inv_type

    def _prepare_invoice_group(self, cr, uid, picking, partner, invoice, context=None):
        """ Builds the dict for grouped invoices
            @param picking: picking object
            @param partner: object of the partner to invoice (not used here, but may be usefull if this function is inherited)
            @param invoice: object of the invoice that we are updating
            @return: dict that will be used to update the invoice
        """
        comment = self._get_comment_invoice(cr, uid, picking)
        return {
            'name': (invoice.name or '') + ', ' + (picking.name or ''),
            'origin': (invoice.origin or '') + ', ' + (picking.name or '') + (picking.origin and (':' + picking.origin) or ''),
            'comment': (comment and (invoice.comment and invoice.comment + "\n" + comment or comment)) or (invoice.comment and invoice.comment or ''),
            'date_invoice': context.get('date_inv', False),
            'user_id': uid,
        }

    def _prepare_invoice(self, cr, uid, picking, partner, inv_type, journal_id, context=None):
        """ Builds the dict containing the values for the invoice
            @param picking: picking object
            @param partner: object of the partner to invoice
            @param inv_type: type of the invoice ('out_invoice', 'in_invoice', ...)
            @param journal_id: ID of the accounting journal
            @return: dict that will be used to create the invoice object
        """
        if isinstance(partner, int):
            partner = self.pool.get('res.partner').browse(cr, uid, partner, context=context)
        if inv_type in ('out_invoice', 'out_refund'):
            account_id = partner.property_account_receivable.id
            payment_term = partner.property_payment_term.id or False
        else:
            account_id = partner.property_account_payable.id
            payment_term = partner.property_supplier_payment_term.id or False
        comment = self._get_comment_invoice(cr, uid, picking)
        invoice_vals = {
            'name': picking.name,
            'origin': (picking.name or '') + (picking.origin and (':' + picking.origin) or ''),
            'type': inv_type,
            'account_id': account_id,
            'partner_id': partner.id,
            'comment': comment,
            'payment_term': payment_term,
            'fiscal_position': partner.property_account_position.id,
            'date_invoice': context.get('date_inv', False),
            'company_id': picking.company_id.id,
            'user_id': uid,
        }
        cur_id = self.get_currency_id(cr, uid, picking)
        if cur_id:
            invoice_vals['currency_id'] = cur_id
        if journal_id:
            invoice_vals['journal_id'] = journal_id
        return invoice_vals

    def _prepare_invoice_line(self, cr, uid, group, picking, move_line, invoice_id,
        invoice_vals, context=None):
        """ Builds the dict containing the values for the invoice line
            @param group: True or False
            @param picking: picking object
            @param: move_line: move_line object
            @param: invoice_id: ID of the related invoice
            @param: invoice_vals: dict used to created the invoice
            @return: dict that will be used to create the invoice line
        """
        if group:
            name = (picking.name or '') + '-' + move_line.name
        else:
            name = move_line.name
        origin = move_line.picking_id.name or ''
        if move_line.picking_id.origin:
            origin += ':' + move_line.picking_id.origin

        if invoice_vals['type'] in ('out_invoice', 'out_refund'):
            account_id = move_line.product_id.property_account_income.id
            if not account_id:
                account_id = move_line.product_id.categ_id.\
                        property_account_income_categ.id
        else:
            account_id = move_line.product_id.property_account_expense.id
            if not account_id:
                account_id = move_line.product_id.categ_id.\
                        property_account_expense_categ.id
        if invoice_vals['fiscal_position']:
            fp_obj = self.pool.get('account.fiscal.position')
            fiscal_position = fp_obj.browse(cr, uid, invoice_vals['fiscal_position'], context=context)
            account_id = fp_obj.map_account(cr, uid, fiscal_position, account_id)
        # set UoS if it's a sale and the picking doesn't have one
        uos_id = move_line.product_uos and move_line.product_uos.id or False
        if not uos_id and invoice_vals['type'] in ('out_invoice', 'out_refund'):
            uos_id = move_line.product_uom.id

        return {
            'name': name,
            'origin': origin,
            'invoice_id': invoice_id,
            'uos_id': uos_id,
            'product_id': move_line.product_id.id,
            'account_id': account_id,
            'price_unit': self._get_price_unit_invoice(cr, uid, move_line, invoice_vals['type']),
            'discount': self._get_discount_invoice(cr, uid, move_line),
            'quantity': move_line.product_uos_qty or move_line.product_qty,
            'invoice_line_tax_id': [(6, 0, self._get_taxes_invoice(cr, uid, move_line, invoice_vals['type']))],
            'account_analytic_id': self._get_account_analytic_invoice(cr, uid, picking, move_line),
        }

    def action_invoice_create(self, cr, uid, ids, journal_id=False, group=False, type='out_invoice', context=None):
        """ Creates invoice based on the invoice state selected for picking.
        @param journal_id: Id of journal
        @param group: Whether to create a group invoice or not
        @param type: Type invoice to be created
        @return: Ids of created invoices for the pickings
        """
        if context is None:
            context = {}

        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')
        partner_obj = self.pool.get('res.partner')
        invoices_group = {}
        res = {}
        inv_type = type
        for picking in self.browse(cr, uid, ids, context=context):
            if picking.invoice_state != '2binvoiced':
                continue
            partner = self._get_partner_to_invoice(cr, uid, picking, context=context)
            if isinstance(partner, int):
                partner = partner_obj.browse(cr, uid, [partner], context=context)[0]
            if not partner:
                raise osv.except_osv(_('Error, no partner!'),
                    _('Please put a partner on the picking list if you want to generate invoice.'))

            if not inv_type:
                inv_type = self._get_invoice_type(picking)

            if group and partner.id in invoices_group:
                invoice_id = invoices_group[partner.id]
                invoice = invoice_obj.browse(cr, uid, invoice_id)
                invoice_vals_group = self._prepare_invoice_group(cr, uid, picking, partner, invoice, context=context)
                invoice_obj.write(cr, uid, [invoice_id], invoice_vals_group, context=context)
            else:
                invoice_vals = self._prepare_invoice(cr, uid, picking, partner, inv_type, journal_id, context=context)
                invoice_id = invoice_obj.create(cr, uid, invoice_vals, context=context)
                invoices_group[partner.id] = invoice_id
            res[picking.id] = invoice_id
            for move_line in picking.move_lines:
                if move_line.state == 'cancel':
                    continue
                if move_line.scrapped:
                    # do no invoice scrapped products
                    continue
                vals = self._prepare_invoice_line(cr, uid, group, picking, move_line,
                                invoice_id, invoice_vals, context=context)
                if vals:
                    invoice_line_id = invoice_line_obj.create(cr, uid, vals, context=context)
                    self._invoice_line_hook(cr, uid, move_line, invoice_line_id)

            invoice_obj.button_compute(cr, uid, [invoice_id], context=context,
                    set_total=(inv_type in ('in_invoice', 'in_refund')))
            self.write(cr, uid, [picking.id], {
                'invoice_state': 'invoiced',
                }, context=context)
            self._invoice_hook(cr, uid, picking, invoice_id)
        self.write(cr, uid, res.keys(), {
            'invoice_state': 'invoiced',
            }, context=context)
        return res




    # FP Note: review all methods above this line for stock.picking

# ----------------------------------------------------
# Move
# ----------------------------------------------------

class stock_move(osv.osv):

    _inherit = "stock.move"

    #TODO cancel a move must delete the accounting entry if not posted yet (otherwise raise an error)
    def action_cancel(self, cr, uid, ids, context=None):
        super(stock_move, self).action_cancel(cr, uid, ids, context=context)

#class stock_inventory(osv.osv):
#    _name = "stock.inventory"
#
#    def action_cancel_draft(self, cr, uid, ids, context=None):
#        """ Cancels the stock move and change inventory state to draft.
#        @return: True
#        """
#        for inv in self.browse(cr, uid, ids, context=context):
#            self.pool.get('stock.move').action_cancel(cr, uid, [x.id for x in inv.move_ids], context=context)
#            self.write(cr, uid, [inv.id], {'state':'draft'}, context=context)
#        return True
#
#    def action_cancel_inventory(self, cr, uid, ids, context=None):
#        """ Cancels both stock move and inventory
#        @return: True
#        """
#        move_obj = self.pool.get('stock.move')
#        account_move_obj = self.pool.get('account.move')
#        for inv in self.browse(cr, uid, ids, context=context):
#            move_obj.action_cancel(cr, uid, [x.id for x in inv.move_ids], context=context)
#            for move in inv.move_ids:
#                 account_move_ids = account_move_obj.search(cr, uid, [('name', '=', move.name)])
#                 if account_move_ids:
#                     account_move_data_l = account_move_obj.read(cr, uid, account_move_ids, ['state'], context=context)
#                     for account_move in account_move_data_l:
#                         if account_move['state'] == 'posted':
#                             raise osv.except_osv(_('User Error!'),
#                                                  _('In order to cancel this inventory, you must first unpost related journal entries.'))
#                         account_move_obj.unlink(cr, uid, [account_move['id']], context=context)
#            self.write(cr, uid, [inv.id], {'state': 'cancel'}, context=context)
#        return True




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
