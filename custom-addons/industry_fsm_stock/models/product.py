# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError

class ProductProduct(models.Model):
    _inherit = 'product.product'

    serial_missing = fields.Boolean(compute='_compute_serial_missing')
    quantity_decreasable = fields.Boolean(compute='_compute_quantity_decreasable')
    quantity_decreasable_sum = fields.Integer(compute='_compute_quantity_decreasable')

    @api.depends('fsm_quantity')
    @api.depends_context('fsm_task_id')
    def _compute_serial_missing(self):
        task_id = self.env.context.get('fsm_task_id')
        if not task_id:
            self.serial_missing = False
            return

        task = self.env['project.task'].browse(task_id)
        sale_lines = self.env['sale.order.line'].sudo().search([('order_id', '=', task.sale_order_id.id), ('task_id', '=', task.id)])
        for product in self:
            if product.tracking != 'none':
                sale_product = sale_lines.filtered(lambda sale: sale.product_id == product)
                product.serial_missing = sale_product.filtered(lambda p: not p.fsm_lot_id and p.product_uom_qty > 0 and not p.qty_delivered)
            else:
                product.serial_missing = False

    @api.depends('fsm_quantity')
    @api.depends_context('fsm_task_id', 'uid')
    def _compute_quantity_decreasable(self):
        # Compute if a product is already delivered. If a quantity is not yet delivered,
        # we can decrease the quantity
        task_id = self.env.context.get('fsm_task_id')
        if not task_id:
            self.quantity_decreasable = True
            self.quantity_decreasable_sum = 0
            return

        task = self.env['project.task'].browse(task_id)
        if not task:
            self.quantity_decreasable = False
            self.quantity_decreasable_sum = 0
            return
        elif task.sale_order_id.sudo().state in ['draft', 'sent']:
            self.quantity_decreasable = True
            self.quantity_decreasable_sum = 0
            return

        moves_read_group = self.env['stock.move'].sudo()._read_group(
            [
                ('sale_line_id.order_id', '=', task.sale_order_id.id),
                ('sale_line_id.task_id', '=', task.id),
                ('product_id', 'in', self.ids),
                ('warehouse_id', '=', self.env.user._get_default_warehouse_id().id),
                ('state', 'not in', ['done', 'cancel']),
            ],
            ['product_id'],
            ['product_uom_qty:sum'],
        )
        move_per_product = {product.id: product_uom_qty for product, product_uom_qty in moves_read_group}

        # If no move line can be found, look into the SOL in case one line has no move and could be used to decrease the qty
        sale_lines_read_group = self.env['sale.order.line'].sudo()._read_group(
            [
                ('order_id', '=', task.sale_order_id.id),
                ('task_id', '=', task.id),
                ('product_id', 'in', self.ids),
                ('move_ids', '=', False),
            ],
            ['product_id'],
            ['product_uom_qty:sum', 'qty_delivered:sum'],
        )
        product_uom_qty_per_product = {
            product.id: product_uom_qty - qty_delivered if product.service_policy != 'delivered_manual' else product_uom_qty
            for product, product_uom_qty, qty_delivered in sale_lines_read_group
            if product_uom_qty > qty_delivered or product.service_policy == 'delivered_manual'
        }

        for product in self:
            product.quantity_decreasable_sum = move_per_product.get(product.id, product_uom_qty_per_product.get(product.id, 0))
            product.quantity_decreasable = product.quantity_decreasable_sum > 0

    def _inverse_fsm_quantity(self):
        super(ProductProduct, self.with_context(industry_fsm_stock_set_quantity=True))._inverse_fsm_quantity()

    def write(self, vals):
        if 'fsm_quantity' in vals and any(product.fsm_quantity - vals['fsm_quantity'] > product.quantity_decreasable_sum for product in self):
            raise UserError(_('The ordered quantity cannot be decreased below the amount already delivered. Instead, create a return in your inventory.'))
        return super().write(vals)

    def action_assign_serial(self, from_onchange=False):
        """ Opens a wizard to assign SN's name on each move lines.
        """
        self.ensure_one()
        if self.tracking == 'none':
            return False
        # If the wizard is triggered from the menu, an error should not be raised, the wizard will be in readonly instead.
        if from_onchange and not self.env.user.has_group('stock.group_stock_user'):
            raise AccessError(_("Adding or updating this product is restricted due to its tracked status. Your current access rights do not allow you to perform these actions. "
            "Please contact your administrator to request the necessary permissions."))

        task_id = self.env.context.get('fsm_task_id')
        task = self.env['project.task'].browse(task_id)
        # project user with no sale rights should be able to change material quantities
        sale_lines = self.env['sale.order.line'].sudo().search([
            ('order_id', '=', task.sale_order_id.id), ('task_id', '=', task.id), ('product_id', '=', self.id), ('product_uom_qty', '>', 0)])
        tracking_line_ids = [(0, 0, {
            'lot_id': line.fsm_lot_id.id,
            'quantity': line.product_uom_qty - line.qty_delivered,
            'product_id': self.id,
            'sale_order_line_id': line.id,
            'company_id': task.sale_order_id.company_id.id,
        }) for line in sale_lines.filtered(lambda sl: sl.product_uom_qty - sl.qty_delivered)]

        lot_done_dict = defaultdict(int)
        for move_line in sale_lines.move_ids.filtered(lambda m: m.state == 'done').move_line_ids:
            lot_done_dict[move_line.lot_id.id] += move_line.quantity

        tracking_validated_line_ids = [(0, 0, {
            'lot_id': vals,
            'quantity': lot_done_dict[vals],
            'product_id': self.id,
            'company_id': task.sale_order_id.company_id.id,
        }) for vals in lot_done_dict]

        validation = self.env['fsm.stock.tracking'].create({
            'task_id': task_id,
            'product_id': self.id,
            'tracking_line_ids': tracking_line_ids,
            'tracking_validated_line_ids': tracking_validated_line_ids,
            'company_id': task.sale_order_id.company_id.id,
        })

        return {
            'name': _('Validate Lot/Serial Number'),
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_model': 'fsm.stock.tracking',
            'res_id': validation.id,
            'views': [(False, 'form')]
        }
