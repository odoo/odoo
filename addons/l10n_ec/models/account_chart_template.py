# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        res = super()._prepare_all_journals(acc_template_ref, company, journals_dict=journals_dict)
        if company.account_fiscal_country_id.code == 'EC':
            for journal_values in res:
                if journal_values.get('type') == 'sale':
                    journal_values.update({
                        'name': f"001-001 {journal_values['name']}",
                        'l10n_ec_entity': '001',
                        'l10n_ec_emission': '001',
                        'l10n_ec_emission_address_id': company.partner_id.id,
                    })

        return res
