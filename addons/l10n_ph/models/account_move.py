# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_name_invoice_report(self):
        self.ensure_one()
        if (
            self.move_type == 'out_invoice'
            and self.company_id.account_fiscal_country_id.code == 'PH'
            and all(self._l10n_ph_cas_get_tax_groups().values())
        ):
            return 'l10n_ph.report_invoice_document'
        return super()._get_name_invoice_report()

    def _l10n_ph_cas_get_tax_groups(self):
        """ Return the ids of the tax groups the BIR CAS invoice needs."""
        self.ensure_one()
        chart_template = self.env['account.chart.template'].with_company(self.company_id)
        return {
            key: (chart_template.ref(xmlid, raise_if_not_found=False) or self.env['account.tax.group']).id
            for key, xmlid in {
                'vatable': 'l10n_ph_tax_group_vatable',
                'zero_rated': 'l10n_ph_tax_group_zero_rated',
                'vat_exempt': 'l10n_ph_tax_group_vat_exempt',
                'percentage_tax': 'l10n_ph_tax_group_percentage_tax',
            }.items()
        }

    def _l10n_ph_cas_get_invoice_report_values(self):
        """ Compute the BIR CAS invoice category and amount breakdowns used by the l10n_ph CAS invoice report. """
        self.ensure_one()
        group_ids = self._l10n_ph_cas_get_tax_groups()
        vals = {
            'vatable_base': 0.0,
            'vatable_tax': 0.0,
            'zero_rated_base': 0.0,
            'vat_exempt_base': 0.0,
            'percentage_tax_base': 0.0,
            'withholding_tax': self.withholding_total_amount_currency,
        }
        present_groups = set()

        for subtotal in (self.tax_totals or {}).get('subtotals', []):
            for tax_group in subtotal.get('tax_groups', []):
                base_amount = tax_group['display_base_amount_currency']
                if base_amount is False:
                    base_amount = tax_group['base_amount_currency']
                if tax_group['id'] == group_ids['vatable']:
                    present_groups.add('vatable')
                    vals['vatable_base'] += base_amount
                    vals['vatable_tax'] += tax_group['tax_amount_currency']
                elif tax_group['id'] == group_ids['zero_rated']:
                    present_groups.add('zero_rated')
                    vals['zero_rated_base'] += base_amount
                elif tax_group['id'] == group_ids['vat_exempt']:
                    present_groups.add('vat_exempt')
                    vals['vat_exempt_base'] += base_amount
                elif tax_group['id'] == group_ids['percentage_tax']:
                    vals['percentage_tax_base'] += base_amount

        if not self.company_id._l10n_ph_is_vat_registered():
            category = 'non_vat'
        elif present_groups and present_groups <= {'vat_exempt'}:
            category = 'vat_exempt'
        elif present_groups and present_groups <= {'zero_rated'}:
            category = 'zero_rated'
        else:
            category = 'mixed'
        vals['category'] = category
        vals['has_vat'] = 'vatable' in present_groups

        return vals
