# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, OrderedSet

import logging
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    to_refund = fields.Boolean(
        "Update quantities on SO/PO", copy=True, default=True,
        help='Trigger a decrease of the delivered/received quantity in the associated Sale Order/Purchase Order')
    account_move_ids = fields.One2many('account.move', 'stock_move_id')
    stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'stock_move_id')
    analytic_account_line_ids = fields.Many2many('account.analytic.line', copy=False)

    def _inverse_picked(self):
        super()._inverse_picked()
        self._account_analytic_entry_move()

    def _filter_anglo_saxon_moves(self, product):
        return self.filtered(lambda m: m.product_id.id == product.id)

    def action_get_account_moves(self):
        self.ensure_one()
        action_data = self.env['ir.actions.act_window']._for_xml_id('account.action_move_journal_line')
        action_data['domain'] = [('id', 'in', self.account_move_ids.ids)]
        return action_data

    def _action_cancel(self):
        self.analytic_account_line_ids.unlink()
        return super()._action_cancel()

    def _should_force_price_unit(self):
        self.ensure_one()
        return False

    def _get_price_unit(self):
        """ Returns the unit price to value this stock move """
        self.ensure_one()
        price_unit = self.price_unit
        precision = self.env['decimal.precision'].precision_get('Product Price')
        # If the move is a return, use the original move's price unit.
        if self.origin_returned_move_id and self.origin_returned_move_id.sudo().stock_valuation_layer_ids:
            layers = self.origin_returned_move_id.sudo().stock_valuation_layer_ids
            # dropshipping create additional positive svl to make sure there is no impact on the stock valuation
            # We need to remove them from the computation of the price unit.
            if self.origin_returned_move_id._is_dropshipped() or self.origin_returned_move_id._is_dropshipped_returned():
                layers = layers.filtered(lambda l: l.product_id.uom_id.compare(l.value, 0) <= 0)
            layers |= layers.stock_valuation_layer_ids
            if self.product_id.lot_valuated:
                layers_by_lot = layers.grouped('lot_id')
                prices = defaultdict(lambda: 0)
                for lot, stock_layers in layers_by_lot.items():
                    qty = sum(stock_layers.mapped("quantity"))
                    val = sum(stock_layers.mapped("value"))
                    prices[lot] = val / qty if not self.product_id.uom_id.is_zero(qty) else 0
            else:
                quantity = sum(layers.mapped("quantity"))
                prices = {self.env['stock.lot']: sum(layers.mapped("value")) / quantity if not layers.uom_id.is_zero(quantity) else 0}
            return prices

        if not float_is_zero(price_unit, precision) or self._should_force_price_unit():
            if self.product_id.lot_valuated:
                return dict.fromkeys(self.lot_ids, price_unit)
            else:
                return {self.env['stock.lot']: price_unit}
        else:
            if self.product_id.lot_valuated:
                return {lot: lot.standard_price or self.product_id.with_company(self.company_id).standard_price for lot in self.lot_ids}
            else:
                return {self.env['stock.lot']: self.product_id.with_company(self.company_id).standard_price}

    @api.model
    def _get_valued_types(self):
        """Returns a list of `valued_type` as strings. During `action_done`, we'll call
        `_is_[valued_type]'. If the result of this method is truthy, we'll consider the move to be
        valued.

        :returns: a list of `valued_type`
        :rtype: list
        """
        return ['in', 'out', 'dropshipped', 'dropshipped_returned']

    def _get_move_directions(self):
        move_in_ids = set()
        move_out_ids = set()
        locations_should_be_valued = (self.move_line_ids.location_id | self.move_line_ids.location_dest_id).filtered(lambda l: l._should_be_valued())
        for record in self:
            for move_line in record.move_line_ids:
                if move_line._should_exclude_for_valuation() or not move_line.picked:
                    continue
                if move_line.location_id not in locations_should_be_valued and move_line.location_dest_id in locations_should_be_valued:
                    move_in_ids.add(record.id)
                if move_line.location_id in locations_should_be_valued and move_line.location_dest_id not in locations_should_be_valued:
                    move_out_ids.add(record.id)

        move_directions = defaultdict(set)
        for record in self:
            if record.id in move_in_ids and not record._is_dropshipped_returned():
                move_directions[record.id].add('in')

            if record.id in move_out_ids and not record._is_dropshipped():
                move_directions[record.id].add('out')

        return move_directions

    def _get_in_move_lines(self):
        """ Returns the `stock.move.line` records of `self` considered as incoming. It is done thanks
        to the `_should_be_valued` method of their source and destionation location as well as their
        owner.

        :returns: a subset of `self` containing the incoming records
        :rtype: recordset
        """
        self.ensure_one()
        res = OrderedSet()
        for move_line in self.move_line_ids:
            if not move_line.picked:
                continue
            if move_line._should_exclude_for_valuation():
                continue
            if not move_line.location_id._should_be_valued() and move_line.location_dest_id._should_be_valued():
                res.add(move_line.id)
        return self.env['stock.move.line'].browse(res)

    def _is_in(self):
        """Check if the move should be considered as entering the company so that the cost method
        will be able to apply the correct logic.

        :returns: True if the move is entering the company else False
        :rtype: bool
        """
        self.ensure_one()
        if self._get_in_move_lines() and not self._is_dropshipped_returned():
            return True
        return False

    def _get_out_move_lines(self):
        """ Returns the `stock.move.line` records of `self` considered as outgoing. It is done thanks
        to the `_should_be_valued` method of their source and destionation location as well as their
        owner.

        :returns: a subset of `self` containing the outgoing records
        :rtype: recordset
        """
        res = self.env['stock.move.line']
        for move_line in self.move_line_ids:
            if not move_line.picked:
                continue
            if move_line._should_exclude_for_valuation():
                continue
            if move_line.location_id._should_be_valued() and not move_line.location_dest_id._should_be_valued():
                res |= move_line
        return res

    def _is_out(self):
        """Check if the move should be considered as leaving the company so that the cost method
        will be able to apply the correct logic.

        :returns: True if the move is leaving the company else False
        :rtype: bool
        """
        self.ensure_one()
        if self._get_out_move_lines() and not self._is_dropshipped():
            return True
        return False

    def _is_dropshipped(self):
        """Check if the move should be considered as a dropshipping move so that the cost method
        will be able to apply the correct logic.

        :returns: True if the move is a dropshipping one else False
        :rtype: bool
        """
        self.ensure_one()
        return (self.location_id.usage == 'supplier' or (self.location_id.usage == 'transit' and not self.location_id.company_id)) \
           and (self.location_dest_id.usage == 'customer' or (self.location_dest_id.usage == 'transit' and not self.location_dest_id.company_id))

    def _is_dropshipped_returned(self):
        """Check if the move should be considered as a returned dropshipping move so that the cost
        method will be able to apply the correct logic.

        :returns: True if the move is a returned dropshipping one else False
        :rtype: bool
        """
        self.ensure_one()
        return (self.location_id.usage == 'customer' or (self.location_id.usage == 'transit' and not self.location_id.company_id)) \
           and (self.location_dest_id.usage == 'supplier' or (self.location_dest_id.usage == 'transit' and not self.location_dest_id.company_id))

    def _prepare_common_svl_vals(self):
        """When a `stock.valuation.layer` is created from a `stock.move`, we can prepare a dict of
        common vals.

        :returns: the common values when creating a `stock.valuation.layer` from a `stock.move`
        :rtype: dict
        """
        self.ensure_one()
        detail = ', '.join(self.scrap_id.scrap_reason_tag_ids.mapped('name')) if self.scrapped else self.product_id.name
        return {
            'stock_move_id': self.id,
            'company_id': self.company_id.id,
            'product_id': self.product_id.id,
            'description': '%s - %s' % (self.reference, detail)
        }

    def _create_in_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circumstances, the quantity to value is different than
            the initial demand of the move (Default value = None). The lot to value is given in
            case of lot valuated product.
        :type forced_quantity: tuple(stock.lot, float)
        """
        svl_vals_list = self._get_in_svl_vals(forced_quantity)
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)

    def _create_out_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circumstances, the quantity to value is different than
            the initial demand of the move (Default value = None). The lot to value is given in
            case of lot valuated product.
        :type forced_quantity: tuple(stock.lot, float)
        """
        svl_vals_list = self._get_out_svl_vals(forced_quantity)
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)

    def _get_out_svl_vals(self, forced_quantity):
        svl_vals_list = []
        for move in self:
            move = move.with_company(move.company_id)
            lines = move._get_out_move_lines()
            quantities = defaultdict(float)
            if forced_quantity:
                quantities[forced_quantity[0]] += forced_quantity[1]
            else:
                for line in lines:
                    quantities[line.lot_id] += line.quantity_product_uom
            if move.product_id.uom_id.is_zero(sum(quantities.values())):
                continue

            if move.product_id.lot_valuated:
                vals = []
                for lot_id, qty in quantities.items():
                    out_vals = move.product_id._prepare_out_svl_vals(
                        qty,
                        move.company_id,
                        lot=lot_id
                    )
                    vals.append(out_vals)
            else:
                vals = [move.product_id._prepare_out_svl_vals(sum(quantities.values()), move.company_id)]
            for val in vals:
                val.update(move._prepare_common_svl_vals())
                if forced_quantity and not move.scrapped:
                    val['description'] = _('Correction of %s (modification of past move)', move.reference)
                val['description'] += val.pop('rounding_adjustment', '')
            svl_vals_list += vals
        return svl_vals_list

    def _create_dropshipped_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circumstances, the quantity to value is different than
            the initial demand of the move (Default value = None). The lot to value is given in
            case of lot valuated product.
        :type forced_quantity: tuple(stock.lot, float)
        """
        svl_vals_list = self._get_dropshipped_svl_vals(forced_quantity)
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)

    def _get_dropshipped_svl_vals(self, forced_quantity):
        svl_vals_list = []
        for move in self:
            move = move.with_company(move.company_id)
            lines = move.move_line_ids
            quantities = defaultdict(float)
            if forced_quantity:
                quantities[forced_quantity[0]] += forced_quantity[1]
            elif move.product_id.lot_valuated:
                for line in lines:
                    quantities[line.lot_id] += line.quantity_product_uom
            else:
                quantities[self.env['stock.lot']] += move.product_qty

            unit_cost = move._get_price_unit()
            if move.product_id.cost_method == 'standard':
                if move.product_id.lot_valuated:
                    unit_cost = {lot: lot.standard_price for lot in quantities}
                else:
                    unit_cost = {self.env['stock.lot']: move.product_id.standard_price}

            common_vals = dict(move._prepare_common_svl_vals(), remaining_qty=0)
            if forced_quantity:
                common_vals['description'] = _('Correction of %s (modification of past move)', move.picking_id.name or move.reference)

            # create the in if it does not come from a valued location (eg subcontract -> customer)
            if not move.location_id._should_be_valued():
                svl_vals_list += [{
                    'unit_cost': unit_cost[lot_id],
                    'value': unit_cost[lot_id] * qty,
                    'quantity': qty,
                    'lot_id': lot_id and lot_id.id,
                    **common_vals,
                } for lot_id, qty in quantities.items()]

            # create the out if it does not go to a valued location (eg customer -> subcontract)
            if not move.location_dest_id._should_be_valued():
                svl_vals_list += [{
                    'unit_cost': unit_cost[lot_id],
                    'value': unit_cost[lot_id] * qty * -1,
                    'quantity': qty * -1,
                    'lot_id': lot_id and lot_id.id,
                    **common_vals,
                } for lot_id, qty in quantities.items()]

        return svl_vals_list

    def _create_dropshipped_returned_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circumstances, the quantity to value is different than
            the initial demand of the move (Default value = None). The lot to value is given in
            case of lot valuated product.
        :type forced_quantity: tuple(stock.lot, float)
        """
        return self._create_dropshipped_svl(forced_quantity=forced_quantity)

    def _action_done(self, cancel_backorder=False):
        # Init a dict that will group the moves by valuation type, according to `move._is_valued_type`.
        valued_moves = {valued_type: self.env['stock.move'] for valued_type in self._get_valued_types()}
        for move in self:
            if move.state == 'done':
                continue
            if move.product_uom.is_zero(move.quantity):
                continue
            if not any(move.move_line_ids.mapped('picked')):
                continue
            for valued_type in self._get_valued_types():
                if getattr(move, '_is_%s' % valued_type)():
                    valued_moves[valued_type] |= move

        res = super()._action_done(cancel_backorder=cancel_backorder)

        # AVCO application
        valued_moves['in'].product_price_update_before_done()

        # '_action_done' might have deleted some exploded stock moves
        valued_moves = {value_type: moves.exists() for value_type, moves in valued_moves.items()}

        # '_action_done' might have created an extra move to be valued
        for move in res - self:
            for valued_type in self._get_valued_types():
                if getattr(move, '_is_%s' % valued_type)():
                    valued_moves[valued_type] |= move

        stock_valuation_layers = self.env['stock.valuation.layer'].sudo()
        # Create the valuation layers in batch by calling `moves._create_valued_type_svl`.
        for valued_type in self._get_valued_types():
            todo_valued_moves = valued_moves[valued_type]
            if todo_valued_moves:
                todo_valued_moves._sanity_check_for_valuation()
                stock_valuation_layers |= getattr(todo_valued_moves, '_create_%s_svl' % valued_type)()

        stock_valuation_layers._validate_accounting_entries()
        stock_valuation_layers._validate_analytic_accounting_entries()

        valued_moves['out'].filtered(lambda m: m.product_id.lot_valuated).sudo()._product_price_update_after_done()

        stock_valuation_layers._check_company()

        # For every in move, run the vacuum for the linked product.
        products_to_vacuum = valued_moves['in'].mapped('product_id')
        company = valued_moves['in'].mapped('company_id') and valued_moves['in'].mapped('company_id')[0] or self.env.company
        products_to_vacuum._run_fifo_vacuum(company)

        return res

    def _sanity_check_for_valuation(self):
        for move in self:
            # Apply restrictions on the stock move to be able to make
            # consistent accounting entries.
            if move._is_in() and move._is_out():
                raise UserError(_("The move lines are not in a consistent state: some are entering and other are leaving the company."))
            company_src = move.mapped('move_line_ids.location_id.company_id')
            company_dst = move.mapped('move_line_ids.location_dest_id.company_id')
            try:
                if company_src:
                    company_src.ensure_one()
                if company_dst:
                    company_dst.ensure_one()
            except ValueError:
                raise UserError(_("The move lines are not in a consistent states: they do not share the same origin or destination company."))
            if company_src and company_dst and company_src.id != company_dst.id:
                raise UserError(_("The move lines are not in a consistent states: they are doing an intercompany in a single step while they should go through the intercompany transit location."))

    def product_price_update_before_done(self, forced_qty=None):
        tmpl_dict = defaultdict(lambda: 0.0)
        lot_tmpl_dict = defaultdict(lambda: 0.0)
        # adapt standard price on incomming moves if the product cost_method is 'average'
        std_price_update = {}
        std_price_update_lot = {}
        for move in self:
            if not move._is_in():
                continue
            if move.with_company(move.company_id).product_id.cost_method == 'standard':
                continue
            product_tot_qty_available = move.product_id.sudo().with_company(move.company_id).quantity_svl + tmpl_dict[move.product_id.id]
            rounding = move.product_id.uom_id.rounding

            valued_move_lines = move._get_in_move_lines()
            quantity_by_lot = defaultdict(float)
            if forced_qty:
                quantity_by_lot[forced_qty[0]] += forced_qty[1]
            else:
                for valued_move_line in valued_move_lines:
                    quantity_by_lot[valued_move_line.lot_id] += valued_move_line.quantity_product_uom

            qty = sum(quantity_by_lot.values())
            move_cost = move._get_price_unit()
            if float_is_zero(product_tot_qty_available, precision_rounding=rounding) \
                    or float_is_zero(product_tot_qty_available + move.product_qty, precision_rounding=rounding) \
                    or float_is_zero(product_tot_qty_available + qty, precision_rounding=rounding):
                new_std_price = next(iter(move_cost.values()))
            else:
                # Get the standard price
                amount_unit = std_price_update.get((move.company_id.id, move.product_id.id)) or move.product_id.with_company(move.company_id).standard_price
                new_std_price = ((amount_unit * product_tot_qty_available) + (next(iter(move_cost.values())) * qty)) / (product_tot_qty_available + qty)

            tmpl_dict[move.product_id.id] += qty
            # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
            move.product_id.with_company(move.company_id.id).with_context(disable_auto_svl=True).sudo().write({'standard_price': new_std_price})
            std_price_update[move.company_id.id, move.product_id.id] = new_std_price

            # Update the standard price of the lot
            if not move.product_id.lot_valuated:
                continue
            for lot, qty in quantity_by_lot.items():
                qty_avail = lot.sudo().with_company(move.company_id).quantity_svl + lot_tmpl_dict[lot.id]
                if float_is_zero(qty_avail, precision_rounding=rounding) \
                        or float_is_zero(qty_avail + qty, precision_rounding=rounding):
                    new_std_price = move_cost[lot]
                else:
                    # Get the standard price
                    amount_unit = std_price_update_lot.get((move.company_id.id, lot.id)) or lot.with_company(move.company_id).standard_price
                    new_std_price = ((amount_unit * qty_avail) + (move_cost[lot] * qty)) / (qty_avail + qty)
                lot_tmpl_dict[lot.id] += qty
                lot.with_company(move.company_id.id).with_context(disable_auto_svl=True).sudo().standard_price = new_std_price
                std_price_update_lot[move.company_id.id, lot.id] = new_std_price

    def _product_price_update_after_done(self):
        """ Outgoing moves lot valuation should recompute the standard price of the product as the
        layer price unit may differ from the product price unit """
        for product, layers in self.stock_valuation_layer_ids.grouped('product_id').items():
            if all(not m._is_out() for m in layers.stock_move_id) or not product.lot_valuated:
                continue
            if layers.with_company(layers.company_id).product_id.cost_method == 'standard':
                continue
            product_qty = product.sudo().with_company(layers.company_id).quantity_svl
            product_value = product.sudo().with_company(layers.company_id).value_svl

            if product.uom_id.is_zero(product_qty):
                return

            # get the standard price
            # write the standard price, as superuser_id because a warehouse manager may not have the right to write on products
            new_std_price = product_value / product_qty
            product.with_company(layers.company_id.id).with_context(disable_auto_svl=True).sudo().write({'standard_price': new_std_price})

    def _get_accounting_data_for_valuation(self):
        """ Return the accounts and journal to use to post Journal Entries for
        the real-time valuation of the quant. """
        self.ensure_one()
        self = self.with_company(self.company_id)
        accounts_data = self.product_id.product_tmpl_id.get_product_accounts()

        acc_src = self._get_src_account(accounts_data)
        acc_dest = self._get_dest_account(accounts_data)

        acc_valuation = accounts_data.get('stock_valuation', False)
        if acc_valuation:
            acc_valuation = acc_valuation.id
        if not accounts_data.get('stock_journal', False):
            raise UserError(_('You don\'t have any stock journal defined on your product category, check if you have installed a chart of accounts.'))
        if not acc_src:
            raise UserError(_('Cannot find a stock input account for the product %s. You must define one on the product category, or on the location, before processing this operation.', self.product_id.display_name))
        if not acc_dest:
            raise UserError(_('Cannot find a stock output account for the product %s. You must define one on the product category, or on the location, before processing this operation.', self.product_id.display_name))
        if not acc_valuation:
            raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))
        journal_id = accounts_data['stock_journal'].id
        return journal_id, acc_src, acc_dest, acc_valuation

    def _get_in_svl_vals(self, forced_quantity):
        svl_vals_list = []
        for move in self:
            move = move.with_company(move.company_id)
            lines = move._get_in_move_lines()
            quantities = defaultdict(float)
            if forced_quantity:
                quantities[forced_quantity[0]] += forced_quantity[1]
            else:
                for line in lines:
                    quantities[line.lot_id] += line.quantity_product_uom
            if move.product_id.lot_valuated:
                unit_cost = {lot: lot.standard_price for lot in move.lot_ids}
            else:
                unit_cost = {self.env['stock.lot']: move.product_id.standard_price}
            if move.product_id.cost_method != 'standard':
                unit_cost = move._get_price_unit()  # May be negative (i.e. decrease an out move).
            if move.product_id.lot_valuated:
                vals = []
                for lot_id, qty in quantities.items():
                    vals.append(move.product_id._prepare_in_svl_vals(qty, abs(unit_cost[lot_id]), lot=lot_id))
            else:
                vals = [move.product_id._prepare_in_svl_vals(sum(quantities.values()), abs(unit_cost[self.env['stock.lot']]))]
            for val in vals:
                val.update(move._prepare_common_svl_vals())
                if forced_quantity:
                    val['description'] = _('Correction of %s (modification of past move)', move.picking_id.name or move.reference)
            svl_vals_list += vals
        return svl_vals_list

    def _get_src_account(self, accounts_data):
        if self.location_id.usage == 'inventory':
            return self.location_id.valuation_in_account_id.id or accounts_data['income'].id
        else:
            return self.location_id.valuation_out_account_id.id or accounts_data['stock_input'].id

    def _get_dest_account(self, accounts_data):
        if self.location_dest_id.usage == 'inventory':
            return self.location_dest_id.valuation_out_account_id.id or accounts_data['expense'].id
        elif not self.location_dest_id.usage in ('production', 'inventory'):
            return accounts_data['stock_output'].id
        else:
            return self.location_dest_id.valuation_in_account_id.id or accounts_data['stock_output'].id

    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id, svl_id, description):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given quant.
        """
        self.ensure_one()

        # the standard_price of the product may be in another decimal precision, or not compatible with the coinage of
        # the company currency... so we need to use round() before creating the accounting entries.
        debit_value = self.company_id.currency_id.round(cost)
        credit_value = debit_value

        valuation_partner_id = self._get_partner_id_for_valuation_lines()
        res = [(0, 0, line_vals) for line_vals in self._generate_valuation_lines_data(valuation_partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description).values()]

        return res

    def _prepare_analytic_lines(self):
        self.ensure_one()
        if not self._get_analytic_distribution() and not self.analytic_account_line_ids:
            return False

        if self.state in ['cancel', 'draft']:
            return False

        amount, unit_amount = 0, 0
        if self.state != 'done':
            if self.picked:
                unit_amount = self.product_uom._compute_quantity(
                    self.quantity, self.product_id.uom_id)
                # Falsy in FIFO but since it's an estimation we don't require exact correct cost. Otherwise
                # we would have to recompute all the analytic estimation at each out.
                amount = - unit_amount * self.product_id.standard_price
        elif self.product_id.valuation == 'real_time' and not self._ignore_automatic_valuation():
            accounts_data = self.product_id.product_tmpl_id.get_product_accounts()
            account_valuation = accounts_data.get('stock_valuation', False)
            analytic_line_vals = self.stock_valuation_layer_ids.account_move_id.line_ids.filtered(
                lambda l: l.account_id == account_valuation)._prepare_analytic_lines()
            amount = - sum(vals['amount'] for vals in analytic_line_vals)
            unit_amount = - sum(vals['unit_amount'] for vals in analytic_line_vals)
        elif sum(self.stock_valuation_layer_ids.mapped('quantity')):
            amount = sum(self.stock_valuation_layer_ids.mapped('value'))
            unit_amount = - sum(self.stock_valuation_layer_ids.mapped('quantity'))

        if self.analytic_account_line_ids and amount == 0 and unit_amount == 0:
            self.analytic_account_line_ids.unlink()
            return False

        return self.env['account.analytic.account']._perform_analytic_distribution(
            self._get_analytic_distribution(), amount, unit_amount, self.analytic_account_line_ids, self)

    def _ignore_automatic_valuation(self):
        return bool(self.picking_id)

    def _prepare_analytic_line_values(self, account_field_values, amount, unit_amount):
        self.ensure_one()
        return {
            'name': self.reference,
            'amount': amount,
            **account_field_values,
            'unit_amount': unit_amount,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_id.uom_id.id,
            'company_id': self.company_id.id,
            'ref': self._description,
            'category': 'other',
        }

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description):
        # This method returns a dictionary to provide an easy extension hook to modify the valuation lines (see purchase for an example)
        self.ensure_one()

        line_vals = {
            'name': description,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': description,
            'partner_id': partner_id,
        }

        svl = self.env['stock.valuation.layer'].browse(svl_id)
        if svl.account_move_line_id.analytic_distribution:
            line_vals['analytic_distribution'] = svl.account_move_line_id.analytic_distribution

        rslt = {
            'credit_line_vals': {
                **line_vals,
                'balance': -credit_value,
                'account_id': credit_account_id,
            },
            'debit_line_vals': {
                **line_vals,
                'balance': debit_value,
                'account_id': debit_account_id,
            },
        }

        if credit_value != debit_value:
            # for supplier returns of product in average costing method, in anglo saxon mode
            diff_amount = debit_value - credit_value
            price_diff_account = self.env.context.get('price_diff_account')
            if not price_diff_account:
                raise UserError(_('Configuration error. Please configure the price difference account on the product or its category to process this operation.'))

            rslt['price_diff_line_vals'] = {
                'name': self.name,
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'balance': -diff_amount,
                'ref': description,
                'partner_id': partner_id,
                'account_id': price_diff_account.id,
            }
        return rslt

    def _get_partner_id_for_valuation_lines(self):
        return (self.picking_id.partner_id and self.env['res.partner']._find_accounting_partner(self.picking_id.partner_id).id) or False

    def _prepare_move_split_vals(self, uom_qty):
        vals = super(StockMove, self)._prepare_move_split_vals(uom_qty)
        vals['to_refund'] = self.to_refund
        return vals

    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        self.ensure_one()
        valuation_partner_id = self._get_partner_id_for_valuation_lines()
        move_ids = self._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id, svl_id, description)
        svl = self.env['stock.valuation.layer'].browse(svl_id)
        if self.env.context.get('force_period_date'):
            date = self.env.context.get('force_period_date')
        elif svl.account_move_line_id:
            date = svl.account_move_line_id.date
        else:
            date = fields.Date.context_today(self)
        return {
            'journal_id': journal_id,
            'line_ids': move_ids,
            'partner_id': valuation_partner_id,
            'date': date,
            'ref': description,
            'stock_move_id': self.id,
            'stock_valuation_layer_ids': [(6, None, [svl_id])],
            'move_type': 'entry',
            'is_storno': self.env.context.get('is_returned') and self.company_id.account_storno,
            'company_id': self.company_id.id,
        }

    def _account_analytic_entry_move(self):
        for move in self:
            analytic_line_vals = move._prepare_analytic_lines()
            if analytic_line_vals:
                move.analytic_account_line_ids += self.env['account.analytic.line'].sudo().create(analytic_line_vals)

    def _should_exclude_for_valuation(self):
        """Determines if this move should be excluded from valuation based on its partner.
        :return: True if the move's restrict_partner_id is different from the company's partner (indicating
                it should be excluded from valuation), False otherwise.
        """
        self.ensure_one()
        return self.restrict_partner_id and self.restrict_partner_id != self.company_id.partner_id

    def _account_entry_move(self, qty, description, svl_id, cost):
        """ Accounting Valuation Entries """
        self.ensure_one()
        am_vals = []
        if not self.product_id.is_storable:
            # no stock valuation for consumable products
            return am_vals
        if self._should_exclude_for_valuation():
            return am_vals

        move_directions = self.env.context.get('move_directions') or False

        self_is_out_move = self_is_in_move = False
        if move_directions:
            self_is_out_move = move_directions.get(self.id) and 'out' in move_directions.get(self.id)
            self_is_in_move = move_directions.get(self.id) and 'in' in move_directions.get(self.id)
        else:
            self_is_out_move = self._is_out()
            self_is_in_move = self._is_in()

        company_from = self_is_out_move and self.mapped('move_line_ids.location_id.company_id') or False
        company_to = self_is_in_move and self.mapped('move_line_ids.location_dest_id.company_id') or False

        journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
        # Create Journal Entry for products arriving in the company; in case of routes making the link between several
        # warehouse of the same company, the transit location belongs to this company, so we don't need to create accounting entries
        if self_is_in_move:
            if self._is_returned(valued_type='in'):
                am_vals.append(self.with_company(company_to).with_context(is_returned=True)._prepare_account_move_vals(acc_dest, acc_valuation, journal_id, qty, description, svl_id, cost))
            else:
                am_vals.append(self.with_company(company_to)._prepare_account_move_vals(acc_src, acc_valuation, journal_id, qty, description, svl_id, cost))

        # Create Journal Entry for products leaving the company
        if self_is_out_move:
            cost = -1 * cost
            if self._is_returned(valued_type='out'):
                am_vals.append(self.with_company(company_from).with_context(is_returned=True)._prepare_account_move_vals(acc_valuation, acc_src, journal_id, qty, description, svl_id, cost))
            else:
                am_vals.append(self.with_company(company_from)._prepare_account_move_vals(acc_valuation, acc_dest, journal_id, qty, description, svl_id, cost))

        if self.company_id.anglo_saxon_accounting:
            # Creates an account entry from stock_input to stock_output on a dropship move. https://github.com/odoo/odoo/issues/12687
            anglosaxon_am_vals = self._prepare_anglosaxon_account_move_vals(acc_src, acc_dest, acc_valuation, journal_id, qty, description, svl_id, cost)
            if anglosaxon_am_vals:
                am_vals.append(anglosaxon_am_vals)

        return am_vals

    def _prepare_anglosaxon_account_move_vals(self, acc_src, acc_dest, acc_valuation, journal_id, qty, description, svl_id, cost):
        anglosaxon_am_vals = {}
        if self._is_dropshipped():
            if cost > 0:
                anglosaxon_am_vals = self.with_company(self.company_id)._prepare_account_move_vals(acc_src, acc_valuation, journal_id, qty, description, svl_id, cost)
            else:
                cost = -1 * cost
                anglosaxon_am_vals = self.with_company(self.company_id)._prepare_account_move_vals(acc_valuation, acc_dest, journal_id, qty, description, svl_id, cost)
        elif self._is_dropshipped_returned():
            if cost > 0 and self.location_dest_id._should_be_valued():
                anglosaxon_am_vals = self.with_company(self.company_id).with_context(is_returned=True)._prepare_account_move_vals(acc_valuation, acc_src, journal_id, qty, description, svl_id, cost)
            elif cost > 0:
                anglosaxon_am_vals = self.with_company(self.company_id).with_context(is_returned=True)._prepare_account_move_vals(acc_dest, acc_valuation, journal_id, qty, description, svl_id, cost)
            else:
                cost = -1 * cost
                anglosaxon_am_vals = self.with_company(self.company_id).with_context(is_returned=True)._prepare_account_move_vals(acc_valuation, acc_src, journal_id, qty, description, svl_id, cost)
        return anglosaxon_am_vals

    def _get_analytic_distribution(self):
        return {}

    def _get_related_invoices(self):  # To be overridden in purchase and sale_stock
        """ This method is overrided in both purchase and sale_stock modules to adapt
        to the way they mix stock moves with invoices.
        """
        return self.env['account.move']

    def _is_returned(self, valued_type):
        self.ensure_one()
        if valued_type == 'in':
            return self.location_id and self.location_id.usage == 'customer'   # goods returned from customer
        if valued_type == 'out':
            return self.location_dest_id and self.location_dest_id.usage == 'supplier'   # goods returned to supplier

    def _get_all_related_aml(self):
        return self.account_move_ids.line_ids

    def _get_all_related_sm(self, product):
        return self.filtered(lambda m: m.product_id == product)

    def _get_layer_candidates(self):
        self.ensure_one()
        return self.stock_valuation_layer_ids
