# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PosOrder(models.Model):
    _inherit = 'pos.order'

    currency_rate = fields.Float(compute='_compute_currency_rate', store=True, digits=0, readonly=True)
    crm_team_id = fields.Many2one('crm.team', string="Sales Team")
    sale_order_origin_id = fields.Many2one('sale.order', string="Linked Sale Order")
    sale_order_count = fields.Integer(string='Sale Order Count', compute='_count_sale_order', readonly=True, groups="sales_team.group_sale_salesman")

    def _count_sale_order(self):
        for order in self:
            order.sale_order_count = len(order.sale_order_origin_id | order.lines.mapped('sale_order_origin_id'))

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
        invoice_vals['team_id'] = self.crm_team_id
        return invoice_vals

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(PosOrder, self)._order_fields(ui_order)
        order_fields['sale_order_origin_id'] = ui_order.get('sale_order_origin_id')
        return order_fields

    def _export_for_ui(self, order):
        result = super(PosOrder, self)._export_for_ui(order)
        result.update({
            'sale_order_origin_id': order.sale_order_origin_id.id,
        })
        return result

    @api.model
    def create_from_ui(self, orders, draft=False):
        order_ids = super(PosOrder, self).create_from_ui(orders, draft)
        for order in self.sudo().browse([o['id'] for o in order_ids]):
            for line in order.lines.filtered(lambda l: l.product_id == order.config_id.down_payment_product_id and l.qty != -1):
                sale_lines = line.sale_order_origin_id.order_line
                sale_line = self.env['sale.order.line'].create({
                    'order_id': line.sale_order_origin_id.id,
                    'product_id': line.product_id.id,
                    'price_unit': line.price_unit,
                    'product_uom_qty': 0,
                    'tax_id': [(6, 0, line.tax_ids.ids)],
                    'is_downpayment': True,
                    'discount': 0,
                    'sequence': sale_lines and sale_lines[-1].sequence + 1 or 10,
                })
                sale_line._compute_tax_id()
                line.sale_order_line_id = sale_line

            # update the demand qty in the stock moves related to the sale order line
            # flush the qty_delivered to make sure the updated qty_delivered is used when
            # updating the demand value
            so_lines = order.lines.mapped('sale_order_line_id')
            so_lines.flush(['qty_delivered'])
            for so_line in so_lines:
                for stock_move in so_line.move_ids:
                    if not stock_move.picking_id.state in ['waiting', 'confirmed', 'assigned']:
                        continue
                    new_qty = so_line.product_uom_qty - so_line.qty_delivered
                    if new_qty < 0:
                        new_qty = 0
                    stock_move.product_uom_qty = new_qty

        return order_ids

    def action_view_sale_order(self):
        self.ensure_one()
        linked_orders = self.sale_order_origin_id | self.lines.mapped('sale_order_origin_id')
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

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        if self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms'):
            vals['narration'] = vals['narration'] + '\n' + self.company_id.invoice_terms if vals['narration'] else self.company_id.invoice_terms
        return vals
