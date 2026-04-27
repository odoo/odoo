# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

L10N_EC_TAXSUPPORTS = [
    ('01', '01 Tax credit for VAT declaration (services and goods other than inventories and fixed assets)'),
    ('02', '02 Cost or Expense for IR declaration (services and goods other than inventories and fixed assets)'),
    ('03', '03 Fixed Asset - Tax Credit for VAT return'),
    ('04', '04 Fixed Asset - Cost or Expense for IR declaration'),
    ('05', '05 Settlement of travel, lodging and food expenses IR expenses (on behalf of employees and not of the company)'),
    ('06', '06 Inventory - Tax Credit for VAT return'),
    ('07', '07 Inventory - Cost or Expense for IR declaration'),
    ('08', '08 Amount paid to request Expense Reimbursement (intermediary)'),
    ('09', '09 Claims Reimbursement'),
    ('10', '10 Distribution of Dividends, Benefits or Profits'),
    ('15', '15 Payments made for own and third-party consumption of digital services'),
    ('00', '00 Special cases whose support does not apply to the above options')
]


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_ec_code_taxsupport = fields.Selection(
        L10N_EC_TAXSUPPORTS,
        string='Tax Support',
        help='Indicates if the purchase invoice supports tax credit or cost or expenses, conforming table 5 of ATS'
    )

    def _prepare_base_line_for_taxes_computation(self, record, **kwargs):
        # EXTENDS 'account'
        results = super()._prepare_base_line_for_taxes_computation(record, **kwargs)
        if (
            isinstance(record, models.Model)
            and record._name == 'account.move.line'
            and record.l10n_ec_withhold_invoice_id
        ):
            results['l10n_ec_withhold_invoice_id'] = record.l10n_ec_withhold_invoice_id
            results['l10n_ec_code_taxsupport'] = record.l10n_ec_code_taxsupport
        return results

    def _prepare_tax_line_for_taxes_computation(self, record, **kwargs):
        # EXTENDS 'account'
        results = super()._prepare_tax_line_for_taxes_computation(record, **kwargs)
        if (
            isinstance(record, models.Model)
            and record._name == 'account.move.line'
            and record.l10n_ec_withhold_invoice_id
        ):
            results['l10n_ec_withhold_invoice_id'] = record.l10n_ec_withhold_invoice_id
            results['l10n_ec_code_taxsupport'] = record.l10n_ec_code_taxsupport
        return results

    def _prepare_base_line_tax_repartition_grouping_key(self, base_line, base_line_grouping_key, tax_data, tax_rep_data):
        # EXTENDS 'account'
        results = super()._prepare_base_line_tax_repartition_grouping_key(base_line, base_line_grouping_key, tax_data, tax_rep_data)
        if 'l10n_ec_withhold_invoice_id' in base_line:
            results['l10n_ec_withhold_invoice_id'] = base_line['l10n_ec_withhold_invoice_id'].id
            results['l10n_ec_code_taxsupport'] = base_line['l10n_ec_code_taxsupport']
        return results

    def _prepare_tax_line_repartition_grouping_key(self, tax_line):
        # EXTENDS 'account'
        results = super()._prepare_tax_line_repartition_grouping_key(tax_line)
        if 'l10n_ec_withhold_invoice_id' in tax_line:
            results['l10n_ec_withhold_invoice_id'] = tax_line['l10n_ec_withhold_invoice_id'].id
            results['l10n_ec_code_taxsupport'] = tax_line['l10n_ec_code_taxsupport']
        return results

    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None, is_refund=False, handle_price_include=True, include_caba_tags=False, rounding_method=None):
        """
        Check that the tax is of the withholding type. Send the 'round' context as True, in this way we force the withholdings
        to be computed with 'round per line', not by 'round globally'.
        """
        withholding_tax_groups = [
            'withhold_vat_sale',
            'withhold_vat_purchase',
            'withhold_income_sale',
            'withhold_income_purchase'
        ]
        is_withhold_tax = self.filtered(lambda x: x.tax_group_id.l10n_ec_type in withholding_tax_groups)
        return super().compute_all(
            price_unit,
            currency=currency,
            quantity=quantity,
            product=product,
            partner=partner,
            is_refund=is_refund,
            handle_price_include=handle_price_include,
            include_caba_tags=include_caba_tags,
            rounding_method='round_per_line' if is_withhold_tax else rounding_method,
        )
