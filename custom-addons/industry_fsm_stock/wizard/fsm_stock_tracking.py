# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError

class FsmStockTracking(models.TransientModel):
    _name = 'fsm.stock.tracking'
    _description = 'Track Stock'

    task_id = fields.Many2one('project.task')
    product_id = fields.Many2one('product.product')
    tracking = fields.Selection(related='product_id.tracking')

    tracking_line_ids = fields.One2many('fsm.stock.tracking.line', 'wizard_tracking_line')
    tracking_validated_line_ids = fields.One2many('fsm.stock.tracking.line', 'wizard_tracking_line_validated')
    company_id = fields.Many2one('res.company', 'Company')
    is_same_warehouse = fields.Boolean('Same warehouse', compute="_compute_is_same_warehouse")

    @api.depends('tracking_line_ids.is_same_warehouse')
    def _compute_is_same_warehouse(self):
        for tracking in self:
            tracking.is_same_warehouse = all(tracking.tracking_line_ids.mapped('is_same_warehouse'))

    def _update_lot_id(self, sale_line, tracking_line):
        for move in sale_line.move_ids:
            for ml in move.move_line_ids:
                if ml.lot_id == sale_line.fsm_lot_id:
                    ml.lot_id = tracking_line.lot_id

    def _get_moves_dict(self, sale_order):
        default_warehouse = self.env.user._get_default_warehouse_id()
        pickings_to_update = sale_order.picking_ids.filtered(
            lambda p:
                (
                        p.location_dest_id == default_warehouse.wh_pack_stock_loc_id
                        or p.location_dest_id == default_warehouse.wh_output_stock_loc_id
                )
                and p.state not in ['done', 'cancel']
        )
        move_read_group = self.env['stock.move']._read_group([
                              ('picking_id', 'in', pickings_to_update.ids),
                              ('product_id', '=', self.product_id.id)
                          ], ['picking_id'], ['id:recordset'])
        moves_per_picking = {}
        for picking, moves in move_read_group:
            moves_per_picking[picking] = moves
        return moves_per_picking

    def _remove_qty_from_intermediate_delivery(self, moves_from_intermediate_pickings, lot, qty_removed, deleted_line=False):
        for pick in moves_from_intermediate_pickings:
            qty_done_diff = qty_removed
            for move in moves_from_intermediate_pickings[pick]:
                if move.state in ['done, cancel']:
                    continue
                for move_line in move.move_line_ids:
                    if move_line.quantity > 0:
                        if not move_line.lot_id:
                            move_line.lot_id = lot
                        elif move_line.lot_id != lot:
                            continue
                        new_line_qty = max(0, move_line.quantity + qty_done_diff)
                        qty_done_diff += move_line.quantity - new_line_qty
                        previous_qty = move_line.quantity
                        move_line.quantity = new_line_qty
                        if deleted_line and move.warehouse_id != self.task_id.sale_order_id.warehouse_id:
                            move.product_uom_qty -= previous_qty - new_line_qty
                        if qty_done_diff == 0:
                            break
                if deleted_line and move.product_uom_qty == 0 and move.warehouse_id != self.task_id.sale_order_id.warehouse_id:
                    move.move_line_ids.unlink()
                    move.state = 'cancel'
                if qty_done_diff == 0:
                    break

    def _add_qty_to_intermediate_delivery_batch(self, moves_from_intermediate_pickings, lot, qty_added):
        ml_to_create = []
        for pick in moves_from_intermediate_pickings:
            for move in moves_from_intermediate_pickings[pick]:
                if move.state in ['done, cancel']:
                    continue
                new_line_needed = True
                for ml in move.move_line_ids:
                    if not ml.lot_id or ml.lot_id == lot:
                        if ml.quantity != qty_added:
                            ml.quantity = qty_added
                        new_line_needed = False
                        break
                # if no ml were available, create a new one
                if new_line_needed:
                    ml_vals = move._prepare_move_line_vals(quantity=0)
                    ml_vals['quantity'] = qty_added
                    ml_vals['lot_id'] = lot.id
                    ml_to_create.append(ml_vals)
        return ml_to_create

    def _add_qty_to_intermediate_delivery(self, moves_from_intermediate_pickings, line, qty_added):
        self.env['stock.move.line'].create(self._add_qty_to_intermediate_delivery_batch(moves_from_intermediate_pickings, line.lot_id, qty_added))

    def generate_lot(self):
        self.ensure_one()
        if self.tracking_line_ids.filtered(lambda l: not l.lot_id):
            raise UserError(_('Each line needs a Lot/Serial Number'))

        SaleOrderLine = self.env['sale.order.line'].sudo()

        sale_lines_remove = SaleOrderLine.search([
            ('order_id', '=', self.task_id.sale_order_id.id),
            ('product_id', '=', self.product_id.id),
            ('id', 'not in', self.tracking_line_ids.sale_order_line_id.ids),
            ('task_id', '=', self.task_id.id)
        ])
        # create the new sale_lines from the wizard
        move_line_qty_per_lot_id = defaultdict(int)
        new_lines = self.tracking_line_ids.filtered(lambda line: not line.sale_order_line_id)
        for line in new_lines:
            qty = line.quantity if self.tracking == 'lot' else 1
            vals = {
                'order_id': self.task_id.sale_order_id.id,
                'product_id': self.product_id.id,
                'product_uom_qty': qty,
                'task_id': self.task_id.id,
                'fsm_lot_id': line.lot_id.id,
            }
            move_line_qty_per_lot_id[line.lot_id] += qty
            SaleOrderLine.with_context(industry_fsm_stock_tracking=True).create(vals)

        dict_moves_per_picking = self._get_moves_dict(self.task_id.sale_order_id)

        if dict_moves_per_picking:  # create/update the move_lines for the intermediate deliveries
            ml_to_create = []
            for lot_id, qty in move_line_qty_per_lot_id.items():
                ml_to_create.extend(self._add_qty_to_intermediate_delivery_batch(dict_moves_per_picking, lot_id, qty))
            self.env['stock.move.line'].create(ml_to_create)

        # set the qty to 0 for the sol and the deliveries from the deleted wizard line
        for sl in sale_lines_remove:
            if sl.qty_delivered == 0 and sl.fsm_lot_id:
                if dict_moves_per_picking:  # handles 2/3 ways deliveries
                    self._remove_qty_from_intermediate_delivery(dict_moves_per_picking, sl.fsm_lot_id, 0-(sl.product_uom_qty - sl.qty_delivered), deleted_line=True)
                editable_moves = sl.move_ids.filtered(lambda m: m.state not in ['done', 'cancel'])
                editable_moves.move_line_ids.unlink()
                editable_moves.lot_ids -= sl.fsm_lot_id
                sl.fsm_lot_id = False
                # If the warehouse of the delivery is different from the one of the sale_order, the procurement.group.run() will not handle the moves correctly.
                # We have to manually set the product_uom_qty and cancel the moves
                if sl.order_id.warehouse_id != self.env.user._get_default_warehouse_id():
                    editable_moves.product_uom_qty = 0
                    editable_moves.state = 'cancel'
            sl.product_uom_qty = sl.qty_delivered

        # update the sol and deliveries according to the modification of the wizard lines
        for line in self.tracking_line_ids:
            qty = line.quantity if self.tracking == 'lot' else 1
            sol = line.sale_order_line_id
            if sol:
                if dict_moves_per_picking:  # handles 2/3 ways deliveries
                    if sol.fsm_lot_id == line.lot_id:
                        current_qty_demand = sol.product_uom_qty - sol.qty_delivered
                        if qty > current_qty_demand:
                            self._add_qty_to_intermediate_delivery(dict_moves_per_picking, line, qty)
                        elif qty < current_qty_demand:
                            self._remove_qty_from_intermediate_delivery(dict_moves_per_picking, sol.fsm_lot_id, qty - current_qty_demand)
                    else:  # the sn/lot id was changed
                        # adds the qty of the new lot_id
                        self._add_qty_to_intermediate_delivery(dict_moves_per_picking, line, qty)
                        # removes the qty of the old lot_id
                        self._remove_qty_from_intermediate_delivery(dict_moves_per_picking, sol.fsm_lot_id, 0-(sol.product_uom_qty - sol.qty_delivered))
                if sol.fsm_lot_id != line.lot_id: # update the lot_id of the deliveries linked to the sale_order_line
                    self._update_lot_id(sol, line)
                line.sale_order_line_id.with_context(industry_fsm_stock_tracking=True).write(
                    {
                        'fsm_lot_id': line.lot_id,
                        'product_uom_qty': qty + line.sale_order_line_id.qty_delivered,
                    })

