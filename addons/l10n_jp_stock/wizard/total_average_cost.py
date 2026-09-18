import contextlib
from datetime import UTC, datetime, time, timedelta

from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round


class L10nJpTotalAverageCostWizard(models.TransientModel):
    _name = 'l10n_jp_stock.total.average.cost.wizard'
    _description = 'JGAAP Total Average Cost Evaluator'

    category_id = fields.Many2one('product.category', string='Category')
    product_ids = fields.Many2many('product.product', string='Products')
    date_from = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: self._default_date_from(),
        help="First day of the period to evaluate. It opens on the first day the last stock closing does not "
             "already cover, because the evaluation and the closing that makes it final cover the same "
             "period; a period the closing reaches into is refused.",
    )
    date_to = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.context_today,
        help="Last day of the period to evaluate, and the date the stock closing that makes it final should "
             "carry. Evaluate again before closing if a stock move of the period changed in the meantime.",
    )
    evaluation_line_ids = fields.One2many(
        'l10n_jp_stock.total.average.cost.line', 'wizard_id',
        string='Evaluation',
        readonly=True,
    )

    @api.model
    def default_get(self, fields):
        if self.env.company.account_fiscal_country_id.code != 'JP':
            raise UserError(self.env._(
                'The total average cost (総平均法) is a Japanese accounting method, '
                'so it can only be evaluated for a Japanese company.',
            ))
        return super().default_get(fields)

    def action_apply_total_average_cost(self):
        """
        Recompute the 総平均法 total average cost over the period and write
        it to the product's standard price, so later sales are costed at it.
        """
        self.ensure_one()
        evaluation = self._evaluate_total_average_cost()
        updated_count = sum(1 for result in evaluation.values() if result['updated'])
        unchanged_count = sum(
            1 for result in evaluation.values() if result['evaluated'] and not result['updated']
        )
        excluded_count = sum(1 for result in evaluation.values() if result['excluded_reason'])
        if updated_count and unchanged_count:
            message = self.env._(
                'Updated the standard price of %(updated)s products; %(unchanged)s already '
                'matched the evaluated cost.',
                updated=updated_count, unchanged=unchanged_count,
            )
            notification_type = 'success'
        elif updated_count:
            message = self.env._('Updated the standard price of %s products.', updated_count)
            notification_type = 'success'
        elif unchanged_count:
            message = self.env._(
                'The standard price of %s products already matches the evaluated cost.',
                unchanged_count,
            )
            notification_type = 'info'
        else:
            message = self.env._(
                'No standard price was updated: no stock movement in the period, '
                'or the result is not positive.',
            )
            notification_type = 'warning'
        if excluded_count:
            # a price that never moved looks like a price the period did not change
            message += ' ' + self.env._(
                'The evaluation left %(count)s products out; preview it to see why.',
                count=excluded_count,
            )
        params = {
            'message': message,
            'sticky': False,
            'type': notification_type,
            'next': {'type': 'ir.actions.act_window_close', 'infos': {'done': True}},
        }
        if updated_count or unchanged_count:
            # an evaluation is only final once the period is closed, which nothing here does
            params['message'] = message + ' ' + self.env._(
                'The period is not final until the stock valuation is closed for it in %s.',
            )
            params['links'] = [{
                'label': self.env._('Inventory Valuation'),
                'url': '/odoo/action-stock_account.action_report_stock_valuation',
            }]
            params['sticky'] = True
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': params,
        }

    def action_preview_total_average_cost(self):
        """
        List what the evaluation would come to, leaving the products as they are.

        Each level is valued off the corrected moves of the level below, so what a
        manufactured good comes to is only known once the evaluation has been carried
        out; the savepoint is what takes it back, whether it finished or raised.
        """
        self.ensure_one()
        self.evaluation_line_ids.unlink()
        with contextlib.closing(self.env.cr.savepoint()):
            evaluation = self._evaluate_total_average_cost()
        self.evaluation_line_ids = [
            Command.create({
                'product_id': product.id,
                'current_cost': result['current_cost'],
                'evaluated_cost': result['evaluated_cost'],
                'pulled_in': result['pulled_in'],
                'excluded_reason': result['excluded_reason'],
            })
            for product, result in evaluation.items()
        ]
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _evaluate_total_average_cost(self):
        """
        Evaluate the 総平均法 cost of the period and write it to the standard price.

        Returns what the period makes of every product it covers, by product: the
        cost it starts from, the cost it is evaluated at, whether the period had
        anything to evaluate it on, whether that moved the price, whether the
        product was pulled in rather than picked, and why it was left out of the
        evaluation, if it was. A caller after the figures alone reads them off
        that instead of off the products.
        """
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(self.env._("The start date must not be after the end date."))
        selected = self._get_selected_products()
        price_precision = self.env['decimal.precision'].precision_get('Product Price')
        period_start, period_end = self._get_period_bounds()
        # sudo: a product manager does not read the closing entries
        if period_start <= (last_closing := self.env.company.sudo()._get_last_closing_date()):
            raise UserError(
                self.env._(
                    'The stock valuation is already closed up to %(closing)s, so the cost of a period '
                    'starting on %(date_from)s can no longer be evaluated.',
                    closing=fields.Datetime.context_timestamp(self, last_closing).date(),
                    date_from=self.date_from,
                ),
            )
        products, pulled_in, moves = self._get_evaluated_products(selected, period_start, period_end)
        evaluation = {
            product: {
                'current_cost': product.standard_price,
                'evaluated_cost': product.standard_price,
                'evaluated': False,
                'updated': False,
                'pulled_in': product in pulled_in,
                'excluded_reason': False,
            }
            for product in products
        }
        moves_by_product = moves.grouped('product_id')
        before_period = period_start - timedelta(seconds=1)
        opening_values = products._get_last_product_value(before_period)
        # sudo: the quantity at hand is computed from those same moves
        opening_stock = products.sudo().with_context(
            allowed_company_ids=self.env.company.ids,
        )._with_valuation_context().with_context(to_date=before_period)
        init_qty_by_product = {product.id: product.qty_available for product in opening_stock}
        production_moves = moves.filtered(
            lambda m: m.location_id.usage == 'production' and m.location_dest_id.usage == 'internal',
        ).grouped('product_id')
        # a manufactured good is valued off its components, so each level is corrected first
        batches, excluded = self._get_evaluation_batches(products, moves, pulled_in)
        for product, reason in excluded.items():
            evaluation[product]['excluded_reason'] = reason
        for batch in batches:
            production_values = self._get_production_move_values(moves.browse([
                move.id for product in batch for move in production_moves.get(product, ())
            ]))
            batch_revalued = self.env['product.product']
            for product in batch:
                init_qty = init_qty_by_product[product.id]
                # 施行令28条1項1号ハ averages acquisitions only
                purchases_qty = purchases_val = returns_qty = returns_val = 0.0
                for move in moves_by_product.get(product, ()):
                    if move._should_exclude_for_valuation():
                        continue
                    qty = move.quantity_product_uom
                    origin_usage = move.location_id.usage
                    dest_usage = move.location_dest_id.usage
                    if move.is_dropship:
                        # a drop-ship is a purchase and a sale for JGAAP even though it never enters stock
                        returned_move = move.origin_returned_move_id
                        if dest_usage != 'supplier':
                            purchases_qty += qty
                            purchases_val += self._get_acquisition_value(move, qty)
                        elif returned_move and self._move_date_local(returned_move) >= self.date_from:
                            # never in stock, so with no origin there is no period to take them
                            # out of, and no price to do it at
                            returns_qty += qty
                            returns_val += self._get_acquisition_value(returned_move, qty)
                    elif (origin_usage in ('supplier', 'transit') and dest_usage == 'internal'):
                        if origin_usage == 'transit' and any(
                            m.company_id == move.company_id and m.location_id.usage == 'internal'
                            for m in move.move_orig_ids
                        ):
                            continue
                        purchases_qty += qty
                        purchases_val += self._get_acquisition_value(move, qty)
                    elif (origin_usage == 'internal' and dest_usage == 'supplier'):
                        returned_move = move.origin_returned_move_id
                        if (not returned_move or self._move_date_local(returned_move) >= self.date_from):
                            returns_qty += qty
                            returns_val += (
                                self._get_acquisition_value(returned_move, qty) if returned_move
                                else qty * (move.price_unit or product.standard_price)
                            )
                    elif (origin_usage == 'production' and dest_usage == 'internal'):
                        purchases_qty += qty
                        purchases_val += production_values.get(move.id, 0.0)
                    elif (origin_usage == 'customer' and dest_usage == 'internal'):
                        # prior-period sale return re-enters at sale-time cost (法人税法基本通達2-2-16)
                        returned_move = move.origin_returned_move_id
                        if (not returned_move or self._move_date_local(returned_move) < self.date_from):
                            purchases_qty += qty
                            returned = move._get_value_from_returns(qty)
                            purchases_val += returned['value']
                            if (remaining := qty - returned['quantity']) > 0:
                                if move.price_unit:
                                    purchases_val += self._get_acquisition_value(move, remaining)
                                else:
                                    # unlinked and unpriced: leaving it out of both is what
                                    # taking it back at the settled average comes to
                                    purchases_qty -= remaining
                opening_cost = opening_values[product].value if product in opening_values else product.standard_price
                init_val = init_qty * opening_cost
                tot_qty = init_qty + purchases_qty - returns_qty
                tot_val = init_val + purchases_val - returns_val
                if product.uom_id.compare(tot_qty, 0) > 0 and product.currency_id.compare_amounts(tot_val, 0) > 0:
                    new_cost = float_round(tot_val / tot_qty, precision_digits=price_precision)
                    evaluation[product].update(evaluated=True, evaluated_cost=new_cost)
                    if float_compare(new_cost, old_price := product.standard_price, precision_digits=price_precision):
                        product.with_context(disable_auto_revaluation=True).standard_price = new_cost
                        product._change_standard_price({product: old_price}, valuation_date=period_start)
                        # sudo: core created this history record elevated too
                        product_value = self.env['product.value'].sudo().search(
                            [
                                ('product_id', '=', product.id),
                                ('move_id', '=', False),
                                ('date', '=', period_start),
                            ],
                            order='id desc', limit=1,
                        )
                        if product_value:
                            product_value.description = self.env._(
                                'Total average cost evaluation %(date_from)s → %(date_to)s: '
                                'opening %(opening)s, purchases +%(purchases)s, reductions −%(reductions)s → cost %(cost)s',
                                date_from=self.date_from, date_to=self.date_to, opening=init_qty,
                                purchases=purchases_qty, reductions=returns_qty, cost=new_cost,
                            )
                        evaluation[product]['updated'] = True
                        batch_revalued |= product
            if batch_revalued:
                # the issues leave at the average it produced (施行令28条1項1号ハ)
                # sudo: replaying the valuation writes the value of every move it covers
                batch_revalued.sudo()._correct_inventory_valuation(period_start)
        return evaluation

    def _get_selected_products(self):
        """
        Return the products the user picked, refusing the ones that cannot be evaluated.

        Naming a product asks for that product, so one this method cannot cost is an
        error; a category only says where to look, so what it cannot cost is left out.
        """
        if self.product_ids:
            products = self.product_ids.filtered(lambda p: p.cost_method == 'standard')
            if len(products) != len(self.product_ids):
                raise UserError(
                    self.env._(
                        'The total average cost can only be applied to products valued with the standard cost method.',
                    ),
                )
            # a closing leaves a real time valuation out, so nothing would protect this
            if real_time := products.filtered(lambda p: p.valuation != 'periodic'):
                raise UserError(
                    self.env._(
                        'The total average cost cannot be applied to products valued in real time, '
                        'as the stock closing that makes a period final leaves them out: %s',
                        ', '.join(real_time.mapped('display_name')),
                    ),
                )
        else:
            if not self.category_id:
                raise UserError(self.env._('Select a category or products.'))
            products = self.env['product.product'].search(
                [('categ_id', 'child_of', self.category_id.id)],
            ).filtered(lambda p: p.cost_method == 'standard' and p.valuation == 'periodic')
        if lot_valuated := products.filtered('lot_valuated'):
            raise UserError(
                self.env._(
                    'The total average cost cannot be applied to products valued lot by lot: %s',
                    ', '.join(lot_valuated.mapped('display_name')),
                ),
            )
        return products

    def _get_evaluated_products(self, selected, period_start, period_end):
        """
        Return the products the period covers, the ones it pulled in, and its moves.

        A good is valued off what the moves of its components were worth, so a
        component left at its old cost values the good on a stale figure. Pulling one
        in can uncover components of its own, and the moves are searched per product,
        so both are repeated until the set stops growing.
        """
        products = selected
        pulled_in = self.env['product.product']
        while True:
            # sudo: nor the moves, the purchase lines and the orders feeding the evaluation,
            # which the closing check just above is the other half of
            moves = self.env['stock.move'].sudo().search(
                self._get_move_domain(products, period_start, period_end),
            )
            # the user never picked these, so one this evaluation cannot cost is
            # dropped rather than refused, the way a category drops its own
            found = self._filter_evaluable(self._get_consumed_components(moves)) - products
            if not found:
                return products, pulled_in, moves
            products |= found
            pulled_in |= found

    def _filter_evaluable(self, products):
        """Return the products of ``products`` the total average cost can be applied to."""
        return products.filtered(
            lambda p: p.cost_method == 'standard' and p.valuation == 'periodic' and not p.lot_valuated,
        )

    def _get_consumed_components(self, moves):
        """
        Return the components the orders behind these moves consumed.

        Without `mrp` nothing is made out of anything; `l10n_jp_mrp` reads the
        orders the moves belong to, when the user asked for their components.
        """
        return self.env['product.product']

    def _default_date_from(self):
        """
        Return the day the last closing left off on, which is where this period starts.

        A closing makes everything up to its own date final, so the period to
        evaluate next is the one that opens the day after. Never later than today,
        so the default cannot land after the end date it is offered with.
        """
        today = fields.Date.context_today(self)
        # sudo: a product manager does not read the closing entries
        if (last_closing := self.env.company.sudo()._get_last_closing_date()) == datetime.min:
            return today
        return min(fields.Datetime.context_timestamp(self, last_closing).date() + timedelta(days=1), today)

    def _get_period_bounds(self):
        """Return the two moments the period spans, in UTC, from the dates the user picked."""
        tz = self.env.tz
        return (
            datetime.combine(self.date_from, time.min, tzinfo=tz).astimezone(UTC).replace(tzinfo=None),
            datetime.combine(self.date_to, time.max, tzinfo=tz).astimezone(UTC).replace(tzinfo=None),
        )

    def _get_evaluation_batches(self, products, moves, pulled_in):
        """
        Return the batches to evaluate in order, and why each left-out product was.

        The batches come in the order their costs depend on each other, and what is
        left out is returned by product with the reason to show the user, rather
        than raised: it has to reach the preview, where the run is looked over.

        Without `mrp` nothing is made out of anything, so a single batch holds them
        all and nothing is left out; `l10n_jp_mrp` splits the manufactured goods
        from the components they consumed, which have to be evaluated and corrected
        first, and leaves out what it cannot order. ``pulled_in`` says which
        products the user did not pick, which is what makes that leniency theirs.
        """
        return [products], {}

    def _get_production_move_values(self, moves):
        """
        Return the acquisition value of each manufacturing receipt, by move id.

        Without `mrp` a receipt from a production location is valued at its own
        unit price; `l10n_jp_mrp` values the order's output at the components
        it consumed instead (法人税法施行令 28条1項1号ハ).
        """
        return {
            move.id: self._get_acquisition_value(move, move.quantity_product_uom)
            for move in moves
        }

    def _get_move_domain(self, products, period_start, period_end):
        """Return the moves the period is evaluated over, for the bridges to narrow."""
        return [
            ('product_id', 'in', products.ids),
            ('company_id', '=', self.env.company.id),
            ('state', '=', 'done'),
            ('date', '>=', period_start),
            ('date', '<=', period_end),
        ]

    def _get_acquisition_value(self, move, qty):
        """
        Return what a quantity of an incoming move cost to acquire (施行令32条1項1号, 2号).

        Core's own ladder without its last resort: the standard price is the cost being
        evaluated, so falling back to it would feed the average its own answer. A
        correction and a landed cost are stated for the whole move, so each is pro rata.
        """
        valued_qty = move._get_valued_qty()
        share = qty / valued_qty if valued_qty else 0.0
        # a correction states what the move finally cost, incidentals included
        manual = move._get_manual_value(qty)
        if manual['quantity']:
            return manual['value'] * share
        billed = move._get_value_from_account_move(qty)
        value = billed['value']
        remaining_qty = qty - billed['quantity']
        # the order only prices the move where purchase_stock is installed
        line = move.purchase_line_id if 'purchase_line_id' in move._fields else False
        if remaining_qty and line:
            value += line._get_stock_move_price_unit(move.date) * move._get_cost_ratio(remaining_qty)
            remaining_qty = 0
        if remaining_qty:
            value += remaining_qty * move.price_unit
        return value + move._get_value_from_extra(qty)['value'] * share

    def _move_date_local(self, move):
        return fields.Datetime.context_timestamp(self, move.date).date()


class L10nJpTotalAverageCostLine(models.TransientModel):
    _name = 'l10n_jp_stock.total.average.cost.line'
    _description = 'JGAAP Total Average Cost Preview Line'

    wizard_id = fields.Many2one(
        'l10n_jp_stock.total.average.cost.wizard',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one('product.product', string='Product', required=True)
    currency_id = fields.Many2one(related='product_id.currency_id')
    current_cost = fields.Monetary(string='Current Cost')
    evaluated_cost = fields.Monetary(
        string='Evaluated Cost',
        help="The cost the period comes to, which is the current one again when the period "
             "holds nothing to evaluate the product on, or when the product is left out.",
    )
    pulled_in = fields.Boolean(
        string='Pulled In',
        help="The evaluation added this product because the cost of a selected one is read "
             "off it; it was not selected itself, and its own cost changes too.",
    )
    excluded_reason = fields.Char(
        string='Left Out',
        help="Why the evaluation cannot cost this product. Nothing is written for it, "
             "selected or not, and the cost it holds is the one it keeps.",
    )
