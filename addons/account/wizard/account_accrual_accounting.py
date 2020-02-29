# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccrualAccountingWizard(models.TransientModel):
    _name = 'account.accrual.accounting.wizard'
    _description = 'Create accrual entry.'

    date = fields.Date(required=True)
    company_id = fields.Many2one('res.company', required=True)
    account_type = fields.Selection([('income', 'Revenue'), ('expense', 'Expense')])
    active_move_line_ids = fields.Many2many('account.move.line')
    journal_id = fields.Many2one('account.journal', required=True, readonly=False,
        domain="[('company_id', '=', company_id), ('type', '=', 'general')]",
        related="company_id.accrual_default_journal_id")
    expense_accrual_account = fields.Many2one('account.account', readonly=False,
        domain="[('company_id', '=', company_id), ('internal_type', 'not in', ('receivable', 'payable')), ('internal_group', '=', 'liability'), ('reconcile', '=', True)]",
        related="company_id.expense_accrual_account_id")
    revenue_accrual_account = fields.Many2one('account.account', readonly=False,
        domain="[('company_id', '=', company_id), ('internal_type', 'not in', ('receivable', 'payable')), ('internal_group', '=', 'asset'), ('reconcile', '=', True)]",
        related="company_id.revenue_accrual_account_id")
    percentage = fields.Float("Percentage", default=100.0)
    total_amount = fields.Monetary(compute="_compute_total_amount", currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    @api.constrains('percentage')
    def _constraint_percentage(self):
        for record in self:
            if not (0.0 < record.percentage <= 100.0):
                raise UserError(_("Percentage must be between 0 and 100"))

    @api.depends('percentage', 'active_move_line_ids')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(record.active_move_line_ids.mapped(lambda l: record.percentage * (l.debit + l.credit) / 100))

    @api.model
    def default_get(self, fields):
        if self.env.context.get('active_model') != 'account.move.line' or not self.env.context.get('active_ids'):
            raise UserError(_('This can only be used on journal items'))
        rec = super(AccrualAccountingWizard, self).default_get(fields)
        active_move_line_ids = self.env['account.move.line'].browse(self.env.context['active_ids'])
        rec['active_move_line_ids'] = active_move_line_ids.ids

        if any(move.state != 'posted' for move in active_move_line_ids.mapped('move_id')):
            raise UserError(_('You can only change the period for posted journal items.'))
        if any(move_line.reconciled for move_line in active_move_line_ids):
            raise UserError(_('You can only change the period for items that are not yet reconciled.'))
        if any(line.account_id.user_type_id != active_move_line_ids[0].account_id.user_type_id for line in active_move_line_ids):
            raise UserError(_('All accounts on the lines must be from the same type.'))
        if any(line.company_id != active_move_line_ids[0].company_id for line in active_move_line_ids):
            raise UserError(_('All lines must be from the same company.'))
        rec['company_id'] = active_move_line_ids[0].company_id.id
        account_types_allowed = self.env.ref('account.data_account_type_expenses') + self.env.ref('account.data_account_type_revenue') + self.env.ref('account.data_account_type_other_income')
        if active_move_line_ids[0].account_id.user_type_id not in account_types_allowed:
            raise UserError(_('You can only change the period for items in these types of accounts: ') + ", ".join(account_types_allowed.mapped('name')))
        rec['account_type'] = active_move_line_ids[0].account_id.user_type_id.internal_group
        return rec

    def amend_entries(self):
        # set the accrual account on the selected journal items
        accrual_account = self.revenue_accrual_account if self.account_type == 'income' else self.expense_accrual_account

        # Generate journal entries.
        move_data = {}
        for aml in self.active_move_line_ids:
            ref1 = _('Accrual Adjusting Entry (%s recognized) for invoice: %s') % (self.percentage, aml.move_id.name)
            ref2 = _('Accrual Adjusting Entry (%s recognized) for invoice: %s') % (100 - self.percentage, aml.move_id.name)
            move_data.setdefault(aml.move_id, (
                [
                    # Values to create moves.
                    {
                        'date': self.date,
                        'ref': ref1,
                        'journal_id': self.journal_id.id,
                        'line_ids': [],
                    },
                    {
                        'date': aml.move_id.date,
                        'ref': ref2,
                        'journal_id': self.journal_id.id,
                        'line_ids': [],
                    },
                ], [
                    # Messages to log on the chatter.
                    (_('Accrual Adjusting Entry ({percent}% recognized) for invoice:') + ' <a href=# data-oe-model=account.move data-oe-id={id}>{name}</a>').format(
                        percent=self.percentage,
                        id=aml.move_id.id,
                        name=aml.move_id.name,
                    ),
                    (_('Accrual Adjusting Entry ({percent}% recognized) for invoice:') + ' <a href=# data-oe-model=account.move data-oe-id={id}>{name}</a>').format(
                        percent=100 - self.percentage,
                        id=aml.move_id.id,
                        name=aml.move_id.name,
                    ),
                ]
            ))

            reported_debit = aml.company_id.currency_id.round((self.percentage / 100) * aml.debit)
            reported_credit = aml.company_id.currency_id.round((self.percentage / 100) * aml.credit)
            if aml.currency_id:
                reported_amount_currency = aml.currency_id.round((self.percentage / 100) * aml.amount_currency)
            else:
                reported_amount_currency = 0.0

            move_data[aml.move_id][0][0]['line_ids'] += [
                (0, 0, {
                    'name': aml.name,
                    'debit': reported_debit,
                    'credit': reported_credit,
                    'amount_currency': reported_amount_currency,
                    'currency_id': aml.currency_id.id,
                    'account_id': aml.account_id.id,
                    'partner_id': aml.partner_id.id,
                }),
                (0, 0, {
                    'name': ref1,
                    'debit': reported_credit,
                    'credit': reported_debit,
                    'amount_currency': -reported_amount_currency,
                    'currency_id': aml.currency_id.id,
                    'account_id': accrual_account.id,
                    'partner_id': aml.partner_id.id,
                }),
            ]

            move_data[aml.move_id][0][1]['line_ids'] += [
                (0, 0, {
                    'name': aml.name,
                    'debit': aml.debit - reported_debit,
                    'credit': aml.credit - reported_credit,
                    'amount_currency': aml.amount_currency - reported_amount_currency,
                    'currency_id': aml.currency_id.id,
                    'account_id': aml.account_id.id,
                    'partner_id': aml.partner_id.id,
                }),
                (0, 0, {
                    'name': ref2,
                    'debit': aml.credit - reported_credit,
                    'credit': aml.debit - reported_debit,
                    'amount_currency': reported_amount_currency - aml.amount_currency,
                    'currency_id': aml.currency_id.id,
                    'account_id': accrual_account.id,
                    'partner_id': aml.partner_id.id,
                }),
            ]

        # Update the account of selected journal items.
        self.active_move_line_ids.write({'account_id': accrual_account.id})

        # When the percentage is 100%, the second move is not needed.
        if self.percentage < 100:
            move_vals = []
            log_messages = []
            for v in move_data.values():
                move_vals += v[0]
                log_messages += v[1]
        else:
            move_vals = [v[0][0] for k, v in move_data.items()]
            log_messages = [v[1][0] for k, v in move_data.items()]

        created_moves = self.env['account.move'].create(move_vals)
        created_moves.post()

        # Reconcile.
        index = 0
        for move in self.active_move_line_ids.mapped('move_id'):
            if self.percentage < 100:
                accrual_moves = created_moves[index:index + 2]
                index += 2
            else:
                accrual_moves = created_moves[index:index + 1]
                index += 1

            to_reconcile = self.active_move_line_ids.filtered(lambda line: line.move_id == move)
            to_reconcile += accrual_moves.mapped('line_ids').filtered(lambda line: line.account_id == accrual_account and not line.reconciled)
            to_reconcile.reconcile()

        # Log messages.
        for created_move, log_message in zip(created_moves, log_messages):
            created_move.message_post(body=log_message)

        # open the generated entries
        action = {
            'name': _('Generated Entries'),
            'domain': [('id', 'in', created_moves.ids)],
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
            'views': [(self.env.ref('account.view_move_tree').id, 'tree'), (False, 'form')],
        }
        if len(created_moves) == 1:
            action.update({'view_mode': 'form', 'res_id': created_moves.id})
        return action
