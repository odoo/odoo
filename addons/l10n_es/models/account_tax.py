# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


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

    @api.model
    def _l10n_es_get_sujeto_tax_types(self):
        return ['sujeto', 'sujeto_isp', 'sujeto_agricultura']

    @api.model
    def _l10n_es_get_main_tax_types(self):
        return {'exento', 'sujeto', 'sujeto_agricultura', 'sujeto_isp', 'no_sujeto', 'no_sujeto_loc', 'no_deducible'}

    @api.model
    def _l10n_es_get_tax_details_for_report(self, base_lines, company):
        def filter_to_apply(base_line, tax_values):
            tax = tax_values['tax_repartition_line'].tax_id
            return (
                tax_values['tax_repartition_line'].factor_percent > 0.0
                and tax.amount != -100
                and tax.l10n_es_type not in ('ignore', 'retencion')
            )

        def grouping_key_generator(base_line, tax_values):
            tax = tax_values['tax_repartition_line'].tax_id
            l10n_es_exempt_reason = tax.l10n_es_exempt_reason if tax.l10n_es_type == 'exento' else False
            recargo_taxes = base_line['taxes'].filtered(lambda t: t.l10n_es_type == 'recargo')
            return {
                'amount': tax.amount,
                'recargo_taxes': recargo_taxes,
                'l10n_es_bien_inversion': tax.l10n_es_bien_inversion,
                'l10n_es_exempt_reason': l10n_es_exempt_reason,
                'l10n_es_type': tax.l10n_es_type,
            }

        to_process = []
        for base_line in base_lines:
            if base_line.get('discount') == 100:
                continue
            to_update_vals, tax_values_list = self._compute_taxes_for_single_line(base_line)
            to_process.append((base_line, to_update_vals, tax_values_list))
        return self._aggregate_taxes(
            to_process,
            filter_tax_values_to_apply=filter_to_apply,
            grouping_key_generator=grouping_key_generator,
        )
