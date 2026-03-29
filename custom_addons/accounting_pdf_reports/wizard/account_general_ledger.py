from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountReportGeneralLedger(models.TransientModel):
    _name = "account.report.general.ledger"
    _inherit = "account.common.account.report"
    _description = "General Ledger Report"

    initial_balance = fields.Boolean(
        string='Include Initial Balances',
        help='If you selected date, this field allow you to add a row '
             'to display the amount of debit/credit/balance that precedes '
             'the filter you have set.'
    )
    sortby = fields.Selection(
        [('sort_date', 'Date'), ('sort_journal_partner', 'Journal & Partner')],
        string='Sort by', required=True, default='sort_date'
    )
    journal_ids = fields.Many2many(
        'account.journal', 'account_report_general_ledger_journal_rel',
        'account_id', 'journal_id', string='Journals', required=True
    )

    def _get_report_data(self, data):
        data = self.pre_print_report(data)
        data['form'].update(self.read(['initial_balance', 'sortby'])[0])
        if data['form'].get('initial_balance') and not data['form'].get('date_from'):
            raise UserError(_("You must define a Start Date"))
        records = self.env[data['model']].browse(data.get('ids', []))
        return records, data

    def _print_report(self, data):
        records, data = self._get_report_data(data)
        return self.env.ref('accounting_pdf_reports.action_report_general_ledger').with_context(landscape=True).report_action(records, data=data)
