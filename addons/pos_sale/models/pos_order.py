# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_compare, float_is_zero, format_date


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
        values['crm_team_id'] = values['crm_team_id'] if values.get('crm_team_id') else session.config_id.crm_team_id.id
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

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        if any(p.payment_method_id._is_online_payment() for p in self.payment_ids):
            sale_orders = self.lines.mapped('sale_order_origin_id')
            for so in sale_orders.filtered(lambda s: s.state in ('draft', 'sent')):
                so.action_confirm()
        return res

    @api.model
    def sync_from_ui(self, orders):
        data = super().sync_from_ui(orders)
        if len(orders) == 0:
            return data

        AccountTax = self.env['account.tax']
        pos_orders = self.browse([o['id'] for o in data["pos.order"]])
        for pos_order in pos_orders:
            # TODO: the way to retrieve the sale order in not consistent... is it a bad code or intended?
            used_pos_lines = pos_order.lines.sale_order_origin_id.order_line.pos_order_line_ids
            downpayment_pos_order_lines = pos_order.lines.filtered(lambda line: (
                line not in used_pos_lines
                and line.product_id == pos_order.config_id.down_payment_product_id
            ))
            so_x_pos_order_lines = downpayment_pos_order_lines\
                .grouped(lambda l: l.sale_order_origin_id or l.refunded_orderline_id.sale_order_origin_id)
            sale_orders = self.env['sale.order']
            for sale_order, pos_order_lines in so_x_pos_order_lines.items():
                if not sale_order:
                    continue

                sale_orders += sale_order
                down_payment_base_lines = pos_order_lines._prepare_tax_base_line_values()
                AccountTax._add_tax_details_in_base_lines(down_payment_base_lines, sale_order.company_id)
                AccountTax._round_base_lines_tax_details(down_payment_base_lines, sale_order.company_id)

                sale_order_sudo = sale_order.sudo()
                sale_order_sudo._create_down_payment_section_line_if_needed()
                sale_order_sudo._create_down_payment_lines_from_base_lines(down_payment_base_lines)

            # Confirm the unconfirmed sale orders that are linked to the sale order lines.
            so_lines = pos_order.lines.mapped('sale_order_line_id')
            sale_orders |= so_lines.mapped('order_id')
            if pos_order.state != 'draft':
                for sale_order in sale_orders.filtered(lambda so: so.state in ['draft', 'sent']):
                    sale_order.action_confirm()

            # update the demand qty in the stock moves related to the sale order line
            # flush the qty_delivered to make sure the updated qty_delivered is used when
            # updating the demand value
            so_lines.flush_recordset(['qty_delivered'])
            # track the waiting pickings
            waiting_picking_ids = set()
            for so_line in so_lines:
                so_line_stock_move_ids = so_line.move_ids.reference_ids.move_ids
                for stock_move in so_line.move_ids:
                    picking = stock_move.picking_id
                    if not picking.state in ['waiting', 'confirmed', 'assigned']:
                        continue

                    def get_expected_qty_to_ship_later():
                        pos_pickings = so_line.pos_order_line_ids.order_id.picking_ids
                        if pos_pickings and all(pos_picking.state in ['confirmed', 'assigned'] for pos_picking in pos_pickings):
                            return sum((so_line._convert_qty(so_line, pos_line.qty, 'p2s') for pos_line in
                                        so_line.pos_order_line_ids if so_line.product_id.type != 'service'), 0)
                        return 0

                    qty_delivered = max(so_line.qty_delivered, get_expected_qty_to_ship_later())
                    new_qty = so_line.product_uom_qty - qty_delivered
                    if stock_move.product_uom.compare(new_qty, 0) <= 0:
                        new_qty = 0
                    stock_move.product_uom_qty = so_line.compute_uom_qty(new_qty, stock_move, False)
                    # If the product is delivered with more than one step, we need to update the quantity of the other steps
                    for move in so_line_stock_move_ids.filtered(lambda m: m.state in ['waiting', 'confirmed', 'assigned'] and m.product_id == stock_move.product_id):
                        move.product_uom_qty = stock_move.product_uom_qty
                        waiting_picking_ids.add(move.picking_id.id)
                    waiting_picking_ids.add(picking.id)

            def is_product_uom_qty_zero(move):
                return move.product_uom.is_zero(move.product_uom_qty)

            # cancel the waiting pickings if each product_uom_qty of move is zero
            for picking in self.env['stock.picking'].browse(waiting_picking_ids):
                if all(is_product_uom_qty_zero(move) for move in picking.move_ids):
                    picking.action_cancel()
                else:
                    # We make sure that the original picking still has the correct quantity reserved
                    picking.action_assign()

        return data

    def action_view_sale_order(self):
        self.ensure_one()
        linked_orders = self.lines.mapped('sale_order_origin_id')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Linked Sale Orders'),
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', linked_orders.ids)],
        }

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

    def _get_invoice_lines_values(self, line_values, pos_line, move_type):
        inv_line_vals = super()._get_invoice_lines_values(line_values, pos_line, move_type)

        if pos_line.sale_order_origin_id:
            origin_line = pos_line.sale_order_line_id
            inv_line_vals["name"] = origin_line.name
            origin_line._set_analytic_distribution(inv_line_vals)

        return inv_line_vals

    def write(self, vals):
        if 'crm_team_id' in vals:
            vals['crm_team_id'] = vals['crm_team_id'] if vals.get('crm_team_id') else self.session_id.crm_team_id.id
        return super().write(vals)

    def _force_create_picking_real_time(self):
        result = super()._force_create_picking_real_time()
        return result or any(self.lines.mapped('sale_order_origin_id'))


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    sale_order_origin_id = fields.Many2one('sale.order', string="Linked Sale Order", index='btree_not_null')
    sale_order_line_id = fields.Many2one('sale.order.line', string="Source Sale Order Line", index='btree_not_null')
    down_payment_details = fields.Text(string="Down Payment Details")
    qty_delivered = fields.Float(
        string="Delivery Quantity",
        compute="_compute_qty_delivered",
        store=True, readonly=False, copy=False)

    @api.depends('order_id.state', 'order_id.picking_ids', 'order_id.picking_ids.state', 'order_id.picking_ids.move_ids.quantity')
    def _compute_qty_delivered(self):
        product_qty_left_to_assign = {}
        for order_line in self:
            if order_line.order_id.state in ['paid', 'done']:
                outgoing_pickings = order_line.order_id.picking_ids.filtered(
                    lambda pick: pick.state == 'done' and pick.picking_type_code == 'outgoing'
                )

                if outgoing_pickings and order_line.order_id.shipping_date:
                    moves = outgoing_pickings.move_ids.filtered(
                        lambda m: m.state == 'done' and m.product_id == order_line.product_id
                    )
                    qty_left = product_qty_left_to_assign.get(order_line.product_id.id, False)
                    if (qty_left):
                        order_line.qty_delivered = min(order_line.qty, qty_left)
                        product_qty_left_to_assign[order_line.product_id.id] -= order_line.qty_delivered
                    else:
                        order_line.qty_delivered = min(order_line.qty, sum(moves.mapped('quantity')))
                        product_qty_left_to_assign[order_line.product_id.id] = sum(moves.mapped('quantity')) - order_line.qty_delivered

                elif outgoing_pickings:
                    # If the order is not delivered later, and in a "paid", "done" or "invoiced" state, it fully delivered
                    order_line.qty_delivered = order_line.qty
                else:
                    order_line.qty_delivered = 0

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ['sale_order_origin_id', 'sale_order_line_id', 'down_payment_details']
        return params

    def _launch_stock_rule_from_pos_order_lines(self):
        orders = self.mapped('order_id')
        for order in orders:
            self.env['stock.move'].browse(order.lines.sale_order_line_id.move_ids._rollup_move_origs()).filtered(lambda ml: ml.state not in ['cancel', 'done'])._action_cancel()
        return super()._launch_stock_rule_from_pos_order_lines()
