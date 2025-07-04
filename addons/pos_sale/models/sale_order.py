# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, Command
from odoo.tools import format_date


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'pos.load.mixin']

    pos_order_line_ids = fields.One2many('pos.order.line', 'sale_order_origin_id', string="Order lines Transfered to Point of Sale", readonly=True, groups="point_of_sale.group_pos_user")
    pos_order_count = fields.Integer(string='Pos Order Count', compute='_count_pos_order', readonly=True, groups="point_of_sale.group_pos_user")
    amount_unpaid = fields.Monetary(
        string="Amount To Pay In POS",
        help="Amount left to pay in POS to avoid double payment or double invoicing.",
        compute='_compute_amount_unpaid',
        store=True,
    )

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [['pos_order_line_ids.order_id.state', '=', 'draft']]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['name', 'state', 'user_id', 'order_line', 'partner_id', 'pricelist_id', 'fiscal_position_id', 'amount_total', 'amount_untaxed', 'amount_unpaid',
            'picking_ids', 'partner_shipping_id', 'partner_invoice_id', 'date_order', 'write_date']

    def load_sale_order_from_pos(self, config_id):
        product_ids = self.order_line.product_id.ids
        product_tmpls = self.env['product.template'].load_product_from_pos(
            config_id,
            [('product_variant_ids.id', 'in', product_ids)]
        )
        sale_order_fields = self._load_pos_data_fields(config_id)
        sale_order_read = self.read(sale_order_fields, load=False)
        sale_order_line_fields = self.order_line._load_pos_data_fields(config_id)
        sale_order_line_read = self.order_line.read(sale_order_line_fields, load=False)
        sale_order_fp_fields = self.env['account.fiscal.position']._load_pos_data_fields(config_id)
        sale_order_fp_read = self.fiscal_position_id.read(sale_order_fp_fields, load=False)
        partner_fields = self.env['res.partner']._load_pos_data_fields(config_id)

        return {
            'sale.order': sale_order_read,
            'sale.order.line': sale_order_line_read,
            'account.fiscal.position': sale_order_fp_read,
            'res.partner': self.partner_id.read(partner_fields, load=False),
            **product_tmpls,
        }

    def _count_pos_order(self):
        for order in self:
            linked_orders = order.pos_order_line_ids.mapped('order_id')
            order.pos_order_count = len(linked_orders)

    def action_view_pos_order(self):
        self.ensure_one()
        linked_orders = self.pos_order_line_ids.mapped('order_id')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Linked POS Orders'),
            'res_model': 'pos.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', linked_orders.ids)],
        }

    @api.depends('order_line', 'amount_total', 'order_line.invoice_lines.parent_state', 'order_line.invoice_lines.price_total', 'order_line.pos_order_line_ids')
    def _compute_amount_unpaid(self):
        for sale_order in self:
            total_invoice_paid = sum(sale_order.order_line.filtered(lambda l: not l.display_type).mapped('invoice_lines').filtered(lambda l: l.parent_state != 'cancel').mapped('price_total'))
            total_pos_paid = sum(sale_order.order_line.filtered(lambda l: not l.display_type).mapped('pos_order_line_ids.price_subtotal_incl'))
            sale_order.amount_unpaid = sale_order.amount_total - (total_invoice_paid + total_pos_paid)

    @api.depends('order_line.pos_order_line_ids')
    def _compute_amount_to_invoice(self):
        super()._compute_amount_to_invoice()
        for order in self:
            # We need to account for all amount paid in POS with and without invoice
            order_amount = sum(order.sudo().pos_order_line_ids.mapped('price_subtotal_incl'))
            order.amount_to_invoice -= order_amount

    @api.depends('order_line.pos_order_line_ids')
    def _compute_amount_invoiced(self):
        super()._compute_amount_invoiced()
        for order in self:
            if order.invoice_status == 'invoiced':
                continue
            # We need to account for the downpayment paid in POS with and without invoice
            order_amount = sum(order.sudo().pos_order_line_ids.filtered(lambda pol: pol.order_id.state in ['paid', 'done', 'invoiced'] and pol.sale_order_line_id.is_downpayment).mapped('price_subtotal_incl'))
            order.amount_invoiced += order_amount

    def _prepare_down_payment_line_values_from_base_line(self, base_line):
        # EXTENDS 'sale'
        so_line_values = super()._prepare_down_payment_line_values_from_base_line(base_line)
        if (
            base_line
            and base_line['record']
            and isinstance(base_line['record'], models.Model)
            and base_line['record']._name == 'pos.order.line'
        ):
            pos_order_line = base_line['record']
            so_line_values['name'] = _(
                "Down payment (ref: %(order_reference)s on \n %(date)s)",
                order_reference=pos_order_line.name,
                date=format_date(pos_order_line.env, pos_order_line.order_id.date_order),
            )
            so_line_values['pos_order_line_ids'] = [Command.set(pos_order_line.ids)]
        return so_line_values


