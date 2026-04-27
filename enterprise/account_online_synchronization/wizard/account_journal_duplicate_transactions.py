from datetime import timedelta

from odoo import api, Command, fields, models, _


class AccountDuplicateTransaction(models.TransientModel):
    _name = 'account.duplicate.transaction.wizard'
    _description = 'Wizard for duplicate transactions'

    date = fields.Date(
        string="Starting Date",
        compute='_compute_date', readonly=False, store=True,
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        domain="[('type', '=', 'bank')]",
    )
    transaction_ids = fields.One2many(
        comodel_name='account.bank.statement.line',
        compute='_compute_transaction_ids',
    )
    first_ids_in_group = fields.Json(compute='_compute_transaction_ids')

    @api.depends('journal_id')
    def _compute_display_name(self):
        for wizard in self:
            wizard.display_name = _('%s duplicate transactions', wizard.journal_id.name or '')

    @api.depends('journal_id', 'date')
    def _compute_transaction_ids(self):
        for wizard in self:
            ids_groups = wizard.journal_id._get_duplicate_transactions(wizard.date or fields.Date.today()) if wizard.journal_id else []
            first_ids_in_group = []
            flat_ids = []
            check_set = set()
            for ids_group in ids_groups:
                group_set = set(ids_group)
                if not group_set & check_set:
                    # list view not supposed to have the same line multiple times
                    check_set.update(group_set)
                    flat_ids.extend(ids_group)
                    first_ids_in_group.append(ids_group[0])
            wizard.write({'transaction_ids': [Command.set(flat_ids)]})
            wizard.first_ids_in_group = first_ids_in_group

    @api.depends('journal_id')
    def _compute_date(self):
        for wizard in self:
            if wizard.date:
                continue

            last_bsl = self.env['account.bank.statement.line'].search_read(
                [], order='id desc', limit=1, fields=['create_date']
            )
            if last_bsl:
                # set date to the oldest transaction date of last sync batch
                bsl = self.env['account.bank.statement.line'].search_read(
                    [('create_date', '>=', last_bsl[0]['create_date'] - timedelta(minutes=10))],
                    order='date', limit=1, fields=['date'],
                )
                wizard.date = bsl[0]['date']
            else:
                wizard.date = fields.Datetime.today()

    def action_display_duplicate_transaction(self):
        return self.journal_id.action_display_duplicate_transaction_from_date(self.date)