class FsmStockTrackingLine(models.TransientModel):
    _name = 'fsm.stock.tracking.line'
    _description = 'Lines for FSM Stock Tracking'

    def _default_warehouse_id(self):
        return [Command.set([self.env.user._get_default_warehouse_id().id])]

    lot_id = fields.Many2one('stock.lot', string='Lot/Serial Number', domain="[('product_id', '=', product_id)]", check_company=True)
    quantity = fields.Float(required=True, default=1)
    product_id = fields.Many2one('product.product')
    sale_order_line_id = fields.Many2one('sale.order.line')
    company_id = fields.Many2one('res.company', 'Company')
    wizard_tracking_line = fields.Many2one('fsm.stock.tracking', string="Tracking Line")
    wizard_tracking_line_validated = fields.Many2one('fsm.stock.tracking', string="Validated Tracking Line")
    is_same_warehouse = fields.Boolean('Same warehouse', compute="_compute_warehouse", default=True)
    warehouse_id = fields.Many2one("stock.warehouse", compute="_compute_warehouse", default=_default_warehouse_id)

    @api.depends_context('uid')
    def _compute_warehouse(self):
        default_warehouse = self.env.user._get_default_warehouse_id()
        for line in self:
            if not isinstance(line.id, models.NewId):
                so_lines_warehouses = line.sale_order_line_id.move_ids.warehouse_id
                if len(so_lines_warehouses) > 1:
                    # If there is more than one we ensure not taking the default warehouse in order to avoid unwanted
                    # moves as this would mean we already have several move_ids (which would only occur through the use
                    # of other apps than FSM (inventory app for instance)). This should indeed not be possible through
                    # the use of the FSM app only.
                    line.warehouse_id = so_lines_warehouses.filtered(lambda w: w.id != default_warehouse.id)[0]
                else:
                    line.warehouse_id = so_lines_warehouses or default_warehouse
            else:
                line.warehouse_id = default_warehouse
            line.is_same_warehouse = not line.warehouse_id or (line.warehouse_id == default_warehouse)
