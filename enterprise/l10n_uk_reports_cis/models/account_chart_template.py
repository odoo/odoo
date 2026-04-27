from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('uk', 'account.account')
    def _get_uk_account_account(self):
        return self._parse_csv('uk', 'account.account', module='l10n_uk_reports_cis')

    @template('uk', 'account.tax.group')
    def _get_uk_account_tax_group(self):
        return self._parse_csv('uk', 'account.tax.group', module='l10n_uk_reports_cis')

    @template('uk', 'account.tax')
    def _get_uk_account_tax(self):
        additionnal = self._parse_csv('uk', 'account.tax', module='l10n_uk_reports_cis')
        self._deref_account_tags('uk', additionnal)
        return additionnal

    def _post_load_data(self, template_code, company, template_data):
        super()._post_load_data(template_code, company, template_data)
        if template_code == 'uk':
            company = company or self.env.company
            cis_report = self.env.ref('l10n_uk_reports_cis.tax_report_cis')
            cis_report.with_company(company).tax_closing_start_date = cis_report.with_company(company).tax_closing_start_date.replace(day=6)
