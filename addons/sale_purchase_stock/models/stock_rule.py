# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_purchase_order_group(self, values):
        group = super()._prepare_purchase_order_group(values)
        if not group and values.get('move_dest_ids') and values['move_dest_ids'][0].procure_method == 'make_to_stock' and values.get('group_id') and values['group_id'].sale_ids:
            procurement_group_vals = {
                'sale_ids': [Command.link(values['group_id'].sale_ids[0].id)]  # FIXME : sale_ids index 0
            }
            group = self.env["procurement.group"].create(procurement_group_vals)
        return group

    def _update_purchase_order_line(self, product_id, product_qty, product_uom, company_id, values, line):
        res = super()._update_purchase_order_line(product_id, product_qty, product_uom, company_id, values, line)
        if values.get('move_dest_ids') and values['move_dest_ids'][0].procure_method == 'make_to_stock' and values.get('group_id') and values['group_id'].sale_ids:  # FIXME : better filter than index 0 on move_dest_ids
            line.order_id.group_id.sale_ids = [Command.link(values['group_id'].sale_ids[0].id)]  # FIXME: CHECK ME sale_ids at index 0 !?
        return res
