from odoo import api, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _l10n_es_regime_code_labels(self):
        labels = super()._l10n_es_regime_code_labels()
        # From the AEAT spec ("DsRegistroVeriFactu.xlsx", lists L8A [IVA] / L8B [IGIC]). None of
        # these are used by SII/TBAI.
        _ = self.env._
        labels.update({
            '11_vf': _("11 - Business premises lease"),
            '18_iva': _("18 - Equivalence surcharge"),
            '19_iva': _("19 - REAGYP"),
            '20': _("20 - Simplified regime"),
        })
        return labels

    @api.depends('company_id.l10n_es_edi_verifactu_required')
    def _compute_l10n_es_available_regime_codes(self):
        super()._compute_l10n_es_available_regime_codes()

    @api.depends('company_id.l10n_es_edi_verifactu_required')
    def _compute_l10n_es_regime_code(self):
        super()._compute_l10n_es_regime_code()

    @api.model
    def _l10n_es_edi_verifactu_get_applicability_name_map(self):
        """Return dict: l10n_es_applicability -> human readable string
        """
        # When no applicability is selected it is '05' / "Other"
        applicability_string = dict(self.env['account.tax']._fields['l10n_es_applicability'].get_description(self.env)['selection'])
        return {
            '01': applicability_string['01'],
            '02': applicability_string['02'],
            '03': applicability_string['03'],
            '05': self.env._("Other"),
        }

    def _l10n_es_get_applicability(self):
        # EXTENDS 'l10n_es'
        """
        Return the Veri*Factu Tax Applicability for the "first" main tax in self.
        Fallback to '05' ("Other") if there is no main tax or the applicability is not set on the "first" one.
        Note: Currently we only support one Veri*Factu Tax Applicability for the whole invoice.
        """
        return super()._l10n_es_get_applicability() or '05'

    @api.model
    def _l10n_es_edi_verifactu_get_tax_details_functions(self, company):
        # Fallback for a tax with no regime code of its own: the company's special VAT regime
        # selector, or '01' if that's empty too.
        fallback_regime_code = company._l10n_es_special_vat_regime_codes().get(
            company.l10n_es_special_vat_regime, '01')

        def base_line_filter(base_line):
            return any(t != 'ignore' for t in base_line['tax_ids'].flatten_taxes_hierarchy().mapped('l10n_es_type'))

        def total_grouping_function(base_line, tax_data):
            return (tax_data
                    and not tax_data['is_reverse_charge']
                    and tax_data['tax'].amount != -100.0
                    and tax_data['tax'].l10n_es_type not in ('ignore', 'retencion'))

        def tax_details_grouping_function(base_line, tax_data):
            if not total_grouping_function(base_line, tax_data):
                return None

            tax = tax_data['tax']
            l10n_es_exempt_reason = tax.l10n_es_exempt_reason if tax.l10n_es_type == 'exento' else False

            # Sujeto taxes with different recargo taxes are kept separate for the output
            # Note: In `_check_record_values` we assert that there is only a single (main tax, recargo tax) pair
            recargo_taxes = self.env['account.tax']
            if tax.l10n_es_type in self.env['account.tax']._l10n_es_get_sujeto_tax_types():
                recargo_taxes = base_line['tax_ids'].filtered(lambda t: t.l10n_es_type == 'recargo')

            regime_source_code = tax.l10n_es_regime_code or fallback_regime_code

            grouping_key = {
                'amount': tax.amount,
                'recargo_taxes': recargo_taxes,
                'l10n_es_bien_inversion': tax.l10n_es_bien_inversion,
                'l10n_es_exempt_reason': l10n_es_exempt_reason,
                'l10n_es_type': tax.l10n_es_type,
                'l10n_es_applicability': tax._l10n_es_get_applicability(),
                'clave_regimen': self._l10n_es_regime_code_aeat(regime_source_code),
            }
            return grouping_key

        return {
            'base_line_filter': base_line_filter,
            'total_grouping_function': total_grouping_function,
            'tax_details_grouping_function': tax_details_grouping_function,
        }
