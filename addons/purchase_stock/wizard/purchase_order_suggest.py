from odoo import api, fields, models


class PurchaseOrderSuggest(models.TransientModel):
    _name = 'purchase.order.suggest'
    _description = 'Purchase Order Suggest'

    purchase_order_id = fields.Many2one('purchase.order', required=True)
    currency_id = fields.Many2one('res.currency', related='purchase_order_id.currency_id')
    partner_id = fields.Many2one('res.partner', related='purchase_order_id.partner_id', change_default=True)
    product_ids = fields.Many2many('product.product')
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")

    based_on = fields.Selection(
        selection=[
            ('actual_demand', "Actual Demand"),
            ('one_week', "Last 7 days"),
            ('one_month', "Last 30 days"),
            ('three_months', "Last 3 months"),
            ('one_year', "Last 12 months"),
            ('last_year', "Same month last year"),
            ('last_year_2', "Next month last year"),
            ('last_year_3', "After next month last year"),
            ('last_year_quarter', "Last year quarter"),
        ],
        default='one_month',
        string='Based on',
        help="Estimate the sales volume for the period based on past period or order the forecasted quantity for that period.",
        required=True
    )
    number_of_days = fields.Integer(
        string="Replenish for", required=True,
        default=7,
        help="Suggested quantities to replenish will be computed to cover this amount of days for all filtered products in this catalog.")
    percent_factor = fields.Integer(default=100, required=True)
    multiplier = fields.Float(compute='_compute_multiplier')

    @api.depends('number_of_days', 'percent_factor')
    def _compute_multiplier(self):
        for suggest in self:
            suggest.multiplier = (suggest.number_of_days / (365.25 / 12)) * (suggest.percent_factor / 100)

    # TODO not called any more but need to figure out how to replace
    def _save_values_for_vendor(self):
        """ Save fields' value as default values for the PO vendor."""
        cid = self.env.company.id
        condition = f'partner_id={self.partner_id.id}'
        for field in ['based_on', 'number_of_days', 'percent_factor']:
            self.env['ir.default'].set('purchase.order.suggest', field, self[field], company_id=cid, condition=condition)
