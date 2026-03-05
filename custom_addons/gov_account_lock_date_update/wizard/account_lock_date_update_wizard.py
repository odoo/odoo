import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountLockDateUpdateWizard(models.TransientModel):
    _name = "account.lock.date.update.wizard"
    _description = "Account Lock Date Update Wizard"

    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    current_lock_date = fields.Date(
        related="company_id.fiscalyear_lock_date",
        readonly=True,
    )
    new_lock_date = fields.Date(required=True)
    suggested_date = fields.Date(compute="_compute_suggested_date")
    note = fields.Text(required=True)
    fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        domain="[('company_id', '=', company_id)]",
    )

    def _ensure_manager(self):
        if not self.env.user.has_group(
            "gov_account_lock_date_update.group_account_lock_date_manager"
        ):
            raise UserError("You are not allowed to update lock dates.")

    @api.depends("company_id")
    def _compute_suggested_date(self):
        today = fields.Date.context_today(self)
        for wizard in self:
            if not wizard.company_id:
                wizard.suggested_date = False
                continue

            fiscal_year_model = self.env["account.fiscal.year"].with_company(wizard.company_id)
            # Contract hook: resolve the fiscal year containing today's date.
            fiscal_year_model.find_daterange_fy(today)

            previous_fy = fiscal_year_model.search(
                [
                    ("company_id", "=", wizard.company_id.id),
                    ("date_to", "<", today),
                    ("active", "=", True),
                ],
                order="date_to desc",
                limit=1,
            )
            wizard.suggested_date = previous_fy.date_to if previous_fy else False
            if previous_fy and not wizard.fiscal_year_id:
                wizard.fiscal_year_id = previous_fy

    @api.constrains("new_lock_date", "current_lock_date")
    def _check_new_lock_date(self):
        for wizard in self:
            if (
                wizard.new_lock_date
                and wizard.current_lock_date
                and wizard.new_lock_date < wizard.current_lock_date
            ):
                raise UserError(
                    "New lock date cannot be earlier than the current lock date."
                )

    # -- GOV INTEGRATION NOTE ----------------------------------
    # Lock date application can be wired to gov.processo
    # workflow phase advancement via base_automation rules.
    # Suggested trigger: when account.lock.date.log record
    # is created with lock_date_new matching fiscal year end,
    # fire automation rule 'period_closed' event.
    # No hard dependency on gov_processos required.
    # -----------------------------------------------------------
    def action_apply(self):
        self.ensure_one()
        self._ensure_manager()

        old_lock_date = self.company_id.fiscalyear_lock_date
        self.company_id.sudo().write({"fiscalyear_lock_date": self.new_lock_date})
        self.env["account.lock.date.log"].sudo().create(
            {
                "company_id": self.company_id.id,
                "user_id": self.env.user.id,
                "date_applied": fields.Datetime.now(),
                "lock_date_old": old_lock_date,
                "lock_date_new": self.new_lock_date,
                "note": self.note,
            }
        )
        return {"type": "ir.actions.act_window_close"}

    def action_apply_and_lock_journals(self):
        self.ensure_one()
        result = self.action_apply()

        try:
            journal_model = self.env["account.journal"].with_company(self.company_id)
            if "journal_lock_date" in journal_model._fields:
                journals = journal_model.search([("company_id", "=", self.company_id.id)])
                journals.write(
                    {
                        "journal_lock_date": self.new_lock_date,
                        "lock_date_note": self.note,
                    }
                )
        except Exception:
            _logger.exception(
                "account_lock_date_update: failed to propagate journal lock dates"
            )
        return result


