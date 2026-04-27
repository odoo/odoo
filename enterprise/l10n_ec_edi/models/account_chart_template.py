# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.account.models.chart_template import template

class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ec', 'account.journal')
    def _get_ec_edi_account_journal(self):
        return {
            'out_withhold': {
                'name': "Retenciones de Clientes",
                'code': 'RVNTA',
                'type': 'general',
                'l10n_ec_withhold_type': 'out_withhold',
                'l10n_ec_entity': False,
                'l10n_ec_is_purchase_liquidation': False,
                'l10n_ec_emission': False,
                'l10n_ec_emission_address_id': False,
                'show_on_dashboard': True,
            },
            'in_withhold': {
                'name': "001-001 Retenciones",
                'code': 'RCMPR',
                'type': 'general',
                'l10n_ec_withhold_type': 'in_withhold',
                'l10n_ec_entity': '001',
                'l10n_ec_emission': '001',
                'l10n_ec_is_purchase_liquidation': False,
                'l10n_ec_emission_address_id': self.env.company.partner_id.id,
                'show_on_dashboard': True,
            },
            'in_liquidation': {
                'name': "001-001 Liquidaciones de Compra",
                'code': 'LIQCO',
                'type': 'purchase',
                'l10n_ec_withhold_type': False,
                'l10n_ec_entity': '001',
                'l10n_ec_emission': '001',
                'l10n_ec_is_purchase_liquidation': True,
                'l10n_latam_use_documents': True,
                'l10n_ec_emission_address_id': self.env.company.partner_id.id,
                'show_on_dashboard': True,
            }
        }

    def _load(self, template_code, company, install_demo, force_create=True):
        # EXTENDS account to create journals and setup withhold taxes in company configuration
        res = super()._load(template_code, company, install_demo, force_create)
        if template_code == 'ec':
            self._l10n_ec_configure_ecuadorian_withhold_taxpayer_type(company)
            self._l10n_ec_setup_profit_withhold_taxes(company)
            self._l10n_ec_copy_taxsupport_codes_from_templates(company)
            self._l10n_ec_configure_default_withhold_accounts(company)
            self._l10n_ec_setup_edi_purchase_journal_account(company)
        return res

    def _l10n_ec_configure_ecuadorian_withhold_taxpayer_type(self, companies):
        # Set proper profit withhold tax on RIMPE on taxpayer type
        for company in companies.filtered(lambda r: r.account_fiscal_country_id.code == 'EC'):
            tax_rimpe_entrepreneur = self.env['account.tax'].search([
                *self.env['account.tax']._check_company_domain(company),
                ('l10n_ec_code_base', '=', '343'),
            ], limit=1)
            tax_rimpe_popular_business = self.env['account.tax'].search([
                *self.env['account.tax']._check_company_domain(self.env.company),
                ('l10n_ec_code_base', '=', '332'),
            ], limit=1)
            if tax_rimpe_entrepreneur:
                rimpe_entrepreneur = self.env.ref('l10n_ec_edi.l10n_ec_taxpayer_type_13')  # RIMPE Regime Entrepreneur
                rimpe_entrepreneur.with_company(company).profit_withhold_tax_id = tax_rimpe_entrepreneur.id
            if tax_rimpe_popular_business:
                rimpe_popular_business = self.env.ref('l10n_ec_edi.l10n_ec_taxpayer_type_15') # RIMPE Regime Popular Business
                rimpe_popular_business.with_company(company).profit_withhold_tax_id = tax_rimpe_popular_business.id

    def _l10n_ec_setup_profit_withhold_taxes(self, companies):
        # Sets fallback taxes for purchase withholds
        for company in companies.filtered(lambda r: r.account_fiscal_country_id.code == 'EC'):
            company.l10n_ec_withhold_services_tax_id = self.env['account.tax'].search([
                *self.env['account.tax']._check_company_domain(company),
                ('l10n_ec_code_ats', '=', '3440'),
                ('tax_group_id.l10n_ec_type', '=', 'withhold_income_purchase'),
            ], limit=1)
            company.l10n_ec_withhold_credit_card_tax_id = self.env['account.tax'].search([
                *self.env['account.tax']._check_company_domain(company),
                ('l10n_ec_code_ats', '=', '332G'),
                ('tax_group_id.l10n_ec_type', '=', 'withhold_income_purchase'),
            ], limit=1)
            company.l10n_ec_withhold_goods_tax_id = self.env['account.tax'].search([
                *self.env['account.tax']._check_company_domain(company),
                ('l10n_ec_code_ats', '=', '312'),
                ('tax_group_id.l10n_ec_type', '=', 'withhold_income_purchase'),
            ], limit=1)

    @template('ec', 'account.tax')
    def _get_ec_edi_account_tax(self):
        return {
            'tax_vat_510_sup_01': {'l10n_ec_code_taxsupport': "01"},
            'tax_vat_05_510_sup_01': {'l10n_ec_code_taxsupport': "01"},
            'tax_vat_15_510_sup_01': {'l10n_ec_code_taxsupport': "01"},
            'tax_vat_510_sup_05': {'l10n_ec_code_taxsupport': "05"},
            'tax_vat_05_510_sup_05': {'l10n_ec_code_taxsupport': "05"},
            'tax_vat_15_510_sup_05': {'l10n_ec_code_taxsupport': "05"},
            'tax_vat_510_sup_06': {'l10n_ec_code_taxsupport': "06"},
            'tax_vat_05_510_sup_06': {'l10n_ec_code_taxsupport': "06"},
            'tax_vat_15_510_sup_06': {'l10n_ec_code_taxsupport': "06"},
            'tax_vat_510_sup_15': {'l10n_ec_code_taxsupport': "15"},
            'tax_vat_05_510_sup_15': {'l10n_ec_code_taxsupport': "15"},
            'tax_vat_15_510_sup_15': {'l10n_ec_code_taxsupport': "15"},
            'tax_vat_511_sup_03': {'l10n_ec_code_taxsupport': "03"},
            'tax_vat_05_511_sup_03': {'l10n_ec_code_taxsupport': "03"},
            'tax_vat_15_511_sup_03': {'l10n_ec_code_taxsupport': "03"},
            'tax_vat_512_sup_04': {'l10n_ec_code_taxsupport': "04"},
            'tax_vat_05_512_sup_04': {'l10n_ec_code_taxsupport': "04"},
            'tax_vat_15_512_sup_04': {'l10n_ec_code_taxsupport': "04"},
            'tax_vat_512_sup_05': {'l10n_ec_code_taxsupport': "05"},
            'tax_vat_05_512_sup_05': {'l10n_ec_code_taxsupport': "05"},
            'tax_vat_15_512_sup_05': {'l10n_ec_code_taxsupport': "05"},
            'tax_vat_512_sup_07': {'l10n_ec_code_taxsupport': "07"},
            'tax_vat_05_512_sup_07': {'l10n_ec_code_taxsupport': "07"},
            'tax_vat_15_512_sup_07': {'l10n_ec_code_taxsupport': "07"},
            'tax_vat_513_sup_01': {'l10n_ec_code_taxsupport': "01"},
            'tax_vat_05_513_sup_01': {'l10n_ec_code_taxsupport': "01"},
            'tax_vat_15_513_sup_01': {'l10n_ec_code_taxsupport': "01"},
            'tax_vat_514_sup_06': {'l10n_ec_code_taxsupport': "06"},
            'tax_vat_05_514_sup_06': {'l10n_ec_code_taxsupport': "06"},
            'tax_vat_15_514_sup_06': {'l10n_ec_code_taxsupport': "06"},
            'tax_vat_515_sup_03': {'l10n_ec_code_taxsupport': "03"},
            'tax_vat_05_515_sup_03': {'l10n_ec_code_taxsupport': "03"},
            'tax_vat_15_515_sup_03': {'l10n_ec_code_taxsupport': "03"},
            'tax_vat_516_sup_07': {'l10n_ec_code_taxsupport': "07"},
            'tax_vat_517_sup_02': {'l10n_ec_code_taxsupport': "02"},
            'tax_vat_517_sup_04': {'l10n_ec_code_taxsupport': "04"},
            'tax_vat_517_sup_05': {'l10n_ec_code_taxsupport': "05"},
            'tax_vat_517_sup_07': {'l10n_ec_code_taxsupport': "07"},
            'tax_vat_517_sup_15': {'l10n_ec_code_taxsupport': "15"},
            'tax_vat_518_sup_02': {'l10n_ec_code_taxsupport': "02"},
            'tax_vat_541_sup_02': {'l10n_ec_code_taxsupport': "02"},
            'tax_vat_542_sup_02': {'l10n_ec_code_taxsupport': "02"},
            'tax_vat_510_08_sup_01': {'l10n_ec_code_taxsupport': "01"},
            'tax_vat_545_sup_08': {'l10n_ec_code_taxsupport': "08"},
            'tax_vat_05_545_sup_08': {'l10n_ec_code_taxsupport': "08"},
            'tax_vat_15_545_sup_08': {'l10n_ec_code_taxsupport': "08"},
            'tax_vat_545_sup_08_vat0': {'l10n_ec_code_taxsupport': "08"},
            'tax_vat_545_sup_08_vat_exempt': {'l10n_ec_code_taxsupport': "08"},
            'tax_vat_545_sup_08_vat_not_charged': {'l10n_ec_code_taxsupport': "08"},
            'tax_vat_545_sup_09': {'l10n_ec_code_taxsupport': "09"},
            'tax_vat_05_545_sup_09': {'l10n_ec_code_taxsupport': "09"},
            'tax_vat_15_545_sup_09': {'l10n_ec_code_taxsupport': "09"},
        }

    def _l10n_ec_copy_taxsupport_codes_from_templates(self, companies):
        for company in companies:
            Template = self.env['account.chart.template'].with_company(company)
            for xml_id, tax_data in Template._get_ec_edi_account_tax().items():
                tax = Template.ref(xml_id, raise_if_not_found=False)
                if tax and 'l10n_ec_code_taxsupport' in tax_data:
                    tax.l10n_ec_code_taxsupport = tax_data['l10n_ec_code_taxsupport']

    def _l10n_ec_configure_default_withhold_accounts(self, companies):
        for company in companies:
            company.l10n_ec_tax_base_sale_account_id = self.env.ref("account.%s_ec_sale_withhold_tax_base" % company.id, raise_if_not_found=False)
            company.l10n_ec_tax_base_purchase_account_id = self.env.ref("account.%s_ec_purchase_withhold_tax_base" % company.id, raise_if_not_found=False)

    def _l10n_ec_setup_edi_purchase_journal_account(self, companies):
        journals = dict(self.env['account.journal']._read_group(domain=[('company_id', 'in', companies.ids), ('code', '=', 'LIQCO')], groupby=['company_id', 'id']))
        for company in companies:
            Template = self.env['account.chart.template'].with_company(company)
            template_code = company.chart_template
            template_data = Template._get_chart_template_data(template_code).pop('template_data')
            if (journal := journals.get(company)) and (expense_account_ref := template_data.get('journal_account_expense_categ_id')):
                journal.default_account_id = Template.ref(expense_account_ref, raise_if_not_found=False)
