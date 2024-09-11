# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.fields import Command


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def _create_invoices(self, sale_orders):
        """Extend to create a dedicated down payment line for the declaration of intent amount."""
        invoice = super()._create_invoices(sale_orders)

        if self.advance_payment_method == 'delivered':
            return invoice

        order = self.sale_order_ids  # super calls ensure_one
        doi_tax = order.l10n_it_edi_doi_id.company_id.l10n_it_edi_doi_tax_id
        if not doi_tax:
            # Includes the case where there is no order.l10n_it_edi_doi_id
            return invoice

        doi_total = 0
        for line in order.order_line:
            if line.tax_id.ids != doi_tax.ids:
                continue
            price_reduce = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            doi_total += price_reduce * line.product_uom_qty

        # The tax on the down payment product was possibly mapped by the doi fiscal position
        # Here we do a custom mapping that does not map taxes that will be mapped to the special doi tax
        doi_fiscal_position = order.l10n_it_edi_doi_id.company_id.l10n_it_edi_doi_fiscal_position_id
        advance_product_taxes = self.product_id.taxes_id.filtered(lambda tax: tax.company_id == order.company_id)
        if advance_product_taxes and doi_fiscal_position and order.fiscal_position_id == doi_fiscal_position:
            custom_mapped_taxes = self.env['account.tax']
            for tax in advance_product_taxes:
                mapped_tax = doi_fiscal_position.map_tax(tax)
                custom_mapped_taxes |= tax if mapped_tax == doi_tax else mapped_tax
            advance_product_taxes = custom_mapped_taxes

        for invoice_line in invoice.invoice_line_ids:
            if not invoice_line.is_downpayment:
                continue
            downpayment_line = invoice_line.sale_line_ids.filtered(lambda line: line.is_downpayment)
            if len(downpayment_line) != 1:
                continue

            if advance_product_taxes:
                downpayment_line.tax_id = advance_product_taxes
                invoice_line.tax_ids = advance_product_taxes

            if order.currency_id.is_zero(doi_total):
                # The order has no lines contributing to the declaration of intent
                continue

            # Split the down payment amount into 2: doi amount and other amount
            down_total = downpayment_line.price_unit
            if all(advance_product_taxes.mapped('price_include')):
                amount_total = order.amount_total
            else:
                amount_total = order.amount_untaxed
            doi_down = order.currency_id.round(doi_total / amount_total * down_total)
            other_down = down_total - doi_down

            if order.currency_id.is_zero(amount_total - doi_total):
                # The whole order amount is under doi_tax
                # We just have to add the tax information on the lines
                downpayment_line.tax_id = doi_tax
                invoice_line.tax_ids = doi_tax
                continue

            # The order amount is partially not under doi_tax
            # Split the down payment line into 2: one for the doi amount and one for the other amount
            downpayment_line.price_unit = other_down
            doi_so_line_values = {
                **self._prepare_so_line_values(order),
                'price_unit': doi_down,
                'tax_id': [Command.set(doi_tax.ids)],
            }
            doi_down_payment_so_line = self.env['sale.order.line'].create(doi_so_line_values)

            # Split the invoice line into 2: one for the doi amount and one for the other amount
            invoice.invoice_line_ids = [
                Command.create(doi_down_payment_so_line._prepare_invoice_line(
                    name=self._get_down_payment_description(order),
                    quantity=1.0,
                )),
                Command.update(invoice_line.id, {
                    'price_unit': other_down,
                }),
            ]

        return invoice
