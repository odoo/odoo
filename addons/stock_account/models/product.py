# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import float_is_zero, float_repr, float_round, float_compare
from odoo.exceptions import ValidationError
from collections import defaultdict
from datetime import datetime


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    cost_method = fields.Selection(
        string="Cost Method",
        selection=[
            ('standard', "Standard Price"),
            ('fifo', "First In First Out (FIFO)"),
            ('average', "Average Cost (AVCO)"),
        ],
        compute='_compute_cost_method',
    )
    valuation = fields.Selection(
        string="Valuation",
        selection=[
            ('periodic', 'Periodic (at closing)'),
            ('real_time', 'Perpetual (at invoicing)'),
        ],
        compute='_compute_valuation', search='_search_valuation',
    )
    lot_valuated = fields.Boolean(
        string="Valuation by Lot/Serial",
        compute='_compute_lot_valuated', store=True, readonly=False,
        help="If checked, the valuation will be specific by Lot/Serial number.",
    )
    property_price_difference_account_id = fields.Many2one(
        'account.account', 'Price Difference Account', company_dependent=True, ondelete='restrict',
        check_company=True,
        help="""With perpetual valuation, this account will hold the price difference between the standard price and the bill price.""")

    def _search_valuation(self, operator, value):
        if operator != '=':
            raise UserError(self.env._("You can only use the '=' operator to search on valuation field."))
        if value not in ['periodic', 'real_time']:
            raise UserError(self.env._("Only the value 'periodic' and 'real_time' are accepted to search on valuation field."))
        domain_categ = Domain([('categ_id.property_valuation', operator, value)])
        domain_company = Domain(['|', ('categ_id.property_valuation', '=', False), ('categ_id', '=', False), ('company_id.inventory_valuation', operator, value)])
        return domain_company | domain_categ

    @api.depends('tracking')
    def _compute_lot_valuated(self):
        for product in self:
            if product.tracking == 'none':
                product.lot_valuated = False

    @api.depends_context('company')
    @api.depends('categ_id.property_cost_method')
    def _compute_cost_method(self):
        for product_template in self:
            product_template.cost_method = (
                product_template.categ_id.with_company(
                    product_template.company_id
                ).property_cost_method
                or (product_template.company_id or self.env.company).cost_method
            )

    @api.depends_context('company')
    @api.depends('categ_id.property_valuation')
    def _compute_valuation(self):
        for product_template in self:
            product_template.valuation = product_template.categ_id.with_company(
                product_template.company_id).property_valuation or self.env.company.inventory_valuation

    def write(self, vals):
        product_to_update = set()
        if 'categ_id' in vals:
            category = self.env['product.category'].browse(vals['categ_id'])
            valuation = category.property_valuation if category else self.env.company.inventory_valuation
            for product in self:
                if product.valuation != valuation:
                    product_to_update.update(product.product_variant_ids.ids)
        res = super().write(vals)
        if 'lot_valuated' in vals:
            self.env['stock.lot'].search([
                ('product_id', 'in', self.product_variant_ids.ids),
            ])._update_standard_price()
        if 'product_to_update':
            self.env['product.product'].browse(product_to_update)._update_standard_price()
        return res

    # -------------------------------------------------------------------------
    # Misc.
    # -------------------------------------------------------------------------
    def _get_product_accounts(self):
        """ Add the stock accounts related to product to the result of super()
        @return: dictionary which contains information regarding stock accounts and super (income+expense accounts)
        """
        accounts = super()._get_product_accounts()

        accounts['stock_valuation'] = (
                self.categ_id.property_stock_valuation_account_id
                or self.categ_id._fields['property_stock_valuation_account_id'].get_company_dependent_fallback(self.categ_id)
                or self.env.company.account_stock_valuation_id
            )
        accounts['stock_variation'] = accounts['stock_valuation'].account_stock_variation_id
        return accounts

    def get_product_accounts(self, fiscal_pos=None):
        """ Add the stock journal related to product to the result of super()
        @return: dictionary which contains all needed information regarding stock accounts and journal and super (income+expense accounts)
        """
        accounts = super().get_product_accounts(fiscal_pos=fiscal_pos)
        accounts.update({
            'stock_journal': (
                self.categ_id.property_stock_journal
                or self.categ_id._fields['property_stock_journal'].get_company_dependent_fallback(self.categ_id)
                or self.env.company.account_stock_journal_id
            )
        })
        return accounts


