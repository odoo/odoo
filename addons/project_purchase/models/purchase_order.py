# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    task_id = fields.Many2one('project.task', string='Task', readonly=True, export_string_translation=False)

    @api.model_create_multi
    def create(self, vals_list):
        purchase_orders = super().create(vals_list)
        for purchase_order in purchase_orders:
            if purchase_order.task_id:
                purchase_order.message_post_with_source(
                    'mail.message_origin_link',
                    render_values={'self': purchase_order, 'origin': purchase_order.task_id},
                    subtype_xmlid='mail.mt_note',
                )
        return purchase_orders
