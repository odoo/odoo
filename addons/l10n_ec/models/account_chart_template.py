# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        res = super()._prepare_all_journals(acc_template_ref, company, journals_dict=journals_dict)
        for journal_values in res:
            if journal_values.get('type') == 'sale' and company.account_fiscal_country_id.code == 'EC':
                journal_values.update({
                    'name': f"001-001 {journal_values['name']}",
                    'l10n_ec_entity': '001',
                    'l10n_ec_emission': '001',
                    'l10n_ec_emission_address_id': company.partner_id.id,
                })

        # Copy tax support codes from tax templates onto corresponding taxes
        tax_templates = self.env['account.tax.template'].search([
            ('chart_template_id', '=', self.id),
            ('type_tax_use', '=', 'purchase')
        ])
        xml_ids = tax_templates.get_external_id()
        for tax_template in tax_templates:
            module, xml_id = xml_ids.get(tax_template.id).split('.')
            tax = self.env.ref('%s.%s_%s' % (module, company.id, xml_id), raise_if_not_found=False)
            if tax:
                tax.l10n_ec_code_taxsupport = tax_template.l10n_ec_code_taxsupport
        return res
