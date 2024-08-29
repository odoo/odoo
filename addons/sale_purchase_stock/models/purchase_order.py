# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.depends('order_line.move_dest_ids.group_id.sale_id', 'order_line.move_ids.move_dest_ids.group_id.sale_id')
    def _compute_sale_order_count(self):
        super()._compute_sale_order_count()

    def _get_sale_orders(self):
        so_linked_moves = self.order_line.move_dest_ids.group_id.sale_id | self.order_line.move_ids.move_dest_ids.group_id.sale_id
        so_proc_group = self.group_id.sale_id
        return super()._get_sale_orders() | so_linked_moves | so_proc_group

    def _post_run_buy(self, procurements):
        self.ensure_one()
        for procurement in procurements:
            group = procurement.get('group_id')
            if group and group.sale_id:
                self.group_id.sale_id = group.sale_id
                group.purchase_order_id = self
                break
        return super()._post_run_buy(procurements)

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_stock_moves(self, picking):
        res = super()._prepare_stock_moves(picking)
        for re in res:
            re['sale_line_id'] = self.sale_line_id.id
        return res

    def _find_candidate(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        # if this is defined, this is a dropshipping line, so no
        # this is to correctly map delivered quantities to the so lines
        lines = self.filtered(lambda po_line: po_line.sale_line_id.id == values['sale_line_id']) if values.get('sale_line_id') else self
        return super(PurchaseOrderLine, lines)._find_candidate(product_id, product_qty, product_uom, location_id, name, origin, company_id, values)

    @api.model
    def _prepare_purchase_order_line_from_procurement(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, po):
        res = super()._prepare_purchase_order_line_from_procurement(product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, po)
        res['sale_line_id'] = values.get('sale_line_id', False)
        return res
