# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import SQL


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    expense_id = fields.Many2one('hr.expense', string='Expense', copy=True, index='btree_not_null')  # copy=True, else we don't know price is tax incl.

    @api.constrains('account_id', 'display_type')
    def _check_payable_receivable(self):
        super(AccountMoveLine, self.filtered(lambda line: line.expense_id.payment_mode != 'company_account'))._check_payable_receivable()

    def _get_attachment_domains(self):
        attachment_domains = super(AccountMoveLine, self)._get_attachment_domains()
        if self.expense_id:
            attachment_domains.append([('res_model', '=', 'hr.expense'), ('res_id', 'in', self.expense_id.ids)])
        return attachment_domains

    @api.model
    def _get_attachment_by_record(self, id_model2attachments, move_line):
        return (
            super()._get_attachment_by_record(id_model2attachments, move_line)
            or id_model2attachments.get(('hr.expense', move_line.expense_id.id))
        )

    def _compute_totals(self):
        expenses = self.filtered('expense_id')
        super(AccountMoveLine, expenses.with_context(force_price_include=True))._compute_totals()
        super(AccountMoveLine, self - expenses)._compute_totals()

    def _get_extra_query_base_tax_line_mapping(self) -> SQL:
        return SQL(' AND (base_line.expense_id IS NULL OR account_move_line.expense_id = base_line.expense_id)')
