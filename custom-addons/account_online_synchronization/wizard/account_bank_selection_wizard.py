# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountBankSelection(models.TransientModel):
    _name = "account.bank.selection"
    _description = "Link a bank account to the selected journal"

    account_online_link_id = fields.Many2one('account.online.link')
    account_online_account_ids = fields.One2many(compute='_compute_online_account', comodel_name='account.online.account')
    institution_name = fields.Char(related="account_online_link_id.name")
    selected_account = fields.Many2one('account.online.account', domain="[('id', 'in', account_online_account_ids)]")

    @api.depends('account_online_link_id')
    def _compute_online_account(self):
        for record in self:
            record.account_online_account_ids = record.account_online_link_id.account_online_account_ids.filtered(lambda l: not l.journal_ids)

    def sync_now(self):
        if not self.selected_account:
            self.selected_account = self.account_online_account_ids[0]
        self.selected_account._assign_journal(self.env.context.get('swift_code'))
        # Get transactions for that account
        action = self.account_online_link_id._fetch_transactions(accounts=self.selected_account)
        if not action:
            action = self.env['ir.actions.act_window']._for_xml_id('account.open_account_journal_dashboard_kanban')
            action['target'] = 'main'
        return action
