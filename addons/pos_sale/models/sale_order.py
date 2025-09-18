# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, Command
from odoo.tools import format_date


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'pos.load.mixin']

    pos_order_line_ids = fields.One2many('pos.order.line', 'sale_order_origin_id', string="Order lines Transferred to Point of Sale", readonly=True, groups="point_of_sale.group_pos_user")
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
        return ['name', 'state', 'user_id', 'line_ids', 'partner_id', 'pricelist_id', 'fiscal_position_id', 'amount_total', 'amount_untaxed', 'amount_unpaid',
            'picking_ids', 'partner_shipping_id', 'partner_invoice_id', 'date_order', 'write_date', 'amount_paid']

    def load_sale_order_from_pos(self, config_id):
        product_ids = self.line_ids.product_id.ids
        product_tmpls = self.env['product.template'].load_product_from_pos(
            config_id,
            [('product_variant_ids.id', 'in', product_ids)]
        )
        sale_order_fields = self._load_pos_data_fields(config_id)
        sale_order_read = self.read(sale_order_fields, load=False)
        sale_order_line_fields = self.line_ids._load_pos_data_fields(config_id)
        sale_order_line_read = self.line_ids.read(sale_order_line_fields, load=False)
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

    @api.depends('transaction_ids.state', 'transaction_ids.amount', 'line_ids', 'amount_total', 'line_ids.invoice_line_ids.parent_state', 'line_ids.invoice_line_ids.price_total', 'line_ids.pos_order_line_ids')
    def _compute_amount_unpaid(self):
        for sale_order in self:
            invoices = sale_order.line_ids.invoice_line_ids.move_id.filtered(lambda invoice: invoice.state in ('draft', 'posted'))
            total_invoices_paid = sum(invoices.mapped('amount_total'))
            pos_orders = sale_order.line_ids.pos_order_line_ids.order_id
            total_pos_orders_paid = sum(pos_orders.mapped('amount_total'))
            sale_order.amount_unpaid = max(sale_order.amount_total - total_invoices_paid - total_pos_orders_paid - sale_order.amount_paid, 0.0)

    @api.depends('line_ids.pos_order_line_ids')
    def _compute_amount_taxinc_to_invoice(self):
        super()._compute_amount_taxinc_to_invoice()
        for order in self:
            # We need to account for all amount paid in POS with and without invoice
            order_amount = sum(order.sudo().pos_order_line_ids.mapped('price_subtotal_incl'))
            order.amount_taxinc_to_invoice -= order_amount

    @api.depends('line_ids.pos_order_line_ids')
    def _compute_amounts_invoice(self):
        super()._compute_amounts_invoice()
        for order in self:
            if order.invoice_state == 'done':
                continue
            # We need to account for the downpayment paid in POS with and without invoice
            order_amount = sum(order.sudo().pos_order_line_ids.filtered(lambda pol: pol.order_id.state in ['paid', 'done', 'invoiced'] and pol.sale_order_line_id.is_downpayment).mapped('price_subtotal_incl'))
            order.amount_taxinc_invoiced += order_amount

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
