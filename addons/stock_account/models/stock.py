# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round, pycompat

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


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'
    
    @api.multi
    def write(self, vals):
        super(StockMoveLine, self).write(vals)
        if 'qty_done' in vals:
            for move in self.mapped('move_id').filtered(lambda m: m.state == 'done'):
                if move.location_id.usage not in ('internal', 'transit') and move.location_dest_id.usage in ('internal', 'transit'):
                    move.value = move.quantity_done * move.price_unit
                move.replay_valuation()


class StockMove(models.Model):
    _inherit = "stock.move"

    to_refund = fields.Boolean(string="To Refund (update SO/PO)",
                               help='Trigger a decrease of the delivered/received quantity in the associated Sale Order/Purchase Order')

    value = fields.Float()
    cumulated_value = fields.Float()
    remaining_qty = fields.Float()
    last_done_move_id = fields.Many2one('stock.move')
    last_done_remaining_qty = fields.Float()
    last_done_qty = fields.Float()

    # TODO: add constraints remaining_qty >= 0
    # TODO: add constrain price_unit = 0 on done move? -> no

    @api.multi
    def _get_price_unit(self):
        self.ensure_one()
        if self.product_id.cost_method == 'average':
            return self.product_id.average_price or self.product_id.standard_price
        if self.product_id.cost_method == 'fifo':
            return self.product_id.fifo_price or self.product_id.standard_price
        return self.product_id.standard_price

    def _update_future_cumulated_value(self, value):
        self.ensure_one()
        domain = self._get_all_domain()
        domain += ['|', ('date', '>', self.date), 
                   '&', ('date', '=', self.date), ('id', '>', self.id)]
        moves = self.search(domain, order='date, id')
        for move in moves:
            move.cumulated_value += value

    @api.model
    def _get_in_base_domain(self, company_id=False):
        return [('state', '=', 'done'), 
                ('location_id.company_id', '=', False), 
                ('location_dest_id.company_id', '=', company_id or self.env.user_id.company_id.id)]

    @api.model
    def _get_out_base_domain(self, company_id=False):
        return [('state', '=', 'done'), 
                ('location_id.company_id', '=', company_id or self.env.user_id.company_id.id), 
                ('location_dest_id.company_id', '=', False)]

    @api.model
    def _get_all_base_domain(self, company_id=False):
        return [('state', '=', 'done'), 
                '|', '&', ('location_id.company_id', '=', False), 
                ('location_dest_id.company_id', '=', company_id or self.env.user_id.company_id.id),
                '&', ('location_id.company_id', '=', company_id or self.env.user_id.company_id.id), 
                ('location_dest_id.company_id', '=', False)]

    def _get_in_domain(self):
        return [('product_id', '=', self.product_id.id)] + self._get_in_base_domain(company_id=self.company_id.id)

    def _get_out_domain(self):
        return [('product_id', '=', self.product_id.id)] + self._get_out_base_domain(company_id=self.company_id.id)

    def _get_all_domain(self):
        return [('product_id', '=', self.product_id.id)] + self._get_all_base_domain(company_id=self.company_id.id)
        
    def _is_in_move(self):
        return not self.location_id.company_id and self.location_dest_id.company_id.id == self.company_id.id 

    def _is_out_move(self):
        return self.location_id.company_id.id == self.company_id.id and not self.location_dest_id.company_id

    @api.multi
    def replay_average(self):
        """
            We try to find a move before this one and use its last done
            qty and cumulated value to update those of the moves after. 
            Meanwhile, we recalculate the averages to determine the value of the outgoing moves
        """
        all_domain = self._get_all_domain()
        start_domain = all_domain + ['|', ('date', '<', self.date), '&', ('date', '=', self.date), ('id', '<', self.id)]
        start_move = self.search(start_domain, limit=1, order='date desc, id desc')
        if start_move:
            all_domain = ['|', ('date', '>', start_move.date),
                     '&', ('date', '=', start_move.date), ('id', '>', start_move.id)] + all_domain
        next_moves = self.search(all_domain, order='date, id')
        if start_move:
            last_cumulated_value = start_move.cumulated_value
            last_done_qty_available = start_move.last_done_qty
        else:
            last_cumulated_value = 0.0
            last_done_qty_available = 0.0
        for move in next_moves:
            if move._is_out_move():
                if last_done_qty_available:
                    move.value = - (last_cumulated_value * move.product_qty / last_done_qty_available)
                last_done_qty_available -= move.product_qty
            else:
                last_done_qty_available += move.product_qty
            last_cumulated_value += move.value
            move.write({'cumulated_value': last_cumulated_value, 
                        'last_done_qty': last_done_qty_available})

    def replay_fifo(self):
        """
            We try to find an outgoing move before this one that did not 
            have a negative stock when it was done and has a corresponding in move. 
            By taking the later in moves and out moves, we recalculate the remaining qties and values on the moves
            Afterwards, we take both in and out moves chronologically and recalculate cumulated value and qty done
        """
        out_domain = self._get_out_domain()
        out_domain += ['|', ('date', '<', self.date),
                     '&', ('date', '=', self.date), ('id', '<', self.id), 
                     ('last_done_move_id', '!=', False),
                     ('last_done_qty', '>=', 0.0)]
        start_move = self.search(out_domain, limit=1, order='date desc, id desc')
        # normally, this will be the case as last_done_qty > 0.0
        use_start_move = start_move and start_move.last_done_move_id and (start_move.last_done_move_id.date < start_move.date or (start_move.last_done_move_id.date == start_move.date and start_move.last_done_move_id.id < start_move.id))
        
        in_domain = self._get_in_domain()
        out_domain = self._get_out_domain()
        if use_start_move:
            first_in_move = start_move.last_done_move_id
            first_in_remaining_qty = start_move.last_done_remaining_qty
            in_domain += ['|', ('date', '>', start_move.last_done_move_id.date), 
                          '&', ('id', '>', start_move.last_done_move_id.id), ('date', '=', start_move.last_done_move_id.date)]
            out_domain += ['|', ('date', '>', start_move.date), 
                           '&', ('date', '=', start_move.date), ('id', '>', start_move.id)]
        else:
            first_in_move = False
            first_in_remaining_qty = 0
        in_moves_needed = self.search(in_domain, order='date, id')
        next_out_moves = self.search(out_domain, order='date, id')
        last_in_move = first_in_move
        last_remaining_qty = first_in_remaining_qty
        if not first_in_move or last_remaining_qty == 0.0 and in_moves_needed:
            last_in_move = in_moves_needed[0]
            in_moves_needed -= in_moves_needed[0]
            last_remaining_qty = last_in_move.product_qty
        if last_in_move:
            for out_move in next_out_moves:
                total_qty = out_move.product_qty
                total_value = 0
                stop = False
                while(total_qty > 0) and not stop:
                    if last_remaining_qty < total_qty:
                        total_qty -= last_remaining_qty
                        total_value += last_remaining_qty * last_in_move.price_unit
                        last_in_move.remaining_qty = 0.0
                        if in_moves_needed:
                            last_in_move = in_moves_needed[0]
                            in_moves_needed -= in_moves_needed[0]
                            last_remaining_qty = last_in_move.product_qty
                        else:
                            stop = True
                    else:
                        total_value += total_qty * last_in_move.price_unit
                        last_remaining_qty -= total_qty
                        last_in_move.remaining_qty = last_remaining_qty
                        total_qty = 0
                out_move.write({'last_done_remaining_qty': last_remaining_qty, 
                                'last_done_move_id': last_in_move.id, 
                                'value': -total_value,
                                'price_unit': total_value / out_move.product_qty,})
                out_move.remaining_qty = total_qty
            for move in in_moves_needed:
                move.remaining_qty = move.product_qty
        # Recalculate last_done_qty and cumulated value on next moves
        domain = self._get_all_domain()
        if use_start_move:
            domain = ['|', ('date', '>', start_move.date),
                     '&', ('date', '=', start_move.date), ('id', '>', start_move.id)] + domain
        next_moves = self.search(domain, order='date, id')
        if use_start_move:
            cumulated_value = start_move.cumulated_value
            qty_available = start_move.last_done_remaining_qty
        else:
            cumulated_value = 0.0
            qty_available = 0.0
        for move in next_moves:
            if move.location_dest_id.usage in ('internal', 'transit'):
                qty_available += move.product_qty
            else:
                qty_available -= move.product_qty
            cumulated_value += move.value
            move.write({'last_done_qty': qty_available,
                        'cumulated_value': cumulated_value})

    def replay_valuation(self):
        self.ensure_one()
        old_value = self.product_id.stock_value
        self.replay()
        self.product_id._compute_stock_value()
        new_value = self.product_id.stock_value
        if self.product_id.valuation == 'real_time':
            self._account_entry_move_adapt_value(new_value - old_value)

    def replay(self):
        if self.product_id.cost_method == 'fifo':
            self.replay_fifo()
        elif self.product_id.cost_method == 'average':
            self.replay_average()

    @api.multi
    def action_done(self):
        """
            For incoming moves, it will put the value corresponding with that move on the stock move, 
            except for standard cost price, where it will put the standard price.  
            For FIFO, it will also check if there was negative stock and compensate the corresponding out moves.   
            For outgoing moves, average price, will apply the average price formula, FIFO will search the 
            corresponding incoming moves where it can reduce the remaining_qty while standard takes the cost from the product
        """
        qty_available = {}
        for move in self:
            #Should write move.price_unit here maybe, certainly on incoming moves
            if move.product_id.cost_method == 'average':
                qty_available[move.product_id.id] = move.product_id.with_context(internal=True).qty_available
        res = super(StockMove, self).action_done()
        for move in res:
            if move._is_in_move():
                if move.product_id.cost_method in ['fifo', 'average']:
                    if not move.price_unit:
                        move.price_unit = move._get_price_unit()
                    move_value = move.price_unit * move.product_qty
                    move.write({'value': move_value, 
                                'cumulated_value': move.product_id._get_latest_cumulated_value(not_move=move) + move_value, 
                                'remaining_qty': move.product_qty, 
                                'last_done_qty': move.product_id.with_context(internal=True).qty_available,})
                    if move.product_id.cost_method == 'fifo':
                        # If you find an out with qty_remaining (because of negative stock), you can change it over there
                        candidates_out = move.product_id._get_candidates_out_move()
                        qty_to_take = move.product_qty
                        for candidate in candidates_out:
                            if candidate.remaining_qty < qty_to_take:
                                qty_taken_on_candidate = candidate.remaining_qty
                            else:
                                qty_taken_on_candidate = qty_to_take
                            move.remaining_qty -= qty_taken_on_candidate
                            qty_to_take -= qty_taken_on_candidate
                            candidate_value = candidate.value - move.price_unit * qty_taken_on_candidate
                            candidate.write({'value': candidate_value, 
                                             'cumulated_value': candidate.cumulated_value - move.price_unit * qty_taken_on_candidate, 
                                             'price_unit': - (candidate_value / candidate.product_qty),
                                             'last_done_move_id': move.id,
                                             'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate})
                            # Might be replaced be reusable code
                            candidate._update_future_cumulated_value(move.price_unit * qty_taken_on_candidate)
                            if qty_to_take <= 0:
                                break
                else:
                    move.write({'price_unit': move.product_id.standard_price,
                                'value': move.product_id.standard_price * move.product_qty})
            elif move._is_out_move():
                if move.product_id.cost_method == 'fifo':
                    qty_to_take = move.product_qty
                    tmp_value = 0
                    candidates = move.product_id._get_candidates_move()
                    last_candidate = False
                    for candidate in candidates:
                        if candidate.remaining_qty <= qty_to_take:
                            qty_taken_on_candidate = candidate.remaining_qty
                        else:
                            qty_taken_on_candidate = qty_to_take
                        tmp_value += qty_taken_on_candidate * candidate.price_unit
                        candidate.remaining_qty -= qty_taken_on_candidate
                        qty_to_take -= qty_taken_on_candidate
                        if qty_to_take == 0:
                            break
                        last_candidate = candidate
                    move.write({'value': -tmp_value,
                                'price_unit': tmp_value / move.product_qty,
                                'cumulated_value': move.product_id._get_latest_cumulated_value(not_move=move) - tmp_value,
                                'last_done_qty': move.product_id.with_context(internal=True).qty_available,
                                'remaining_qty': qty_to_take if qty_to_take > 0 else 0.0, #TODO: price is 0 on it, because it is the easiest, but it might use the standard price e.g.
                                'last_done_move_id': last_candidate and last_candidate.id or False,
                                'last_done_remaining_qty': last_candidate and last_candidate.remaining_qty or 0.0,
                                })
                elif move.product_id.cost_method == 'average':
                    curr_rounding = move.company_id.currency_id.rounding
                    avg_price_unit = float_round(move.product_id._get_latest_cumulated_value(not_move=move) / qty_available[move.product_id.id], precision_rounding=curr_rounding)
                    move_value = float_round(-avg_price_unit * move.product_qty, precision_rounding=curr_rounding)
                    move.write({'value': move_value,
                                'price_unit': move_value / move.product_qty,
                                'cumulated_value': move.product_id._get_latest_cumulated_value(not_move=move) + move_value,
                                'last_done_qty': move.product_id.with_context(internal=True).qty_available,
                                })
                else:
                    move.write({'price_unit': move.product_id.standard_price,
                                'value': - move.product_id.standard_price * move.product_qty})
                
        for move in res.filtered(lambda m: m.product_id.valuation == 'real_time'):
            move._account_entry_move()
        return res

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
            valuation_amount = cost

        # the standard_price of the product may be in another decimal precision, or not compatible with the coinage of
        # the company currency... so we need to use round() before creating the accounting entries.
        debit_value = self.company_id.currency_id.round(valuation_amount)

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
            'debit': debit_value if debit_value > 0 else 0,
            'credit': -debit_value if debit_value < 0 else 0,
            'account_id': debit_account_id,
        }
        credit_line_vals = {
            'name': self.name,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': self.picking_id.name,
            'partner_id': partner_id,
            'credit': credit_value if credit_value > 0 else 0,
            'debit': -credit_value if credit_value < 0 else 0,
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

    def _create_account_move_line(self, credit_account_id, debit_account_id, journal_id, value_adapt = 0.0):
        self.ensure_one()
        AccountMove = self.env['account.move']
        if not value_adapt:
            value_adapt = self.value
        move_lines = self._prepare_account_move_line(self.product_qty, abs(value_adapt), credit_account_id, debit_account_id)
        if move_lines:
            date = self._context.get('force_period_date', fields.Date.context_today(self))
            new_account_move = AccountMove.create({
                'journal_id': journal_id,
                'line_ids': move_lines,
                'date': date,
                'ref': self.picking_id.name,
                'company_id': self.company_id.id})
            new_account_move.post()

    def _account_entry_move(self):
        """ Accounting Valuation Entries """
        self.ensure_one()
        if self.product_id.type != 'product':
            # no stock valuation for consumable products
            return False
        if self.restrict_partner_id:
            # if the move isn't owned by the company, we don't make any valuation
            return False

        location_from = self.location_id
        location_to = self.location_dest_id
        company_from = location_from.usage == 'internal' and location_from.company_id or False
        company_to = location_to and (location_to.usage == 'internal') and location_to.company_id or False

        # Create Journal Entry for products arriving in the company; in case of routes making the link between several
        # warehouse of the same company, the transit location belongs to this company, so we don't need to create accounting entries
        if company_to and (self.location_id.usage not in ('internal', 'transit') and self.location_dest_id.usage == 'internal' or company_from != company_to):
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
            if location_from and location_from.usage == 'customer':  # goods returned from customer
                self.with_context(force_company=company_to.id)._create_account_move_line(acc_dest, acc_valuation, journal_id)
            else:
                self.with_context(force_company=company_to.id)._create_account_move_line(acc_src, acc_valuation, journal_id)

        # Create Journal Entry for products leaving the company
        if company_from and (self.location_id.usage == 'internal' and self.location_dest_id.usage not in ('internal', 'transit') or company_from != company_to):
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
            if location_to and location_to.usage == 'supplier':  # goods returned to supplier
                self.with_context(force_company=company_from.id)._create_account_move_line(acc_valuation, acc_src, journal_id)
            else:
                self.with_context(force_company=company_from.id)._create_account_move_line(acc_valuation, acc_dest, journal_id)

        if self.company_id.anglo_saxon_accounting and self.location_id.usage == 'supplier' and self.location_dest_id.usage == 'customer':
            # Creates an account entry from stock_input to stock_output on a dropship move. https://github.com/odoo/odoo/issues/12687
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
            self._create_account_move_line(acc_src, acc_dest, journal_id)
            

    def _account_entry_move_adapt_value(self, value_adapt):
        """ Adapt value stuff"""
        self.ensure_one()
        if self.product_id.type != 'product' or self.restrict_partner_id: #Owner could be about some quantities only?
            return False
        
        in_move = self._is_in_move()
        out_move = self._is_out_move()
        in_move_normal = False
        in_move_return = False
        out_move_normal = False
        out_move_return = False
        if in_move or out_move:
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
            if value_adapt > 0.0 and in_move:
                if self.location_id.usage == 'customer':
                    in_move_return = True
                else:
                    in_move_normal = True
            elif value_adapt < 0.0 and out_move:
                if self.location_dest_id.usage == 'supplier':
                    out_move_return = True
                else:
                    out_move_normal = True
            elif value_adapt < 0.0 and in_move:
                if self.location_id.usage == 'customer':
                    out_move_normal =True
                else:
                    out_move_return = True
            elif value_adapt > 0.0 and out_move:
                if self.location_dest_id.usage == 'supplier':
                    in_move_normal = True
                else:
                    in_move_return = True

        if in_move_return:  # goods returned from customer
            self._create_account_move_line(acc_dest, acc_valuation, journal_id, value_adapt=value_adapt)
        elif in_move_normal:
            self.with_context._create_account_move_line(acc_src, acc_valuation, journal_id, value_adapt=value_adapt)
        elif out_move_return:
            self._create_account_move_line(acc_valuation, acc_src, journal_id, value_adapt=value_adapt)
        elif out_move_normal:
            self._create_account_move_line(acc_valuation, acc_dest, journal_id, value_adapt=value_adapt)
        # Dropship
        if self.company_id.anglo_saxon_accounting and self.location_id.usage == 'supplier' and self.location_dest_id.usage == 'customer':
            # Creates an account entry from stock_input to stock_output on a dropship move. https://github.com/odoo/odoo/issues/12687
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
            if value_adapt > 0.0:
                self._create_account_move_line(acc_src, acc_dest, journal_id, value_adapt=value_adapt)
            else:
                self._create_account_move_line(acc_dest, acc_src, journal_id, value_adapt=value_adapt)
            


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    @api.multi
    def _create_returns(self):
        new_picking_id, pick_type_id = super(StockReturnPicking, self)._create_returns()
        new_picking = self.env['stock.picking'].browse([new_picking_id])
        for move in new_picking.move_lines:
            return_picking_line = self.product_return_moves.filtered(lambda r: r.move_id == move.origin_returned_move_id)
            if return_picking_line and return_picking_line.to_refund:
                move.to_refund = True
        return new_picking_id, pick_type_id


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    to_refund = fields.Boolean(string="To Refund (update SO/PO)", help='Trigger a decrease of the delivered/received quantity in the associated Sale Order/Purchase Order')
