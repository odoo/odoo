# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import SUPERUSER_ID, api, models
import logging
_logger = logging.getLogger(__name__)


class account_invoice_line(osv.osv):
    _inherit = "account.invoice.line"

    _columns = {
        'move_id': fields.many2one('stock.move', string="Move line", help="If the invoice was generated from a stock.picking, reference to the related move line."),
    }

    def move_line_get(self, cr, uid, invoice_id, context=None):
        res = super(account_invoice_line,self).move_line_get(cr, uid, invoice_id, context=context)
        if self.company_id.anglo_saxon_accounting:
            inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=context)
            if inv.type in ('out_invoice','out_refund'):
                for i_line in inv.invoice_line_ids:
                    res.extend(self._anglo_saxon_sale_move_lines(cr, uid, i_line, res, context=context))
        return res

    def _get_price(self, cr, uid, inv, company_currency, i_line, price_unit):
        cur_obj = self.pool.get('res.currency')
        decimal_precision = self.pool.get('decimal.precision')
        if inv.currency_id.id != company_currency:
            price = cur_obj.compute(cr, uid, company_currency, inv.currency_id.id, price_unit * i_line.quantity, context={'date': inv.date_invoice})
        else:
            price = price_unit * i_line.quantity
        return round(price, inv.currency_id.decimal_places)

    @api.v8
    def get_invoice_line_account(self, type, product, fpos, company):
        if self.company_id.anglo_saxon_accounting and type in ('in_invoice', 'in_refund'):
            accounts = product.product_tmpl_id.get_product_accounts(fpos)
            if type == 'in_invoice':
                return accounts['stock_input']
            return accounts['stock_ouput']
        return super(account_invoice_line, self).get_invoice_line_account(type, product, fpos, company)

    def _anglo_saxon_sale_move_lines(self, cr, uid, i_line, res, context=None):
        """Return the additional move lines for sales invoices and refunds.

        i_line: An account.invoice.line object.
        res: The move line entries produced so far by the parent move_line_get.
        """
        inv = i_line.invoice_id
        company_currency = inv.company_id.currency_id.id

        if i_line.product_id.type == 'product' and i_line.product_id.valuation == 'real_time':
            # debit account dacc will be the output account
            # first check the product, if empty check the category
            dacc = i_line.product_id.property_stock_account_output and i_line.product_id.property_stock_account_output.id
            if not dacc:
                dacc = i_line.product_id.categ_id.property_stock_account_output_categ_id and i_line.product_id.categ_id.property_stock_account_output_categ_id.id
            # in both cases the credit account cacc will be the expense account
            # first check the product, if empty check the category
            cacc = i_line.product_id.property_account_expense_id and i_line.product_id.property_account_expense_id.id
            if not cacc:
                cacc = i_line.product_id.categ_id.property_account_expense_categ_id and i_line.product_id.categ_id.property_account_expense_categ_id.id
            if dacc and cacc:
                if i_line.move_id:
                    price = i_line.move_id.product_id.standard_price
                    from_unit = i_line.move_id.product_tmpl_id.uom_id.id
                    to_unit = i_line.move_id.product_uom.id
                    price_unit = self.pool['product.uom']._compute_price(cr, uid, from_unit, price, to_uom_id=to_unit)
                else:
                    price_unit = i_line.product_id.standard_pric
                return [
                    {
                        'type':'src',
                        'name': i_line.name[:64],
                        'price_unit':price_unit,
                        'quantity':i_line.quantity,
                        'price':self._get_price(cr, uid, inv, company_currency, i_line, price_unit),
                        'account_id':dacc,
                        'product_id':i_line.product_id.id,
                        'uom_id':i_line.uom_id.id,
                        'account_analytic_id': False,
                        'taxes':i_line.invoice_line_tax_ids,
                    },

                    {
                        'type':'src',
                        'name': i_line.name[:64],
                        'price_unit':price_unit,
                        'quantity':i_line.quantity,
                        'price': -1 * self._get_price(cr, uid, inv, company_currency, i_line, price_unit),
                        'account_id':cacc,
                        'product_id':i_line.product_id.id,
                        'uom_id':i_line.uom_id.id,
                        'account_analytic_id': False,
                        'taxes':i_line.invoice_line_tax_ids,
                    },
                ]
        return []

