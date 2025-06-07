# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.tools.float_utils import float_repr


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    def _l10n_cl_prices_and_taxes(self):
        """ this method is preserved here to allow compatibility with old templates,
        Nevertheless it will be deprecated in future versions, since it had been replaced by
        the method _l10n_cl_get_line_amounts, which is the same method used to calculate
        the values for the XML (DTE) file
        """
        self.ensure_one()
        invoice = self.move_id
        included_taxes = self.tax_ids.filtered(lambda x: x.l10n_cl_sii_code == 14) if self.move_id._l10n_cl_include_sii() else self.tax_ids
        if not included_taxes:
            price_unit = self.tax_ids.compute_all(
                self.price_unit,
                currency=invoice.currency_id,
                product=self.product_id,
                partner=invoice.partner_id,
                rounding_method='round_globally',
            )
            price_unit = price_unit['total_excluded']
            price_subtotal = self.price_subtotal
        else:
            price_unit = included_taxes.compute_all(
                self.price_unit, invoice.currency_id, 1.0, self.product_id, invoice.partner_id)['total_included']
            price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
            price_subtotal = included_taxes.compute_all(
                price, invoice.currency_id, self.quantity, self.product_id, invoice.partner_id)['total_included']
        price_net = price_unit * (1 - (self.discount or 0.0) / 100.0)
        return {
            'price_unit': price_unit,
            'price_subtotal': price_subtotal,
            'price_net': price_net
        }

    def _l10n_cl_get_line_amounts(self):
        """
        This method is used to calculate the amount and taxes of the lines required in the Chilean localization
        electronic documents.
        """
        # If in this fix we should check for boletas, we have the following cases, and how this affects the xml
        # for facturas and boletas:

        # 1. local invoice in same currency tax not included in price
        # 2. local invoice in same currency tax included in price (there is difference of -1 peso in amount_untaxed
        # and +1 peso in vat tax amount. The lines are OK
        # 3. local invoice in different currency tax not included in price
        # 4. local invoice in different currency tax include in price -> this is the most problematic case because
        # 5. foreign invoice in different currency (without tax)
        if self.display_type != 'product':
            return {
                'price_subtotal': 0,
            }
        line_sign = self.price_subtotal / abs(self.price_subtotal) if self.price_subtotal else 0
        domestic_invoice_other_currency = self.move_id.currency_id != self.move_id.company_id.currency_id and not \
            self.move_id.l10n_latam_document_type_id._is_doc_type_export()
        export = self.move_id.l10n_latam_document_type_id._is_doc_type_export()
        if not export:
            # This is to manage case 1, 2, 3 and 4
            # cases 1 and 2: domestic invoice in same currency and cases 3 and 4 with other currency
            main_currency = self.move_id.company_id.currency_id
            main_currency_field = 'balance'
            second_currency_field = 'price_subtotal'
            second_currency = self.currency_id
            main_currency_rate = 1
            second_currency_rate = 1 / self.move_id.invoice_currency_rate if self.move_id.invoice_currency_rate else 1
            inverse_rate = second_currency_rate if domestic_invoice_other_currency else main_currency_rate
        else:
            # This is to manage case 5 (export docs)
            main_currency = self.currency_id
            second_currency = self.move_id.company_id.currency_id
            main_currency_field = 'price_subtotal'
            second_currency_field = 'balance'
            inverse_rate = 1 / self.move_id.invoice_currency_rate if self.move_id.invoice_currency_rate else 1
        price_subtotal = abs(self[main_currency_field]) * line_sign
        if self.quantity and self.discount != 100.0:
            price_unit = (price_subtotal / abs(self.quantity)) / (1 - self.discount / 100)
            if self.move_id.l10n_latam_document_type_id._is_doc_type_electronic_ticket():
                price_item_document = (self.price_total / abs(self.quantity)) / (1 - self.discount / 100)
                price_line_document = self.price_total
            else:
                price_item_document = price_unit
                price_line_document = price_subtotal
        else:
            price_item_document = price_line_document = 0.0
            price_unit = self.price_unit

        if self.discount == 100:
            price_before_discount = price_unit * self.quantity
        else:
            price_before_discount = price_subtotal / (1 - self.discount / 100)
        discount_amount = price_before_discount * self.discount / 100
        values = {
            'decimal_places': main_currency.decimal_places,
            'price_item': round(price_unit, 6),
            'price_item_document': round(price_item_document, 2),
            'price_line_document': price_line_document,
            'total_discount': main_currency.round(discount_amount),
            'price_subtotal': main_currency.round(price_subtotal),
            'exempt': bool(not self.tax_ids),
            'main_currency': main_currency,
        }
        if domestic_invoice_other_currency or export:
            price_subtotal_second = abs(self[second_currency_field]) * line_sign
            if self.quantity and self.discount != 100.0:
                price_unit_second = (price_subtotal_second / abs(self.quantity)) / (1 - self.discount / 100)
            else:
                price_unit_second = self.price_unit
            discount_amount_second = price_unit_second * self.quantity - price_subtotal_second
            values['second_currency'] = {
                'price': second_currency.round(price_unit_second),
                'currency_name': self.move_id._format_length(second_currency.name, 3),
                'conversion_rate': round(inverse_rate, 4),
                'amount_discount': second_currency.round(discount_amount_second),
                'total_amount': second_currency.round(price_subtotal_second),
                'round_currency': second_currency.decimal_places,
            }

        values['line_description'] = '%s (%s: %s @ %s)' % (
            self.name,
            values['second_currency']['currency_name'],
            float_repr(values['second_currency']['price'], values['second_currency']['round_currency']),
            self.move_id._float_repr_float_round(values['second_currency']['conversion_rate'], values['second_currency']['round_currency']),
        ) if values.get('second_currency') and not self.l10n_latam_document_type_id._is_doc_type_export() else self.name
        return values
