# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockLot(models.Model):
    _inherit = 'stock.lot'

    lot_valuated = fields.Boolean(related='product_id.lot_valuated', readonly=True, store=False)
    avg_cost = fields.Monetary(string="Average Cost", compute='_compute_value', compute_sudo=True, readonly=True, currency_field='company_currency_id')
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
        for lot in self:
            if not lot.lot_valuated:
                lot.total_value = 0.0
                lot.avg_cost = 0.0
                continue
            valuated_product = lot.product_id.with_context(at_date=at_date, lot_id=lot.id)
            qty_valued = lot.product_qty
            qty_available = lot.with_context(warehouse_id=False).product_qty
            if valuated_product.uom_id.is_zero(qty_valued):
                lot.total_value = 0
                lot.avg_cost = 0.0
            elif valuated_product.cost_method == 'standard' or valuated_product.uom_id.is_zero(qty_available):
                lot.total_value = lot.standard_price * qty_valued
            elif valuated_product.cost_method == 'average':
                lot.total_value = valuated_product.with_context(warehouse_id=False)._run_avco(at_date=at_date, lot=lot.with_context(warehouse_id=False), force_recompute=True)[1][valuated_product.id] * qty_valued / qty_available
            else:
                lot.total_value = valuated_product.with_context(warehouse_id=False)._run_fifo(at_date=at_date, lot=lot.with_context(warehouse_id=False))[1].get(valuated_product.id, 0) * qty_valued / qty_available
            lot.avg_cost = lot.total_value / qty_valued if qty_valued else 0.0

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
                lot.standard_price = lot.product_id._run_avco(lot=lot, force_recompute=True)[0][lot.product_id.id]
            else:
                lot.standard_price = lot.product_id._run_fifo(lot=lot)[0].get(lot.product_id.id, lot.standard_price)

    def _change_standard_price(self, old_price):
        """Helper to create the stock valuation layers and the account moves
        after an update of standard price.

        :param new_price: new standard price
        """
        product_values = []
        now = fields.Datetime.now()
        for lot in self:
            product = lot.product_id
            old_value = old_price.get(lot)
            value = lot.standard_price
            if product.cost_method != 'average' or value == old_value:
                continue
            quantity = lot.product_qty
            product_values.append({
                'product_id': product.id,
                'lot_id': lot.id,
                'quantity': quantity,
                'old_value': old_value,
                'value': value,
                'company_id': product.company_id.id or self.env.company.id,
                'date': now,
                'description': self.env._('%(lot)s price update from %(old_value)s to %(new_value)s for %(quantity)s by %(user)s',
                    lot=lot.name, old_value=old_value, new_value=value, quantity=quantity, user=self.env.user.name)
            })
        self.env['product.value'].sudo().create(product_values)
