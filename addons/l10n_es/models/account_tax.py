# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.tools import frozendict


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_es_exempt_reason = fields.Selection(
        selection=[
            ('E1', 'Art. 20'),
            ('E2', 'Art. 21'),
            ('E3', 'Art. 22'),
            ('E4', 'Art. 23 y 24'),
            ('E5', 'Art. 25'),
            ('E6', 'Otros'),
        ],
        string="Exempt Reason (Spain)",
    )
    l10n_es_type = fields.Selection(
        selection=[
            ('exento', 'Exento'),
            ('sujeto', 'Sujeto'),
            ('sujeto_agricultura', 'Sujeto Agricultura'),
            ('sujeto_isp', 'Sujeto ISP'),
            ('no_sujeto', 'No Sujeto'),
            ('no_sujeto_loc', 'No Sujeto por reglas de Localization'),
            ('no_deducible', 'No Deducible'),
            ('retencion', 'Retencion'),
            ('recargo', 'Recargo de Equivalencia'),
            ('dua', 'DUA'),
            ('ignore', 'Ignore even the base amount'),
        ],
        string="Tax Type (Spain)", default='sujeto'
    )
    l10n_es_bien_inversion = fields.Boolean('Bien de Inversion', default=False)

    # -------------------------------------------------------------------------
    # EDI HELPERS
    # -------------------------------------------------------------------------

    def _l10n_es_get_regime_code(self):
        # Regime codes (ClaveRegimenEspecialOTrascendencia)
        # NOTE there's 11 more codes to implement, also there can be up to 3 in total
        # See https://www.gipuzkoa.eus/documents/2456431/13761128/Anexo+I.pdf/2ab0116c-25b4-f16a-440e-c299952d683d
        oss_tag = self.env.ref('l10n_eu_oss.tag_oss', raise_if_not_found=False)

        # If there's an OSS tax, it is considered an OSS operation
        if oss_tag and oss_tag in self.invoice_repartition_line_ids.tag_ids:
            return '17'

        if self.filtered(lambda t: t.l10n_es_exempt_reason == 'E2'):
            return '02'

        return '01'

    @api.model
    def _l10n_es_get_sujeto_tax_types(self):
        return ['sujeto', 'sujeto_isp', 'sujeto_agricultura']

    @api.model
    def _l10n_es_get_main_tax_types(self):
        return {'exento', 'sujeto', 'sujeto_agricultura', 'sujeto_isp', 'no_sujeto', 'no_sujeto_loc', 'no_deducible'}

    @api.model
    def _l10n_es_get_tax_details_functions(self, company):
        def base_line_filter(base_line):
            return any(t != 'ignore' for t in base_line['tax_ids'].flatten_taxes_hierarchy().mapped('l10n_es_type'))

        def total_grouping_function(base_line, tax_data):
            return (
                tax_data
                and not tax_data['is_reverse_charge']
                and tax_data['tax'].amount != -100.0
                and tax_data['tax'].l10n_es_type not in ('ignore', 'retencion')
            )

        def tax_details_grouping_function(base_line, tax_data):
            if not total_grouping_function(base_line, tax_data):
                return None

            tax = tax_data['tax']
            l10n_es_exempt_reason = tax.l10n_es_exempt_reason if tax.l10n_es_type == 'exento' else False

            recargo_taxes = self.env['account.tax']
            if tax.l10n_es_type in self.env['account.tax']._l10n_es_get_sujeto_tax_types():
                recargo_taxes = base_line['tax_ids'].filtered(lambda t: t.l10n_es_type == 'recargo')

            return {
                'amount': tax.amount,
                'recargo_taxes': recargo_taxes,
                'l10n_es_bien_inversion': tax.l10n_es_bien_inversion,
                'l10n_es_exempt_reason': l10n_es_exempt_reason,
                'l10n_es_type': tax.l10n_es_type,
            }

        return {
            'base_line_filter': base_line_filter,
            'total_grouping_function': total_grouping_function,
            'tax_details_grouping_function': tax_details_grouping_function,
        }

    @api.model
    def _l10n_es_get_tax_details_for_report(self, base_lines, company, tax_lines=None):
        tax_details_functions = self._l10n_es_get_tax_details_functions(company)
        base_line_filter = tax_details_functions['base_line_filter']
        total_grouping_function = tax_details_functions['total_grouping_function']
        tax_details_grouping_function = tax_details_functions['tax_details_grouping_function']

        base_lines = [base_line for base_line in base_lines if base_line_filter(base_line)]

        self._add_tax_details_in_base_lines(base_lines, company)
        self._round_base_lines_tax_details(base_lines, company, tax_lines=tax_lines)

        base_lines_aggregated_values_for_totals = self._aggregate_base_lines_tax_details(base_lines, total_grouping_function)
        totals = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values_for_totals)[True]

        base_lines_aggregated_values_for_tax_details = self._aggregate_base_lines_tax_details(base_lines, tax_details_grouping_function)
        tax_details = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values_for_tax_details)

        return {
            'base_amount': totals['base_amount'],
            'tax_amount': totals['tax_amount'],
            'tax_details': {key: tax_detail for key, tax_detail in tax_details.items() if key},
            'tax_details_per_record': {
                frozendict(base_line): {key: tax_detail for key, tax_detail in tax_details.items() if key}
                for base_line, tax_details in base_lines_aggregated_values_for_tax_details
            },
        }
