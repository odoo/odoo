# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools.float_utils import float_compare
from datetime import date
from collections import defaultdict

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
            # Notify related SO if quantity has been decreased in MO
            if float_compare(manufacturing_order.product_qty, vals['product_qty'], precision_rounding=manufacturing_order.product_uom_id.rounding) > 0:
                related_sale_orders = manufacturing_order.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id
                for sale_order in related_sale_orders:
                    sales_to_nofify[sale_order] |= manufacturing_order

        for sale_order, manufacturing_order in sales_to_nofify.items():
            sale_order.activity_schedule(
                'mail.mail_activity_data_warning',
                date.today(),
                note="Something happened in the MO",
                user_id=sale_order.user_id.id or SUPERUSER_ID
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
