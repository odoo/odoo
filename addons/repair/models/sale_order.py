# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    repair_order_ids = fields.One2many(
        comodel_name='repair.order', inverse_name='sale_order_id',
        string='Repair Order', groups='stock.group_stock_user')
    repair_count = fields.Integer(
        "Repair Order(s)", compute='_compute_repair_count', groups='stock.group_stock_user')

    @api.depends('repair_order_ids')
    def _compute_repair_count(self):
        for order in self:
            order.repair_count = len(order.repair_order_ids)

    def _action_cancel(self):
        res = super()._action_cancel()
        self.order_line._cancel_repair_order()
        return res

    def _action_confirm(self):
        res = super()._action_confirm()
        self.order_line._create_repair_order()
        return res

    def action_show_repair(self):
        self.ensure_one()
        if self.repair_count == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "repair.order",
                "views": [[False, "form"]],
                "res_id": self.repair_order_ids.id,
            }
        elif self.repair_count > 1:
            return {
                "name": _("Repair Orders"),
                "type": "ir.actions.act_window",
                "res_model": "repair.order",
                "view_mode": "list,form",
                "domain": [('sale_order_id', '=', self.id)],
            }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_qty_delivered(self):
        repair_delivered_qties = defaultdict(float)
        remaining_so_lines = self
        for so_line in self:
            move = so_line.move_ids.sudo().filtered(lambda m: m.repair_id and m.state == 'done')
            if len(move) != 1:
                continue
            remaining_so_lines -= so_line
            repair_delivered_qties[so_line] = move.quantity
        delivered_qties = super(SaleOrderLine, remaining_so_lines)._prepare_qty_delivered()
        delivered_qties.update(repair_delivered_qties)
        return delivered_qties

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res.filtered(lambda line: line.state in ('sale', 'done'))._create_repair_order()
        return res

    def write(self, vals):
        if 'product_uom_qty' in vals:
            old_product_uom_qty = {line.id: line.product_uom_qty for line in self}
            res = super().write(vals)
            for line in self:
                if line.state in ('sale', 'done') and line.product_id:
                    if line.product_uom_id.compare(old_product_uom_qty[line.id], 0) <= 0 and line.product_uom_id.compare(line.product_uom_qty, 0) > 0:
                        self._create_repair_order()
                    if line.product_uom_id.compare(old_product_uom_qty[line.id], 0) > 0 and line.product_uom_id.compare(line.product_uom_qty, 0) <= 0:
                        self._cancel_repair_order()
            return res
        return super().write(vals)

    def _action_launch_stock_rule(self, **kwargs):
        # Picking must be generated for products created from the SO but not for parts added from the RO, as they're already handled there
        lines_without_repair_move = self.filtered(lambda line: not line.move_ids.sudo().repair_id)
        return super(SaleOrderLine, lines_without_repair_move)._action_launch_stock_rule(**kwargs)

    def _create_repair_order(self):
        new_repair_vals = []
        for line in self:
            # One RO for each line with at least a quantity of 1, quantities > 1 don't create multiple ROs
            if any(line.id == ro.sale_order_line_id.id for ro in line.order_id.sudo().repair_order_ids) and line.product_uom_id.compare(line.product_uom_qty, 0) > 0:
                binded_ro_ids = line.order_id.sudo().repair_order_ids.filtered(lambda ro: ro.sale_order_line_id.id == line.id and ro.state == 'cancel')
                binded_ro_ids.action_repair_cancel_draft()
                binded_ro_ids._action_repair_confirm()
                continue
            if line.product_template_id.sudo().service_tracking != 'repair' or line.move_ids.sudo().repair_id or line.product_uom_id.compare(line.product_uom_qty, 0) <= 0:
                continue

            order = line.order_id
            new_repair_vals.append({
                'state': 'confirmed',
                'partner_id': order.partner_id.id,
                'sale_order_id': order.id,
                'sale_order_line_id': line.id,
                'picking_type_id': order.warehouse_id.repair_type_id.id,
            })

        if new_repair_vals:
            self.env['repair.order'].sudo().create(new_repair_vals)

    def _cancel_repair_order(self):
        # Each RO binded to a SO line with Qty set to 0 or cancelled is set to 'Cancelled'
        binded_ro_ids = self.env['repair.order']
        for line in self:
            binded_ro_ids |= line.order_id.sudo().repair_order_ids.filtered(lambda ro: ro.sale_order_line_id.id == line.id and ro.state != 'done')
        binded_ro_ids.action_repair_cancel()

    def has_valued_move_ids(self):
        res = super().has_valued_move_ids()
        return res and not self.move_ids.repair_id
