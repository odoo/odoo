from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountFiscalYear(models.Model):
    _name = "account.fiscal.year"
    _description = "Fiscal Year"
    _order = "date_from desc"

    name = fields.Char(required=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    active = fields.Boolean(default=True)

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for fiscal_year in self:
            if fiscal_year.date_from and fiscal_year.date_to and fiscal_year.date_from >= fiscal_year.date_to:
                raise ValidationError("Fiscal year start date must be before end date.")

    @api.constrains("date_from", "date_to", "company_id")
    def _check_overlapping(self):
        for fiscal_year in self:
            if not fiscal_year.date_from or not fiscal_year.date_to or not fiscal_year.company_id:
                continue
            overlapping_domain = [
                ("id", "!=", fiscal_year.id),
                ("company_id", "=", fiscal_year.company_id.id),
                ("date_from", "<=", fiscal_year.date_to),
                ("date_to", ">=", fiscal_year.date_from),
            ]
            if self.search_count(overlapping_domain):
                raise ValidationError(
                    "Fiscal years cannot overlap for the same company."
                )

    @api.model
    def find_daterange_fy(self, dt):
        date_value = fields.Date.to_date(dt) if dt else fields.Date.context_today(self)
        return self.search(
            [
                ("company_id", "=", self.env.company.id),
                ("date_from", "<=", date_value),
                ("date_to", ">=", date_value),
                ("active", "=", True),
            ],
            order="date_from desc",
            limit=1,
        )

    def get_gov_closure_status(self):
        self.ensure_one()
        company = self.company_id
        date_to = self.date_to
        fiscal_lock_date = company.fiscalyear_lock_date
        fiscal_lock_satisfied = bool(fiscal_lock_date and date_to and fiscal_lock_date >= date_to)

        journal_model = self.env["account.journal"].with_company(company)
        journal_lock_supported = hasattr(journal_model, "_get_journal_lock_date")
        journals = journal_model.search([("company_id", "=", company.id)])

        effective_locked_journals = journals.browse()
        if journal_lock_supported and date_to:
            effective_locked_journals = journals.filtered(
                lambda journal: journal._get_journal_lock_date()
                and journal._get_journal_lock_date() >= date_to
            )

        public_accounting_enabled = bool(getattr(company, "gov_public_accounting_enabled", False))
        journal_lock_complete = (
            fiscal_lock_satisfied
            if not journals
            else len(effective_locked_journals) == len(journals)
        )
        reporting_ready = bool(
            public_accounting_enabled and fiscal_lock_satisfied and journal_lock_complete
        )

        return {
            "company_id": company.id,
            "fiscal_year_id": self.id,
            "date_from": self.date_from,
            "date_to": date_to,
            "public_accounting_enabled": public_accounting_enabled,
            "fiscal_lock_date": fiscal_lock_date,
            "fiscal_lock_satisfied": fiscal_lock_satisfied,
            "journal_lock_supported": journal_lock_supported,
            "journal_count": len(journals),
            "journal_locked_count": len(effective_locked_journals),
            "journal_lock_complete": journal_lock_complete,
            "reporting_ready": reporting_ready,
        }

    def is_gov_reporting_ready(self):
        self.ensure_one()
        return bool(self.get_gov_closure_status()["reporting_ready"])
