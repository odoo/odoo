from odoo import fields, models
from odoo.tools.float_utils import float_round


class StockOrderpointSuggest(models.TransientModel):
    _name = 'stock.orderpoint.suggest'
    _description = 'Stock Orderpoint Min-Max Suggestion'

    orderpoint_ids = fields.Many2many('stock.warehouse.orderpoint')
    based_on = fields.Selection(
        selection=[
            ('one_week', "Last 7 days"),
            ('one_month', "Last 30 days"),
            ('three_months', "Last 3 months"),
            ('one_year', "Last 12 months"),
            ('last_year', "Same month last year"),
            ('last_year_2', "Next month last year"),
            ('last_year_3', "After next month last year"),
            ('last_year_quarter', "Last year quarter"),
            ('custom', "Custom Demand"),
        ],
        default='one_month',
        string='Based on',
        help="Estimate the daily average future demand volume based on past period or choose Custom Demand to enter manually average daily demand.",
        required=True
    )
    percent_factor = fields.Integer(default=100, required=True)

    def action_apply(self):
        self.orderpoint_ids.min_max_based_on = self.based_on
        self.orderpoint_ids.min_max_based_on_factor = self.percent_factor
        for orderpoint in self.orderpoint_ids:
            new_daily_demand = orderpoint._get_daily_demand()
            new_product_min_qty = new_daily_demand * (orderpoint.product_min_qty / orderpoint.daily_demand) if orderpoint.daily_demand else 0
            old_qty_diff = orderpoint.product_max_qty - orderpoint.product_min_qty
            new_product_max_qty = new_product_min_qty + (new_daily_demand * (old_qty_diff / orderpoint.daily_demand)) if orderpoint.daily_demand else 0
            orderpoint.write({
                'daily_demand': new_daily_demand,
                'product_min_qty': float_round(new_product_min_qty, precision_rounding=1),
                'product_max_qty': float_round(new_product_max_qty, precision_rounding=1),
            })
