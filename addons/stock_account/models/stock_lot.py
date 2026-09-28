# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, api, fields, models


class StockLot(models.Model):
    _inherit = 'stock.lot'

    lot_valuated = fields.Boolean(related='product_id.lot_valuated', readonly=True, store=False)
    avg_cost = fields.Monetary(string="Average Cost", compute='_compute_value', compute_sudo=True, store=False, readonly=True, currency_field='company_currency_id')
    total_value = fields.Monetary(string="Total Value", compute='_compute_value', compute_sudo=True, currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', 'Valuation Currency', compute='_compute_value', compute_sudo=True)
    standard_price = fields.Float(
        "Cost", company_dependent=True,
        min_display_digits='Product Price', groups="base.group_user",
        help="""Value of the lot (automatically computed in AVCO).
        Used to value the product when the purchase cost is not known (e.g. inventory adjustment).
        Used to compute margins on sale orders."""
    )

    @api.depends('product_id.lot_valuated', 'product_id.product_tmpl_id.lot_valuated', 'product_id.stock_move_ids.value', 'standard_price')
    @api.depends_context('to_date', 'company', 'warehouse_id')
    def _compute_value(self):
        """Compute totals of multiple svl related values"""
        company_id = self.env.company
        self.company_currency_id = company_id.currency_id
        at_date = fields.Datetime.to_datetime(self.env.context.get('to_date'))

        valued = self.filtered('lot_valuated')
        if self - valued:
            (self - valued).total_value = 0.0
            (self - valued).avg_cost = 0.0
        if not valued:
            return

        qty_valued = {lot.id: lot.product_qty for lot in valued}
        qty_available = {
            lot.id: lot.product_qty
            for lot in valued.with_context(warehouse_id=False)
        }

        fifo_lots = self.browse()
        avco_lots = self.browse()
        for lot in valued:
            product = lot.product_id
            qv, qa = qty_valued[lot.id], qty_available[lot.id]
            if product.uom_id.is_zero(qv):
                lot.total_value = 0.0
                lot.avg_cost = 0.0
            elif product.cost_method == 'standard' or product.uom_id.is_zero(qa):
                lot.total_value = lot.standard_price * qv
                lot.avg_cost = lot.standard_price
            elif product.cost_method == 'average':
                avco_lots |= lot
            else:
                fifo_lots |= lot

        for lot in avco_lots:
            product = lot.product_id.with_context(at_date=at_date, lot_id=lot.id, warehouse_id=False)
            avco_result = product._run_avco(at_date=at_date, lot=lot.with_context(warehouse_id=False))
            lot.total_value = avco_result[1] * qty_valued[lot.id] / qty_available[lot.id]
            lot.avg_cost = avco_result[0]

        if fifo_lots:
            fifo_values = fifo_lots._fifo_value_batch(qty_available, at_date)
            for lot in fifo_lots:
                qa = qty_available[lot.id]
                value = fifo_values.get(lot.id, 0.0)
                lot.total_value = value * qty_valued[lot.id] / qa
                lot.avg_cost = value / qa if qa else 0.0

    def _fifo_value_batch(self, qty_by_lot, at_date=None):
        """Mirrors standard _run_fifo"""
        domain = [
            ('lot_id', 'in', self.ids),
            ('state', '=', 'done'),
            ('move_id.is_in', '=', True),
        ]
        if at_date:
            domain.append(('date', '<=', at_date))

        lines = self.env['stock.move.line'].search_fetch(
            domain,
            ['lot_id', 'move_id', 'quantity_product_uom', 'date'],
            order='date desc, id desc',
        )

        moves = lines.move_id
        moves.fetch(['value', 'quantity'])
        unit_cost = {}
        for move in moves:
            valued_qty = move._get_valued_qty()
            unit_cost[move.id] = move.value / valued_qty if valued_qty else 0.0

        # Value each lot by consuming its most recent receipts until its quantity is covered.
        remaining = dict(qty_by_lot)
        values = defaultdict(float)
        for line in lines:
            lot_id = line.lot_id.id
            need = remaining.get(lot_id, 0.0)
            if need <= 0:
                continue
            take = min(need, line.quantity_product_uom)
            values[lot_id] += take * unit_cost[line.move_id.id]
            remaining[lot_id] = need - take

        for lot in self:
            if lot.product_id.uom_id.compare(remaining.get(lot.id, 0.0), 0) > 0:
                product = lot.product_id.with_context(
                    at_date=at_date, lot_id=lot.id, warehouse_id=False)
                values[lot.id] = product._run_fifo(
                    qty_by_lot[lot.id], lot=lot.with_context(warehouse_id=False), at_date=at_date)
        return values

    # TODO: remove avg cost column in master and merge the two compute methods
    def _compute_avg_cost(self):
        # DEPRECATED: This method is no longer used.
        self.avg_cost = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        lots = super().create(vals_list)
        for product, lots_by_product in lots.grouped('product_id').items():
            if product.lot_valuated:
                lots_by_product.filtered(lambda lot: not lot.standard_price).with_context(disable_auto_revaluation=True).write({
                    'standard_price': product.standard_price,
                })
        return lots

    def write(self, vals):
        old_price = False
        if 'standard_price' in vals and not self.env.context.get('disable_auto_revaluation'):
            old_price = {lot: lot.standard_price for lot in self}
        res = super().write(vals)
        if old_price:
            self._change_standard_price(old_price)
        return res

    def _update_standard_price(self):
        # TODO: Add extra value and extra quantity kwargs to avoid total recomputation
        for lot in self:
            lot = lot.with_context(disable_auto_revaluation=True)
            if not lot.product_id.lot_valuated:
                continue
            if lot.product_id.cost_method == 'standard':
                if not lot.standard_price:
                    lot.standard_price = lot.product_id.standard_price
                continue
            elif lot.product_id.cost_method == 'average':
                lot.standard_price = lot.product_id._run_avco(lot=lot)[0]
            else:
                lot.standard_price = lot.product_id._run_fifo_batch(lot=lot)[0].get(lot.product_id.id, lot.standard_price)

    def _change_standard_price(self, old_price):
        """Helper to create the stock valuation layers and the account moves
        after an update of standard price.

        :param new_price: new standard price
        """
        product_values = []
        for lot in self:
            if lot.product_id.cost_method != 'average' or lot.standard_price == old_price:
                continue
            product = lot.product_id
            product_values.append({
                'product_id': product.id,
                'lot_id': lot.id,
                'value': lot.standard_price,
                'company_id': product.company_id.id or self.env.company.id,
                'date': fields.Datetime.now(),
                'description': _('%(lot)s price update from %(old_price)s to %(new_price)s by %(user)s',
                    lot=lot.name, old_price=old_price, new_price=lot.standard_price, user=self.env.user.name)
            })
        self.env['product.value'].sudo().create(product_values)
