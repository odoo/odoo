# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.tools import float_compare

class HrExpenseSplitWizard(models.TransientModel):
    _name = 'hr.expense.split.wizard'
    _description = 'Expense Split Wizard'

    expense_id = fields.Many2one('hr.expense', string='Expense', required=True)
    expense_split_line_ids = fields.One2many('hr.expense.split', 'wizard_id')
    total_amount = fields.Monetary('Total Amount', compute='_compute_total_amount', currency_field='currency_id')
    total_amount_original = fields.Monetary('Total amount original', related='expense_id.total_amount', currency_field='currency_id', help='Total amount of the original Expense that we are splitting')
    total_amount_taxes = fields.Monetary('Taxes', currency_field='currency_id', compute='_compute_total_amount_taxes')
    split_possible = fields.Boolean(help='The sum of after split shut remain the same', compute='_compute_split_possible')
    currency_id = fields.Many2one('res.currency', related='expense_id.currency_id')

    @api.depends('expense_split_line_ids.total_amount')
    def _compute_total_amount(self):
        for wizard in self:
            wizard.total_amount = sum(wizard.expense_split_line_ids.mapped('total_amount'))

    @api.depends('expense_split_line_ids.amount_tax')
    def _compute_total_amount_taxes(self):
        for wizard in self:
            wizard.total_amount_taxes = sum(wizard.expense_split_line_ids.mapped('amount_tax'))

    @api.depends('total_amount_original', 'total_amount')
    def _compute_split_possible(self):
        for wizard in self:
            wizard.split_possible = wizard.total_amount_original and (float_compare(wizard.total_amount_original, wizard.total_amount, precision_digits=2) == 0)

    def action_split_expense(self):
        self.ensure_one()
        expense_split = self.expense_split_line_ids[0]
        copied_expenses = self.env["hr.expense"]
        if expense_split:
            self.expense_id.write(expense_split._get_values())

            self.expense_split_line_ids -= expense_split
            if self.expense_split_line_ids:
                for split in self.expense_split_line_ids:
                    copied_expenses |= self.expense_id.copy(split._get_values())

                attachment_ids = self.env['ir.attachment'].search([
                    ('res_model', '=', 'hr.expense'),
                    ('res_id', '=', self.expense_id.id)
                ])

                for coplied_expense in copied_expenses:
                    for attachment in attachment_ids:
                        attachment.copy({'res_model': 'hr.expense', 'res_id': coplied_expense.id})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.expense',
            'name': _('Split Expenses'),
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('id', 'in', (copied_expenses | self.expense_split_line_ids.expense_id).ids)],
        }
