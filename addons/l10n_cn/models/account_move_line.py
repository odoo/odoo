from odoo import fields, models

from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_cn_output_vat_offset_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Output VAT Offset Account",
        default=lambda self: self.env.company.l10n_cn_output_vat_offset_account_id,
        domain="[('account_type', '=', 'liability_current')]",
    )
    l10n_cn_expense_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Expense Account",
    )
    l10n_cn_balance_deduction_ids = fields.One2many(
        comodel_name='l10n_cn.balance.deduction',
        inverse_name='move_line_id',
    )

    def action_open_l10n_cn_balance_deduction(self):
        return {
            'name': self.env._('Balance Deduction'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'form',
            'view_id': self.env.ref('l10n_cn.view_move_line_form_balance_deduction').id,
            'res_id': self.id,
            'target': 'new',
        }

    def write(self, vals):
        res = super().write(vals)
        for line in self.filtered(lambda line: line.move_id.country_code == 'CN' and line.move_id.l10n_cn_differential_taxation_method == '02'):
            deducted_amount = sum(line.l10n_cn_balance_deduction_ids.mapped('deduct_amount'))
            if deducted_amount > line.price_total:
                raise ValidationError(self.env._("The sum of all balance deductions cannot exceed the invoice line amount."))

        return res