class ProductProduct(models.Model):
    _inherit = 'product.product'

    avg_cost = fields.Monetary(
        string="Average Cost", compute='_compute_value',
        compute_sudo=True, currency_field='company_currency_id')
    total_value = fields.Monetary(
        string="Total Value", compute='_compute_value',
        compute_sudo=True, currency_field='company_currency_id')
    company_currency_id = fields.Many2one(
        'res.currency', 'Valuation Currency', compute='_compute_value', compute_sudo=True,
        help="Technical field to correctly show the currently selected company's currency that corresponds "
             "to the totaled value of the product's valuation layers")

    @api.depends_context('to_date', 'company')
    @api.depends('cost_method', 'stock_move_ids.value', 'standard_price')
    def _compute_value(self):
        """Compute totals of multiple svl related values"""
        company_id = self.env.company
        self.company_currency_id = company_id.currency_id

        for product in self:
            at_date = fields.Datetime.to_datetime(product.env.context.get('to_date'))
            if at_date:
                product = product.with_context(at_date=at_date)
            qty_available = product.sudo(False)._with_valuation_context().qty_available
            if product.lot_valuated:
                product.total_value = product._get_value_from_lots()
            elif product.cost_method == 'standard':
                standard_price = product.standard_price
                if at_date:
                    standard_price = product._get_standard_price_at_date(at_date)
                product.total_value = standard_price * qty_available
            elif product.cost_method == 'average':
                product.total_value = product._run_avco(at_date=at_date)[1]
            else:
                product.total_value = product._run_fifo(qty_available, at_date=at_date)
            product.avg_cost = product.total_value / qty_available if qty_available else 0.0

    def write(self, vals):
        old_price = False
        if 'standard_price' in vals and not self.env.context.get('disable_auto_revaluation'):
            old_price = {product: product.standard_price for product in self}
        if 'lot_valuated' in vals:
            # lot_valuated must be updated from the ProductTemplate
            self.product_tmpl_id.write({'lot_valuated': vals.pop('lot_valuated')})
        res = super().write(vals)
        if old_price:
            self._change_standard_price(old_price)
        return res

    # -------------------------------------------------------------------------
    # Private
    # -------------------------------------------------------------------------

    def _change_standard_price(self, old_price):
        for product in self:
            if product.cost_method == 'fifo' or product.standard_price == old_price.get(product):
                continue
            self.env['product.value'].sudo().create({
                'product_id': product.id,
                'value': product.standard_price,
                'company_id': product.company_id.id or self.env.company.id,
                'date': fields.Datetime.now(),
                'description': _('Price update from %(old_price)s to %(new_price)s by %(user)s',
                    old_price=old_price.get(product), new_price=product.standard_price, user=self.env.user.name)
            })
        return

    def _get_standard_price_at_date(self, date=None):
        self.ensure_one()
        product_value_domain = Domain([
            ('product_id', '=', self.id),
            ('move_id', '=', False),
            ('lot_id', '=', False),
        ])
        if date:
            product_value_domain &= Domain([('date', '<=', date)])
        product_value = self.env['product.value'].search(product_value_domain, limit=1, order="date DESC, id DESC")
        if not product_value:
            # If there is no history then get the first value
            product_value = self.env['product.value'].search([
                ('product_id', '=', self.id),
                ('move_id', '=', False),
                ('lot_id', '=', False),
            ], limit=1, order="date, id")
        if self.cost_method != 'fifo':
            return product_value.value if product_value else self.standard_price
        last_in_domain = Domain([('is_in', '=', True), ('product_id', '=', self.id)])
        if date:
            last_in_domain &= Domain([('date', '<=', date)])
        last_in = self.env['stock.move'].search(last_in_domain, order='date desc, id desc', limit=1)
        if not product_value and not last_in:
            return self.standard_price
        if (product_value and last_in and product_value.date > last_in.date) or not last_in:
            return product_value.value
        return last_in._get_value(at_date=date) / last_in._get_valued_qty()

    def _get_value_from_lots(self):
        lots = self.env['stock.lot'].search([
            ('product_id', 'in', self.ids),
            ('product_qty', '!=', 0),
        ])
        return sum(lots.mapped('total_value'))

    def _with_valuation_context(self):
        self_with_context = self
        valued_locations = self.env['stock.location'].search([('is_valued_internal', '=', True)])
        self_with_context = self.with_context(location=valued_locations.ids)
        # In FIFO, the stack in on stock.move and their value is already computed base on the owner
        if self.cost_method != 'fifo':
            self_with_context = self_with_context.with_context(
                owners=[False, self.env.company.partner_id.id]
            )
        return self_with_context

    def _get_remaining_moves(self):
        moves_qty_by_product = {}
        for product in self:
            moves, remaining_qty = product._run_fifo_get_stack()
            moves = self.env['stock.move'].concat(*moves)
            if not moves:
                continue
            qty_by_move = {m: m.quantity for m in moves[1:]}
            qty_by_move[moves[0]] = remaining_qty
            moves_qty_by_product[product] = qty_by_move
        return moves_qty_by_product

    def _run_avco(self, at_date=None, lot=None, method="realtime"):
        """ Recompute the average cost of the product base on the last closing
        inventory value and all the incoming moves during the period."""
        # TODO remove at the end and do at real time
        self.ensure_one()
        # Get value and quantity from last closing
        quantity = 0
        # Get value and quantity for all incoming
        moves_domain = Domain([
            ('product_id', '=', self.id),
            ('company_id', '=', self.env.company.id),
        ])
        if lot:
            moves_domain &= Domain([
                ('move_line_ids.lot_id', 'in', lot.id),
            ])
        if at_date:
            moves_domain &= Domain([
                ('date', '<=', at_date),
            ])
        moves_in = self.env['stock.move'].search(moves_domain & Domain(['|', ('is_in', '=', True), ('is_dropship', '=', True)]))
        moves_out = self.env['stock.move'].search(moves_domain & Domain(['|', ('is_out', '=', True), ('is_dropship', '=', True)])) if method == "realtime" else self.env['stock.move']
        # TODO convert to company UoM
        product_value_domain = Domain([('product_id', '=', self.id)])
        if lot:
            product_value_domain &= Domain(['|', ('lot_id', '=', lot.id), ('lot_id', '=', False)])
        else:
            product_value_domain &= Domain([('lot_id', '=', False)])
        if at_date:
            product_value_domain &= Domain([('date', '<=', at_date)])

        product_values = self.env['product.value'].search(product_value_domain, order="date, id")
        avco_value = 0
        avco_total_value = 0
        moves = moves_in | moves_out
        moves = moves.sorted('date, id')

        # If the last value was defined by the user just return it
        if product_values and not moves_in:
            quantity = self._with_valuation_context().with_context(to_date=at_date).qty_available
            last_value = product_values[-1]
            return last_value.value, last_value.value * quantity
        if product_values and moves_in and product_values[-1].date > moves_in[-1].date:
            quantity = self._with_valuation_context().with_context(to_date=at_date).qty_available
            if lot:
                quantity = lot.product_qty
            avco_value = product_values[-1].value
            return avco_value, avco_value * quantity

        # TODO Only browse from last product_value
        for move in moves:
            while product_values and move.date >= product_values[0].date:
                product_value = product_values[0]
                product_values = product_values[1:]
                avco_value = product_value.value
                avco_total_value = avco_value * quantity
            if move.is_in or move.is_dropship:
                in_qty = move._get_valued_qty()
                in_value = move.value
                if at_date or move.is_dropship:
                    in_value = move._get_value(at_date=at_date)
                if lot:
                    lot_qty = move._get_valued_qty(lot)
                    in_value = in_value * lot_qty / in_qty
                    in_qty = lot_qty
                if quantity < 0 and quantity + in_qty >= 0:
                    positive_qty = quantity + in_qty
                    ratio = positive_qty / in_qty
                    avco_total_value = ratio * in_value
                else:
                    avco_total_value += in_value
                quantity += in_qty
                avco_value = avco_total_value / quantity if quantity else 0
            if move.is_out or move.is_dropship:
                out_qty = move._get_valued_qty()
                out_value = out_qty * avco_value
                if lot:
                    lot_qty = move._get_valued_qty(lot)
                    out_value = out_value * lot_qty / out_qty
                    out_qty = lot_qty
                avco_total_value -= out_value
                quantity -= out_qty

        return avco_value, avco_total_value

    def _run_fifo(self, quantity, lot=None, at_date=None, location=None):
        """ Returns the value for the next outgoing product base on the qty give as argument."""
        self.ensure_one()
        if self.uom_id.compare(quantity, 0) <= 0:
            if at_date:
                return quantity * self._get_standard_price_at_date(at_date)
            return quantity * self.standard_price
        external_location = location and location.is_valued_external

        fifo_cost = 0
        fifo_stack, qty_on_first_move = self._run_fifo_get_stack(lot=lot, at_date=at_date, location=location)
        last_move = False
        # Going up to get the quantity in the argument
        while quantity > 0 and fifo_stack:
            move = fifo_stack.pop(0)
            last_move = move
            move_value = move.value
            if at_date:
                move_value = move._get_value(at_date=at_date)
            if qty_on_first_move:
                valued_qty = move._get_valued_qty()
                in_qty = qty_on_first_move
                in_value = move_value * in_qty / valued_qty
                qty_on_first_move = 0
            else:
                in_qty = move._get_valued_qty()
                in_value = move_value
            if in_qty > quantity:
                in_value = in_value * quantity / in_qty
                in_qty = quantity
            fifo_cost += in_value
            quantity -= in_qty
        # When we required more quantity than available we extrapolate with the last known price
        if quantity > 0:
            if last_move and last_move.quantity:
                fifo_cost += quantity * (last_move.value / last_move.quantity)
            else:
                fifo_cost += quantity * self.standard_price
        return fifo_cost

    def _run_fifo_get_stack(self, lot=None, at_date=None, location=None):
        # TODO: return a list of tuple (move, valued_qty) instead
        external_location = location and location.is_valued_external
        fifo_stack = []
        fifo_stack_size = 0
        if location:
            self = self.with_context(location=location.ids)  # noqa: PLW0642
        if lot:
            fifo_stack_size = lot.product_qty
        else:
            fifo_stack_size = int(self._with_valuation_context().with_context(to_date=at_date).qty_available)
        if fifo_stack_size <= 0:
            return fifo_stack, 0

        moves_domain = Domain([
            ('product_id', '=', self.id),
            ('company_id', '=', self.env.company.id)
        ])
        if lot:
            moves_domain &= Domain([('move_line_ids.lot_id', 'in', lot.id)])
        if at_date:
            moves_domain &= Domain([('date', '<=', at_date)])
        if location:
            moves_domain &= Domain([('location_dest_id', '=', location.id)])
        if external_location:
            moves_domain &= Domain([('is_out', '=', True)])
        else:
            moves_domain &= Domain([('is_in', '=', True)])

        # Base limit to 100 to avoid issue with other UoM than Unit
        initial_limit = fifo_stack_size * 10
        unit_uom = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
        if unit_uom and self.uom_id != unit_uom:
            initial_limit = max(initial_limit, 100)
        moves_in = self.env['stock.move'].search(moves_domain, order='date desc, id desc', limit=initial_limit)

        remaining_qty_on_first_stack_move = 0
        current_offset = 0
        # Go to the bottom of the stack
        while fifo_stack_size > 0 and moves_in:
            move = moves_in[0]
            moves_in = moves_in[1:]
            in_qty = move._get_valued_qty()
            fifo_stack.append(move)
            remaining_qty_on_first_stack_move = min(in_qty, fifo_stack_size)
            fifo_stack_size -= in_qty
            if fifo_stack_size > 0 and not moves_in:
                # We need to fetch more moves
                current_offset += 1
                moves_in = self.env['stock.move'].search(moves_domain, order='date desc, id desc', offset=current_offset * initial_limit, limit=initial_limit)
        fifo_stack.reverse()
        return fifo_stack, remaining_qty_on_first_stack_move

    def _update_standard_price(self, extra_value=None, extra_quantity=None):
        # TODO: Add extra value and extra quantity kwargs to avoid total recomputation
        for product in self:
            if product.cost_method == 'standard':
                continue
            if product.cost_method == 'fifo':
                qty_available = product._with_valuation_context().qty_available
                if product.uom_id.compare(qty_available, 0) > 0:
                    product.with_context(disable_auto_revaluation=True).standard_price = product.total_value / qty_available
                else:
                    product.with_context(disable_auto_revaluation=True).standard_price = product._get_standard_price_at_date()
                continue
            new_standard_price = product._run_avco()[0]
            if new_standard_price:
                product.with_context(disable_auto_revaluation=True).standard_price = new_standard_price


