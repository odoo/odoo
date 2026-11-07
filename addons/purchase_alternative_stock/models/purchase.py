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
        qty_by_order = defaultdict(float)
        countable_orders = {}
        for order, product, *_, qty in groups:
            if purchase_group := order.purchase_group_id:
                key = purchase_group.id, product.id
                qty_by_order[order.id, product.id] += qty
                if qty_by_order[order.id, product.id] > qty_by_order[countable_orders.setdefault(key, order.id), product.id]:
                    countable_orders[key] = order.id
        return [
            group for group in groups
            if countable_orders.get((group[0].purchase_group_id.id, group[1].id), group[0].id) == group[0].id
        ]
