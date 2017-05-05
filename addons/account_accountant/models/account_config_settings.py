# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
import datetime


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    fiscalyear_last_day = fields.Integer(related='company_id.fiscalyear_last_day', default=31)
    fiscalyear_last_month = fields.Selection([
        (1, 'January'),
        (2, 'February'),
        (3, 'March'),
        (4, 'April'),
        (5, 'May'),
        (6, 'June'),
        (7, 'July'),
        (8, 'August'),
        (9, 'September'),
        (10, 'October'),
        (11, 'November'),
        (12, 'December')
        ], related='company_id.fiscalyear_last_month', default=12)
    period_lock_date = fields.Date(related='company_id.period_lock_date')
    fiscalyear_lock_date = fields.Date(related='company_id.fiscalyear_lock_date')
    use_anglo_saxon = fields.Boolean(string='Anglo-Saxon Accounting', related='company_id.anglo_saxon_accounting')
    transfer_account_id = fields.Many2one('account.account', string="Transfer Account",
        related='company_id.transfer_account_id',
        domain=lambda self: [('reconcile', '=', True), ('user_type_id.id', '=', self.env.ref('account.data_account_type_current_assets').id)],
        help="Intermediary account used when moving money from a liquidity account to another")
    tax_cash_basis_journal_id = fields.Many2one(
        'account.journal',
        related='company_id.tax_cash_basis_journal_id',
        string="Tax Cash Basis Journal",)
    account_accountant_opening_move_id = fields.Many2one(string='Opening journal entry', comodel_name='account.move', related='company_id.account_accountant_opening_move_id')
    account_accountant_opening_journal_id = fields.Many2one(string='Opening journal', comodel_name='account.journal', related='company_id.account_accountant_opening_journal_id')
    account_accountant_opening_date = fields.Date(string='Accounting opening date', related='company_id.account_accountant_opening_date')
    account_accountant_opening_move_adjustment_amount = fields.Monetary(string='Adjustment difference', related="company_id.account_accountant_opening_move_adjustment_amount")
    account_accountant_opening_adjustment_account_id = fields.Many2one(string='Adjustment account', comodel_name='account.account', related='company_id.account_accountant_opening_adjustment_account_id')
    account_accountant_setup_opening_move_done = fields.Boolean(string='Opening move set', compute='_compute_account_accountant_setup_opening_move_done')

    @api.depends('company_id.account_accountant_opening_move_id.state')
    def _compute_account_accountant_setup_opening_move_done(self):
        for record in self:
            record.account_accountant_setup_opening_move_done = record.company_id.opening_move_posted()

    def define_opening_move_action(self):
        action = self.env.ref(self.company_id.setting_chart_of_accounts_action())
        return action.read([])[0] # Element at position 0 always exists, as it is defined in XML
