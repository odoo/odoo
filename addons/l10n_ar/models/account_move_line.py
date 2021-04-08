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
            l10n_latam_price_unit = price_unit['total_excluded']
            not_included_taxes = self.tax_ids
            l10n_latam_price_subtotal = self.price_subtotal
        else:
            not_included_taxes = self.tax_ids - included_taxes
            l10n_latam_price_unit = included_taxes.compute_all(
                self.price_unit, invoice.currency_id, 1.0, self.product_id, invoice.partner_id)['total_included']
            price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
            l10n_latam_price_subtotal = included_taxes.compute_all(
                price, invoice.currency_id, self.quantity, self.product_id, invoice.partner_id)['total_included']
        l10n_latam_price_net = l10n_latam_price_unit * (1 - (self.discount or 0.0) / 100.0)

        return {
            'l10n_latam_tax_ids': not_included_taxes,
            'l10n_latam_price_unit': l10n_latam_price_unit,
            'l10n_latam_price_subtotal': l10n_latam_price_subtotal,
            'l10n_latam_price_net': l10n_latam_price_net
        }
