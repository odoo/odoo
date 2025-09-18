# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _, Command
from odoo.fields import Domain
from odoo.tools import OrderedSet
from odoo.exceptions import UserError

VALUATION_DICT = {
    'value': 0,
    'quantity': 0,
    'description': False,
}


class StockMove(models.Model):
    _inherit = "stock.move"

    to_refund = fields.Boolean(
        "Update quantities on SO/PO", copy=True, default=True,
        help='Trigger a decrease of the delivered/received quantity in the associated Sale Order/Purchase Order')
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Company Currency', readonly=True)
    value = fields.Monetary(
        "Value", currency_field='company_currency_id',
        help="The current value of the move. It's zero if the move is not valued.")
    value_justification = fields.Text(
        "Value Description", compute="_compute_value_justification")
    value_computed_justification = fields.Text(
        "Computed Value Description", compute="_compute_value_justification")
    # Useful for testing and custom valuation
    value_manual = fields.Monetary(
        "Manual Value", currency_field='company_currency_id',
        compute="_compute_value_manual", inverse="_inverse_value_manual")
    standard_price = fields.Float(related='product_id.standard_price', string='Standard Price')

    # To remove and only use value
    price_unit = fields.Float("Price Unit")
    is_in = fields.Boolean(string='Is Incoming (valued)', compute='_compute_is_in', store=True)
    is_out = fields.Boolean(string='Is Outgoing (valued)', compute='_compute_is_out', store=True)
    is_dropship = fields.Boolean(string='Is Dropship', compute='_compute_is_dropship', store=True)
    is_valued = fields.Boolean(string='Is Valued', compute='_compute_is_valued')

    remaining_qty = fields.Float(
        string='Remaining Quantity', compute='_compute_remaining_qty', search='search_remaining_qty')
    remaining_value = fields.Monetary(
        currency_field='company_currency_id',
        string='Remaining Value', compute='_compute_remaining_value')

    analytic_account_line_ids = fields.Many2many('account.analytic.line', copy=False)
    account_move_id = fields.Many2one('account.move', 'stock_move_id', copy=False, index="btree_not_null")

    def search_remaining_qty(self, operator, value):
        if operator != '=' or not isinstance(value, bool) or value is not True:
            raise UserError(_("Only is set (= True) is supported in search for remaining_qty."))
        products = 'default_product_id' in self.env.context and self.env['product.product'].browse(self.env.context['default_product_id']) or self.env['product.product']
        if not products:
            products = self.env['product.product'].search([('is_storable', '=', True), ('qty_available', '>', 0)])
        move_ids = []
        for qty_by_move in products._get_remaining_moves().values():
            for move in qty_by_move:
                move_ids.append(move.id)
        return [('id', 'in', move_ids)]

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

    def _compute_value_justification(self):
        self.value_justification = False
        self.value_computed_justification = False
        for move in self:
            if not move.is_in:
                continue
            move.value_justification = move._get_value_data()['description']
            computed_value_data = move._get_value_data(ignore_manual_update=True)
            if computed_value_data['description'] == move.value_justification:
                move.value_computed_justification = False
            else:
                value = move.company_currency_id.format(computed_value_data['value'])
                move.value_computed_justification = self.env._(
                    'Computed value: %(value)s\n%(description)s',
                    value=value, description=computed_value_data['description'])

    @api.depends('quantity', 'product_id.stock_move_ids.value')
    def _compute_remaining_qty(self):
        products = self.product_id
        remaining_by_product = products._get_remaining_moves()

        for move in self:
            move.remaining_qty = remaining_by_product.get(move.product_id, {}).get(move, 0)

    @api.depends('value', 'remaining_qty')
    def _compute_remaining_value(self):
        for move in self:
            if not move.is_in:
                move.remaining_value = 0
                continue
            ratio = move.remaining_qty / move.quantity if move.quantity else 0
            if move.product_id.cost_method == 'fifo':
                move.remaining_value = ratio * move.value if ratio else 0
            else:
                move.remaining_value = move.remaining_qty * move.with_company(move.company_id).standard_price

    def _inverse_picked(self):
        super()._inverse_picked()
        self.sudo()._create_analytic_move()

    def _inverse_value_manual(self):
        for move in self:
            if move.value_manual == move.value:
                continue
            self.env['product.value'].create({
                'move_id': move.id,
                'value': move.value_manual,
                'company_id': move.company_id.id,
            })

    def action_adjust_valuation(self):
        if len(self) != 1:
            raise UserError(_("You can only adjust valuation for one move at a time."))
        action = self.env['ir.actions.act_window']._for_xml_id("stock_account.product_value_action")
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
        # stack. Limitation when validating at same time out and ins
        moves_out = self.filtered(lambda m: m._is_out())
        moves_out._set_value()
        moves = super()._action_done(cancel_backorder=cancel_backorder)
        moves_in = moves.filtered(lambda m: m.is_in or m.is_dropship)
        moves_in._set_value()
        moves._create_account_move()
        # Update standard price on outgoing fifo or lot valuated average products
        moves_out.product_id.filtered(lambda p: p.cost_method == 'fifo' or (p.cost_method == 'average' and p.lot_valuated))._update_standard_price()
        (moves_in | moves_out).sudo()._create_analytic_move()
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
        account_move = self.env['account.move'].sudo().create({
            'journal_id': self.company_id.account_stock_journal_id.id,
            'line_ids': [Command.create(aml_vals) for aml_vals in aml_vals_list],
            'date': self.env.context.get('force_period_date') or fields.Date.context_today(self),
        })
        self.env['stock.move'].browse(move_to_link).account_move_id = account_move.id
        account_move._post()
        return account_move

    def _create_analytic_move(self):
        for move in self:
            analytic_line_vals = move._prepare_analytic_lines()
            if analytic_line_vals:
                move.analytic_account_line_ids += self.env['account.analytic.line'].sudo().create(analytic_line_vals)

    def _get_account_move_line_vals(self):
        if self.location_id.valuation_account_id:
            debit_acc = self.product_id._get_product_accounts()['stock_valuation']
            credit_acc = self.location_id.valuation_account_id
        else:
            debit_acc = self.location_dest_id.valuation_account_id
            credit_acc = self.product_id._get_product_accounts()['stock_valuation']
        value = self._get_aml_value()
        return [{
            'account_id': credit_acc.id,
            'name': self.reference + ' - ' + self.product_id.name,
            'debit': 0,
            'credit': value,
            'product_id': self.product_id.id,
        }, {
            'account_id': debit_acc.id,
            'name': self.reference + ' - ' + self.product_id.name,
            'debit': value,
            'credit': 0,
            'product_id': self.product_id.id,
        }]

    def _get_aml_value(self):
        self.ensure_one()
        return self.value

    def _get_analytic_distribution(self):
        return {}

    def _get_price_unit(self):
        """ Returns the unit price to value this stock move """
        if len(self.product_id) > 1:
            return 0
        total_value = sum(self.mapped('value'))
        total_qty = sum(m._get_valued_qty() for m in self)
        return total_value / total_qty if total_qty else 0

    def _get_cogs_price_unit(self, quantity=0):
        """ Returns the COGS unit price to value this stock move
        quantity should be given in product uom """

        if len(self.product_id) > 1:
            return 0
        total_qty = sum(m._get_valued_qty() for m in self)
        if not total_qty:
            return 0
        return sum(self.mapped('value')) / total_qty if self.product_id.cost_method == 'fifo' or \
            (self.product_id.lot_valuated and self.product_id.cost_method == 'average') else self.product_id.standard_price

    @api.model
    def _get_valued_types(self):
        """Returns a list of `valued_type` as strings. During `action_done`, we'll call
        `_is_[valued_type]'. If the result of this method is truthy, we'll consider the move to be
        valued.

        :returns: a list of `valued_type`
        :rtype: list
        """
        return ['in', 'out', 'dropshipped', 'dropshipped_returned']

    def _set_value(self, correction_quantity=None):
        """Set the value of the move.

        :param correction_quantity: if set, it means that the quantity of the move has been
            changed by this amount (can be positive or negative). In that case, we just update
            the value of the move based on the ratio of extra_quantity / quantity. It only applies
            on out_move since their value is computed during action_done, and it's used to get a
            more accurate value for COGS. In case of in move correction, you have to call _set_value
            without arguments.
        """
        products_to_recompute = set()
        lots_to_recompute = set()
        fifo_qty_processed = defaultdict(float)

        for move in self:
            # Incoming moves
            if move.is_dropship or move.is_in:
                products_to_recompute.add(move.product_id.id)
                if move.product_id.lot_valuated:
                    lots_to_recompute.update(move.move_line_ids.lot_id.ids)
            if move.is_in:
                move.value = move.sudo()._get_value()
                continue
            # Outgoing moves
            if not move._is_out():
                continue
            if correction_quantity:
                previous_qty = move.quantity - correction_quantity
                ratio = correction_quantity / previous_qty if previous_qty else 0
                move.value += ratio * move.value
                continue
            if move.product_id.lot_valuated:
                value = 0.0
                for move_line in move.move_line_ids:
                    if move_line.lot_id:
                        value += move_line.lot_id.standard_price * move_line.quantity_product_uom
                    else:
                        value += move.product_id.standard_price * move_line.quantity_product_uom
                move.value = value
                continue

            if move.product_id.cost_method == 'fifo':
                valued_qty = move._get_valued_qty()
                move.value = move.product_id.with_context(fifo_qty_already_processed=fifo_qty_processed[move.product_id])._run_fifo(valued_qty)
                fifo_qty_processed[move.product_id] += valued_qty
            else:
                move.value = move.product_id.standard_price * move._get_valued_qty()

        # Recompute the standard price
        self.env['product.product'].browse(products_to_recompute)._update_standard_price()
        self.env['stock.lot'].browse(lots_to_recompute)._update_standard_price()

    def _get_value(self, forced_std_price=False, at_date=False, ignore_manual_update=False):
        return self._get_value_data(forced_std_price, at_date, ignore_manual_update)['value']

    def _get_value_data(
        self,
        forced_std_price=False,
        at_date=False,
        ignore_manual_update=False,
        add_extra_value=True,
    ):
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
        descriptions = []

        if not ignore_manual_update:
            manual_data = self._get_manual_value(
                remaining_qty, at_date)
            # In case of manual update we will skip extra cost
            if manual_data['quantity']:
                add_extra_value = False
            value += manual_data['value']
            remaining_qty -= manual_data['quantity']
            if manual_data.get('description'):
                descriptions.append(manual_data['description'])

        # 1. take from Invoice/Bills
        if remaining_qty:
            account_data = self._get_value_from_account_move(remaining_qty, at_date)
            value += account_data['value']
            remaining_qty -= account_data['quantity']
            if account_data.get('description'):
                descriptions.append(account_data['description'])

        if remaining_qty:
            production_data = self._get_value_from_production(remaining_qty, at_date)
            value += production_data["value"]
            remaining_qty -= production_data["quantity"]
            if production_data.get("description"):
                descriptions.append(production_data["description"])

        # 2. from SO/PO lines
        if remaining_qty:
            quotation_data = self._get_value_from_quotation(remaining_qty, at_date)
            value += quotation_data['value']
            remaining_qty -= quotation_data['quantity']
            if quotation_data.get('description'):
                descriptions.append(quotation_data['description'])

        # 3. from returns
        if remaining_qty:
            return_data = self._get_value_from_returns(remaining_qty, at_date)
            value += return_data['value']
            remaining_qty -= return_data['quantity']
            if return_data.get('description'):
                descriptions.append(return_data['description'])

        # 4. standard_price
        if remaining_qty:
            std_price_data = self._get_value_from_std_price(remaining_qty, forced_std_price, at_date)
            value += std_price_data['value']
            descriptions.append(std_price_data.get('description'))

        if add_extra_value:
            extra_data = self._get_value_from_extra(valued_qty, at_date)
            value += extra_data['value']
            if extra_data.get('description'):
                descriptions.append(extra_data['description'])

        return {
            'value': value,
            'quantity': valued_qty,
            'description': '\n'.join(descriptions),
        }

    def _get_valued_qty(self, lot=None):
        self.ensure_one()
        if self._is_in():
            return sum(self._get_in_move_lines(lot).mapped('quantity_product_uom'))
        if self._is_out():
            return sum(self._get_out_move_lines(lot).mapped('quantity_product_uom'))
        if self.is_dropship:
            if lot:
                return sum(self.move_line_ids.filtered(lambda ml: ml.lot_id == lot).mapped('quantity_product_uom'))
            return self.product_uom._compute_quantity(self.quantity, self.product_id.uom_id)
        return 0

    def _get_manual_value(self, quantity, at_date=None):
        valuation_data = dict(VALUATION_DICT)
        domain = Domain([('move_id', '=', self.id)])
        if at_date:
            domain &= Domain([('date', '<=', at_date)])
        manual_value = self.env['product.value'].sudo().search(domain, order="date desc, id desc", limit=1)
        if manual_value:
            valuation_data['value'] = manual_value.value
            valuation_data['quantity'] = quantity
            description = _("Adjusted on %(date)s by %(user)s",
                date=manual_value.date,
                user=manual_value.user_id.name,
            )
            if manual_value.description:
                description += "\n" + manual_value.description
            valuation_data['description'] = description
        return valuation_data

    def _get_value_from_account_move(self, quantity, at_date=None):
        return dict(VALUATION_DICT)

    def _get_value_from_production(self, quantity, at_date=None):
        return dict(VALUATION_DICT)

    def _get_value_from_quotation(self, quantity, at_date=None):
        return dict(VALUATION_DICT)

    def _get_value_from_returns(self, quantity, at_date=None):
        if self.origin_returned_move_id and self.origin_returned_move_id.is_out:
            origin_move = self.origin_returned_move_id
            return {
                'value': origin_move.value * quantity / origin_move._get_valued_qty(),
                'quantity': quantity,
                'description': _('Value based on original move %(reference)s', reference=origin_move.reference),
            }
        return dict(VALUATION_DICT)

    def _get_value_from_std_price(self, quantity, std_price=False, at_date=None):
        std_price = std_price if std_price else self.product_id.standard_price
        if at_date and self.product_id.cost_method == 'standard':
            std_price = std_price or self.product_id._get_standard_price_at_date(at_date)
        # If multiple lots keep standard_price from product
        elif self.product_id.lot_valuated and len(self.lot_ids) == 1:
            std_price = self.lot_ids.standard_price
        return {
            'value': std_price * quantity,
            'quantity': quantity,
            'description': self.env._("%(quantity)s %(uom)s at product's cost",
                quantity=quantity,
                uom=self.product_id.uom_id.name,
            ),
        }

    def _get_value_from_extra(self, quantity, at_date=None):
        return dict(VALUATION_DICT)

    def _get_move_directions(self):
        return defaultdict(set)

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
                amount = unit_amount * self.product_id.standard_price
            else:
                return False
        else:
            amount = self.value
            unit_amount = self._get_valued_qty()

        if self._is_out():
            amount = -amount

        if self.analytic_account_line_ids and amount == 0 and unit_amount == 0:
            self.analytic_account_line_ids.unlink()
            return False

        return self.env['account.analytic.account']._perform_analytic_distribution(
            self._get_analytic_distribution(), amount, unit_amount, self.analytic_account_line_ids, self)

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

    def _should_create_account_move(self):
        """Determines if an account move should be created for this move.
        :return: True if an account move should be created, False otherwise.
        """
        self.ensure_one()
        return self.product_id.is_storable and self.is_valued\
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
