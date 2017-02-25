# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round

import logging
_logger = logging.getLogger(__name__)


class StockInventory(models.Model):
    _inherit = "stock.inventory"

    accounting_date = fields.Date(
        'Force Accounting Date',
        help="Choose the accounting date at which you want to value the stock "
             "moves created by the inventory instead of the default one (the "
             "inventory end date)")

    @api.multi
    def post_inventory(self):
        acc_inventories = self.filtered(lambda inventory: inventory.accounting_date)
        for inventory in acc_inventories:
            res = super(StockInventory, inventory.with_context(force_period_date=inventory.accounting_date)).post_inventory()
        other_inventories = self - acc_inventories
        if other_inventories:
            res = super(StockInventory, other_inventories).post_inventory()
        return res


class StockLocation(models.Model):
    _inherit = "stock.location"

    valuation_in_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account (Incoming)',
        domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)],
        help="Used for real-time inventory valuation. When set on a virtual location (non internal type), "
             "this account will be used to hold the value of products being moved from an internal location "
             "into this location, instead of the generic Stock Output Account set on the product. "
             "This has no effect for internal locations.")
    valuation_out_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account (Outgoing)',
        domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)],
        help="Used for real-time inventory valuation. When set on a virtual location (non internal type), "
             "this account will be used to hold the value of products being moved out of this location "
             "and into an internal location, instead of the generic Stock Output Account set on the product. "
             "This has no effect for internal locations.")


