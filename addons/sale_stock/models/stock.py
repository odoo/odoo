# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _


class StockLocationRoute(models.Model):
    _inherit = "stock.location.route"
    sale_selectable = fields.Boolean("Selectable on Sales Order Line")


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_related_invoices(self):
        """ Overridden from stock_account to return the customer invoices
        related to this stock move.
        """
        rslt = super(StockMove, self)._get_related_invoices()
        invoices = self.mapped('picking_id.sale_id.invoice_ids').filtered(lambda x: x.state == 'posted')
        rslt += invoices
        #rslt += invoices.mapped('reverse_entry_ids')
        return rslt

    def _get_source_document(self):
        res = super()._get_source_document()
        return self.group_id.sale_id or res

    def _assign_picking_post_process(self, new=False):
        super(StockMove, self)._assign_picking_post_process(new=new)
        if new:
            picking_id = self.mapped('picking_id')
            sale_order_ids = self.filtered(
                lambda m: m.location_id.usage == 'customer' or m.location_dest_id.usage == 'customer'
            ).mapped('group_id.sale_id')
            for sale_order_id in sale_order_ids:
                picking_id.message_post_with_view(
                    'mail.message_origin_link',
                    values={'self': picking_id, 'origin': sale_order_id},
                    subtype_id=self.env.ref('mail.mt_note').id)

    def _create_extra_so_line(self):
        sale_order_lines_vals = []

        moves_by_so_product = defaultdict(set)

        for move in self:
            sale_order = move.picking_id.sale_id
            if not move.picking_id.sale_id or move.location_dest_id.usage != 'customer' or not move.quantity_done:
                continue
            moves_by_so_product[(move.product_id, sale_order)].add(move.id)

        for (product, sale_order), move_ids in moves_by_so_product.items():
            sale_order_lines = sale_order.order_line.filtered(
                lambda l: l.product_id == product)

            if sale_order_lines:
                continue

            extra_quantity = sum(self.env['stock.move'].browse(
                move_ids).mapped('quantity_done'))
            so_line_vals = {
                'move_ids': [(4, move.id, 0)],
                'name': product.display_name,
                'order_id': sale_order.id,
                'product_id': product.id,
                'product_uom_qty': 0,
                'qty_delivered': extra_quantity,
            }
            if product.invoice_policy == 'order':
                # No unit price if the product is invoiced on the ordered qty.
                so_line_vals['price_unit'] = 0
            sale_order_lines_vals.append(so_line_vals)

        if sale_order_lines_vals:
            self.env['sale.order.line'].create(sale_order_lines_vals)


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    sale_id = fields.Many2one('sale.order', 'Sale Order')


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_custom_move_fields(self):
        fields = super(StockRule, self)._get_custom_move_fields()
        fields += ['partner_id']
        return fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sale_id = fields.Many2one(related="group_id.sale_id", string="Sales Order", store=True, readonly=False)

    def _action_done(self):
        res = super()._action_done()
        self.move_lines._create_extra_so_line()
        return res


class ProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    sale_order_ids = fields.Many2many('sale.order', string="Sales Orders", compute='_compute_sale_order_ids')
    sale_order_count = fields.Integer('Sale order count', compute='_compute_sale_order_ids')

    @api.depends('name')
    def _compute_sale_order_ids(self):
        sale_orders = defaultdict(lambda: self.env['sale.order'])
        for move_line in self.env['stock.move.line'].search([('lot_id', 'in', self.ids), ('state', '=', 'done')]):
            move = move_line.move_id
            if move.picking_id.location_dest_id.usage == 'customer' and move.sale_line_ids.order_id:
                sale_orders[move_line.lot_id.id] |= move.sale_line_ids.order_id
        for lot in self:
            lot.sale_order_ids = sale_orders[lot.id]
            lot.sale_order_count = len(lot.sale_order_ids)

    def action_view_so(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action['domain'] = [('id', 'in', self.mapped('sale_order_ids.id'))]
        action['context'] = dict(self._context, create=False)
        return action