class ProductCategory(models.Model):
    _inherit = 'product.category'

    anglo_saxon_accounting = fields.Boolean(
        string="Use Anglo-Saxon Accounting", compute="_compute_anglo_saxon_accounting",
        help="If checked, the product will be valued using the Anglo-Saxon accounting method.")
    property_valuation = fields.Selection(
        string="Inventory Valuation",
        selection=[
            ('periodic', 'Periodic (at closing)'),
            ('real_time', 'Perpetual (at invoicing)'),
        ],
        company_dependent=True, copy=True, tracking=True,
        help="""Periodic: The accounting entries are suggested manually in the inventory valuation report.
        Perpetual: An accounting entry is automatically created to value the inventory when a product is billed or invoiced.
        """)
    property_cost_method = fields.Selection(
        string="Costing Method",
        selection=[
            ('standard', "Standard Price"),
            ('fifo', "First In First Out (FIFO)"),
            ('average', "Average Cost (AVCO)"),
        ],
        company_dependent=True, copy=True,
        default=lambda self: self.env.company.cost_method,
        help="""Standard Price: The products are valued at their standard cost defined on the product.
        Average Cost (AVCO): The products are valued at weighted average cost.
        First In First Out (FIFO): The products are valued supposing those that enter the company first will also leave it first.
        """,
        tracking=True,
    )
    property_stock_journal = fields.Many2one(
        'account.journal', 'Stock Journal', company_dependent=True,
        help="When doing automated inventory valuation, this is the Accounting Journal in which entries will be automatically posted when stock moves are processed.")
    property_stock_valuation_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account', company_dependent=True, ondelete='restrict',
        check_company=True,
        help="""When automated inventory valuation is enabled on a product, this account will hold the current value of the products.""")
    property_price_difference_account_id = fields.Many2one(
        'account.account', 'Price Difference Account', company_dependent=True, ondelete='restrict',
        check_company=True,
        help="""With perpetual valuation, this account will hold the price difference between the standard price and the bill price.""")
    account_stock_variation_id = fields.Many2one(
        'account.account', string="Stock Variation Account", readonly=False,
        related="property_stock_valuation_account_id.account_stock_variation_id")

    @api.depends_context('company')
    def _compute_anglo_saxon_accounting(self):
        self.anglo_saxon_accounting = self.env.company.anglo_saxon_accounting

    def write(self, vals):
        products_to_update = self.env['product.product']
        if 'property_cost_method' in vals:
            updated_categories = self.filtered(lambda c: c.property_cost_method != vals['property_cost_method'])
            if updated_categories:
                products_to_update = self.env['product.product'].search([('categ_id', 'in', updated_categories.ids)])
        res = super().write(vals)
        if products_to_update:
            products_to_update._update_standard_price()
        return res
