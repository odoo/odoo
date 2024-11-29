from odoo import api, models, fields


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_tr_default_sales_return_account_id = fields.Many2one(
        comodel_name='account.account',
        readonly=False,
        store=True,
        compute='_compute_l10n_tr_default_sales_return_account_id',
        check_company=True,
    )

    @api.depends('type', 'company_id.country_code')
    def _compute_l10n_tr_default_sales_return_account_id(self):
        for journal in self:
            if journal.l10n_tr_default_sales_return_account_id:
                continue

            if journal.country_code == 'TR' and journal.type == 'sale':
                ChartTemplate = self.env['account.chart.template'].with_company(journal.company_id)
                return_account = ChartTemplate.ref('tr610', raise_if_not_found=False)
                journal.l10n_tr_default_sales_return_account_id = return_account
            else:
                journal.l10n_tr_default_sales_return_account_id = False
