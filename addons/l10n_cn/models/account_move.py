# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, fields, models, _
from odoo.exceptions import ValidationError
from odoo.fields import Domain

try:
    from cn2an import an2cn
except ImportError:
    an2cn = None


class AccountMove(models.Model):
    _inherit = 'account.move'

    fapiao = fields.Char(string='Fapiao Number', copy=False, tracking=True)
    l10n_cn_differential_taxation_method = fields.Selection(
        selection=[
            ('01', 'Full Amount Fapiao'),
            ('02', 'Net Amount Fapiao')
        ],
        string="VAT Differential Taxation",
    )
    l10n_cn_output_vat_offset_move_id = fields.Many2one(
        string="Output VAT Offset Move",
        comodel_name='account.move',
        copy=False,
    )

    @api.constrains('fapiao')
    def _check_fapiao(self):
        for record in self:
            if record.fapiao and not record.fapiao.isdecimal():
                raise ValidationError(_("Please enter a correct fapiao number."))

    @api.model
    def check_cn2an(self):
        return an2cn

    @api.model
    def _convert_to_amount_in_word(self, number):
        """Convert number to ``amount in words`` for Chinese financial usage."""
        if not self.check_cn2an():
            return None
        return an2cn(number, 'rmb')

    def _count_attachments(self):
        domains = [[('res_model', '=', 'account.move'), ('res_id', '=', self.id)]]
        statement_ids = self.line_ids.mapped('statement_id')
        payment_ids = self.line_ids.mapped('payment_id')
        if statement_ids:
            domains.append([('res_model', '=', 'account.bank.statement'), ('res_id', 'in', statement_ids.ids)])
        if payment_ids:
            domains.append([('res_model', '=', 'account.payment'), ('res_id', 'in', payment_ids.ids)])
        return self.env['ir.attachment'].search_count(Domain.OR(domains))

    def _post(self, soft=True):
        entry_to_create = {}

        cn_moves = self.filtered(lambda move: move.country_code == 'CN' and move.l10n_cn_differential_taxation_method == '02')
        journal_id = self.company_id.l10n_cn_output_vat_offset_journal_id
        if cn_moves and not (journal_id and journal_id.active):
            raise ValidationError(self.env._("No active 'Output VAT Offset Journal' is configured. Please select an active journal in the settings before confirming the invoice."))

        for move in cn_moves:
            line_vals = []
            for line in move.invoice_line_ids:
                if len(line.tax_ids) != 1 or line.tax_ids.amount_type != 'percent' or not line.tax_ids.amount:
                    raise ValidationError(self.env._("Each invoice line must have one and only one non-zero rate tax with a percentage computation type."))
                if not line.l10n_cn_balance_deduction_ids:
                    raise ValidationError(self.env._("Please provide Balance Deduction Information for all applicable invoice lines before confirming the invoice."))

                tax_amount = line.tax_ids[0].amount / 100
                deducted_amount = sum(line.l10n_cn_balance_deduction_ids.mapped('deduct_amount'))
                balance = (deducted_amount / (1 + tax_amount)) * tax_amount

                is_credit_note = move.move_type == 'out_refund'
                debit_amount = 0 if is_credit_note else balance
                credit_amount = balance if is_credit_note else 0

                line_vals.extend([
                    move._prepare_l10n_cn_output_vat_offset_line_vals(line.name, line.l10n_cn_output_vat_offset_account_id, credit=credit_amount, debit=debit_amount),
                    move._prepare_l10n_cn_output_vat_offset_line_vals(line.name, line.l10n_cn_expense_account_id, credit=debit_amount, debit=credit_amount),
                ])

            entry_to_create[move] = line_vals

        res = super()._post(soft=soft)

        if not entry_to_create:
            return res

        for move, line_vals in entry_to_create.items():
            entry = self.env['account.move'].create({
                'journal_id': journal_id.id,
                'move_type': 'entry',
                'currency_id': move.currency_id.id,
                'date': move.date,
                'ref': move.name,
                'line_ids': [
                    Command.create(line_val)
                    for line_val in line_vals
                ],
            })
            move.l10n_cn_output_vat_offset_move_id = entry

            entry._post()

        return res

    def _prepare_l10n_cn_output_vat_offset_line_vals(self, name, account_id, credit, debit):
        """Prepare account move line values for an Output VAT offset journal entry."""
        return {
            'name': name,
            'partner_id': self.partner_id.id,
            'account_id': account_id.id,
            'debit': debit,
            'credit': credit,
            'date': self.date,
            'currency_id': self.currency_id.id,
        }

    def button_draft(self):
        offset_moves = self.mapped("l10n_cn_output_vat_offset_move_id")
        posted_offset_moves = offset_moves.filtered(lambda move: move.state == "posted")
        if posted_offset_moves:
            posted_offset_moves.button_draft()
        if offset_moves:
            offset_moves.unlink()
        return super().button_draft()

    def action_open_l10n_cn_output_vat_offset_entries(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Output VAT Offset Entries"),
            'res_model': 'account.move.line',
            'domain': [('id', 'in', self.l10n_cn_output_vat_offset_move_id.line_ids.ids)],
            'views': [(self.env.ref('account.view_move_line_tree').id, 'list')],
            'context': {
                'expand': True,
            }
        }

    def _reverse_moves(self, default_values_list=None, cancel=False):
        reverse_moves = super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)
        for move, reverse_move in zip(self, reverse_moves):
            for line, reverse_line in zip(move.invoice_line_ids, reverse_move.invoice_line_ids):
                reverse_line.l10n_cn_balance_deduction_ids = [
                    Command.create(vals)
                    for vals in line.l10n_cn_balance_deduction_ids.copy_data()
                ]
        return reverse_moves
