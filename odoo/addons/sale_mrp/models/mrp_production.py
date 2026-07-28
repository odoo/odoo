# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


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
