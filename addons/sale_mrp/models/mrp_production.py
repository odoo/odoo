# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, Command


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

    @api.model_create_multi
    def create(self, vals_list):
        # this override checks if the production comes from a sale order (MTO)
        # If it's the case, we need to retreive the product_no_variant_attribute_value_ids and
        # the product_custom_attribute_value_ids as there is no other way to determine them from the product itself
        for vals in vals_list:
            if 'move_dest_ids' not in vals:
                continue
            dest_move = self.env['stock.move'].browse(
                self._fields['move_dest_ids'].convert_to_cache(vals_list[0]['move_dest_ids'], self))
            if len(dest_move) != 1:
                continue
            order_line = dest_move.sale_line_id
            if not order_line:
                continue
            vals.update({
                'product_no_variant_attribute_value_ids': [Command.set(order_line.product_no_variant_attribute_value_ids.ids)],
                'product_custom_attribute_value_ids': [Command.set(order_line.product_custom_attribute_value_ids.ids)],
            })
        return super().create(vals_list)
