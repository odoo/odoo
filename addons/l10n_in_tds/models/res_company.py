import logging

from odoo import fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_in_withholding_account_id = fields.Many2one(
        comodel_name='account.account',
        string="TDS Account",
        check_company=True,
    )
    l10n_in_withholding_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="TDS Journal",
        check_company=True,
    )

    def _l10n_in_load_tds_chart_of_accounts_and_taxes(self, company):
        """ Load Chart of Accounts and Taxes for TDS """
        if company.l10n_in_tds:
            env = self.env
            data = {
                model: env['account.chart.template']._parse_csv('in', model, module='l10n_in_tds')
                for model in [
                    'account.account',
                    'account.tax',
                ]
            }
            ChartTemplate = env['account.chart.template'].with_company(company)
            try:
                ChartTemplate._deref_account_tags('in', data['account.tax'])
                ChartTemplate._pre_reload_data(company, {}, data)
                ChartTemplate._load_data(data)
            except ValidationError as e:
                _logger.warning("Error while updating Chart of Accounts for company %s: %s", company.name, e.args[0])
