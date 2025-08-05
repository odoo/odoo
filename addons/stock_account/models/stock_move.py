# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _, Command
from odoo.fields import Domain
from odoo.tools import OrderedSet


class StockMove(models.Model):
    _inherit = "stock.move"

    to_refund = fields.Boolean(
        string="Update quantities on SO/PO", copy=True,
        help='Trigger a decrease of the delivered/received quantity in the associated Sale Order/Purchase Order')
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Company Currency', readonly=True)
    value = fields.Monetary(
        "Value", currency_field='company_currency_id',
        help="The current value of the move. It's zero if the move is not valued.")
    # Useful for testing and custom valuation
    value_manual = fields.Monetary(
        "Manual Value", currency_field='company_currency_id',
        compute="_compute_value_manual", inverse="_inverse_value_manual")

    # To remove and only use value
    price_unit = fields.Float("Price Unit")
    is_in = fields.Boolean(string='Is Incoming (valued)', compute='_compute_is_in', store=True)
    is_out = fields.Boolean(string='Is Outgoing (valued)', compute='_compute_is_out', store=True)
    is_dropship = fields.Boolean(string='Is Dropship', compute='_compute_is_dropship', store=True)
    is_valued = fields.Boolean(string='Is Valued', compute='_compute_is_valued')

    remaining_qty = fields.Float(
        string='Remaining Quantity', compute='_compute_remaining_qty')
    remaining_value = fields.Monetary(
        currency_field='company_currency_id',
        string='Remaining Value', compute='_compute_remaining_value')

    analytic_account_line_ids = fields.Many2many('account.analytic.line', copy=False)
    account_move_id = fields.Many2one('account.move', 'stock_move_id', copy=False, index="btree_not_null")

    @api.depends('state', 'move_line_ids')
    def _compute_is_in(self):
        for move in self:
            if move.state != 'done':
                move.is_in = False
                continue
            move.is_in = move._is_in()

    @api.depends('state', 'move_line_ids')
    def _compute_is_out(self):
        for move in self:
            if move.state != 'done':
                move.is_out = False
                continue
            move.is_out = move._is_out()

    @api.depends('state')
    def _compute_is_dropship(self):
        for move in self:
            if move.state != 'done':
                move.is_dropship = False
                continue
            move.is_dropship = move._is_dropshipped() or move._is_dropshipped_returned()

    @api.depends('state', 'move_line_ids')
    def _compute_is_valued(self):
        for move in self:
            move.is_valued = move.is_in or move.is_out

    def _compute_value_manual(self):
        for move in self:
            move.value_manual = move.value

    def _compute_remaining_qty(self):
        products = self.product_id
        remaining_by_product = products._get_remaining_moves()

        for move in self:
            move.remaining_qty = remaining_by_product.get(move.product_id, {}).get(move, 0)

    @api.depends('value')
    def _compute_remaining_value(self):
        for move in self:
            if not move.is_in:
                move.remaining_value = 0
                continue
            ratio = move.remaining_qty / move.quantity if move.quantity else 0
            if move.product_id.cost_method == 'fifo':
                move.remaining_value = ratio * move.value if ratio else 0
            else:
                move.remaining_value = move.remaining_qty * move.product_id.standard_price

    def _inverse_value_manual(self):
        for move in self:
            if move.value_manual == move.value:
                continue
            self.env['product.value'].create({
                'move_id': move.id,
                'value': move.value_manual,
                'company_id': move.company_id.id,
            })
            move._set_value()

    def action_adjust_valuation(self):
        action = self.env['ir.actions.act_window']._for_xml_id("stock_account.stock_move_revaluation_action")
        product = self.product_id if len(self.product_id) == 1 else False
        if product:
            action['name'] = _('Adjust Valuation: %(product)s', product=product.display_name)
        action['target'] = 'new'
        action['context'] = {
            'default_move_id': self.id,
        }
        return action

    def _action_done(self, cancel_backorder=False):
        # Use _is_out() instead of is_out since the move is not done
        # It's called before action_done since we need the current fifo
        # stack. Limitation when validating at same time out and in.s
        moves_out = self.filtered(lambda m: m._is_out())
        moves_out._set_value()
        moves = super()._action_done(cancel_backorder=cancel_backorder)
        moves_in = moves.filtered(lambda m: m.is_in or m.is_dropship)
        moves_in._set_value()
        moves._create_account_move()
        return moves

    def _create_account_move(self):
        """ Create account move for specific location or analytic."""
        aml_vals_list = []
        move_to_link = set()
        for move in self:
            if move._should_create_account_move():
                aml_vals_list += move._get_account_move_line_vals()
                move_to_link.add(move.id)
        if not aml_vals_list:
            return self.env['account.move']
        account_move = self.env['account.move'].create({
            'journal_id': self.company_id.account_stock_journal_id.id,
            'line_ids': [Command.create(aml_vals) for aml_vals in aml_vals_list],
        })
        self.env['stock.move'].browse(move_to_link).account_move_id = account_move.id
        account_move._post()
        return account_move

    def _get_account_move_line_vals(self):
        if self.location_id.valuation_account_id:
            debit_acc = self.product_id._get_product_accounts()['stock_valuation']
            credit_acc = self.location_id.valuation_account_id
        else:
            debit_acc = self.location_dest_id.valuation_account_id
            credit_acc = self.product_id._get_product_accounts()['stock_valuation']
        return [{
            'account_id': credit_acc.id,
            'name': self.reference,
            'debit': 0,
            'credit': self.value,
            'product_id': self.product_id.id,
        }, {
            'account_id': debit_acc.id,
            'name': self.reference,
            'debit': self.value,
            'credit': 0,
            'product_id': self.product_id.id,
        }]

    def _get_average_price_unit(self):
        if len(self.product_id) > 1:
            return 0
        # TODO handle returns ect
        total_value = sum(self.mapped('value'))
        total_qty = sum(m._get_valued_qty() for m in self)
        return total_value / total_qty if total_qty else self.product_id.standard_price

    def _get_price_unit(self):
        """ Returns the unit price to value this stock move """
        self.ensure_one()
        # TODO: Don't use self.quantity but real valued quantity
        if not self._get_valued_qty():
            return 0.0
        return self._get_value()[0] / self._get_valued_qty()

    @api.model
    def _get_valued_types(self):
        """Returns a list of `valued_type` as strings. During `action_done`, we'll call
        `_is_[valued_type]'. If the result of this method is truthy, we'll consider the move to be
        valued.

        :returns: a list of `valued_type`
        :rtype: list
        """
        return ['in', 'out', 'dropshipped', 'dropshipped_returned']

    def _set_value(self):
        """Set the value of the move"""
        # TODO groupby product to avoid using twice the same stack
        products_to_recompute = set()
        lots_to_recompute = set()

        for move in self:
            # Incoming moves
            if move.is_dropship or move.is_in:
                products_to_recompute.add(move.product_id.id)
                if move.product_id.lot_valuated:
                    lots_to_recompute.update(move.move_line_ids.lot_id.ids)
            if move.is_in:
                move.value = move.sudo()._get_value()[0]
                continue
            # Outgoing moves
            if not move._is_out():
                continue
            if move.product_id.cost_method == 'fifo':
                move.value = move.product_id._run_fifo(move.quantity)
            else:
                move.value = move.product_id.standard_price * move.quantity

        # Recompute the standard price
        self.env['product.product'].browse(products_to_recompute)._update_standard_price()
        self.env['stock.lot'].browse(lots_to_recompute)._update_standard_price()

    def _get_value(self, forced_std_price=False, at_date=False):
        """Returns the value and the quantity valued on the move
        In priority order:
        - Take value from accounting documents (invoices, bills)
        - Take value from quotations + landed costs
        - Take value from product cost

        Forced standard price is useful when we have to get the value
        of a move in the past with the standard price at that time.
        """
        # TODO: Make multi
        self.ensure_one()
        # It probably needs a priority order:
        # 1. take from Invoice/Bills
        # 2. from SO/PO lines
        # 3. standard_price

        valued_qty = remaining_qty = self._get_valued_qty()
        value = 0

        manual_value, manual_qty = self._get_manual_value(remaining_qty, at_date)
        value += manual_value
        remaining_qty -= manual_qty

        # 1. take from Invoice/Bills
        if remaining_qty:
            account_move_value, account_move_qty = self._get_value_from_account_move(remaining_qty, at_date)
            value += account_move_value
            remaining_qty -= account_move_qty

        # 2. from SO/PO lines
        if remaining_qty:
            quotation_value, quotation_qty = self._get_value_from_quotation(remaining_qty, at_date)
            value += quotation_value
            remaining_qty -= quotation_qty

        # 3. standard_price
        if remaining_qty:
            std_price_value = self._get_value_from_std_price(remaining_qty, forced_std_price, at_date)
            value += std_price_value

        return value, valued_qty

    def _get_valued_qty(self, lot=None):
        self.ensure_one()
        if self.is_in:
            return sum(self._get_in_move_lines(lot).mapped('quantity'))
        if self.is_out:
            return sum(self._get_out_move_lines(lot).mapped('quantity'))
        if self.is_dropship:
            if lot:
                return sum(self.move_line_ids.filtered(lambda ml: ml.lot_id == lot).mapped('quantity'))
            return self.quantity
        return 0

    def _get_manual_value(self, quantity, at_date=None):
        domain = Domain([('move_id', '=', self.id)])
        if at_date:
            domain &= Domain([('date', '<=', at_date)])
        manual_value = self.env['product.value'].search(domain, order="date desc, id desc", limit=1)
        if manual_value:
            return manual_value.value, quantity
        return 0, 0

    def _get_value_from_account_move(self, quantity, at_date=None):
        return 0, 0

    def _get_value_from_quotation(self, quantity, at_date=None):
        return 0, 0

    def _get_value_from_std_price(self, quantity, std_price=False, at_date=None):
        std_price = std_price or self.product_id.standard_price
        return std_price * quantity

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

    def _get_in_move_lines(self, lot=None):
        """ Returns the `stock.move.line` records of `self` considered as incoming. It is done thanks
        to the `_should_be_valued` method of their source and destionation location as well as their
        owner.

        :returns: a subset of `self` containing the incoming records
        :rtype: recordset
        """
        res = OrderedSet()
        for move_line in self.move_line_ids:
            if lot and move_line.lot_id != lot:
                continue
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
        return self._get_in_move_lines() and not self._is_dropshipped_returned()

    def _get_out_move_lines(self, lot=None):
        """ Returns the `stock.move.line` records of `self` considered as outgoing. It is done thanks
        to the `_should_be_valued` method of their source and destionation location as well as their
        owner.

        :returns: a subset of `self` containing the outgoing records
        :rtype: recordset
        """
        res = self.env['stock.move.line']
        for move_line in self.move_line_ids:
            if lot and move_line.lot_id != lot:
                continue
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
        return self._get_out_move_lines() and not self._is_dropshipped()

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

    def _should_create_account_move(self):
        """Determines if an account move should be created for this move.
        :return: True if an account move should be created, False otherwise.
        """
        self.ensure_one()
        return self.is_valued\
        and (self.location_dest_id.valuation_account_id or self.location_id.valuation_account_id)\
        and self.product_id.valuation == 'real_time'

    def _should_exclude_for_valuation(self):
        """Determines if this move should be excluded from valuation based on its partner.
        :return: True if the move's restrict_partner_id is different from the company's partner (indicating
                it should be excluded from valuation), False otherwise.
        """
        self.ensure_one()
        return self.restrict_partner_id and self.restrict_partner_id != self.company_id.partner_id

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
            return self.location_dest_id and self.location_dest_id.usage == 'supplier'
        return bool(self.picking_id.return_picking_id)
