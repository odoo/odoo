# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools.float_utils import float_compare
from collections import defaultdict
from datetime import date

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    sale_order_count = fields.Integer(
        "Count of Source SO",
        compute='_compute_sale_order_count',
        groups='sales_team.group_sale_salesman')

    @api.depends('procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id')
    def _compute_sale_order_count(self):
        for production in self:
            production.sale_order_count = len(production.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id)

    def write(self, vals):
        if not vals.get('product_qty'):
            return super().write(vals)

        sales_to_nofify = defaultdict(lambda: self.env['mrp.production'])
        for manufacturing_order in self:
            # Compute total quantity to sell for this product in related SO
            related_so = manufacturing_order.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id
            if not related_so:
                continue
            total_qty_sold = sum(related_so.order_line.filtered(lambda ol: ol.product_id.id == manufacturing_order.product_id.id).mapped('product_uom_qty'))
            # Compute total quantity to produce for this product in MO related to those SO
            all_related_mo = related_so.procurement_group_id.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids
            total_qty_produced = sum(all_related_mo.filtered(lambda mo: mo.product_id.id == manufacturing_order.product_id.id and mo.id != manufacturing_order.id).mapped('product_uom_qty'))
            total_qty_produced += vals.get('product_qty')
            if float_compare(total_qty_sold, total_qty_produced, precision_rounding=manufacturing_order.product_uom_id.rounding) > 0:
                for sale_order in related_so:
                    sales_to_nofify[sale_order] |= manufacturing_order

        for sale_order, manufacturing_orders in sales_to_nofify.items():
            render_context = {
                'manufacturing_orders': manufacturing_orders,
                'new_quantity': vals.get('product_qty')
            }
            sale_order._activity_schedule_with_view(
                'mail.mail_activity_data_warning',
                date.today(),
                user_id=sale_order.user_id.id or SUPERUSER_ID,
                views_or_xmlid='sale_mrp.exception_sale_on_manufacture_quantity_decreased',
                render_context=render_context
            )

        return super().write(vals)

    def action_view_sale_orders(self):
        self.ensure_one()
        sale_order_ids = self.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id.ids
        action = {
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
        }
        if len(sale_order_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': sale_order_ids[0],
            })
        else:
            action.update({
                'name': _("Sources Sale Orders of %s", self.name),
                'domain': [('id', 'in', sale_order_ids)],
                'view_mode': 'tree,form',
            })
        return action
