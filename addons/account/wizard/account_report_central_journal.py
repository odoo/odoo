from openerp import models, fields, api


class account_central_journal(models.TransientModel):
    _name = 'account.central.journal'
    _description = 'Account Central Journal'
    _inherit = "account.common.journal.report"

    journal_ids = fields.Many2many('account.journal', 'account_central_journal_journal_rel', 'account_id', 'journal_id', string='Journals', required=True)

    @api.multi
    def _print_report(self, data):
        data = self.pre_print_report(data)
        return self.env['report'].get_action(self.env['account.central.journal'], 'account.report_centraljournal', data=data)

