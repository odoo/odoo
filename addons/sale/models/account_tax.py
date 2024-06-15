from odoo import api, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _prepare_document_line_from_so_line(self, so_line):
        return self._prepare_document_line(
            price_unit=so_line.price_unit,
            quantity=so_line.product_uom_qty,
            discount=so_line.discount,
            product=so_line.product_id,
            taxes=so_line.tax_id,
        )

    @api.model
    def _create_document_from_so(self, so, with_lines=True):
        company = so.company_id or self.env.company
        currency = so.currency_id or company.currency_id
        document_values = self._create_document_for_taxes_computation(currency=currency, company=company)
        if not with_lines:
            return document_values

        for so_line in so.order_line.filtered(lambda x: not x.display_type):
            document_values['lines'].append(self._prepare_document_line_from_so_line(so_line))

        self._add_line_tax_amounts_to_document(document_values)
        return document_values
