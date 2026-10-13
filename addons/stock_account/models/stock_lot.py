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
    @api.depends_context('to_date', 'company', 'warehouse_id', 'allowed_company_ids')
    def _compute_value(self):
        """Compute totals of multiple svl related values"""
        company_id = self.env.company
        self.company_currency_id = company_id.currency_id
        at_date = fields.Datetime.to_datetime(self.env.context.get('to_date'))
        lots = self.with_context(owners=[False, self.env.company.partner_id.id])
        total_value_by_lot_id = defaultdict(float)
        valued_quantity_by_lot_id = defaultdict(float)

        for company in self.env.companies:
            lots = lots.with_company(company.id).with_context(allowed_company_ids=company.ids)

            for lot in lots:
                if not lot.lot_valuated:
                    continue
                valuated_product = lot.product_id.with_context(at_date=at_date, lot_id=lot.id)
                qty_valued = lot.product_qty
                qty_available = lot.with_context(warehouse_id=False).product_qty
                if valuated_product.uom_id.is_zero(qty_valued):
                    continue
                elif valuated_product.cost_method == 'standard' or valuated_product.uom_id.is_zero(qty_available):
                    total_value = lot.standard_price * qty_valued
                    total_value_by_lot_id[lot.id] += company.currency_id._convert(total_value, self.env.company.currency_id)
                    valued_quantity_by_lot_id[lot.id] += qty_valued
                elif valuated_product.cost_method == 'average':
                    avco_result = valuated_product.with_context(warehouse_id=False)._run_avco(at_date=at_date, lot=lot.with_context(warehouse_id=False))
                    total_value = avco_result[1] * qty_valued / qty_available
                    total_value_by_lot_id[lot.id] += company.currency_id._convert(total_value, self.env.company.currency_id)
                    valued_quantity_by_lot_id[lot.id] += qty_valued
                else:
                    fifo_value = valuated_product.with_context(warehouse_id=False)._run_fifo(qty_available, at_date=at_date, lot=lot.with_context(warehouse_id=False))
                    total_value = fifo_value * qty_valued / qty_available
                    total_value_by_lot_id[lot.id] += company.currency_id._convert(total_value, self.env.company.currency_id)
                    valued_quantity_by_lot_id[lot.id] += qty_valued

        for lot in self:
            lot.total_value = total_value_by_lot_id[lot.id]
            quantity = valued_quantity_by_lot_id[lot.id]
            lot.avg_cost = total_value_by_lot_id[lot.id] / quantity if quantity else 0

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
        lots = self.with_context(owners=[False, self.env.company.partner_id.id])
        for lot in lots:
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