class account_invoice(osv.osv):
    _inherit = "account.invoice"

    def _prepare_refund(self, cr, uid, invoice, date_invoice=None, date=None, description=None, journal_id=None, context=None):
        invoice_data = super(account_invoice, self)._prepare_refund(cr, uid, invoice, date, date,
                                                                    description, journal_id, context=context)
        #for anglo-saxon accounting
        if invoice.company_id.anglo_saxon_accounting and invoice.type == 'in_invoice':
            fiscal_position = self.pool.get('account.fiscal.position')
            for dummy, dummy, line_dict in invoice_data['invoice_line_ids']:
                if line_dict.get('product_id'):
                    product = self.pool.get('product.product').browse(cr, uid, line_dict['product_id'], context=context)
                    counterpart_acct_id = product.property_stock_account_output and \
                            product.property_stock_account_output.id
                    if not counterpart_acct_id:
                        counterpart_acct_id = product.categ_id.property_stock_account_output_categ_id and \
                                product.categ_id.property_stock_account_output_categ_id.id
                    if counterpart_acct_id:
                        fpos = invoice.fiscal_position_id or False
                        line_dict['account_id'] = fiscal_position.map_account(cr, uid,
                                                                              fpos,
                                                                              counterpart_acct_id)
        return invoice_data


#----------------------------------------------------------
# Stock Location
#----------------------------------------------------------

