from odoo import models


class StockValuationReport(models.AbstractModel):
    _inherit = 'stock_account.stock.valuation.report'

    # TODO remove in master
    def _compute_goods_delivered_not_invoiced(self, date=False, product_category=False):
        """ Compute valuation for already delivered but not invoiced yet goods,.
        sale order by sale order."""
        domain = [('qty_to_invoice', '!=', 0)]
        if product_category:
            domain += [('product_id.categ_id', '=', product_category.id)]
        if date:
            domain += [('order_id.date_order', '<=', date)]
        sol_by_order = self.env['sale.order.line']._read_group(
            domain=domain,
            groupby=['order_id'],
            aggregates=['id:recordset']
        )
        not_invoiced_delivered_lines = []
        total = 0
        for order, order_lines in sol_by_order:
            value = 0
            for order_line in order_lines:
                confirmed_invoice_lines = order_line.invoice_lines.filtered(
                    lambda aml: aml.move_id.state == 'posted'
                )
                invoiced_value = sum(confirmed_invoice_lines.mapped('amount_currency'), 0)
                value += order_line.price_subtotal + invoiced_value
            not_invoiced_delivered_lines.append({
                'id': order.id,
                'display_name': order.display_name,
                'value': value,
            })
            total += value
        return {
            'lines': not_invoiced_delivered_lines,
            'value': total,
        }
