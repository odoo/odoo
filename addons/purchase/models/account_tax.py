from odoo import api, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    def _hook_compute_is_used(self, taxes_to_compute):
        # OVERRIDE in order to fetch taxes used in purchase

        used_taxes = super()._hook_compute_is_used(taxes_to_compute)
        taxes_to_compute -= used_taxes

        if taxes_to_compute:
            self.env['purchase.order.line'].flush_model(['taxes_id'])
            self.env.cr.execute("""
                SELECT id
                FROM account_tax
                WHERE EXISTS(
                    SELECT 1
                    FROM account_tax_purchase_order_line_rel AS pur
                    WHERE account_tax_id IN %s
                    AND account_tax.id = pur.account_tax_id
                )
            """, [tuple(taxes_to_compute)])

            used_taxes.update([tax[0] for tax in self.env.cr.fetchall()])

        return used_taxes

    @api.model
    def _prepare_document_line_from_po_line(self, po_line):
        return self._prepare_document_line(
            price_unit=po_line.price_unit,
            quantity=po_line.product_qty,
            discount=po_line.discount,
            product=po_line.product_id,
            taxes=po_line.taxes_id,
        )

    @api.model
    def _create_document_from_po(self, po, with_lines=True):
        company = po.company_id or self.env.company
        currency = po.currency_id or company.currency_id
        document_values = self._create_document_for_taxes_computation(currency=currency, company=company)
        if not with_lines:
            return document_values

        for po_line in po.order_line.filtered(lambda x: not x.display_type):
            document_values['lines'].append(self._prepare_document_line_from_po_line(po_line))

        self._add_line_tax_amounts_to_document(document_values)
        return document_values