class stock_location(osv.osv):
    _inherit = "stock.location"

    _columns = {
        'valuation_in_account_id': fields.many2one('account.account', 'Stock Valuation Account (Incoming)', domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)],
                                                   help="Used for real-time inventory valuation. When set on a virtual location (non internal type), "
                                                        "this account will be used to hold the value of products being moved from an internal location "
                                                        "into this location, instead of the generic Stock Output Account set on the product. "
                                                        "This has no effect for internal locations."),
        'valuation_out_account_id': fields.many2one('account.account', 'Stock Valuation Account (Outgoing)', domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)],
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

    def _get_inventory_value(self, cr, uid, quant, context=None):
        if quant.product_id.cost_method in ('real'):
            return quant.cost * quant.qty
        return super(stock_quant, self)._get_inventory_value(cr, uid, quant, context=context)

    @api.cr_uid_ids_context
    def _price_update(self, cr, uid, quant_ids, newprice, context=None):
        ''' This function is called at the end of negative quant reconciliation and does the accounting entries adjustemnts and the update of the product cost price if needed
        '''
        if context is None:
            context = {}
        account_move_obj = self.pool['account.move']
        super(stock_quant, self)._price_update(cr, uid, quant_ids, newprice, context=context)
        for quant in self.browse(cr, uid, quant_ids, context=context):
            move = self._get_latest_move(cr, uid, quant, context=context)
            valuation_update = newprice - quant.cost
            # this is where we post accounting entries for adjustment, if needed
            if not quant.company_id.currency_id.is_zero(valuation_update):
                # If neg quant period already closed (likely with manual valuation), skip update
                if account_move_obj._check_lock_date(cr, uid, [move.id], context=context):
                    ctx = dict(context, force_valuation_amount=valuation_update)
                    self._account_entry_move(cr, uid, [quant], move, context=ctx)

            #update the standard price of the product, only if we would have done it if we'd have had enough stock at first, which means
            #1) the product cost's method is 'real'
            #2) we just fixed a negative quant caused by an outgoing shipment
            if quant.product_id.cost_method == 'real' and quant.location_id.usage != 'internal':
                self.pool.get('stock.move')._store_average_cost_price(cr, uid, move, context=context)

    def _account_entry_move(self, cr, uid, quants, move, context=None):
        """
        Accounting Valuation Entries

        quants: browse record list of Quants to create accounting valuation entries for. Unempty and all quants are supposed to have the same location id (thay already moved in)
        move: Move to use. browse record
        """
        if context is None:
            context = {}
        location_obj = self.pool.get('stock.location')
        location_from = move.location_id
        location_to = quants[0].location_id
        company_from = location_obj._location_owner(cr, uid, location_from, context=context)
        company_to = location_obj._location_owner(cr, uid, location_to, context=context)

        if move.product_id.valuation != 'real_time':
            return False
        for q in quants:
            if q.owner_id:
                #if the quant isn't owned by the company, we don't make any valuation entry
                return False
            if q.qty <= 0:
                #we don't make any stock valuation for negative quants because the valuation is already made for the counterpart.
                #At that time the valuation will be made at the product cost price and afterward there will be new accounting entries
                #to make the adjustments when we know the real cost price.
                return False

        #in case of routes making the link between several warehouse of the same company, the transit location belongs to this company, so we don't need to create accounting entries
        # Create Journal Entry for products arriving in the company
        if company_to and (move.location_id.usage not in ('internal', 'transit') and move.location_dest_id.usage == 'internal' or company_from != company_to):
            ctx = context.copy()
            ctx['force_company'] = company_to.id
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation(cr, uid, move, context=ctx)
            if location_from and location_from.usage == 'customer':
                #goods returned from customer
                self._create_account_move_line(cr, uid, quants, move, acc_dest, acc_valuation, journal_id, context=ctx)
            else:
                self._create_account_move_line(cr, uid, quants, move, acc_src, acc_valuation, journal_id, context=ctx)

        # Create Journal Entry for products leaving the company
        if company_from and (move.location_id.usage == 'internal' and move.location_dest_id.usage not in ('internal', 'transit') or company_from != company_to):
            ctx = context.copy()
            ctx['force_company'] = company_from.id
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation(cr, uid, move, context=ctx)
            if location_to and location_to.usage == 'supplier':
                #goods returned to supplier
                self._create_account_move_line(cr, uid, quants, move, acc_valuation, acc_src, journal_id, context=ctx)
            else:
                self._create_account_move_line(cr, uid, quants, move, acc_valuation, acc_dest, journal_id, context=ctx)

    def _quant_create(self, cr, uid, qty, move, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False, force_location_from=False, force_location_to=False, context=None):
        quant = super(stock_quant, self)._quant_create(cr, uid, qty, move, lot_id=lot_id, owner_id=owner_id, src_package_id=src_package_id, dest_package_id=dest_package_id, force_location_from=force_location_from, force_location_to=force_location_to, context=context)
        if move.product_id.valuation == 'real_time':
            self._account_entry_move(cr, uid, [quant], move, context)
        return quant

    def move_quants_write(self, cr, uid, quants, move, location_dest_id, dest_package_id, lot_id=False, context=None):
        res = super(stock_quant, self).move_quants_write(cr, uid, quants, move, location_dest_id,  dest_package_id, lot_id=lot_id, context=context)
        if move.product_id.valuation == 'real_time':
            self._account_entry_move(cr, uid, quants, move, context=context)
        return res


    def _get_accounting_data_for_valuation(self, cr, uid, move, context=None):
        """
        Return the accounts and journal to use to post Journal Entries for the real-time
        valuation of the quant.

        :param context: context dictionary that can explicitly mention the company to consider via the 'force_company' key
        :returns: journal_id, source account, destination account, valuation account
        :raise: osv.except_osv() is any mandatory account or journal is not defined.
        """
        product_obj = self.pool.get('product.template')
        accounts = product_obj.browse(cr, uid, move.product_id.product_tmpl_id.id, context).get_product_accounts()
        if move.location_id.valuation_out_account_id:
            acc_src = move.location_id.valuation_out_account_id.id
        else:
            acc_src = accounts['stock_input'].id

        if move.location_dest_id.valuation_in_account_id:
            acc_dest = move.location_dest_id.valuation_in_account_id.id
        else:
            acc_dest = accounts['stock_output'].id

        acc_valuation = accounts.get('stock_valuation', False)
        if acc_valuation:
            acc_valuation = acc_valuation.id
        journal_id = accounts['stock_journal'].id
        return journal_id, acc_src, acc_dest, acc_valuation

    def _prepare_account_move_line(self, cr, uid, move, qty, cost, credit_account_id, debit_account_id, context=None):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given quant.
        """
        if context is None:
            context = {}
        currency_obj = self.pool.get('res.currency')
        if context.get('force_valuation_amount'):
            valuation_amount = context.get('force_valuation_amount')
        else:
            if move.product_id.cost_method == 'average':
                valuation_amount = cost if move.location_id.usage != 'internal' and move.location_dest_id.usage == 'internal' else move.product_id.standard_price
            else:
                valuation_amount = cost if move.product_id.cost_method == 'real' else move.product_id.standard_price
        #the standard_price of the product may be in another decimal precision, or not compatible with the coinage of
        #the company currency... so we need to use round() before creating the accounting entries.
        valuation_amount = currency_obj.round(cr, uid, move.company_id.currency_id, valuation_amount * qty)
        partner_id = (move.picking_id.partner_id and self.pool.get('res.partner')._find_accounting_partner(move.picking_id.partner_id).id) or False
        debit_line_vals = {
                    'name': move.name,
                    'product_id': move.product_id.id,
                    'quantity': qty,
                    'product_uom_id': move.product_id.uom_id.id,
                    'ref': move.picking_id and move.picking_id.name or False,
                    'date': move.date,
                    'partner_id': partner_id,
                    'debit': valuation_amount > 0 and valuation_amount or 0,
                    'credit': valuation_amount < 0 and -valuation_amount or 0,
                    'account_id': debit_account_id,
        }
        credit_line_vals = {
                    'name': move.name,
                    'product_id': move.product_id.id,
                    'quantity': qty,
                    'product_uom_id': move.product_id.uom_id.id,
                    'ref': move.picking_id and move.picking_id.name or False,
                    'date': move.date,
                    'partner_id': partner_id,
                    'credit': valuation_amount > 0 and valuation_amount or 0,
                    'debit': valuation_amount < 0 and -valuation_amount or 0,
                    'account_id': credit_account_id,
        }
        return [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]

    def _create_account_move_line(self, cr, uid, quants, move, credit_account_id, debit_account_id, journal_id, context=None):
        #group quants by cost
        quant_cost_qty = {}
        for quant in quants:
            if quant_cost_qty.get(quant.cost):
                quant_cost_qty[quant.cost] += quant.qty
            else:
                quant_cost_qty[quant.cost] = quant.qty
        move_obj = self.pool.get('account.move')
        for cost, qty in quant_cost_qty.items():
            move_lines = self._prepare_account_move_line(cr, uid, move, qty, cost, credit_account_id, debit_account_id, context=context)
            date = context.get('force_period_date', move.date)
            new_move = move_obj.create(cr, uid, {'journal_id': journal_id,
                                      'line_ids': move_lines,
                                      'date': date,
                                      'ref': move.picking_id.name}, context=context)
            move_obj.post(cr, uid, [new_move], context=context)

    #def _reconcile_single_negative_quant(self, cr, uid, to_solve_quant, quant, quant_neg, qty, context=None):
    #    move = self._get_latest_move(cr, uid, to_solve_quant, context=context)
    #    quant_neg_position = quant_neg.negative_dest_location_id.usage
    #    remaining_solving_quant, remaining_to_solve_quant = super(stock_quant, self)._reconcile_single_negative_quant(cr, uid, to_solve_quant, quant, quant_neg, qty, context=context)
    #    #update the standard price of the product, only if we would have done it if we'd have had enough stock at first, which means
    #    #1) there isn't any negative quant anymore
    #    #2) the product cost's method is 'real'
    #    #3) we just fixed a negative quant caused by an outgoing shipment
    #    if not remaining_to_solve_quant and move.product_id.cost_method == 'real' and quant_neg_position != 'internal':
    #        self.pool.get('stock.move')._store_average_cost_price(cr, uid, move, context=context)
    #    return remaining_solving_quant, remaining_to_solve_quant

class stock_move(osv.osv):
    _inherit = "stock.move"

    def action_done(self, cr, uid, ids, context=None):
        self.product_price_update_before_done(cr, uid, ids, context=context)
        res = super(stock_move, self).action_done(cr, uid, ids, context=context)
        self.product_price_update_after_done(cr, uid, ids, context=context)
        return res

    def _store_average_cost_price(self, cr, uid, move, context=None):
        ''' move is a browe record '''
        product_obj = self.pool.get('product.product')
        if any([q.qty <= 0 for q in move.quant_ids]):
            #if there is a negative quant, the standard price shouldn't be updated
            return
        #Note: here we can't store a quant.cost directly as we may have moved out 2 units (1 unit to 5€ and 1 unit to 7€) and in case of a product return of 1 unit, we can't know which of the 2 costs has to be used (5€ or 7€?). So at that time, thanks to the average valuation price we are storing we will svaluate it at 6€
        average_valuation_price = 0.0
        for q in move.quant_ids:
            average_valuation_price += q.qty * q.cost
        average_valuation_price = average_valuation_price / move.product_qty
        # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
        ctx = dict(context, force_company=move.company_id.id)
        product_obj.write(cr, SUPERUSER_ID, [move.product_id.id], {'standard_price': average_valuation_price}, context=ctx)
        self.write(cr, uid, [move.id], {'price_unit': average_valuation_price}, context=context)

    def product_price_update_before_done(self, cr, uid, ids, context=None):
        product_obj = self.pool.get('product.product')
        tmpl_dict = {}
        for move in self.browse(cr, uid, ids, context=context):
            #adapt standard price on incomming moves if the product cost_method is 'average'
            if (move.location_id.usage == 'supplier') and (move.product_id.cost_method == 'average'):
                product = move.product_id
                prod_tmpl_id = move.product_id.product_tmpl_id.id
                qty_available = move.product_id.product_tmpl_id.qty_available
                if tmpl_dict.get(prod_tmpl_id):
                    product_avail = qty_available + tmpl_dict[prod_tmpl_id]
                else:
                    tmpl_dict[prod_tmpl_id] = 0
                    product_avail = qty_available
                if product_avail <= 0:
                    new_std_price = move.price_unit
                else:
                    # Get the standard price
                    amount_unit = product.standard_price
                    new_std_price = ((amount_unit * product_avail) + (move.price_unit * move.product_qty)) / (product_avail + move.product_qty)
                tmpl_dict[prod_tmpl_id] += move.product_qty
                # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
                ctx = dict(context or {}, force_company=move.company_id.id)
                product_obj.write(cr, SUPERUSER_ID, [product.id], {'standard_price': new_std_price}, context=ctx)

    def product_price_update_after_done(self, cr, uid, ids, context=None):
        '''
        This method adapts the price on the product when necessary
        '''
        for move in self.browse(cr, uid, ids, context=context):
            #adapt standard price on outgoing moves if the product cost_method is 'real', so that a return
            #or an inventory loss is made using the last value used for an outgoing valuation.
            if move.product_id.cost_method == 'real' and move.location_dest_id.usage != 'internal':
                #store the average price of the move on the move and product form
                self._store_average_cost_price(cr, uid, move, context=context)

class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.model
    def generate_journals(self, acc_template_ref, company, journals_dict=None):
        journal_to_add = [{'name': _('Stock Journal'), 'type': 'general', 'code': 'STJ', 'favorite': False, 'sequence': 8}]
        super(AccountChartTemplate, self).generate_journals(acc_template_ref=acc_template_ref, company=company, journals_dict=journal_to_add)

    @api.multi
    def generate_properties(self, acc_template_ref, company, property_list=None):
        super(AccountChartTemplate, self).generate_properties(acc_template_ref=acc_template_ref, company=company)
        PropertyObj = self.env['ir.property'] # Property Stock Journal
        value = self.env['account.journal'].search([('company_id', '=', company.id), ('code', '=', 'STJ'), ('type', '=', 'general')], limit=1)
        if value:
            field = self.env['ir.model.fields'].search([('name', '=', 'property_stock_journal'), ('model', '=', 'product.category'), ('relation', '=', 'account.journal')], limit=1)
            vals = {
                'name': 'property_stock_journal',
                'company_id': company.id,
                'fields_id': field.id,
                'value': 'account.journal,%s' % value.id,
            }
            properties = PropertyObj.search([('name', '=', 'property_stock_journal'), ('company_id', '=', company.id)])
            if properties:
                #the property exist: modify it
                properties.write(vals)
            else:
                #create the property
                PropertyObj.create(vals)

        todo_list = [ # Property Stock Accounts
            'property_stock_account_input_categ_id',
            'property_stock_account_output_categ_id',
            'property_stock_valuation_account_id',
        ]
        for record in todo_list:
            account = getattr(self, record)
            value = account and 'account.account,' + str(acc_template_ref[account.id]) or False
            if value:
                field = self.env['ir.model.fields'].search([('name', '=', record), ('model', '=', 'product.category'), ('relation', '=', 'account.account')], limit=1)
                vals = {
                    'name': record,
                    'company_id': company.id,
                    'fields_id': field.id,
                    'value': value,
                    'res_id': 'product.category,'+str(self.env['ir.model.data'].xmlid_to_res_id('product.product_category_all')),
                }
                properties = PropertyObj.search([('name', '=', record), ('company_id', '=', company.id)])
                if properties:
                    #the property exist: modify it
                    properties.write(vals)
                else:
                    #create the property
                    PropertyObj.create(vals)

        return True
