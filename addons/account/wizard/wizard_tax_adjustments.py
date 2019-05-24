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
    adjustment_type = fields.Selection([('debit', 'Applied on debit journal item'), ('credit', 'Applied on credit journal item')], string="Adjustment Type", required=True)
    tax_report_line_id = fields.Many2one(string="Report Line", comodel_name='account.tax.report.line', required=True, help="The report line to make an adjustment for.")
    company_currency_id = fields.Many2one('res.currency', readonly=True, default=lambda x: x.env.company_id.currency_id)
    country_id = fields.Many2one(string="Country", comodel_name='res.country', readonly=True, default=lambda x: x.env.company_id.country_id)

    def create_move(self):
        move_line_vals = []

        is_debit = self.adjustment_type == 'debit'
        sign_multiplier = (self.amount<0 and -1 or 1) * (self.adjustment_type == 'credit' and -1 or 1)
        filter_lambda = (sign_multiplier < 0) and (lambda x: x.tax_negate) or (lambda x: not x.tax_negate)
        adjustment_tag = self.tax_report_line_id.tag_ids.filtered(filter_lambda)

        # Vals for the amls corresponding to the ajustment tag
        move_line_vals.append((0, 0, {
            'name': self.reason,
            'debit': is_debit and abs(self.amount) or 0,
            'credit': not is_debit and abs(self.amount) or 0,
            'account_id': is_debit and self.debit_account_id.id or self.credit_account_id.id,
            'tag_ids': [(6, False, [adjustment_tag.id])],
        }))

        # Vals for the counterpart line
        move_line_vals.append((0, 0, {
            'name': self.reason,
            'debit': not is_debit and abs(self.amount) or 0,
            'credit': is_debit and abs(self.amount) or 0,
            'account_id': is_debit and self.credit_account_id.id or self.debit_account_id.id,
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

        # Return an action opening the created move
        action = self.env.ref(self.env.context.get('action', 'account.action_move_line_form'))
        result = action.read()[0]
        result['views'] = [(False, 'form')]
        result['res_id'] = move.id
        return result
