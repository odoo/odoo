# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _get_account_from_template(self, companies, template):
        if template:
            return self.env['account.account'].search([('company_id', 'in', companies.ids), ('code', '=', template.code)])
        return self.env['account.account']

    def _load(self, company):
        # EXTENDS account to setup taxes groups accounts configuration
        res = super()._load(company)
        self._l10n_ec_configure_ecuadorian_tax_groups_accounts(company)
        return res

    def _l10n_ec_configure_ecuadorian_tax_groups_accounts(self, companies):
        '''
        Set tax groups accounts for automatic closing entry in 103 and 104 reports
        The structure of the variable with the list of accounts by tax group:
        ('<tax_group_record_id>', '<payable_account_code>', '<receivable_account_code>')
        '''
        _TAX_GROUPS_ACCOUNTS_LIST = [
            ('tax_group_vat_05', '21070102', '11050202'),
            ('tax_group_vat_08', '21070102', '11050202'),
            ('tax_group_vat_12', '21070102', '11050202'),
            ('tax_group_vat_13', '21070102', '11050202'),
            ('tax_group_vat14', '21070102', '11050202'),
            ('tax_group_vat_15', '21070102', '11050202'),
            ('tax_group_vat0', '21070102', '11050202'),
            ('tax_group_vat_not_charged', '21070102', '11050202'),
            ('tax_group_vat_exempt', '21070102', '11050202'),
            ('tax_group_ice', '21070104', '21070104'),
            ('tax_group_irbpnr', '21070105', '21070105'),
            ('tax_group_withhold_vat_sale', '21070102', '11050203'),
            ('tax_group_withhold_vat_purchase', '21070102', '11050203'),
            ('tax_group_withhold_income_sale', '21070103', '11050201'),
            ('tax_group_withhold_income_purchase', '21070103', '11050201'),
            ('tax_group_outflows', '21070106', '11050205'),
            ('tax_group_others', '21070106', '11050205'),
        ]
        for tax_group_xml_id, payable_account_code, receivable_account_code in _TAX_GROUPS_ACCOUNTS_LIST:
            for company in companies.filtered(lambda company: company.account_fiscal_country_id.code == 'EC' and
                                                              company.chart_template_id == self.env.ref('l10n_ec.l10n_ec_ifrs')):
                # search accounts
                AccountObject = self.env['account.account']
                company_domain = [('company_id', '=', company.id)]
                payable_account_id = AccountObject.search([('code', '=', payable_account_code)] + company_domain)
                receivable_account_id = AccountObject.search([('code', '=', receivable_account_code)] + company_domain)
                # set accounts in tax groups by company
                self.env.ref(f'l10n_ec.{tax_group_xml_id}').with_company(company).property_tax_payable_account_id = payable_account_id
                self.env.ref(f'l10n_ec.{tax_group_xml_id}').with_company(company).property_tax_receivable_account_id = receivable_account_id

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
                    sale_account = acc_template_ref.get(self.env.ref('l10n_ec.ec410101', raise_if_not_found=False))
                    if sale_account:
                        journal_values['default_account_id'] = sale_account.id
                if journal_values.get('type') == 'purchase':
                    purchase_account = acc_template_ref.get(self.env.ref('l10n_ec.ec52022816', raise_if_not_found=False))
                    if purchase_account:
                        journal_values['default_account_id'] = purchase_account.id
        return res
