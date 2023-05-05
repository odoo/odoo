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

    @api.depends('pricelist_id.currency_id', 'date_order', 'company_id')
    def _compute_currency_rate(self):
        for order in self:
            date_order = order.date_order or fields.Datetime.now()
            order.currency_rate = self.env['res.currency']._get_conversion_rate(order.company_id.currency_id, order.pricelist_id.currency_id, order.company_id, date_order)

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
            if sale_orders[0].payment_term_id:
                invoice_vals['invoice_payment_term_id'] = sale_orders[0].payment_term_id.id
            if sale_orders[0].partner_invoice_id != sale_orders[0].partner_id:
                invoice_vals['partner_id'] = sale_orders[0].partner_invoice_id.id
        return invoice_vals

    @api.model
    def create_from_ui(self, orders, draft=False):
        order_ids = super(PosOrder, self).create_from_ui(orders, draft)
        for order in self.sudo().browse([o['id'] for o in order_ids]):
            for line in order.lines.filtered(lambda l: l.product_id == order.config_id.down_payment_product_id and l.qty > 0 and l.sale_order_origin_id):
                sale_lines = line.sale_order_origin_id.order_line
                sale_line = self.env['sale.order.line'].create({
                    'order_id': line.sale_order_origin_id.id,
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
                    if not picking.state in ['waiting', 'confirmed', 'assigned']:
                        continue
                    new_qty = so_line.product_uom_qty - so_line.qty_delivered
                    if float_compare(new_qty, 0, precision_rounding=stock_move.product_uom.rounding) <= 0:
                        new_qty = 0
                    stock_move.product_uom_qty = so_line.compute_uom_qty(new_qty, stock_move, False)
                    #If the product is delivered with more than one step, we need to update the quantity of the other steps
                    for move in so_line_stock_move_ids.filtered(lambda m: m.state in ['waiting', 'confirmed'] and m.product_id == stock_move.product_id):
                        move.product_uom_qty = stock_move.product_uom_qty
                    waiting_picking_ids.add(picking.id)

            def is_product_uom_qty_zero(move):
                return float_is_zero(move.product_uom_qty, precision_rounding=move.product_uom.rounding)

            # cancel the waiting pickings if each product_uom_qty of move is zero
            for picking in self.env['stock.picking'].browse(waiting_picking_ids):
                if all(is_product_uom_qty_zero(move) for move in picking.move_ids):
                    picking.action_cancel()

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


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    sale_order_origin_id = fields.Many2one('sale.order', string="Linked Sale Order")
    sale_order_line_id = fields.Many2one('sale.order.line', string="Source Sale Order Line")
    down_payment_details = fields.Text(string="Down Payment Details")

    def _export_for_ui(self, orderline):
        result = super()._export_for_ui(orderline)
        # NOTE We are not exporting 'sale_order_line_id' because it is being used in any views in the POS App.
        result['down_payment_details'] = bool(orderline.down_payment_details) and orderline.down_payment_details
        result['sale_order_origin_id'] = bool(orderline.sale_order_origin_id) and orderline.sale_order_origin_id.read(fields=['name'])[0]
        return result

    def _order_line_fields(self, line, session_id):
        result = super()._order_line_fields(line, session_id)
        vals = result[2]
        if vals.get('sale_order_origin_id', False):
            vals['sale_order_origin_id'] = vals['sale_order_origin_id']['id']
        if vals.get('sale_order_line_id', False):
            vals['sale_order_line_id'] = vals['sale_order_line_id']['id']
        return result
