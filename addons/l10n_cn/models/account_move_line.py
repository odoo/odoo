from collections import defaultdict

from odoo import api, Command, fields, models
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_cn_output_vat_offset_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Output VAT Offset Account",
        default=lambda self: self.env.company.l10n_cn_output_vat_offset_account_id,
        domain="[('account_type', '=', 'liability_current')]",
        check_company=True,
    )
    l10n_cn_balance_deduction_ids = fields.One2many(
        string="Balance Deductions",
        comodel_name='l10n_cn.balance.deduction',
        inverse_name='move_line_id',
        check_company=True,
    )
    l10n_cn_output_vat_offset_move_id = fields.Many2one(
        string="Output VAT Offset Entry",
        comodel_name='account.move',
        copy=False,
        check_company=True,
    )
    l10n_cn_differential_taxation_method = fields.Selection(
        related='move_id.l10n_cn_differential_taxation_method',
    )

    @api.constrains('l10n_cn_balance_deduction_ids', 'price_total')
    def _check_l10n_cn_balance_deduction_amount(self):
        for line in self.filtered(
            lambda line: (
                line.move_id.country_code == 'CN'
                and line.l10n_cn_differential_taxation_method
            ),
        ):
            deducted_amount = sum(line.l10n_cn_balance_deduction_ids.mapped('deduct_amount'))
            if deducted_amount > line.price_total:
                raise ValidationError(self.env._("The sum of all balance deductions cannot exceed the invoice line amount."))

    def action_open_l10n_cn_balance_deduction(self):
        self.ensure_one()

        return self._get_records_action(
            name=self.env._('Balance Deduction'),
            views=[(self.env.ref('l10n_cn.view_move_line_form_balance_deduction').id, 'form')],
            target='new',
        )

    def action_reset_balance_deduction_to_draft(self):
        """Reset balance deduction information to draft for full-amount differential taxation (method '01').

        Reverses and reconciles the linked Output VAT offset move—preserving the audit
        trail—and clears the offset move reference.
        """
        self.ensure_one()

        if self.l10n_cn_differential_taxation_method != '01':
            return None

        offset_move = self.l10n_cn_output_vat_offset_move_id
        offset_move._reverse_moves(
            default_values_list=[{
                'ref': self.env._("Reversal of: %s", offset_move.name),
                'l10n_cn_output_vat_offset_origin_id': self.move_id.id,
            }],
            cancel=True,
        )
        self.l10n_cn_output_vat_offset_move_id = False
        return self.action_open_l10n_cn_balance_deduction()

    def action_save_l10n_cn_balance_deduction(self):
        """Save balance deduction details and generate the Output VAT offset move if the invoice is already posted.

        For full-amount differential taxation (method '01'), creating or updating balance deduction info
        on a posted invoice automatically creates and posts the corresponding Output VAT offset move.
        """
        self.ensure_one()

        if (
            self.move_id.state == 'posted'
            and not self.l10n_cn_output_vat_offset_move_id
            and self.l10n_cn_differential_taxation_method == '01'
            and self.l10n_cn_balance_deduction_ids
        ):
            offset_move = self.env['account.move'].create(
                self._prepare_l10n_cn_output_vat_offset_move_vals(),
            )
            offset_move.action_post()

    def _copy_data_extend_business_fields(self, values):
        super()._copy_data_extend_business_fields(values)
        values["l10n_cn_balance_deduction_ids"] = [
            Command.create(vals)
            for vals in self.l10n_cn_balance_deduction_ids.copy_data()
        ]

    def _l10n_cn_calculate_total_balance(self):
        account_balances = defaultdict(float)
        total_balance = 0.0

        for deduction in self.l10n_cn_balance_deduction_ids:
            taxes_data = self.tax_ids._get_tax_details(
                deduction.deduct_amount, 1, document_tax_mode='tax_included',
            )['taxes_data']
            balance = sum(tax_data['tax_amount'] for tax_data in taxes_data)
            account_balances[deduction.expense_account_id] += balance
            total_balance += balance

        return account_balances, total_balance

    def _prepare_l10n_cn_output_vat_offset_move_vals(self):
        """Prepare values for an Output VAT Offset Entry."""

        move = self.move_id
        is_credit_note = move.move_type == 'out_refund'
        line_vals = []

        for line in self.filtered(lambda line: line.tax_ids.amount):
            account_balances, total_balance = line._l10n_cn_calculate_total_balance()

            line_vals.append(
                move._prepare_l10n_cn_output_vat_offset_line_vals(
                    line.name,
                    line.l10n_cn_output_vat_offset_account_id,
                    balance=-total_balance if is_credit_note else total_balance,
                ),
            )

            for account, balance in account_balances.items():
                line_vals.append(
                    move._prepare_l10n_cn_output_vat_offset_line_vals(
                        line.name,
                        account,
                        balance=balance if is_credit_note else -balance,
                    ),
                )

        if not line_vals:
            return False

        return {
            'journal_id': move.company_id.l10n_cn_output_vat_offset_journal_id.id,
            'move_type': 'entry',
            'currency_id': move.currency_id.id,
            'date': move.date,
            'ref': move.name,
            'partner_id': move.partner_id.id,
            'l10n_cn_output_vat_offset_origin_id': move.id,
            'l10n_cn_output_vat_offset_origin_line_ids': self.ids,
            'line_ids': [
                Command.create(vals)
                for vals in line_vals
            ],
        }
