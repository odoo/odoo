from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_cz_reverse_charge = fields.Boolean(
        string="Reverse Charge Tax",
        help="Indicates if the tax is to be used with reverse charge transactions",
    )

    def _prepare_base_line_for_taxes_computation(self, record, **kwargs):
        # EXTENDS 'account'
        results = super()._prepare_base_line_for_taxes_computation(record, **kwargs)
        if (
                isinstance(record, models.Model)
                and record._name == 'account.move.line'
                and record.l10n_cz_supplies_code
        ):
            results['l10n_cz_supplies_code'] = record.l10n_cz_supplies_code
        return results

    def _prepare_tax_line_for_taxes_computation(self, record, **kwargs):
        # EXTENDS 'account'
        results = super()._prepare_tax_line_for_taxes_computation(record, **kwargs)
        if (
                isinstance(record, models.Model)
                and record._name == 'account.move.line'
                and record.l10n_cz_supplies_code
        ):
            results['l10n_cz_supplies_code'] = record.l10n_cz_supplies_code
        return results

    def _prepare_base_line_tax_repartition_grouping_key(self, base_line, base_line_grouping_key, tax_data, tax_rep_data):
        # EXTENDS 'account'
        results = super()._prepare_base_line_tax_repartition_grouping_key(base_line, base_line_grouping_key, tax_data, tax_rep_data)
        if 'l10n_cz_supplies_code' in base_line:
            results['l10n_cz_supplies_code'] = base_line['l10n_cz_supplies_code']
        return results

    def _prepare_tax_line_repartition_grouping_key(self, tax_line):
        # EXTENDS 'account'
        results = super()._prepare_tax_line_repartition_grouping_key(tax_line)
        if 'l10n_cz_supplies_code' in tax_line:
            results['l10n_cz_supplies_code'] = tax_line['l10n_cz_supplies_code']
        return results
