from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrExpensePostWizard(models.TransientModel):
    _name = "hr.expense.post.wizard"
    _description = "Expense Posting Wizard"

    @api.model
    def _default_employee_journal_id(self):
        company_journal_id = self.env.company.expense_journal_id
        if company_journal_id:
            _debug.logic("post_journal", by="company", journal=company_journal_id)
            return company_journal_id.id
        closest_parent_company_journal = self.env.company.parent_ids[
            ::-1
        ].expense_journal_id[:1]
        if closest_parent_company_journal:
            _debug.logic(
                "post_journal",
                by="parent_company",
                journal=closest_parent_company_journal,
            )
            return closest_parent_company_journal.id

        journal = self.env["account.journal"].search(
            [
                *self.env["account.journal"]._check_company_domain(self.env.company.id),
                ("type", "=", "purchase"),
            ],
            limit=1,
        )
        _debug.logic("post_journal", by="first_purchase", journal=journal)
        return journal.id

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        readonly=True,
    )

    accounting_date = fields.Date(
        default=fields.Date.context_today,
        help="Specify the bill date of the related vendor bill.",
    )
    employee_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        default=_default_employee_journal_id,
        domain=[("type", "=", "purchase")],
        check_company=True,
        help="The journal used when the expense is paid by employee.",
    )

    def action_post_entry(self):
        expenses = self.env["hr.expense"].browse(self.env.context["active_ids"])
        if not self.env["account.move"].has_access("create"):
            _debug.logic("post_entry_refused", reason="no_move_create_access")
            raise UserError(
                _("You don't have the rights to create accounting entries.")
            )
        expense_receipt_vals_list = [
            {
                **new_receipt_vals,
                "journal_id": self.employee_journal_id.id,
                "invoice_date": self.accounting_date,
            }
            for new_receipt_vals in expenses._prepare_receipts_vals()
        ]
        moves_sudo = self.env["account.move"].sudo().create(expense_receipt_vals_list)
        _debug.lifecycle(
            "post_entry_moves_created",
            expenses=expenses,
            moves=moves_sudo,
            journal=self.employee_journal_id,
            accounting_date=self.accounting_date,
        )
        for move_sudo in moves_sudo:
            move_sudo._message_set_main_attachment_id(
                move_sudo.attachment_ids, force=True, filter_xml=False
            )
        moves_sudo.action_post()

        if not self.company_id.expense_journal_id:
            _debug.lifecycle(
                "company_expense_journal_set",
                company=self.company_id,
                journal=self.employee_journal_id,
            )
            self.sudo().company_id.expense_journal_id = self.employee_journal_id.id

        moves_ids = moves_sudo.ids + self.env.context.get("company_paid_move_ids", ())

        action = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
        }
        if len(moves_ids) == 1:
            action.update(
                {
                    "name": moves_sudo.ref,
                    "view_mode": "form",
                    "res_id": moves_ids[0],
                }
            )
        else:
            list_view = self.env.ref(
                "hr_expense.view_move_list_expense", raise_if_not_found=False
            )
            action.update(
                {
                    "name": _("New expense entries"),
                    "view_mode": "list,form",
                    "views": [(list_view and list_view.id, "list"), (False, "form")],
                    "domain": [("id", "in", moves_ids)],
                }
            )
        return action