class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.multi
    def _compute_inventory_value(self):
        real_value_quants = self.filtered(lambda quant: quant.product_id.cost_method == 'real')
        for quant in real_value_quants:
            quant.inventory_value = quant.cost * quant.qty
        return super(StockQuant, self - real_value_quants)._compute_inventory_value()

    @api.multi
    def _price_update(self, newprice):
        ''' This function is called at the end of negative quant reconciliation
        and does the accounting entries adjustemnts and the update of the product
        cost price if needed '''
        super(StockQuant, self)._price_update(newprice)
        for quant in self:
            move = quant._get_latest_move()
            valuation_update = newprice - quant.cost
            # this is where we post accounting entries for adjustment, if needed
            # If neg quant period already closed (likely with manual valuation), skip update
            if not quant.company_id.currency_id.is_zero(valuation_update) and move._check_lock_date():
                quant.with_context(force_valuation_amount=valuation_update)._account_entry_move(move)

            # update the standard price of the product, only if we would have
            # done it if we'd have had enough stock at first, which means
            # 1) the product cost's method is 'real'
            # 2) we just fixed a negative quant caused by an outgoing shipment
            if quant.product_id.cost_method == 'real' and quant.location_id.usage != 'internal':
                move._store_average_cost_price()

    def _account_entry_move(self, move):
        """ Accounting Valuation Entries """
        if move.product_id.type != 'product' or move.product_id.valuation != 'real_time':
            # no stock valuation for consumable products
            return False
        if any(quant.owner_id or quant.qty <= 0 for quant in self):
            # if the quant isn't owned by the company, we don't make any valuation en
            # we don't make any stock valuation for negative quants because the valuation is already made for the counterpart.
            # At that time the valuation will be made at the product cost price and afterward there will be new accounting entries
            # to make the adjustments when we know the real cost price.
            return False

        location_from = move.location_id
        location_to = self[0].location_id  # TDE FIXME: as the accounting is based on this value, should probably check all location_to to be the same
        company_from = location_from.usage == 'internal' and location_from.company_id or False
        company_to = location_to and (location_to.usage == 'internal') and location_to.company_id or False

        # Create Journal Entry for products arriving in the company; in case of routes making the link between several
        # warehouse of the same company, the transit location belongs to this company, so we don't need to create accounting entries
        if company_to and (move.location_id.usage not in ('internal', 'transit') and move.location_dest_id.usage == 'internal' or company_from != company_to):
            journal_id, acc_src, acc_dest, acc_valuation = move._get_accounting_data_for_valuation()
            if location_from and location_from.usage == 'customer':  # goods returned from customer
                self.with_context(force_company=company_to.id)._create_account_move_line(move, acc_dest, acc_valuation, journal_id)
            else:
                self.with_context(force_company=company_to.id)._create_account_move_line(move, acc_src, acc_valuation, journal_id)

        # Create Journal Entry for products leaving the company
        if company_from and (move.location_id.usage == 'internal' and move.location_dest_id.usage not in ('internal', 'transit') or company_from != company_to):
            journal_id, acc_src, acc_dest, acc_valuation = move._get_accounting_data_for_valuation()
            if location_to and location_to.usage == 'supplier':  # goods returned to supplier
                self.with_context(force_company=company_from.id)._create_account_move_line(move, acc_valuation, acc_src, journal_id)
            else:
                self.with_context(force_company=company_from.id)._create_account_move_line(move, acc_valuation, acc_dest, journal_id)

        if move.company_id.anglo_saxon_accounting and move.location_id.usage == 'supplier' and move.location_dest_id.usage == 'customer':
            # Creates an account entry from stock_input to stock_output on a dropship move. https://github.com/odoo/odoo/issues/12687
            journal_id, acc_src, acc_dest, acc_valuation = move._get_accounting_data_for_valuation()
            self.with_context(force_company=move.company_id.id)._create_account_move_line(move, acc_src, acc_dest, journal_id)

    def _create_account_move_line(self, move, credit_account_id, debit_account_id, journal_id):
        # group quants by cost
        quant_cost_qty = defaultdict(lambda: 0.0)
        for quant in self:
            quant_cost_qty[quant.cost] += quant.qty

        AccountMove = self.env['account.move']
        for cost, qty in quant_cost_qty.iteritems():
            move_lines = move._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id)
            if move_lines:
                date = self._context.get('force_period_date', fields.Date.context_today(self))
                new_account_move = AccountMove.create({
                    'journal_id': journal_id,
                    'line_ids': move_lines,
                    'date': date,
                    'ref': move.picking_id.name})
                new_account_move.post()
                new_account_move.message_post_with_view('mail.message_origin_link',
                        values={'self': new_account_move, 'origin': move.picking_id},
                        subtype_id=self.env.ref('mail.mt_note').id)

    def _quant_create_from_move(self, qty, move, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False, force_location_from=False, force_location_to=False):
        quant = super(StockQuant, self)._quant_create_from_move(qty, move, lot_id=lot_id, owner_id=owner_id, src_package_id=src_package_id, dest_package_id=dest_package_id, force_location_from=force_location_from, force_location_to=force_location_to)
        quant._account_entry_move(move)
        if move.product_id.valuation == 'real_time':
            # If the precision required for the variable quant cost is larger than the accounting
            # precision, inconsistencies between the stock valuation and the accounting entries
            # may arise.
            # For example, a box of 13 units is bought 15.00. If the products leave the
            # stock one unit at a time, the amount related to the cost will correspond to
            # round(15/13, 2)*13 = 14.95. To avoid this case, we split the quant in 12 + 1, then
            # record the difference on the new quant.
            # We need to make sure to able to extract at least one unit of the product. There is
            # an arbitrary minimum quantity set to 2.0 from which we consider we can extract a
            # unit and adapt the cost.
            curr_rounding = move.company_id.currency_id.rounding
            cost_rounded = float_round(quant.cost, precision_rounding=curr_rounding)
            cost_correct = cost_rounded
            if float_compare(quant.product_id.uom_id.rounding, 1.0, precision_digits=1) == 0\
                    and float_compare(quant.qty * quant.cost, quant.qty * cost_rounded, precision_rounding=curr_rounding) != 0\
                    and float_compare(quant.qty, 2.0, precision_rounding=quant.product_id.uom_id.rounding) >= 0:
                quant_correct = quant._quant_split(quant.qty - 1.0)
                cost_correct += (quant.qty * quant.cost) - (quant.qty * cost_rounded)
                quant.sudo().write({'cost': cost_rounded})
                quant_correct.sudo().write({'cost': cost_correct})
        return quant

    def _quant_update_from_move(self, move, location_dest_id, dest_package_id, lot_id=False, entire_pack=False):
        res = super(StockQuant, self)._quant_update_from_move(move, location_dest_id, dest_package_id, lot_id=lot_id, entire_pack=entire_pack)
        self._account_entry_move(move)
        return res


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.multi
    def action_done(self):
        self.product_price_update_before_done()
        res = super(StockMove, self).action_done()
        self.product_price_update_after_done()
        return res

    @api.multi
    def product_price_update_before_done(self):
        tmpl_dict = defaultdict(lambda: 0.0)
        # adapt standard price on incomming moves if the product cost_method is 'average'
        std_price_update = {}
        for move in self.filtered(lambda move: move.location_id.usage == 'supplier' and move.product_id.cost_method == 'average'):
            product_tot_qty_available = move.product_id.qty_available + tmpl_dict[move.product_id.id]

            # if the incoming move is for a purchase order with foreign currency, need to call this to get the same value that the quant will use.
            if product_tot_qty_available <= 0:
                new_std_price = move.get_price_unit()
            else:
                # Get the standard price
                amount_unit = std_price_update.get(move.product_id.id) or move.product_id.standard_price
                new_std_price = ((amount_unit * product_tot_qty_available) + (move.get_price_unit() * move.product_qty)) / (product_tot_qty_available + move.product_qty)

            tmpl_dict[move.product_id.id] += move.product_qty
            # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
            move.product_id.with_context(force_company=move.company_id.id).write({'standard_price': new_std_price})
            std_price_update[move.product_id.id] = new_std_price

    @api.multi
    def product_price_update_after_done(self):
        ''' Adapt standard price on outgoing moves, so that a
        return or an inventory loss is made using the last value used for an outgoing valuation. '''
        to_update_moves = self.filtered(lambda move: move.location_dest_id.usage != 'internal')
        to_update_moves._store_average_cost_price()

    def _store_average_cost_price(self):
        """ Store the average price of the move on the move and product form (costing method 'real')"""
        for move in self.filtered(lambda move: move.product_id.cost_method == 'real'):
            # product_obj = self.pool.get('product.product')
            if any(q.qty <= 0 for q in move.quant_ids) or move.product_qty == 0:
                # if there is a negative quant, the standard price shouldn't be updated
                return
            # Note: here we can't store a quant.cost directly as we may have moved out 2 units
            # (1 unit to 5€ and 1 unit to 7€) and in case of a product return of 1 unit, we can't
            # know which of the 2 costs has to be used (5€ or 7€?). So at that time, thanks to the
            # average valuation price we are storing we will valuate it at 6€
            valuation_price = sum(q.qty * q.cost for q in move.quant_ids)
            average_valuation_price = valuation_price / move.product_qty

            move.product_id.with_context(force_company=move.company_id.id).sudo().write({'standard_price': average_valuation_price})
            move.write({'price_unit': average_valuation_price})

        for move in self.filtered(lambda move: move.product_id.cost_method != 'real' and not move.origin_returned_move_id):
            # Unit price of the move should be the current standard price, taking into account
            # price fluctuations due to products received between move creation (e.g. at SO
            # confirmation) and move set to done (delivery completed).
            move.write({'price_unit': move.product_id.standard_price})

    @api.multi
    def _get_accounting_data_for_valuation(self):
        """ Return the accounts and journal to use to post Journal Entries for
        the real-time valuation of the quant. """
        self.ensure_one()
        accounts_data = self.product_id.product_tmpl_id.get_product_accounts()

        if self.location_id.valuation_out_account_id:
            acc_src = self.location_id.valuation_out_account_id.id
        else:
            acc_src = accounts_data['stock_input'].id

        if self.location_dest_id.valuation_in_account_id:
            acc_dest = self.location_dest_id.valuation_in_account_id.id
        else:
            acc_dest = accounts_data['stock_output'].id

        acc_valuation = accounts_data.get('stock_valuation', False)
        if acc_valuation:
            acc_valuation = acc_valuation.id
        if not accounts_data.get('stock_journal', False):
            raise UserError(_('You don\'t have any stock journal defined on your product category, check if you have installed a chart of accounts'))
        if not acc_src:
            raise UserError(_('Cannot find a stock input account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (self.product_id.name))
        if not acc_dest:
            raise UserError(_('Cannot find a stock output account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (self.product_id.name))
        if not acc_valuation:
            raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))
        journal_id = accounts_data['stock_journal'].id
        return journal_id, acc_src, acc_dest, acc_valuation

    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given quant.
        """
        self.ensure_one()

        if self._context.get('force_valuation_amount'):
            valuation_amount = self._context.get('force_valuation_amount')
        else:
            if self.product_id.cost_method == 'average':
                valuation_amount = cost if self.location_id.usage == 'supplier' and self.location_dest_id.usage == 'internal' else self.product_id.standard_price
            else:
                valuation_amount = cost if self.product_id.cost_method == 'real' else self.product_id.standard_price
        # the standard_price of the product may be in another decimal precision, or not compatible with the coinage of
        # the company currency... so we need to use round() before creating the accounting entries.
        debit_value = self.company_id.currency_id.round(valuation_amount * qty)

        # check that all data is correct
        if self.company_id.currency_id.is_zero(debit_value):
            if self.product_id.cost_method == 'standard':
                raise UserError(_("The found valuation amount for product %s is zero. Which means there is probably a configuration error. Check the costing method and the standard price") % (self.product_id.name,))
            return []
        credit_value = debit_value

        if self.product_id.cost_method == 'average' and self.company_id.anglo_saxon_accounting:
            # in case of a supplier return in anglo saxon mode, for products in average costing method, the stock_input
            # account books the real purchase price, while the stock account books the average price. The difference is
            # booked in the dedicated price difference account.
            if self.location_dest_id.usage == 'supplier' and self.origin_returned_move_id and self.origin_returned_move_id.purchase_line_id:
                debit_value = self.origin_returned_move_id.price_unit * qty
            # in case of a customer return in anglo saxon mode, for products in average costing method, the stock valuation
            # is made using the original average price to negate the delivery effect.
            if self.location_id.usage == 'customer' and self.origin_returned_move_id:
                debit_value = self.origin_returned_move_id.price_unit * qty
                credit_value = debit_value
        partner_id = (self.picking_id.partner_id and self.env['res.partner']._find_accounting_partner(self.picking_id.partner_id).id) or False
        debit_line_vals = {
            'name': self.name,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': self.picking_id.name,
            'partner_id': partner_id,
            'debit': debit_value,
            'credit': 0,
            'account_id': debit_account_id,
        }
        credit_line_vals = {
            'name': self.name,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': self.picking_id.name,
            'partner_id': partner_id,
            'credit': credit_value,
            'debit': 0,
            'account_id': credit_account_id,
        }
        res = [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
        if credit_value != debit_value:
            # for supplier returns of product in average costing method, in anglo saxon mode
            diff_amount = debit_value - credit_value
            price_diff_account = self.product_id.property_account_creditor_price_difference
            if not price_diff_account:
                price_diff_account = self.product_id.categ_id.property_account_creditor_price_difference_categ
            if not price_diff_account:
                raise UserError(_('Configuration error. Please configure the price difference account on the product or its category to process this operation.'))
            price_diff_line = {
                'name': self.name,
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'ref': self.picking_id.name,
                'partner_id': partner_id,
                'credit': diff_amount > 0 and diff_amount or 0,
                'debit': diff_amount < 0 and -diff_amount or 0,
                'account_id': price_diff_account.id,
            }
            res.append((0, 0, price_diff_line))
        return res
