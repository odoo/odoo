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
    journal_id = fields.Many2one('account.journal', required=True, related="company_id.accrual_default_journal_id", readonly=False)
    expense_accrual_account = fields.Many2one('account.account', related="company_id.expense_accrual_account_id", readonly=False)
    revenue_accrual_account = fields.Many2one('account.account', related="company_id.revenue_accrual_account_id", readonly=False)
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
        # gather the origin account on seleced journal items
        origin_accounts = {}
        for aml in self.active_move_line_ids:
            origin_accounts[aml.id] = aml.account_id.id

        # set the accrual account on the selected journal items
        self.active_move_line_ids.write({'account_id': (self.revenue_accrual_account if self.account_type == 'income' else self.expense_accrual_account).id})

        # create the accrual move(s) and reconcile accrual items together
        for aml in self.active_move_line_ids:
            reported_debit = aml.company_id.currency_id.round((self.percentage / 100) * aml.debit)
            reported_credit = aml.company_id.currency_id.round((self.percentage / 100) * aml.credit)
            ref = _('Accrual Adjusting Entry ({percent}% recognized) for invoice: {name}').format(percent=self.percentage, name=aml.move_id.name)
            move_data = [{
                'date': self.date,
                'ref': ref,
                'journal_id': self.journal_id.id,
                'line_ids': [
                    (0, 0, {
                        'name': aml.name,
                        'debit': reported_debit,
                        'credit': reported_credit,
                        'account_id': origin_accounts[aml.id],
                        'partner_id': aml.partner_id.id,
                    }),
                    (0, 0, {
                        'name': ref,
                        'debit': reported_credit,
                        'credit': reported_debit,
                        'account_id': (self.revenue_accrual_account if self.account_type == 'income' else self.expense_accrual_account).id,
                        'partner_id': aml.partner_id.id,
                    }),
                ],
            }]
            message_data = [(_('Accrual Adjusting Entry ({percent}% recognized) for invoice:') + ' <a href=# data-oe-model=account.move data-oe-id={id}>{name}</a>').format(
                percent=self.percentage,
                id=aml.move_id.id,
                name=aml.move_id.name,
            )]
            # in case the percentage to recognize is not 100%, another entry is created to keep the remaining balance in the same account at the original date
            if self.percentage < 100:
                ref = _('Accrual Adjusting Entry ({percent}% recognized) for invoice: {name}').format(percent=100 - self.percentage, name=aml.move_id.name)
                move_data.append({
                    'date': aml.move_id.date,
                    'ref': ref,
                    'journal_id': self.journal_id.id,
                    'line_ids': [
                        (0, 0, {
                            'name': aml.name,
                            'debit': aml.debit - reported_debit,
                            'credit': aml.credit - reported_credit,
                            'account_id': origin_accounts[aml.id],
                            'partner_id': aml.partner_id.id,
                        }),
                        (0, 0, {
                            'name': ref,
                            'debit': aml.credit - reported_credit,
                            'credit': aml.debit - reported_debit,
                            'account_id': (self.revenue_accrual_account if self.account_type == 'income' else self.expense_accrual_account).id,
                            'partner_id': aml.partner_id.id,
                        }),
                    ],
                })
                message_data.append((_('Accrual Adjusting Entry ({percent}% recognized) for invoice:') + ' <a href=# data-oe-model=account.move data-oe-id={id}>{name}</a>').format(
                    percent=self.percentage,
                    id=aml.move_id.id,
                    name=aml.move_id.name,
                ))

            created_ids = self.env['account.move'].create(move_data)
            created_ids.post()
            for move, msg in zip(created_ids, message_data):
                move.message_post(body=msg)

            # reconcile journal items on the accrual account
            to_reconcile = created_ids.line_ids.filtered(lambda line: line.account_id in (self.revenue_accrual_account + self.expense_accrual_account)) + aml
            to_reconcile.reconcile()

        # open the generated entries
        action = {
            'name': _('Generated Entries'),
            'domain': [('id', 'in', created_ids.ids)],
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
            'views': [(self.env.ref('account.view_move_tree').id, 'tree'), (False, 'form')],
        }
        if len(created_ids) == 1:
            action.update({'view_mode': 'form', 'res_id': created_ids.id})
        return action
