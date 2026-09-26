import logging

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, Command
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self, company=False):
        demo_data = super()._get_demo_data(company)
        if company.account_fiscal_country_id.code == 'LU':
            demo_data['account.move'] = self._get_demo_data_move(company)
        return demo_data

    def _post_load_demo_data(self, company=False):
        super()._post_load_demo_data(company)
        if company.account_fiscal_country_id.code == 'LU':
            invoices = (
                    self.ref('demo_bill_lu')
                    + self.ref('demo_invoice_lu')
                    + self.ref('demo_move_affect_result_lu')
            )
            for move in invoices:
                try:
                    move.action_post()
                except (UserError, ValidationError):
                    _logger.exception('Error while posting demo data')

    def _get_demo_data_move(self, company=False):
        moves = super()._get_demo_data_move(company)
        if company.account_fiscal_country_id.code == 'LU':
            cid = company.id or self.env.company.id
            last_year = fields.Date.today() - relativedelta(years=1, month=1, day=1)
            misc_journal = self.env['account.journal'].search(
                domain=[
                    *self.env['account.journal']._check_company_domain(cid),
                    ('type', '=', 'general'),
                ],
                limit=1,
            )
            equity_unaffected_account = self.env['account.account'].search(
                domain=[
                *self.env['account.account']._check_company_domain(cid),
                    ('account_type', '=', 'equity_unaffected')
                ],
                limit=1,
            )
            equity_account = self.env['account.account'].search(
                domain=[
                *self.env['account.account']._check_company_domain(cid),
                    ('account_type', '=', 'equity')
                ],
                limit=1,
            )
            moves.update({
                self.company_xmlid('demo_bill_lu'): {
                    'move_type': 'in_invoice',
                    'partner_id': 'base.res_partner_12',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date': (last_year + relativedelta(month=2)).strftime('%Y-%m-%d'),
                    'invoice_line_ids': [
                        Command.create({'price_unit': 300}),
                    ],
                },
                self.company_xmlid('demo_invoice_lu'): {
                    'move_type': 'out_invoice',
                    'partner_id': 'base.res_partner_2',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date': (last_year + relativedelta(month=7)).strftime('%Y-%m-%d'),
                    'invoice_line_ids': [
                        Command.create({'price_unit': 1000}),
                    ],
                },
                self.company_xmlid('demo_move_affect_result_lu'): {
                    'move_type': 'entry',
                    'ref': self.env._("Annual Closing %s", last_year.year),
                    'date': (last_year + relativedelta(month=12, day=31)).strftime('%Y-%m-%d'),
                    'journal_id': misc_journal.id,
                    'line_ids': [
                        Command.create({'debit': 700.0, 'credit': 0.0, 'account_id': equity_unaffected_account.id}),
                        Command.create({'debit': 0.0, 'credit': 700.0, 'account_id': equity_account.id}),
                    ],
                },
            })
        return moves
