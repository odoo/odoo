# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    def _l10n_ar_prices_and_taxes(self):
        self.ensure_one()
        invoice = self.move_id
        included_taxes = \
            invoice.l10n_latam_document_type_id and invoice.l10n_latam_document_type_id._filter_taxes_included(
                self.tax_ids)
        if not included_taxes:
            price_unit = self.tax_ids.with_context(round=False).compute_all(
                self.price_unit, invoice.currency_id, 1.0, self.product_id, invoice.partner_id)
            price_unit = price_unit['total_excluded']
            not_included_taxes = self.tax_ids
            price_subtotal = self.price_subtotal
        else:
            not_included_taxes = self.tax_ids - included_taxes
            price_unit = included_taxes.compute_all(
                self.price_unit, invoice.currency_id, 1.0, self.product_id, invoice.partner_id)['total_included']
            price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
            price_subtotal = included_taxes.compute_all(
                price, invoice.currency_id, self.quantity, self.product_id, invoice.partner_id)['total_included']
        price_net = price_unit * (1 - (self.discount or 0.0) / 100.0)

        return {
            'taxes': not_included_taxes,
            'price_unit': price_unit,
            'price_subtotal': price_subtotal,
            'price_net': price_net
        }
