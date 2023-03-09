# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    task_id = fields.Many2one('project.task', string='Task', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        purchase_orders = super().create(vals_list)
        for purchase_order in purchase_orders:
            if purchase_order.task_id:
                purchase_order.message_post(body=_("Purchase Order created from task %s", f"<a href='#' data-oe-model='project.task' data-oe-id='{purchase_order.task_id.id}'>{purchase_order.task_id.name}</a>"))
        return purchase_orders
