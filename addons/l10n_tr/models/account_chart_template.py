from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _load(self, company):
        res = super()._load(company)
        if company.account_fiscal_country_id.code == 'TR':
            company.account_sale_tax_id = self.env.ref(f"l10n_tr.{company.id}_tr_kdv_sale_18")
            company.account_purchase_tax_id = self.env.ref(f"l10n_tr.{company.id}_tr_kdv_purchase_18")
        return res


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    def _get_tax_vals(self, company, tax_template_to_tax):
        res = super()._get_tax_vals(company, tax_template_to_tax)
        res['l10n_tr_exception_code_ids'] = self.l10n_tr_exception_code_ids.ids
        return res
