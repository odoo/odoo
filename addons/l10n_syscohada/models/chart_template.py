# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    @api.model
    def _create_cash_discount_loss_account(self, company, code_digits):
        if not self == self.env.ref('l10n_syscohada.syscohada_chart_template'):
            return super()._create_cash_discount_loss_account(company, code_digits)
        cash_discount_loss_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '601900')], limit=1)
        if not cash_discount_loss_account:
            return self.env['account.account'].create({
                'name': _("Rabais, Remises et Ristournes obtenus (non ventilés)"),
                'code': 601900,
                'account_type': 'expense',
                'company_id': company.id,
            })
        return cash_discount_loss_account

    @api.model
    def _create_cash_discount_gain_account(self, company, code_digits):
        if not self == self.env.ref('l10n_syscohada.syscohada_chart_template'):
            return super()._create_cash_discount_gain_account(company, code_digits)
        cash_discount_gain_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '701900')], limit=1)
        if not cash_discount_gain_account:
            return self.env['account.account'].create({
                'name': _("Rabais, remises, ristournes accordés (non ventilés)"),
                'code': 701900,
                'account_type': 'income_other',
                'company_id': company.id,
            })
        return cash_discount_gain_account
