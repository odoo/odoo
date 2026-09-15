from datetime import date, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountFinancialYearOp(models.TransientModel):
    _name = "account.financial.year.op"
    _description = "Opening Balance of Financial Year"

    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
    )
    opening_move_posted = fields.Boolean(compute="_compute_opening_move_posted")
    opening_date = fields.Date(
        related="company_id.account_opening_date",
        string="Opening Date",
        readonly=False,
        required=True,
        help="Date from which the accounting is managed in Odoo. It is the date of the opening entry.",
    )
    fiscalyear_last_day = fields.Integer(
        related="company_id.fiscalyear_last_day",
        readonly=False,
        required=True,
        help="The last day of the month will be used if the chosen day doesn't exist.",
    )
    fiscalyear_last_month = fields.Selection(
        related="company_id.fiscalyear_last_month",
        readonly=False,
        required=True,
        help="The last day of the month will be used if the chosen day doesn't exist.",
    )

    @api.depends("company_id.account_opening_move_id")
    def _compute_opening_move_posted(self):
        for record in self:
            record.opening_move_posted = record.company_id.opening_move_posted()

    @api.constrains("fiscalyear_last_day", "fiscalyear_last_month")
    @_debug.perf.timed
    def _check_fiscalyear(self):
        for wiz in self:
            try:
                date(2020, int(wiz.fiscalyear_last_month), wiz.fiscalyear_last_day)
            except ValueError as err:
                raise ValidationError(
                    _(
                        "Incorrect fiscal year date: day is out of range for month. Month: %(month)s; Day: %(day)s",
                        month=wiz.fiscalyear_last_month,
                        day=wiz.fiscalyear_last_day,
                    )
                ) from err

    @api.model
    def _company_fields_to_update(self):
        return {"fiscalyear_last_day", "fiscalyear_last_month", "opening_date"}

    @api.model
    def _update_company(self, company_id, vals):
        company_fields_to_update = {k: k for k in self._company_fields_to_update()}
        company_fields_to_update["opening_date"] = "account_opening_date"
        company_id.write(
            {
                company_field: vals[wizard_field]
                for wizard_field, company_field in company_fields_to_update.items()
                if wizard_field in vals
            }
        )
        opening_date = vals.get("opening_date", company_id.account_opening_date)
        opening_move = company_id.account_opening_move_id
        if opening_date and opening_move.state == "draft":
            opening_move.write(
                {
                    "date": fields.Date.from_string(opening_date) - timedelta(days=1),
                }
            )

    @api.model_create_multi
    @_debug.perf.timed
    def create(self, vals_list):
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "create",
                model=self._name,
                count=len(vals_list),
                fields=sorted({key for vals in vals_list for key in vals}),
            )
        for vals in vals_list:
            if "company_id" in vals:
                company = self.env["res.company"].browse(vals["company_id"])
                _debug.logic("setup_company_fields_forwarded", company=company)
                self._update_company(company, vals)

                for key in self._company_fields_to_update():
                    vals.pop(key, None)

        return super().create(vals_list)

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        for wiz in self:
            wiz._update_company(wiz.company_id, vals)

        for key in self._company_fields_to_update():
            vals.pop(key, None)

        return super().write(vals)

    @_debug.perf.timed
    def action_save_onboarding_fiscal_year(self):
        _debug.lifecycle("action_save_onboarding_fiscal_year", records=self)
        step_state = (
            self.env["onboarding.onboarding.step"]
            .with_company(self.company_id)
            .action_validate_step("account.onboarding_onboarding_step_fiscal_year")
        )
        if step_state == "JUST_DONE":
            self.env.ref(
                "account.onboarding_onboarding_account_dashboard"
            )._prepare_rendering_values()
        return {"type": "ir.actions.client", "tag": "soft_reload"}


