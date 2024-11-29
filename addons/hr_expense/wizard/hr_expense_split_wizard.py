# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class HrExpenseSplitWizard(models.TransientModel):
    _name = 'hr.expense.split.wizard'
    _description = 'Expense Split Wizard'

    expense_id = fields.Many2one(comodel_name='hr.expense', string='Expense', required=True)
    expense_split_line_ids = fields.One2many(comodel_name='hr.expense.split', inverse_name='wizard_id')
    total_amount_currency = fields.Monetary(string='Total Amount', compute='_compute_total_amount_currency', currency_field='currency_id')
    total_amount_currency_original = fields.Monetary(
        string='Total amount original', related='expense_id.total_amount_currency',
        currency_field='currency_id',
        help='Total amount of the original Expense that we are splitting',
    )
    tax_amount_currency = fields.Monetary(
        string='Taxes',
        currency_field='currency_id',
        compute='_compute_tax_amount_currency',
    )
    split_possible = fields.Boolean(help='The sum of after split shut remain the same', compute='_compute_split_possible')
    currency_id = fields.Many2one(comodel_name='res.currency', related='expense_id.currency_id')

    @api.depends('expense_split_line_ids.total_amount_currency')
    def _compute_total_amount_currency(self):
        for wizard in self:
            wizard.total_amount_currency = sum(wizard.expense_split_line_ids.mapped('total_amount_currency'))

    @api.depends('expense_split_line_ids.tax_amount_currency')
    def _compute_tax_amount_currency(self):
        for wizard in self:
            wizard.tax_amount_currency = sum(wizard.expense_split_line_ids.mapped('tax_amount_currency'))

    @api.depends('total_amount_currency_original', 'total_amount_currency')
    def _compute_split_possible(self):
        for wizard in self:
            wizard.split_possible = wizard.total_amount_currency_original \
                    and wizard.currency_id.compare_amounts(wizard.total_amount_currency_original, wizard.total_amount_currency) == 0

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

                for copied_expense in copied_expenses:
                    for attachment in attachment_ids:
                        attachment.copy({'res_model': 'hr.expense', 'res_id': copied_expense.id})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.expense',
            'name': _('Split Expenses'),
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('id', 'in', (copied_expenses | self.expense_split_line_ids.expense_id).ids)],
        }
