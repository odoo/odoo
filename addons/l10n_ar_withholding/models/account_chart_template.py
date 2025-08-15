from odoo import models, api
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    # ar base
    @template('ar_base', 'account.account')
    def _get_ar_base_withholding_account_account(self):
        return self._parse_csv('ar_base', 'account.account', module='l10n_ar_withholding')

    # ri chart
    @template('ar_ri', 'account.tax.group')
    def _get_ar_ri_withholding_account_tax_group(self):
        return self._parse_csv('ar_ri', 'account.tax.group', module='l10n_ar_withholding')

    @template('ar_ri', 'account.tax')
    def _get_ar_ri_withholding_account_tax(self):
        additional = self._parse_csv('ar_ri', 'account.tax', module='l10n_ar_withholding')
        self._deref_account_tags('ar_ri', additional)
        return additional

    # ex chart
    @template('ar_ex', 'account.tax.group')
    def _get_ar_ex_withholding_account_tax_group(self):
        return self._parse_csv('ar_ex', 'account.tax.group', module='l10n_ar_withholding')

    @template('ar_ex', 'account.tax')
    def _get_ar_ex_withholding_account_tax(self):
        additional = self._parse_csv('ar_ex', 'account.tax', module='l10n_ar_withholding')
        self._deref_account_tags('ar_ex', additional)
        return additional

    @template('ar_base', 'res.company')
    def _get_ar_base_res_company(self):
        res = super()._get_ar_base_res_company()
        res[self.env.company.id].update({'l10n_ar_tax_base_account_id': 'base_tax_account'})
        return res

    @api.model
    def _l10n_ar_add_wth_sequences(self, company):
        """
        Add sequences to withholding taxes.

        This method ensures that each withholding tax has a unique sequence
        for numbering purposes. It creates sequences for non-profit taxes
        and profits taxes (earnings and earnings scale) and assigns them to
        the corresponding taxes.

        :param company: The company for which the sequences are being created.
        """
        company.ensure_one()

        # Creation of sequences and assignment of tags for tax settlement
        withholdings_domain = [
            ('company_id', '=', company.id),
            ('type_tax_use', '=', 'none'),
            ('country_code', '=', 'AR'),
            ('l10n_ar_withholding_payment_type', '=', 'supplier'),
        ]
        non_profits_domain = withholdings_domain + [('l10n_ar_tax_type', 'not in', ['earnings', 'earnings_scale'])]

        for tax in self.env['account.tax'].with_context(active_test=False).search(non_profits_domain):
            sequence = self.env['ir.sequence'].create({
                'name': tax.invoice_label or tax.name,
                'prefix': '%(year)s-',
                'padding': 8,
                'number_increment': 1,
                'implementation': 'standard',
                'company_id': company.id,
            })
            tax.l10n_ar_withholding_sequence_id = sequence.id

        profits_domain = withholdings_domain + [('l10n_ar_tax_type', 'in', ['earnings', 'earnings_scale'])]
        sequence = self.env['ir.sequence'].create({
                "name": "Profits Tax Withholding",
                'prefix': '%(year)s-',
                'padding': 8,
                'number_increment': 1,
                'implementation': 'standard',
                'company_id': company.id,
            })
        profits_taxes = self.env['account.tax'].with_context(active_test=False).search(profits_domain)
        profits_taxes.l10n_ar_withholding_sequence_id = sequence.id

    def _load(self, template_code, company, install_demo, force_create=True):
        """
        After creating the taxes from the account.tax-ar_ri.csv, account.tax-ar_ex.csv, account.tax-ar_base.csv file of l10n_ar
        during the installation of the chart of accounts for a new Argentine company,
        this method adds the corresponding sequences for withholding taxes.

        :param template_code: The code of the chart template being loaded.
        :param company: The company for which the chart of accounts is being installed.
        :param install_demo: Boolean indicating whether demo data should be installed.
        :param force_create: Boolean indicating whether to force the creation of records.
        :return: The result of the super method call.
        """
        # Call super to create the taxes
        res = super()._load(template_code, company, install_demo, force_create=force_create)
        company = company or self.env.company
        if company.chart_template in ('ar_ri', 'ar_ex', 'ar_base'):
            self.sudo()._l10n_ar_add_wth_sequences(company)
        return res

    @api.model
    def _l10n_ar_wth_post_init(self):
        template_codes = ['ar_ri', 'ar_ex', 'ar_base']
        ar_companies = self.env['res.company'].search([('chart_template', 'in', template_codes), ('parent_id', '=', False)])
        for company in ar_companies:
            template_code = company.chart_template
            ChartTemplate = self.env['account.chart.template'].with_company(company)
            data = {
                model: self._parse_csv(template_code, model, module='l10n_ar_withholding')
                for model in [
                    'account.account',
                    'account.tax.group',
                    'account.tax',
                ]
            }
            ChartTemplate._deref_account_tags(template_code, data['account.tax'])
            ChartTemplate._pre_reload_data(company, {}, data)
            ChartTemplate._load_data(data)
            company.l10n_ar_tax_base_account_id = ChartTemplate.ref('base_tax_account')

            if self.env.ref('base.module_l10n_ar_withholding').demo:
                self.env['account.chart.template']._post_load_demo_data(company)
            self.sudo()._l10n_ar_add_wth_sequences(company)