class AccountSetupBankManualConfig(models.TransientModel):
    _name = "account.setup.bank.manual.config"
    _inherits = {"res.partner.bank": "res_partner_bank_id"}
    _description = "Bank setup manual config"
    _check_company_auto = True

    res_partner_bank_id = fields.Many2one(
        comodel_name="res.partner.bank",
        required=True,
        ondelete="cascade",
    )
    new_journal_name = fields.Char(
        inverse="_inverse_linked_journal",
        default=lambda self: self.linked_journal_id.name,
        required=True,
        help="Will be used to name the Journal related to this bank account",
    )
    linked_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        compute="_compute_linked_journal_id",
        inverse="_inverse_linked_journal",
        check_company=True,
    )
    bank_bic = fields.Char(
        related="bank_id.bic",
        string="Bic",
        readonly=False,
    )
    num_journals_without_account_bank = fields.Integer(
        default=lambda self: self._number_unlinked_journal("bank")
    )
    num_journals_without_account_credit = fields.Integer(
        default=lambda self: self._number_unlinked_journal("credit")
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
        required=True,
    )

    def _number_unlinked_journal(self, journal_type):
        return self.env["account.journal"].search_count(
            [
                *self._get_domain_unlinked_journal(journal_type),
                ("id", "!=", self.default_linked_journal_id(journal_type)),
            ]
        )

    def _get_domain_unlinked_journal(self, journal_type):
        return [
            *self.env["account.journal"]._check_company_domain(self.env.company),
            ("type", "=", journal_type),
            ("bank_account_id", "=", False),
        ]

    @api.onchange("acc_number")
    def _onchange_acc_number(self):
        for record in self:
            record.new_journal_name = record.acc_number

    @api.model_create_multi
    @_debug.perf.timed
    def create(self, vals_list):
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "create",
                model=self._name,
                count=len(vals_list),
                fields=sorted({key for vals in vals_list for key in vals}),
            )
        wanted_bics = {
            vals["bank_bic"]
            for vals in vals_list
            if not vals.get("bank_id") and vals.get("bank_bic")
        }
        bank_by_bic = {
            bank.bic: bank
            for bank in self.env["res.bank"].search([("bic", "in", list(wanted_bics))])
        }
        _debug.pipeline(
            "setup_banks_resolved",
            wanted_bics=len(wanted_bics),
            found=len(bank_by_bic),
            to_create=len(wanted_bics) - len(bank_by_bic),
        )
        for bic in wanted_bics - bank_by_bic.keys():
            bank_by_bic[bic] = self.env["res.bank"].create({"name": bic, "bic": bic})

        for vals in vals_list:
            vals["partner_id"] = self.env.company.partner_id.id
            vals["new_journal_name"] = vals["acc_number"]

            if not vals.get("bank_id") and vals.get("bank_bic"):
                vals["bank_id"] = bank_by_bic[vals["bank_bic"]].id

        return super().create(vals_list)

    @api.onchange("linked_journal_id")
    def _onchange_new_journal_related_data(self):
        for record in self:
            if record.linked_journal_id:
                record.new_journal_name = record.linked_journal_id.name

    @api.depends("journal_id")
    def _compute_linked_journal_id(self):
        journal_type = self.env.context.get("journal_type", "bank")
        for record in self:
            record.linked_journal_id = (
                record.journal_id and record.journal_id[0]
            ) or record.default_linked_journal_id(journal_type)

    def default_linked_journal_id(self, journal_type):
        candidates = self.env["account.journal"].search(
            self._get_domain_unlinked_journal(journal_type)
        )
        if not candidates:
            return False
        journals_with_moves = [
            journal.id
            for [journal] in self.env["account.move"]._read_group(
                [("journal_id", "in", candidates.ids)], groupby=["journal_id"]
            )
        ]
        return next(
            (j.id for j in candidates if j.id not in journals_with_moves), False
        )

    @_debug.perf.timed
    def _inverse_linked_journal(self):
        journal_type = self.env.context.get("journal_type", "bank")
        for record in self:
            selected_journal = record.linked_journal_id
            if not selected_journal:
                new_journal_code = self.env[
                    "account.journal"
                ]._get_next_journal_default_code(journal_type, self.env.company)
                company = self.env.company
                record.linked_journal_id = self.env["account.journal"].create(
                    {
                        "name": record.new_journal_name,
                        "code": new_journal_code,
                        "type": journal_type,
                        "company_id": company.id,
                        "bank_account_id": record.res_partner_bank_id.id,
                        "bank_statements_source": "undefined",
                    }
                )
            else:
                selected_journal.bank_account_id = record.res_partner_bank_id.id
                selected_journal.name = record.new_journal_name

    def action_finish_bank_setup(self):
        return {"type": "ir.actions.client", "tag": "soft_reload"}

    @api.depends_context("company")
    def _compute_company_id(self):
        for wizard in self:
            wizard.company_id = self.env.company
