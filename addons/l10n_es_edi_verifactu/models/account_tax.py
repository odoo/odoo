from odoo import api, fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_es_applicability = fields.Selection(
        selection=[
            ('iva', 'VAT'),
            ('igic', 'IGIC'),
            ('ipsi', 'IPSI'),
            ('other', 'Other'),
        ],
        string="Applicability (Spain)",
        default='iva',
    )

    @api.model
    def _l10n_es_edi_verifactu_get_tax_types_map(self):
        """Return dict: l10n_es_applicability -> verifactu tax type
        """
        return {
            'iva': '01',
            'ipsi': '02',
            'igic': '03',
            'other': '05',
        }

    @api.model
    def _l10n_es_edi_verifactu_get_tax_types_name_map(self):
        """Return dict: verifactu tax type -> human readable string
        """
        # We use the applicability selection strings since every applicability is mapped to a single verifactu tax type
        applicability_string = dict(self.env['account.tax']._fields['l10n_es_applicability'].get_description(self.env)['selection'])
        return {
            '01': applicability_string['iva'],
            '02': applicability_string['ipsi'],
            '03': applicability_string['igic'],
            '05': applicability_string['other'],
        }

    def _l10n_es_edi_verifactu_filter_main_taxes(self):
        return self.filtered(
            lambda tax: tax.l10n_es_type not in ('retencion', 'recargo', 'dua', 'ignore')
                        and tax.l10n_es_applicability
        )

    @api.model
    def _l10n_es_edi_verifactu_get_tax_details_functions(self, company):
        def full_filter_invl_to_apply(line):
            return any(t != 'ignore' for t in line.tax_ids.flatten_taxes_hierarchy().mapped('l10n_es_type'))

        verifactu_tax_type_map = self._l10n_es_edi_verifactu_get_tax_types_map()

        def grouping_key_generator(base_line, tax_values):
            tax = tax_values['tax_repartition_line'].tax_id

            l10n_es_exempt_reason = tax.l10n_es_exempt_reason if tax.l10n_es_type == 'exento' else False

            # Sujeto taxes with different recargo taxes are kept separate for the output
            # Note: In `_check_record_values` we assert that there is only a single (main tax, recargo tax) pair
            recargo_taxes = self.env['account.tax']
            if tax.l10n_es_type in self.env['account.tax']._l10n_es_get_sujeto_tax_types():
                recargo_taxes = base_line['taxes'].filtered(lambda t: t.l10n_es_type == 'recargo')

            grouping_key = {
                'amount': tax.amount,
                'recargo_taxes': recargo_taxes,
                'l10n_es_bien_inversion': tax.l10n_es_bien_inversion,
                'l10n_es_exempt_reason': l10n_es_exempt_reason,
                'l10n_es_type': tax.l10n_es_type,
                'verifactu_tax_type': verifactu_tax_type_map.get(tax.l10n_es_applicability),
                'is_main_tax': bool(tax._l10n_es_edi_verifactu_filter_main_taxes()),
            }
            return grouping_key

        def filter_to_apply(base_line, tax_values):
            return (tax_values['tax_repartition_line'].factor_percent > 0.0
                    and tax_values['tax_repartition_line'].tax_id.amount != -100.0
                    and tax_values['tax_repartition_line'].tax_id.l10n_es_type not in ('ignore', 'retencion'))

        return {
            'full_filter_invl_to_apply': full_filter_invl_to_apply,
            'grouping_key_generator': grouping_key_generator,
            'filter_to_apply': filter_to_apply,
        }
