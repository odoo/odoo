from odoo import _, api, fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_es_applicability = fields.Selection(
        selection=[
            ('01', "VAT"),
            ('02', "IPSI"),
            ('03', "IGIC"),
        ],
        string="Applicability (Spain)",
    )

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
            '05': _("Other"),
        }

    def _l10n_es_edi_verifactu_get_applicability(self):
        """
        Return the Veri*Factu Tax Applicability for the "first" main tax in self.
        Fallback to '05' ("Other") if there is no main tax or the applicability is not set on the "first" one.
        Note: Currently we only support one Veri*Factu Tax Applicability for the whole invoice.
        """
        main_tax_types = self._l10n_es_get_main_tax_types()
        main_taxes = self.filtered(lambda tax: tax.l10n_es_type in main_tax_types)
        if not main_taxes:
            return '05'
        return main_taxes[0].l10n_es_applicability or '05'

    def _l10n_es_edi_verifactu_get_suggested_clave_regimen(self, special_regime, forced_tax_applicability=None):
        """
        Return a suggested Clave Regimen for the taxes in `self` to be used for the Veri*Factu document.
        Note: Currently we only support one Clave Regimen for a whole Veri*Factu document.
        """
        taxes = self
        if forced_tax_applicability:
            # Remove main taxes with a different Veri*Factu tax applicability
            main_tax_types = self._l10n_es_get_main_tax_types()
            taxes = taxes.filtered(
                lambda tax: (tax.l10n_es_type not in main_tax_types
                             or tax._l10n_es_edi_verifactu_get_applicability() == forced_tax_applicability)
            )

        tax_applicability = forced_tax_applicability or taxes._l10n_es_edi_verifactu_get_applicability()
        if not tax_applicability:
            return False

        VAT = tax_applicability == '01'
        IGIC = tax_applicability == '03'
        if not (VAT or IGIC):
            return False

        recargo_taxes = taxes.filtered(lambda tax: tax.l10n_es_type == 'recargo')
        oss_tag = self.env.ref('l10n_eu_oss.tag_oss', raise_if_not_found=False)

        regimen_key = None
        if VAT and oss_tag and oss_tag.id in taxes.repartition_line_ids.tag_ids.ids:
            # oss
            regimen_key = '17_iva'
        elif taxes.filtered(lambda tax: tax.l10n_es_type == 'exento' and tax.l10n_es_exempt_reason == 'E2'):
            # export
            regimen_key = '02'
        elif VAT and special_regime == 'simplified':
            # simplified
            regimen_key = '20_iva'
        elif VAT and special_regime == 'reagyp':
            # REAGYP
            regimen_key = '19_iva'
        elif VAT and (recargo_taxes or special_regime == 'recargo'):
            # recargo
            regimen_key = '18_iva'
        else:
            regimen_key = '01'

        return regimen_key

    @api.model
    def _l10n_es_edi_verifactu_get_tax_details_functions(self, company):
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

            grouping_key = {
                'amount': tax.amount,
                'recargo_taxes': recargo_taxes,
                'l10n_es_bien_inversion': tax.l10n_es_bien_inversion,
                'l10n_es_exempt_reason': l10n_es_exempt_reason,
                'l10n_es_type': tax.l10n_es_type,
                'l10n_es_applicability': tax._l10n_es_edi_verifactu_get_applicability(),
            }
            return grouping_key

        return {
            'base_line_filter': base_line_filter,
            'total_grouping_function': total_grouping_function,
            'tax_details_grouping_function': tax_details_grouping_function,
        }