class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = ['sale.order.line', 'pos.load.mixin']

    pos_order_line_ids = fields.One2many('pos.order.line', 'sale_order_line_id', string="Order lines Transfered to Point of Sale", readonly=True, groups="point_of_sale.group_pos_user")

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('order_id', 'in', [order['id'] for order in data['sale.order']])]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['discount', 'display_name', 'price_total', 'price_unit', 'product_id', 'product_uom_qty', 'qty_delivered',
            'qty_invoiced', 'qty_to_invoice', 'display_type', 'name', 'tax_ids', 'is_downpayment', 'extra_tax_data',
            'write_date', 'product_custom_attribute_value_ids'
        ]

    @api.depends('pos_order_line_ids.qty', 'pos_order_line_ids.order_id.picking_ids', 'pos_order_line_ids.order_id.picking_ids.state')
    def _compute_qty_delivered(self):
        super()._compute_qty_delivered()
        for sale_line in self:
            pos_lines = sale_line.sudo().pos_order_line_ids.filtered(lambda order_line: order_line.order_id.state not in ['cancel', 'draft'])
            if all(picking.state == 'done' for picking in pos_lines.order_id.picking_ids):
                sale_line.qty_delivered += sum((self._convert_qty(sale_line, pos_line.qty, 'p2s') for pos_line in pos_lines if sale_line.product_id.type != 'service'), 0)

    @api.depends('pos_order_line_ids.qty')
    def _compute_qty_invoiced(self):
        super()._compute_qty_invoiced()
        for sale_line in self:
            pos_lines = sale_line.sudo().pos_order_line_ids.filtered(lambda order_line: order_line.order_id.state not in ['cancel', 'draft'])
            sale_line.qty_invoiced += sum([self._convert_qty(sale_line, pos_line.qty, 'p2s') for pos_line in pos_lines], 0)

    def _get_sale_order_fields(self):
        return ["product_id", "display_name", "price_unit", "product_uom_qty", "tax_ids", "qty_delivered", "qty_invoiced", "discount", "qty_to_invoice", "price_total", "is_downpayment"]

    def read_converted(self):
        field_names = self._get_sale_order_fields()
        results = []
        for sale_line in self:
            if sale_line.product_type or (sale_line.is_downpayment and sale_line.price_unit != 0):
                product_uom = sale_line.product_id.uom_id
                sale_line_uom = sale_line.product_uom_id
                item = sale_line.read(field_names, load=False)[0]
                if sale_line.product_id.tracking != 'none':
                    item['lot_names'] = sale_line.move_ids.move_line_ids.lot_id.mapped('name')
                    item['lot_qty_by_name'] = {line.lot_id.name: line.quantity for line in sale_line.move_ids.move_line_ids}
                if product_uom == sale_line_uom:
                    results.append(item)
                    continue
                item['product_uom_qty'] = self._convert_qty(sale_line, item['product_uom_qty'], 's2p')
                item['qty_delivered'] = self._convert_qty(sale_line, item['qty_delivered'], 's2p')
                item['qty_invoiced'] = self._convert_qty(sale_line, item['qty_invoiced'], 's2p')
                item['qty_to_invoice'] = self._convert_qty(sale_line, item['qty_to_invoice'], 's2p')
                item['price_unit'] = sale_line_uom._compute_price(item['price_unit'], product_uom)
                results.append(item)

            elif sale_line.display_type == 'line_note':
                if results:
                    if results[-1].get('customer_note'):
                        results[-1]['customer_note'] += "--" + sale_line.name
                    else:
                        results[-1]['customer_note'] = sale_line.name


        return results

    @api.model
    def _convert_qty(self, sale_line, qty, direction):
        """Converts the given QTY based on the given SALE_LINE and DIR.

        if DIR='s2p': convert from sale line uom to product uom
        if DIR='p2s': convert from product uom to sale line uom
        """
        product_uom = sale_line.product_id.uom_id
        sale_line_uom = sale_line.product_uom_id
        if direction == 's2p':
            return sale_line_uom._compute_quantity(qty, product_uom, False)
        elif direction == 'p2s':
            return product_uom._compute_quantity(qty, sale_line_uom, False)

    def unlink(self):
        # do not delete downpayment lines created from pos
        pos_downpayment_lines = self.filtered(lambda line: line.is_downpayment and line.sudo().pos_order_line_ids)
        return super(SaleOrderLine, self - pos_downpayment_lines).unlink()

    @api.depends('pos_order_line_ids')
    def _compute_untaxed_amount_invoiced(self):
        super()._compute_untaxed_amount_invoiced()
        for line in self:
            line.untaxed_amount_invoiced += sum(line.sudo().pos_order_line_ids.mapped('price_subtotal'))

    def _get_downpayment_line_price_unit(self, invoices):
        return super()._get_downpayment_line_price_unit(invoices) + sum(
            pol.price_unit for pol in self.sudo().pos_order_line_ids
        )

    @api.depends('product_id', 'pos_order_line_ids')
    def _compute_name(self):
        for sol in self:
            if sol.sudo().pos_order_line_ids:
                downpayment_sols = sol.pos_order_line_ids.mapped('refunded_orderline_id.sale_order_line_id')
                for downpayment_sol in downpayment_sols:
                    downpayment_sol.name = _("%(line_description)s (Cancelled)", line_description=downpayment_sol.name)
            else:
                super()._compute_name()
