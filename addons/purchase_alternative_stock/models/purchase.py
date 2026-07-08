# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

    def _get_countable_rfq_groups(self, groups):
        groups = super()._get_countable_rfq_groups(groups)
        countable_groups = {}
        for group in groups:
            order, product, *_, qty = group
            key = (order.purchase_group_id or order, product)
            if key not in countable_groups or qty > countable_groups[key][-1]:
                countable_groups[key] = group
        return countable_groups.values()
