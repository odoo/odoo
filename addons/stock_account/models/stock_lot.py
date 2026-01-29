# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class StockLot(models.Model):
    _inherit = 'stock.lot'

    lot_valuated = fields.Boolean(related='product_id.lot_valuated', readonly=True, store=False)
    avg_cost = fields.Monetary(string="Average Cost", compute='_compute_avg_cost', store=True, readonly=True, currency_field='company_currency_id')
    total_value = fields.Monetary(string="Total Value", compute='_compute_value', compute_sudo=True, currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', 'Valuation Currency', compute='_compute_value', compute_sudo=True)
    standard_price = fields.Float(
        "Cost", company_dependent=True,
        min_display_digits='Product Price', groups="base.group_user",
        help="""Value of the lot (automatically computed in AVCO).
        Used to value the product when the purchase cost is not known (e.g. inventory adjustment).
        Used to compute margins on sale orders."""
    )

    @api.depends('product_id.lot_valuated', 'product_id.product_tmpl_id.lot_valuated', 'product_id.stock_move_ids.value')
    @api.depends_context('to_date', 'company', 'warehouse_id')
    def _compute_value(self):
        """Compute totals of multiple svl related values"""
        company_id = self.env.company
        self.company_currency_id = company_id.currency_id
        at_date = fields.Datetime.to_datetime(self.env.context.get('to_date'))

        for lot in self:
            if not lot.lot_valuated:
                lot.total_value = 0.0
                continue
            valuated_product = lot.product_id.with_context(at_date=at_date, lot_id=lot.id)
            qty_valued = valuated_product.qty_available
            qty_available = valuated_product.with_context(warehouse_id=False).qty_available
            if valuated_product.uom_id.is_zero(qty_valued):
                lot.total_value = 0
            elif valuated_product.cost_method == 'standard' or valuated_product.uom_id.is_zero(qty_available):
                lot.total_value = lot.standard_price * qty_valued
            elif valuated_product.cost_method == 'average':
                lot.total_value = valuated_product.with_context(warehouse_id=False)._run_avco(at_date=at_date, lot=lot)[1] * qty_valued / qty_available
            else:
                lot.total_value = valuated_product.with_context(warehouse_id=False)._run_fifo(qty_available, at_date=at_date, lot=lot) * qty_valued / qty_available

    # TODO: remove avg cost column in master and merge the two compute methods
    @api.depends('product_id.lot_valuated')
    @api.depends_context('to_date')
    def _compute_avg_cost(self):
        """Compute totals of multiple svl related values"""
        at_date = fields.Datetime.to_datetime(self.env.context.get('to_date'))

        self.avg_cost = 0.0
        for lot in self:
            if not lot.lot_valuated:
                continue

            qty_available = lot.product_qty
            if lot.product_id.cost_method == 'standard':
                total_value = lot.standard_price * qty_available
            elif lot.product_id.cost_method == 'average':
                total_value = lot.product_id._run_avco(at_date=at_date, lot=lot)[1]
            else:
                total_value = lot.product_id._run_fifo(qty_available, at_date=at_date, lot=lot)
            lot.avg_cost = total_value / qty_available if qty_available else 0.0

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
            lot.standard_price = lot.product_id._run_avco(lot=lot)[0]

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
