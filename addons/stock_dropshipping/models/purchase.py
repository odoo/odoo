# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, models, fields, SUPERUSER_ID


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    dropship_picking_count = fields.Integer("Dropship Count", compute='_compute_incoming_picking_count')

    @api.depends('picking_ids.is_dropship')
    def _compute_incoming_picking_count(self):
        super()._compute_incoming_picking_count()
        for order in self:
            dropship_count = len(order.picking_ids.filtered(lambda p: p.is_dropship))
            order.incoming_picking_count -= dropship_count
            order.dropship_picking_count = dropship_count

    def action_view_picking(self):
        return self._get_action_view_picking(self.picking_ids.filtered(lambda p: not p.is_dropship))

    def action_view_dropship(self):
        return self._get_action_view_picking(self.picking_ids.filtered(lambda p: p.is_dropship))

    def _prepare_group_vals(self):
        res = super()._prepare_group_vals()
        sale_orders = self.order_line.sale_order_id
        if len(sale_orders) == 1:
            res['sale_id'] = sale_orders.id
        return res

    def _create_picking(self):
        multi_so = self.filtered(
            lambda po: po.state in ('purchase', 'done')
            and po.picking_type_id.code == 'dropship'
            and len(po.order_line.sale_line_id.order_id) > 1
            and not po.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
            and any(p.type == 'consu' for p in po.order_line.product_id)
        )
        super(PurchaseOrder, self - multi_so)._create_picking()

        StockPicking = self.env['stock.picking']
        for order in multi_so:
            order = order.with_company(order.company_id)
            lines_by_so = defaultdict(lambda: self.env['purchase.order.line'])
            for line in order.order_line:
                lines_by_so[line.sale_line_id.order_id] |= line
            created = StockPicking
            all_moves = self.env['stock.move']
            for lines in lines_by_so.values():
                picking = StockPicking.with_user(SUPERUSER_ID).create(order._prepare_picking())
                moves = lines._create_stock_moves(picking)
                moves = moves.filtered(lambda m: m.state not in ('done', 'cancel'))._action_confirm()
                for seq, move in enumerate(sorted(moves, key=lambda m: m.date), start=1):
                    move.sequence = seq * 5
                moves._action_assign()
                picking.message_post_with_source(
                    'mail.message_origin_link',
                    render_values={'self': picking, 'origin': order},
                    subtype_xmlid='mail.mt_note',
                )
                created |= picking
                all_moves |= moves
            forward_pickings = StockPicking._get_impacted_pickings(all_moves)
            (created | forward_pickings).action_confirm()
        return True


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_stock_moves(self, picking):
        res = super()._prepare_stock_moves(picking)
        sale_group = self.sale_line_id.order_id.procurement_group_id
        if sale_group:
            for vals in res:
                vals['group_id'] = sale_group.id
        return res
