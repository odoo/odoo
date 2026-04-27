# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.tools import float_compare, float_round


class Task(models.Model):
    _inherit = "project.task"

    stock_move_customer_product_count = fields.Integer(compute='_compute_stock_move_customer_product_total')

    def _prepare_materials_delivery(self):
        """ Prepare the materials delivery

            We validate the stock and generates/updates delivery order.
            This method is called at the end of the action_fsm_validate method in industry_fsm_sale.
        """
        for task in self.filtered(lambda x: x.allow_billable and x.sale_order_id):
            exception = False
            sale_line = self.env['sale.order.line'].sudo().search([('order_id', '=', task.sale_order_id.id), ('task_id', '=', task.id)])
            for order_line in sale_line:
                to_log = {}
                total_qty = sum(order_line.move_ids.filtered(lambda m: m.state != 'cancel' and not m.move_dest_ids).mapped('product_uom_qty'))
                if (float_compare(order_line.product_uom_qty, total_qty, precision_rounding=order_line.product_uom.rounding) < 0
                    and order_line.product_id in order_line.move_ids.product_id):
                    to_log[order_line] = (order_line.product_uom_qty, total_qty)

                if to_log:
                    exception = True
                    documents = self.env['stock.picking']._log_activity_get_documents(to_log, 'move_ids', 'UP')
                    documents = {k: v for k, v in documents.items() if k[0].state not in ['cancel', 'done']}
                    self.env['sale.order']._log_decrease_ordered_quantity(documents)
            if not exception:
                task.sudo()._validate_stock()

    def _validate_stock(self, done_picking_ids=None):
        self.ensure_one()
        if not done_picking_ids:
            done_picking_ids = set()
        all_fsm_sn_moves = self.env['stock.move']
        ml_to_create = []
        for so_line in self.sale_order_id.order_line:
            if not (so_line.task_id.is_fsm or so_line.project_id.is_fsm or so_line.fsm_lot_id):
                continue
            qty = so_line.product_uom_qty - so_line.qty_delivered
            fsm_sn_moves = self.env['stock.move']
            if not qty:
                continue
            for move in so_line.move_ids:
                if move.state in ['done', 'cancel'] or (move.quantity >= qty and move.picked):
                    continue
                fsm_sn_moves |= move
                while move.move_orig_ids.filtered(lambda m: not m.picked or m.quantity < qty):
                    move = move.move_orig_ids
                    fsm_sn_moves |= move
            for fsm_sn_move in fsm_sn_moves:
                ml_vals = False
                if not fsm_sn_move.move_line_ids:
                    ml_vals = fsm_sn_move._prepare_move_line_vals(quantity=0)
                    ml_vals['quantity'] = fsm_sn_move.product_uom_qty
                    ml_vals['lot_id'] = so_line.fsm_lot_id.id
                    ml_to_create.append(ml_vals)
                else:
                    qty_done = 0
                    fsm_sn_move.move_line_ids.lot_id = so_line.fsm_lot_id
                    for move_line in fsm_sn_move.move_line_ids:
                        qty_done += move_line.quantity
                    missing_qty = fsm_sn_move.product_uom_qty - qty_done
                    if missing_qty > 0:
                        ml_vals = fsm_sn_move._prepare_move_line_vals(quantity=0)
                        ml_vals['quantity'] = missing_qty
                        ml_vals['lot_id'] = so_line.fsm_lot_id.id
                        ml_to_create.append(ml_vals)
                if ml_vals:
                    quants = self.env['stock.quant']._gather(fsm_sn_move.product_id, fsm_sn_move.location_id, lot_id=so_line.fsm_lot_id)
                    if fsm_sn_move.product_id.tracking == "serial":
                        quants = quants.filtered(lambda q: q.quantity == 1.0)
                    ml_vals['location_id'] = quants[:1].location_id.id or fsm_sn_move.location_id.id
            all_fsm_sn_moves |= fsm_sn_moves
        self.env['stock.move.line'].create(ml_to_create)
        for so_line in self.sale_order_id.order_line:
            # set the quantity delivered of the sol to the quantity ordered for the product linked to the task
            if so_line.task_id == self and so_line.product_id.service_policy not in ['delivered_timesheet', 'delivered_milestones']:
                so_line.qty_delivered = so_line.product_uom_qty

        def is_fsm_material_picking(picking, task):
            """ this function returns if the picking is a picking ready to be validated. """
            moves = picking.move_ids
            while moves.move_dest_ids:
                moves = moves.move_dest_ids
            for move in moves:
                sol = move.sale_line_id
                if sol.fsm_lot_id:
                    continue
                if not (sol.product_id != task.project_id.timesheet_product_id \
                and sol != task.sale_line_id \
                # On the last and, we check if the task is either done (and thus already done for the delivery) or the current one (and thus about to be validated)
                # if not, we can not validate the delivery
                and (sol.task_id == task or sol.task_id.fsm_done)):
                    return False
            return True

        pickings_to_do = self.sale_order_id.picking_ids.filtered(lambda p: p.state not in ['done', 'cancel'] and is_fsm_material_picking(p, self))
        # set the quantity done as the initial demand before validating the pickings
        for move in pickings_to_do.move_ids:
            if move.state in ('done', 'cancel') or move in all_fsm_sn_moves:
                continue
            rounding = move.product_uom.rounding
            if float_compare(move.quantity, move.product_uom_qty, precision_rounding=rounding) < 0:
                qty_to_do = float_round(
                    move.product_uom_qty - move.quantity,
                    precision_rounding=rounding,
                    rounding_method='HALF-UP')
                move.quantity = qty_to_do
        pickings_to_do.with_context(skip_sms=True, cancel_backorder=True).button_validate()

        # With new push rules, some pickings may not be created before previous picking validation, hence the need to go through the pickings again.
        done_picking_ids.update(pickings_to_do.ids)
        remaining_to_do = self.sale_order_id.picking_ids.filtered(lambda p: p.state not in ['done', 'cancel'] and is_fsm_material_picking(p, self))
        if any(remaining_id not in done_picking_ids for remaining_id in remaining_to_do.ids):
            self._validate_stock(done_picking_ids=done_picking_ids)

    def _get_task_SOL_stock_move_customer(self):
        return self.env['stock.move'].search([
            ('sale_line_id.order_id', '=', self.sale_order_id.id),
            ('sale_line_id.task_id', '=', False),
            ('state', 'not in', ['done', 'cancel']),
            ('location_dest_usage', '=', 'customer'),
        ])

    def _compute_stock_move_customer_product_total(self):
        for record in self:
            customer_move_lines = record.sudo()._get_task_SOL_stock_move_customer()
            record.stock_move_customer_product_count = round(sum(customer_move_lines.mapped('product_uom_qty')))

    def action_fsm_pick_up(self):
        stock_move_ids = self.sudo()._get_task_SOL_stock_move_customer()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pick Up Material'),
            'view_mode': 'list',
            'domain': [('id', 'in', stock_move_ids.ids)],
            'res_model': 'stock.move',
            'views': [(self.env.ref('industry_fsm_stock.view_move_tree_picking_redirect').id, 'list')],
        }

    def _fsm_ensure_sale_order(self):
        """Since we want to use the current user warehouse when using the FSM product kanban view, the SO must
           be confirmed before adding any product trough the product kanban view.
           We cannot indeed wait that the user actually adds a product trough the FSM product kanban view
           to do so as there would be a risk that all the existing SOL (possibly added in a (pre)sale phase)
           would get that user's default warehouse when the SO gets confirmed and the picking generated."""
        sale_order = super()._fsm_ensure_sale_order()
        if sale_order.state == 'draft':
            sale_order.action_confirm()
        return sale_order

    def _fsm_create_sale_order(self):
        """Since we want to use the current user warehouse when using the FSM product kanban view, the SO must
           be confirmed before adding any product trough the product kanban view.
           We cannot indeed wait that the user actually adds a product trough the FSM product kanban view
           to do so as there would be a risk that all the existing SOL (possibly added in a (pre)sale phase)
           would get that user's default warehouse when the SO gets confirmed and the picking generated."""
        super()._fsm_create_sale_order()
        sale_order = self.sale_order_id
        if self.env.user.has_group('project.group_project_user'):
            sale_order = self.sale_order_id.sudo()
        sale_order.with_context(fsm_create_sale_order=True).action_confirm()

    def action_fsm_view_material(self):
        action = super(Task, self).action_fsm_view_material()
        action['context'].update({"warehouse_id": self.env.user._get_default_warehouse_id().id})
        return action

    def action_fsm_validate(self, stop_running_timers=False):
        """Since SOs for FSM tasks are confirmed right after creation
           and this blocks the creation of pickings,
           we do not lock sales orders for FSM tasks after confirmation.
           Instead, we lock the SOs when we mark the FSM task as done."""
        res = super().action_fsm_validate(stop_running_timers)
        if res is True:
            self.sudo().sale_order_id.filtered(lambda so: so._should_be_locked()).action_lock()
        return res
