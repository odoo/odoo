# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import float_is_zero


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _sale_get_invoice_price(self, order):
        """ Based on the current stock move, compute the price to reinvoice the analytic line that is going to be created (so the
            price of the sale line).
        """
        self.ensure_one()

        if self.product_id.expense_policy == 'sales_price':
            return order.pricelist_id._get_product_price(
                self.product_id,
                1.0,
                uom=self.product_uom,
                date=order.date_order,
            )

        uom_precision_digits = self.env['decimal.precision'].precision_get('Product Unit')
        if float_is_zero(self.quantity, precision_digits=uom_precision_digits):
            return 0.0

        price_unit = self.product_id.standard_price
        # Prevent unnecessary currency conversion that could be impacted by exchange rate
        # fluctuations
        if self.company_id.currency_id and price_unit and self.company_id.currency_id == order.currency_id:
            return self.company_id.currency_id.round(price_unit)

        currency_id = self.company_id.currency_id
        if currency_id and currency_id != order.currency_id:
            price_unit = currency_id._convert(price_unit, order.currency_id, order.company_id, order.date_order or fields.Date.today())
        return price_unit

    def _sale_prepare_sale_line_values(self, order, price, last_sequence):
        """ Generate the sale.line creation value from the current stock move """
        self.ensure_one()

        fpos = order.fiscal_position_id or order.fiscal_position_id._get_fiscal_position(order.partner_id)
        product_taxes = self.product_id.taxes_id._filter_taxes_by_company(order.company_id)
        taxes = fpos.map_tax(product_taxes)

        return {
            'order_id': order.id,
            'name': self.name,
            'sequence': last_sequence,
            'price_unit': price,
            'tax_ids': [x.id for x in taxes],
            'discount': 0.0,
            'product_id': self.product_id.id,
            'product_uom_qty': self.product_uom_qty,
            'qty_delivered': self.quantity,
        }

    def _get_new_picking_values(self):
        return {
            **super()._get_new_picking_values(),
            'project_id': self.sale_line_id.order_id.project_id.id,
        }

    def _assign_picking_values(self, picking):
        return {
            **super()._assign_picking_values(picking),
            'project_id': self[:1].sale_line_id.order_id.project_id.id,
        }

    def _prepare_procurement_values(self):
        res = super()._prepare_procurement_values()
        project = self.sale_line_id.order_id.project_id
        if project:
            res['project_id'] = project.id
        return res
