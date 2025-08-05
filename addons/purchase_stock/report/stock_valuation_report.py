from odoo import models


class StockValuationReport(models.AbstractModel):
    _inherit = 'stock_account.stock.valuation.report'

    def _get_report_data(self, date=False, product_category=False, warehouse=False):
        data = super()._get_report_data(date, product_category, warehouse)
        not_invoiced_received_data = self._compute_goods_received_not_invoiced(date, product_category)
        data['not_invoiced_received_goods'] = not_invoiced_received_data
        return data

    def _compute_goods_received_not_invoiced(self, date=False, product_category=False):
        """ Compute valuation for already received but not invoiced yet goods,
        purchase order by purchase order."""
        domain = [('qty_to_invoice', '!=', 0)]
        if product_category:
            domain += [('product_id.categ_id', '=', product_category.id)]
        if date:
            domain += [('date_approve', '<=', date)]
        purchase_order_lines = self.env['purchase.order.line'].search(domain)
        purchase_orders = purchase_order_lines.order_id
        not_invoiced_received_lines = []
        total = 0
        for order in purchase_orders:
            order_lines = purchase_order_lines.filtered(lambda pol: pol.order_id == order)
            value = 0
            for order_line in order_lines:
                confirmed_invoice_lines = order_line.invoice_lines.filtered(
                    lambda aml: aml.move_id.state == 'posted'
                )
                invoiced_value = sum(confirmed_invoice_lines.mapped('amount_currency'), 0)
                value += order_line.price_subtotal - invoiced_value
            not_invoiced_received_lines.append({
                'id': order.id,
                'display_name': order.display_name,
                'value': -value,
            })
            total -= value
        return {
            'lines': not_invoiced_received_lines,
            'value': total,
        }
