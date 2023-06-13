# -*- coding: utf-8 -*-
from odoo import models, Command, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    # Write paperformat and report template used on company
    def _load(self, company):
        res = super(AccountChartTemplate, self)._load(company)
        if self in [
            self.env.ref('l10n_de_skr03.l10n_de_chart_template', raise_if_not_found=False),
            self.env.ref('l10n_de_skr04.l10n_chart_de_skr04', raise_if_not_found=False)
        ]:
            company.write({
                'external_report_layout_id': self.env.ref('l10n_din5008.external_layout_din5008').id,
                'paperformat_id': self.env.ref('l10n_din5008.paperformat_euro_din').id
            })

            outstanding_receipt = company.account_journal_payment_debit_account_id
            outstanding_payment = company.account_journal_payment_credit_account_id

            asset_tag = self.env.ref('l10n_de.tag_de_asset_bs_B_II_4')
            outstanding_receipt['tag_ids'] += asset_tag
            outstanding_payment['tag_ids'] += asset_tag

        return res

    def _prepare_transfer_account_template(self):
        res = super(AccountChartTemplate, self)._prepare_transfer_account_template(None)
        if self in [
            self.env.ref('l10n_de_skr03.l10n_de_chart_template', raise_if_not_found=False),
            self.env.ref('l10n_de_skr04.l10n_chart_de_skr04', raise_if_not_found=False)
        ]:
            tag_ids = res.get('tag_ids', [])
            tag_ids += [Command.link(self.env.ref('l10n_de.tag_de_asset_bs_B_II_4').id)]
            res['tag_ids'] = tag_ids

        return res

    def _create_liquidity_journal_suspense_account(self, company, code_digits):
        if self not in [
            self.env.ref('l10n_de_skr03.l10n_de_chart_template', raise_if_not_found=False),
            self.env.ref('l10n_de_skr04.l10n_chart_de_skr04', raise_if_not_found=False)
        ]:
            return super()._create_liquidity_journal_suspense_account(company, code_digits)
        return self.env['account.account'].create({
            'name': _("Bank Suspense Account"),
            'code': self.env['account.account']._search_new_account_code(company, code_digits, company.bank_account_code_prefix or ''),
            'account_type': 'asset_current',
            'company_id': company.id,
            'tag_ids': self.env.ref('l10n_de.tag_de_asset_bs_B_IV')
        })
