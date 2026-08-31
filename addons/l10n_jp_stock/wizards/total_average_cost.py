from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools import float_round


class L10nJpTotalAverageCostWizard(models.TransientModel):
    _name = 'l10n_jp_stock.total.average.cost.wizard'
    _description = 'JGAAP Total Average Cost Evaluator'

    category_id = fields.Many2one('product.category', string='Category')
    product_ids = fields.Many2many('product.product', string='Products')
    date_from = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.context_today,
    )
    date_to = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.context_today,
    )

    def action_apply_total_average_cost(self):
        """Recompute the 総平均法 total average cost over the period and write
        it to the product's standard price, so later sales are costed at it."""
        if self.date_from > self.date_to:
            raise UserError(self.env._("The start date must not be after the end date."))
        if self.product_ids:
            products = self.product_ids.filtered(lambda p: p.cost_method == 'standard')
            if len(products) != len(self.product_ids):
                raise UserError(
                    self.env._(
                        'The total average cost can only be applied to products valued with the standard cost method.',
                    ),
                )
        else:
            if not self.category_id:
                raise UserError(self.env._('Select a category or products.'))
            products = self.env['product.product'].search(
                [('categ_id', 'child_of', self.category_id.id)],
            ).filtered(lambda p: p.cost_method == 'standard')
        updated_count = 0
        unchanged_count = 0
        tz = ZoneInfo(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        period_start = datetime.combine(self.date_from, time.min, tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
        period_end = datetime.combine(self.date_to, time.max, tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
        moves = self.env['stock.move'].sudo().search_fetch([
                ('product_id', 'in', products.ids),
                ('company_id', '=', self.env.company.id),
                ('state', '=', 'done'),
                ('date', '>=', period_start),
                ('date', '<=', period_end),
            ], [
                'product_id',
                'date',
                'quantity_product_uom',
                'location_id',
                'location_dest_id',
                'origin_returned_move_id',
                'purchase_line_id',
                'price_unit',
                'is_dropship',
                'company_id',
                'move_orig_ids',
            ],
        )
        moves_by_product = moves.grouped('product_id')
        production_values = self._get_production_move_values(moves.filtered(
            lambda m: m.location_id.usage == 'production' and m.location_dest_id.usage == 'internal',
        ))
        opening_values = products._get_last_product_value(period_start)
        for product in products:
            init_qty = product.sudo().with_context(
                to_date=period_start - timedelta(seconds=1),
                allowed_company_ids=self.env.company.ids,
            ).qty_available
            purchases_qty = purchases_val = returns_qty = returns_val = 0.0
            # 施行令28条1項1号ハ averages acquisitions only
            for move in moves_by_product.get(product, ()):
                qty = move.quantity_product_uom
                origin_usage = move.location_id.usage
                dest_usage = move.location_dest_id.usage
                if move.is_dropship:
                    # a drop-ship is a purchase and a sale for JGAAP even though it never enters stock
                    if not move.origin_returned_move_id:
                        purchases_qty += qty
                        purchases_val += qty * self._get_purchase_unit_price(move)
                    elif self._move_date_local(move.origin_returned_move_id) < self.date_from:
                        purchases_qty += qty
                        purchases_val += qty * self._get_purchase_unit_price(move.origin_returned_move_id)
                elif (origin_usage in ('supplier', 'transit') and dest_usage == 'internal'):
                    if origin_usage == 'transit' and any(
                        m.company_id == move.company_id and m.location_id.usage == 'internal'
                        for m in move.move_orig_ids
                    ):
                        continue
                    purchases_qty += qty
                    purchases_val += qty * self._get_purchase_unit_price(move)
                elif (origin_usage == 'internal' and dest_usage == 'supplier'):
                    returned_move = move.origin_returned_move_id
                    if (not returned_move or self._move_date_local(returned_move) >= self.date_from):
                        returns_qty += qty
                        returns_val += qty * (self._get_purchase_unit_price(move) or product.standard_price)
                elif (origin_usage == 'production' and dest_usage == 'internal'):
                    purchases_qty += qty
                    purchases_val += production_values.get(move.id, 0.0)
                elif (origin_usage == 'customer' and dest_usage == 'internal'):
                    # prior-period sale return re-enters at sale-time cost (法人税法基本通達2-2-16)
                    returned_move = move.origin_returned_move_id
                    if (not returned_move or self._move_date_local(returned_move) < self.date_from):
                        purchases_qty += qty
                        if returned_move and returned_move.value and returned_move.quantity_product_uom:
                            # the sale is outgoing, so core stores its value negatively
                            purchases_val += qty * abs(returned_move.value) / returned_move.quantity_product_uom
                        else:
                            purchases_val += qty * self._get_purchase_unit_price(move)

            opening_cost = opening_values[product].value if product in opening_values else product.standard_price
            init_val = init_qty * opening_cost
            tot_qty = init_qty + purchases_qty - returns_qty
            tot_val = init_val + purchases_val - returns_val
            if tot_qty > 0 and tot_val > 0:
                new_cost = float_round(
                    tot_val / tot_qty,
                    precision_digits=self.env['decimal.precision'].precision_get('Product Price'),
                )
                if new_cost != (old_price := product.standard_price):
                    product.with_context(disable_auto_revaluation=True).standard_price = new_cost
                    product._change_standard_price({product: old_price}, valuation_date=period_end)
                    product_value = self.env['product.value'].sudo().search(
                        [('product_id', '=', product.id), ('move_id', '=', False)],
                        order='id desc', limit=1,
                    )
                    if product_value:
                        product_value.description = self.env._(
                            'Total average cost evaluation %(date_from)s → %(date_to)s: '
                            'opening %(opening)s, purchases +%(purchases)s, reductions −%(reductions)s → cost %(cost)s',
                            date_from=self.date_from, date_to=self.date_to, opening=init_qty,
                            purchases=purchases_qty, reductions=returns_qty, cost=new_cost,
                        )
                    updated_count += 1
                else:
                    unchanged_count += 1
        if updated_count:
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
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': self.env._('Total Average Cost'),
                'message': message,
                'sticky': False,
                'type': notification_type,
                'next': {'type': 'ir.actions.act_window_close', 'infos': {'done': True}},
            },
        }

    def _get_production_move_values(self, moves):
        """Return the acquisition value of each manufacturing receipt, by move id.

        Without ``mrp`` a receipt from a production location is valued at its own
        unit price; ``l10n_jp_mrp`` values the order's output at the materials
        it consumed instead (法人税法施行令 28条1項1号ハ).
        """
        return {
            move.id: move.quantity_product_uom * self._get_purchase_unit_price(move)
            for move in moves
        }

    def _move_date_local(self, move):
        return fields.Datetime.context_timestamp(self, move.date).date()

    def _get_purchase_unit_price(self, move):
        if m := move.origin_returned_move_id:
            return self._get_purchase_unit_price(m)
        if m := move.purchase_line_id:
            return m._get_stock_move_price_unit(self._move_date_local(move))
        return move.price_unit
