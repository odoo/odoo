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
        if company.account_fiscal_country_id.code == 'CH':
            demo_data['account.move'] = self._get_demo_data_move(company)
        return demo_data

    def _post_load_demo_data(self, company=False):
        super()._post_load_demo_data(company)
        if company.account_fiscal_country_id.code == 'CH':
            invoices = (
                    self.ref('demo_bill_ch')
                    + self.ref('demo_invoice_ch')
                    + self.ref('demo_move_affect_result_ch')
            )
            for move in invoices:
                try:
                    move.action_post()
                except (UserError, ValidationError):
                    _logger.exception('Error while posting demo data')

    def _get_demo_data_move(self, company=False):
        moves = super()._get_demo_data_move(company)
        if company.account_fiscal_country_id.code == 'CH':
            last_year = fields.Date.today() - relativedelta(years=1, month=1, day=1)
            moves.update({
                self.company_xmlid('demo_bill_ch'): {
                    'move_type': 'in_invoice',
                    'partner_id': 'base.res_partner_12',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date': (last_year + relativedelta(month=2)).strftime('%Y-%m-%d'),
                    'invoice_line_ids': [
                        Command.create({'product_id': 'product.product_delivery_01', 'price_unit': 300}),
                    ],
                },
                self.company_xmlid('demo_invoice_ch'): {
                    'move_type': 'out_invoice',
                    'partner_id': 'base.res_partner_2',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date': (last_year + relativedelta(month=7)).strftime('%Y-%m-%d'),
                    'invoice_line_ids': [
                        Command.create({'product_id': 'product.product_delivery_02', 'price_unit': 10, 'quantity': 100}),
                    ],
                },
                self.company_xmlid('demo_move_affect_result_ch'): {
                    'move_type': 'entry',
                    'ref': self.env._("Annual Closing %s", last_year.year),
                    'date': (last_year + relativedelta(month=12, day=31)).strftime('%Y-%m-%d'),
                    'journal_id': 'general',
                    'line_ids': [
                        Command.create({'debit': 700.0, 'credit': 0.0, 'account_id': 'unaffected_earnings_account'}),
                        Command.create({'debit': 0.0, 'credit': 700.0, 'account_id': 'ch_coa_2800'}),
                    ],
                },
            })
        return moves
