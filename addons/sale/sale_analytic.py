# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    def _compute_analytic(self, domain=None):
        lines = {}
        if not domain:
            domain = [('so_line', 'in', self.ids), ('amount', '<', 0.0)]
        data = self.env['account.analytic.line'].read_group(
            domain,
            ['so_line', 'unit_amount', 'product_uom_id'], ['product_uom_id', 'so_line'], lazy=False
        )
        for d in data:
            if not d['product_uom_id']:
                continue
            line = self.browse(d['so_line'][0])
            lines.setdefault(line, 0.0)
            uom = self.env['product.uom'].browse(d['product_uom_id'][0])

            qty = self.env['product.uom']._compute_qty_obj(uom, d['unit_amount'], line.product_uom)
            lines[line] += qty

        for line, qty in lines.items():
            line.qty_delivered = qty
        return True


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"
    so_line = fields.Many2one('sale.order.line', string='Sale Order Line')

    def _get_invoice_price(self, order):
        return abs(self.amount / self.unit_amount)

    def _get_sale_order_line_vals(self):
        order = self.env['sale.order'].search([('project_id', '=', self.account_id.id), ('state', '=', 'sale')], limit=1)

        last_so_line = self.env['sale.order.line'].search([('order_id', '=', order.id)], order='sequence desc', limit=1)
        last_sequence = last_so_line.sequence + 1 if last_so_line else 100

        fpos = order.fiscal_position_id or order.partner_id.property_account_position_id
        taxes = fpos.map_tax(self.product_id.taxes_id)
        price = self._get_invoice_price(order)

        return {
            'order_id': order.id,
            'name': self.name,
            'sequence': last_sequence,
            'price_unit': price,
            'tax_id': [x.id for x in taxes],
            'discount': 0.0,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': 0.0,
            'qty_delivered': self.unit_amount,
        }

    def _get_sale_order_line(self, vals=None):
        result = dict(vals or {})
        sol = result.get('so_line', False) or self.so_line
        if not sol and self.account_id and self.product_id and self.product_id.invoice_policy in ('cost', 'order'):
            sol = self.env['sale.order.line'].search([
                ('order_id.project_id', '=', self.account_id.id),
                ('state', '=', 'sale'),
                ('product_id', '=', self.product_id.id)],
                limit=1)
            result.update({'so_line': sol.id})

        if not sol and self.account_id and self.product_id and self.product_id.invoice_policy == 'cost':
            order_line_vals = self._get_sale_order_line_vals()
            sol = self.env['sale.order.line'].create(order_line_vals)
            sol._compute_tax_id()
            result.update({'so_line': sol.id})

        return result

    @api.multi
    def write(self, values):
        if self._context.get('create', False):
            return super(AccountAnalyticLine, self).write(values)

        todo = self.mapped('so_line')
        result = super(AccountAnalyticLine, self).write(values)
        if 'so_line' in values:
            todo |= self.mapped('so_line')

        for line in self:
            res = self._get_sale_order_line(vals=values)
            super(AccountAnalyticLine, line).write(res)
            if 'so_line' in res:
                todo |= line.mapped('so_line')

        todo._compute_analytic()
        return result

    @api.model
    def create(self, values):
        line = super(AccountAnalyticLine, self).create(values)
        res = line._get_sale_order_line(vals=values)
        line.with_context(create=True).write(res)
        line.mapped('so_line')._compute_analytic()
        return line
