from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    expense_id = fields.Many2one(
        comodel_name="hr.expense",
        index="btree_not_null",
        copy=True,
    )

    def _compute_partner_id(self):
        expense_lines = self.filtered("move_id.expense_ids")
        _debug.logic(
            "partner_from_expense_move",
            expense_lines=expense_lines,
            others=self - expense_lines,
        )
        super(AccountMoveLine, self - expense_lines)._compute_partner_id()
        for line in expense_lines:
            line.partner_id = line.move_id.partner_id

    @api.constrains("account_id", "display_type")
    def _check_payable_receivable(self):
        super(
            AccountMoveLine,
            self.filtered(
                lambda line: line.expense_id.payment_mode != "company_account"
            ),
        )._check_payable_receivable()

    def _get_attachment_domains(self):
        attachment_domains = super()._get_attachment_domains()
        if self.expense_id:
            attachment_domains.append(
                [
                    ("res_model", "=", "hr.expense"),
                    ("res_id", "in", self.expense_id.ids),
                ]
            )
        return attachment_domains

    @api.model
    def _get_attachment_by_record(self, id_model2attachments, move_line):
        return super()._get_attachment_by_record(
            id_model2attachments, move_line
        ) or id_model2attachments.get(("hr.expense", move_line.expense_id.id))

    def _compute_totals(self):
        expenses = self.filtered("expense_id")
        super(
            AccountMoveLine, expenses.with_context(force_price_include=True)
        )._compute_totals()
        super(AccountMoveLine, self - expenses)._compute_totals()

    @api.model
    def _get_base_tax_line_mapping_conditions(self) -> list[SQL]:
        return [
            *super()._get_base_tax_line_mapping_conditions(),
            SQL(
                "(base_line.expense_id IS NULL"
                " OR account_move_line.expense_id = base_line.expense_id)"
            ),
        ]
