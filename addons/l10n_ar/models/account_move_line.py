# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _l10n_ar_prices_and_taxes(self):
        self.ensure_one()
        invoice = self.move_id
        include_vat = invoice._l10n_ar_include_vat()

        AccountTax = self.env['account.tax']
        base_line = invoice._prepare_product_base_line_for_taxes_computation(self)
        if include_vat:
            base_line['tax_ids'] = self.tax_ids.filtered('tax_group_id.l10n_ar_vat_afip_code')
        AccountTax._add_tax_details_in_base_line(base_line, self.company_id, rounding_method='round_globally')

        tax_details = base_line['tax_details']
        discount = base_line['discount']
        price_unit = base_line['price_unit']
        quantity = base_line['quantity']
        if include_vat:
            raw_total = tax_details['raw_total_included_currency']
        else:
            raw_total = tax_details['raw_total_excluded_currency']

        if discount == 100.0:
            price_subtotal = price_unit * quantity
        else:
            price_subtotal = raw_total / (1 - discount / 100.0)

        if quantity:
            price_unit = raw_total / quantity
            price_net = price_subtotal / quantity
        else:
            price_unit = 0.0
            price_net = 0.0

        return {
            'price_unit': price_unit,
            'price_subtotal': price_subtotal,
            'price_net': price_net,
        }
