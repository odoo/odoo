# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.tools import float_repr


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_ubl_values(self):
        self.ensure_one()

        def format_monetary(amount, currency):
            # Format the monetary values to avoid trailing decimals (e.g. 90.85000000000001).
            return float_repr(amount, currency.decimal_places)

        invoice_line_values = []

        # Tax lines.
        aggregated_taxes_details = {line.tax_line_id.id: {
            'line': line,
            'tax_amount': -line.amount_currency,
            'tax_base_amount': 0.0,
        } for line in self.line_ids.filtered('tax_line_id')}

        # Invoice lines.
        for line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
            price_unit_with_discount = line.price_unit * (1 - (line.discount / 100.0))
            taxes_res = line.tax_ids.compute_all(
                price_unit_with_discount,
                currency=line.currency_id,
                quantity=line.quantity,
                product=line.product_id,
                partner=self.partner_id,
                is_refund=line.move_id.move_type in ('in_refund', 'out_refund'),
            )

            line_template_values = {
                'line': line,
                'taxes': [],
            }

            for tax_res in taxes_res['taxes']:
                tax = self.env['account.tax'].browse(tax_res['id'])
                line_template_values['taxes'].append({
                    'tax': tax,
                    'tax_amount': tax_res['amount'],
                    'tax_base_amount': tax_res['base'],
                })
                if tax.id in aggregated_taxes_details:
                    aggregated_taxes_details[tax.id]['tax_base_amount'] += tax_res['base']

            invoice_line_values.append(line_template_values)

        return {
            'invoice': self,
            'ubl_version': 2.1,
            'type_code': 380 if self.move_type == 'out_invoice' else 381,
            'payment_means_code': 42 if self.journal_id.bank_account_id else 31,
            'format_monetary': format_monetary,
            'tax_details': list(aggregated_taxes_details.values()),
            'invoice_line_values': invoice_line_values
        }
