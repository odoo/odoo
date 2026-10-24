# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    on_time_rate_perc = fields.Float(string="OTD", compute="_compute_on_time_rate_perc")

    @api.depends('on_time_rate')
    def _compute_on_time_rate_perc(self):
        for po in self:
            if po.on_time_rate >= 0:
                po.on_time_rate_perc = po.on_time_rate / 100
            else:
                po.on_time_rate_perc = -1


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    on_time_rate_perc = fields.Float(string="OTD", related="order_id.on_time_rate_perc")

    @api.model
    def _get_countable_rfq_groups(self, groups):
        groups = super()._get_countable_rfq_groups(groups)
        qty_by_order = defaultdict(lambda: defaultdict(float))
        for order, product, *_, qty in groups:
            if purchase_group := order.purchase_group_id:
                qty_by_order[purchase_group.id, product.id][order.id] += qty
        countable_orders = {key: max(order_qty, key=order_qty.get) for key, order_qty in qty_by_order.items()}
        return [
            group for group in groups
            if not (purchase_group := group[0].purchase_group_id)
            or countable_orders[purchase_group.id, group[1].id] == group[0].id
        ]
