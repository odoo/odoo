# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    def _compute_analytic(self, domain=None):
        lines = {}
        if not domain:
            domain = [('so_line', 'in', self.ids), ('unit_amount', '<=', 0.0)]
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
            if line.product_uom.category_id == uom.category_id:
                qty = self.env['product.uom']._compute_qty_obj(uom, d['unit_amount'], line.product_uom)
            else:
                qty = d['unit_amount']
            lines[line] += qty

        for line, qty in lines.items():
            line.qty_delivered = qty
        return True


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"
    so_line = fields.Many2one('sale.order.line', string='Sale Order Line')

    def _get_invoice_price(self, order):
        if self.unit_amount == 0.0:
            return 0.0
        price_unit = abs(self.amount / self.unit_amount)
        if self.currency_id and self.currency_id != order.currency_id:
            price_unit = self.currency_id.compute(price_unit, order.currency_id)
        return price_unit

    def _get_sale_order_line_vals(self):
        order = self.env['sale.order'].search([('project_id', '=', self.account_id.id)], limit=1)
        if not order:
            return False
        if order.state != 'sale':
            raise UserError(_('The Sale Order %s linked to the Analytic Account must be validated before registering expenses.' % order.name))

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
        so_line = result.get('so_line', False) or self.so_line
        if not so_line and self.account_id and self.product_id and self.product_id.invoice_policy in ('cost', 'order'):
            so_lines = self.env['sale.order.line'].search([
                ('order_id.project_id', '=', self.account_id.id),
                ('state', '=', 'sale'),
                ('product_id', '=', self.product_id.id)])
            # Use the existing SO line only if the unit prices are the same, otherwise we create
            # a new line
            for line in so_lines:
                if line.product_id.invoice_policy != 'cost' or (line.product_id.invoice_policy == 'cost' and line.price_unit == self._get_invoice_price(line.order_id)):
                    result.update({'so_line': line.id})
                    so_line = line
                    break

            else:
                # This will trigger the creation of a new SO line
                so_line = False

        if not so_line and self.account_id and self.product_id and self.product_id.invoice_policy == 'cost':
            order_line_vals = self._get_sale_order_line_vals()
            if order_line_vals:
                so_line = self.env['sale.order.line'].create(order_line_vals)
                so_line._compute_tax_id()
                result.update({'so_line': so_line.id})

        return result

    @api.multi
    def write(self, values):
        if self._context.get('create', False):
            return super(AccountAnalyticLine, self).write(values)

        lines = super(AccountAnalyticLine, self).write(values)
        for line in self:
            res = line.sudo()._get_sale_order_line(vals=values)
            super(AccountAnalyticLine, line).write(res)

        self.mapped('so_line').sudo()._compute_analytic()
        return lines

    @api.model
    def create(self, values):
        line = super(AccountAnalyticLine, self).create(values)
        res = line.sudo()._get_sale_order_line(vals=values)
        line.with_context(create=True).write(res)
        line.mapped('so_line').sudo()._compute_analytic()
        return line
