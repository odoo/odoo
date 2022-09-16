# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _get_fp_vals(self, company, position):
        res = super()._get_fp_vals(company, position)
        if company.country_id.code == 'BR':
            res['l10n_br_fp_type'] = position['l10n_br_fp_type']
        return res

    @api.model
    def _create_cash_discount_loss_account(self, company, code_digits):
        if not self == self.env.ref('l10n_br.l10n_br_account_chart_template'):
            return super()._create_cash_discount_loss_account(company, code_digits)
        cash_discount_loss_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '3.01.01.01.02.02')], limit=1)
        if not cash_discount_loss_account:
            return self.env['account.account'].create({
                'name': _("(-) Descontos Incondicionais e Abatimentos"),
                'code': "3.01.01.01.02.02",
                'account_type': 'expense',
                'company_id': company.id,
            })
        return cash_discount_loss_account

    @api.model
    def _create_cash_discount_gain_account(self, company, code_digits):
        if not self == self.env.ref('l10n_br.l10n_br_account_chart_template'):
            return super()._create_cash_discount_gain_account(company, code_digits)
        cash_discount_gain_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '3.01.01.05.01.48')], limit=1)
        if not cash_discount_gain_account:
            return self.env['account.account'].create({
                'name': _("Cash Discount Gain"),
                'code': "3.01.01.05.01.48",
                'account_type': 'income_other',
                'company_id': company.id,
            })
        return cash_discount_gain_account
