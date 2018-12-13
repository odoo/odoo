# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class TaxAdjustments(models.TransientModel):
    _name = 'tax.adjustments.wizard'
    _description = 'Tax Adjustments Wizard'

    @api.multi
    def _get_default_journal(self):
        return self.env['account.journal'].search([('type', '=', 'general')], limit=1).id

    reason = fields.Char(string='Justification', required=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, default=_get_default_journal, domain=[('type', '=', 'general')])
    date = fields.Date(required=True, default=fields.Date.context_today)
    debit_account_id = fields.Many2one('account.account', string='Debit account', required=True, domain=[('deprecated', '=', False)])
    credit_account_id = fields.Many2one('account.account', string='Credit account', required=True, domain=[('deprecated', '=', False)])
    amount = fields.Monetary(currency_field='company_currency_id', required=True)
    adjustment_type = fields.Selection([('debit', 'Applied on debit journal item'), ('credit', 'Applied on credit journal item')], string="Adjustment Type", store=False, required=True)
    company_currency_id = fields.Many2one('res.currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)
    tax_id = fields.Many2one('account.tax', string='Adjustment Tax', ondelete='restrict', domain=[('type_tax_use', '=', 'adjustment')], required=True)

    @api.multi
    def _create_move(self):
        adjustment_type = self.env.context.get('adjustment_type', (self.amount > 0.0 and 'debit' or 'credit'))
        move_line_vals = []

        is_debit = adjustment_type == 'debit'
        for tax_vals in self.tax_id.compute_all(abs(self.amount))['taxes']:
            repartition_line = self.env['account.tax.repartition.line'].browse(tax_vals['tax_repartition_line_id'])
            # Vals for the amls corresponding to the tax
            move_line_vals.append((0, 0, {
                'name': self.reason,
                'debit': is_debit and abs(self.amount) or 0,
                'credit': not is_debit and abs(self.amount) or 0,
                'account_id': is_debit and self.debit_account_id.id or self.credit_account_id.id,
                'tax_line_id': tax_vals['id'],
                'tax_repartition_line_id': repartition_line.id,
                'tag_ids': [(6, False, repartition_line.tag_ids.ids)],
            }))

        # Vals for the counterpart line
        move_line_vals.append((0, 0, {
            'name': self.reason,
            'debit': not is_debit and abs(self.amount) or 0,
            'credit': is_debit and abs(self.amount) or 0,
            'account_id': is_debit and self.credit_account_id.id or self.debit_account_id.id,
            'tax_line_id': False,
        }))

        # Create the move
        vals = {
            'journal_id': self.journal_id.id,
            'date': self.date,
            'state': 'draft',
            'line_ids': move_line_vals,
        }
        move = self.env['account.move'].create(vals)
        move.post()
        return move.id

    @api.multi
    def create_move_debit(self):
        return self.with_context(adjustment_type='debit').create_move()

    @api.multi
    def create_move_credit(self):
        return self.with_context(adjustment_type='credit').create_move()

    def create_move(self):
        #create the adjustment move
        move_id = self._create_move()
        #return an action showing the created move
        action = self.env.ref(self.env.context.get('action', 'account.action_move_line_form'))
        result = action.read()[0]
        result['views'] = [(False, 'form')]
        result['res_id'] = move_id
        return result
