# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.exceptions import UserError


class AccountPartnerLedger(models.TransientModel):

    _name = 'account.partner.ledger'
    _inherit = 'account.common.partner.report'
    _description = 'Account Partner Ledger'


    initial_balance = fields.Boolean(string='Include Initial Balances',
                                help='If you selected to filter by date, this field allow you to add a row to display the amount of debit/credit/balance that precedes the filter you\'ve set.')
    filters = fields.Selection([('filter_no', 'No Filters'), ('filter_date', 'Date'), ('unreconciled', 'Unreconciled Entries')], string="Filter by", required=True, default='filter_no')
    page_split = fields.Boolean(string='One Partner Per Page', help='Display Ledger Report with One partner per page')
    amount_currency = fields.Boolean(string="With Currency", help="It adds the currency column on report if the currency differs from the company currency.")
    journal_ids = fields.Many2many('account.journal', 'account_partner_ledger_journal_rel', 'account_id', 'journal_id', string='Journals', required=True)

    @api.onchange('filters')
    def _onchange_filters(self):
        if self.filters in ['filter_no', 'unreconciled']:
            self.initial_balance = False
            self.date_from = False
            self.date_to = False

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update(self.read(['initial_balance', 'filters', 'page_split', 'amount_currency'])[0])
        if data['form'].get('initial_balance') and not data['form'].get('date_from'):
            raise UserError(_("You must define a Start Date"))
        return self.env['report'].get_action(self, 'account.report_partnerledger', data=data)
