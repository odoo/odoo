# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.fields import Command


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def _create_invoices(self, sale_orders):
        """Extend to create a dedicated downpayment line for the declaration of intent amount."""
        invoice = super()._create_invoices(sale_orders)

        if self.advance_payment_method == 'delivered':
            return invoice

        order = self.sale_order_ids  # super calls ensure_one
        doi_tax = order.l10n_it_edi_doi_id.company_id.l10n_it_edi_doi_tax_id
        if not doi_tax:
            # includes the case there is no order.l10n_it_edi_doi_id
            return invoice

        # Check that the order actually has lines contributing to the declaration
        order_doi_lines = order.order_line.filtered(lambda line: line.tax_id.ids == doi_tax.ids)
        if not order_doi_lines:
            return invoice

        doi_total = 0
        for line in order_doi_lines:
            price_reduce = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            doi_total += price_reduce * line.product_uom_qty

        for invoice_line in invoice.invoice_line_ids:
            if not invoice_line.is_downpayment:
                continue
            downpayment_line = invoice_line.sale_line_ids.filtered(lambda line: line.is_downpayment)
            if len(downpayment_line) != 1:
                continue

            # split the downpayment amount into 2: doi amount and other amount
            down_total = downpayment_line.price_unit
            amount_total = sum(order.order_line.mapped("price_total"))
            doi_down = invoice.currency_id.round(doi_total / amount_total * down_total)
            other_down = down_total - doi_down

            # split the downpayment line into 2: one for the doi amount and one for the other amount
            downpayment_line.price_unit = other_down
            doi_so_line_values = {
                **self._prepare_so_line_values(order),
                'price_unit': doi_down,
                'tax_id': [Command.set(doi_tax.ids)],
            }
            doi_so_line_values['price_unit'] = doi_down
            doi_down_payment_so_line = self.env['sale.order.line'].create(doi_so_line_values)

            # split the invoice line into 2: one for the doi amount and one for the other amount
            invoice.write({'invoice_line_ids': [
                Command.create(doi_down_payment_so_line._prepare_invoice_line(
                    name=self._get_down_payment_description(order),
                    quantity=1.0,
                )),
                Command.update(invoice_line.id, {
                    'price_unit': other_down,
                }),
            ]})

        return invoice
