# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        res = super(AccountChartTemplate, self)._prepare_all_journals(acc_template_ref, company, journals_dict=journals_dict)
        for journal in res:
            if journal.get('code') == 'INV' and company.country_code == 'EC':
                journal.update({
                    'name': '001-001 ' + journal.get('name'),
                    'l10n_ec_entity': '001',
                    'l10n_ec_emission': '001',
                    'l10n_ec_emission_address_id': company.partner_id.id,
                })
        return res
