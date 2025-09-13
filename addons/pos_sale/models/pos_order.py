# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_compare, float_is_zero

class PosOrder(models.Model):
    _inherit = 'pos.order'

    currency_rate = fields.Float(compute='_compute_currency_rate', store=True, digits=0, readonly=True)
    crm_team_id = fields.Many2one('crm.team', string="Sales Team", ondelete="set null")
    sale_order_count = fields.Integer(string='Sale Order Count', compute='_count_sale_order', readonly=True, groups="sales_team.group_sale_salesman")

    def _count_sale_order(self):
        for order in self:
            order.sale_order_count = len(order.lines.mapped('sale_order_origin_id'))

    @api.model
    def _complete_values_from_session(self, session, values):
        values = super(PosOrder, self)._complete_values_from_session(session, values)
        values.setdefault('crm_team_id', session.config_id.crm_team_id.id)
        return values

    @api.depends('date_order', 'company_id')
    def _compute_currency_rate(self):
        for order in self:
            date_order = order.date_order or fields.Datetime.now()
            order.currency_rate = self.env['res.currency']._get_conversion_rate(order.company_id.currency_id, order.currency_id, order.company_id, date_order.date())

    def _prepare_invoice_vals(self):
        invoice_vals = super(PosOrder, self)._prepare_invoice_vals()
        invoice_vals['team_id'] = self.crm_team_id.id
        sale_orders = self.lines.mapped('sale_order_origin_id')
        if sale_orders:
            if sale_orders[0].partner_invoice_id.id != sale_orders[0].partner_shipping_id.id:
                invoice_vals['partner_shipping_id'] = sale_orders[0].partner_shipping_id.id
            else:
                addr = self.partner_id.address_get(['delivery'])
                invoice_vals['partner_shipping_id'] = addr['delivery']
            if sale_orders[0].payment_term_id and not sale_orders[0].payment_term_id.early_discount:
                invoice_vals['invoice_payment_term_id'] = sale_orders[0].payment_term_id.id
            else:
                invoice_vals['invoice_payment_term_id'] = False
            if sale_orders[0].partner_invoice_id != sale_orders[0].partner_id:
                invoice_vals['partner_id'] = sale_orders[0].partner_invoice_id.id
        return invoice_vals

    @api.model
    def create_from_ui(self, orders, draft=False):
        order_ids = super(PosOrder, self).create_from_ui(orders, draft)
        if draft:
            return order_ids

        for order in self.sudo().browse([o['id'] for o in order_ids]):
            for line in order.lines.filtered(lambda l: l.product_id == order.config_id.down_payment_product_id and l.qty != 0 and (l.sale_order_origin_id or l.refunded_orderline_id.sale_order_origin_id)):
                sale_lines = line.sale_order_origin_id.order_line or line.refunded_orderline_id.sale_order_origin_id.order_line
                sale_order_origin = line.sale_order_origin_id or line.refunded_orderline_id.sale_order_origin_id
                sale_line = self.env['sale.order.line'].create({
                    'order_id': sale_order_origin.id,
                    'product_id': line.product_id.id,
                    'price_unit': line.price_unit,
                    'product_uom_qty': 0,
                    'tax_id': [(6, 0, line.tax_ids.ids)],
                    'is_downpayment': True,
                    'discount': line.discount,
                    'sequence': sale_lines and sale_lines[-1].sequence + 1 or 10,
                })
                line.sale_order_line_id = sale_line

            so_lines = order.lines.mapped('sale_order_line_id')

            # confirm the unconfirmed sale orders that are linked to the sale order lines
            sale_orders = so_lines.mapped('order_id')
            for sale_order in sale_orders.filtered(lambda so: so.state in ['draft', 'sent']):
                sale_order.action_confirm()

            # update the demand qty in the stock moves related to the sale order line
            # flush the qty_delivered to make sure the updated qty_delivered is used when
            # updating the demand value
            so_lines.flush_recordset(['qty_delivered'])
            # track the waiting pickings
            waiting_picking_ids = set()
            for so_line in so_lines:
                so_line_stock_move_ids = so_line.move_ids.group_id.stock_move_ids
                for stock_move in so_line.move_ids:
                    picking = stock_move.picking_id
                    if picking.state not in ['waiting', 'confirmed', 'assigned']:
                        continue

                    def get_expected_qty_to_ship_later():
                        pos_pickings = so_line.pos_order_line_ids.order_id.picking_ids
                        if pos_pickings and all(pos_picking.state in ['confirmed', 'assigned'] for pos_picking in pos_pickings):
                            return sum((so_line._convert_qty(so_line, pos_line.qty, 'p2s') for pos_line in
                                        so_line.pos_order_line_ids if so_line.product_id.type != 'service'), 0)
                        return 0

                    qty_delivered = max(so_line.qty_delivered, get_expected_qty_to_ship_later())
                    new_qty = so_line.product_uom_qty - qty_delivered
                    if float_compare(new_qty, 0, precision_rounding=stock_move.product_uom.rounding) <= 0:
                        new_qty = 0
                    stock_move.product_uom_qty = so_line.compute_uom_qty(new_qty, stock_move, False)
                    # If the product is delivered with more than one step, we need to update the quantity of the other steps
                    for move in so_line_stock_move_ids.filtered(lambda m: m.state in ['waiting', 'confirmed', 'assigned'] and m.product_id == stock_move.product_id):
                        move.product_uom_qty = stock_move.product_uom_qty
                        waiting_picking_ids.add(move.picking_id.id)
                    waiting_picking_ids.add(picking.id)

            def is_product_uom_qty_zero(move):
                return float_is_zero(move.product_uom_qty, precision_rounding=move.product_uom.rounding)

            # cancel the waiting pickings if each product_uom_qty of move is zero
            for picking in self.env['stock.picking'].browse(waiting_picking_ids):
                if all(is_product_uom_qty_zero(move) for move in picking.move_ids):
                    picking.action_cancel()
                else:
                    # We make sure that the original picking still has the correct quantity reserved
                    picking.action_assign()

        return order_ids

    def action_view_sale_order(self):
        self.ensure_one()
        linked_orders = self.lines.mapped('sale_order_origin_id')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Linked Sale Orders'),
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', linked_orders.ids)],
        }

    def _get_invoice_lines_values(self, line_values, pos_line):
        inv_line_vals = super()._get_invoice_lines_values(line_values, pos_line)

        if pos_line.sale_order_origin_id:
            origin_line = pos_line.sale_order_line_id
            origin_line._set_analytic_distribution(inv_line_vals)

        return inv_line_vals

    def _get_fields_for_order_line(self):
        fields = super(PosOrder, self)._get_fields_for_order_line()
        fields.extend([
            'sale_order_origin_id',
            'down_payment_details',
            'sale_order_line_id',
        ])
        return fields

    def _prepare_order_line(self, order_line):
        order_line = super()._prepare_order_line(order_line)
        if order_line.get('sale_order_origin_id'):
            order_line['sale_order_origin_id'] = {
                'id': order_line['sale_order_origin_id'][0],
                'name': order_line['sale_order_origin_id'][1],
            }
        if order_line.get('sale_order_line_id'):
            order_line['sale_order_line_id'] = {
                'id': order_line['sale_order_line_id'][0],
            }
        return order_line

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    sale_order_origin_id = fields.Many2one('sale.order', string="Linked Sale Order")
    sale_order_line_id = fields.Many2one('sale.order.line', string="Source Sale Order Line")
    down_payment_details = fields.Text(string="Down Payment Details")

    def _export_for_ui(self, orderline):
        result = super()._export_for_ui(orderline)
        result['down_payment_details'] = bool(orderline.down_payment_details) and orderline.down_payment_details
        result['sale_order_origin_id'] = bool(orderline.sale_order_origin_id) and orderline.sale_order_origin_id.read(fields=['name'])[0]
        result['sale_order_line_id'] = bool(orderline.sale_order_line_id) and orderline.sale_order_line_id.read(fields=['name'])[0]
        return result

    def _order_line_fields(self, line, session_id=None):
        result = super()._order_line_fields(line, session_id)
        vals = result[2]
        if vals.get('sale_order_origin_id', False):
            vals['sale_order_origin_id'] = vals['sale_order_origin_id']['id']
        if vals.get('sale_order_line_id', False):
            #We need to make sure the order line has not been deleted while the order was being handled in the PoS
            order_line = self.env['sale.order.line'].search([('id', '=', vals['sale_order_line_id']['id'])], limit=1)
            vals['sale_order_line_id'] = order_line.id if order_line else False
        return result

    def _launch_stock_rule_from_pos_order_lines(self):
        orders = self.mapped('order_id')
        for order in orders:
            self.env['stock.move'].browse(order.lines.sale_order_line_id.move_ids._rollup_move_origs()).filtered(lambda ml: ml.state not in ['cancel', 'done'])._action_cancel()
        return super()._launch_stock_rule_from_pos_order_lines()
