from odoo import models, api, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        """ If EGYPT chart, we add 2 new journals TA and IFRS"""
        if self == self.env.ref('l10n_eg.egypt_chart_template_standard'):
            if not journals_dict:
                journals_dict = []
            journals_dict.extend(
                [{"name": "Tax Adjustments", "company_id": company.id, "code": "TA", "type": "general", "sequence": 1,
                  "favorite": True},
                 {"name": "IFRS 16", "company_id": company.id, "code": "IFRS", "type": "general", "favorite": True,
                  "sequence": 10}])
        return super()._prepare_all_journals(acc_template_ref, company, journals_dict=journals_dict)

    @api.model
    def _create_cash_discount_loss_account(self, company, code_digits):
        if not self == self.env.ref('l10n_eg.egypt_chart_template_standard'):
            return super()._create_cash_discount_loss_account(company, code_digits)
        cash_discount_loss_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '400079')], limit=1)
        if not cash_discount_loss_account:
            return self.env['account.account'].create({
                'name': _("Cash Discount Loss"),
                'code': 400079,
                'account_type': 'expense',
                'company_id': company.id,
            })
        return cash_discount_loss_account

    @api.model
    def _create_cash_discount_gain_account(self, company, code_digits):
        if not self == self.env.ref('l10n_eg.egypt_chart_template_standard'):
            return super()._create_cash_discount_gain_account(company, code_digits)
        cash_discount_gain_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '500014')], limit=1)
        if not cash_discount_gain_account:
            return self.env['account.account'].create({
                'name': _("Cash Discount Gain"),
                'code': 500014,
                'account_type': 'income_other',
                'company_id': company.id,
            })
        return cash_discount_gain_account
