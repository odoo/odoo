import datetime

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

from .account_return_type import PERIODS

_debug = DebugLog(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    totals_below_sections = fields.Boolean(
        string="Add totals below sections",
        compute="_compute_totals_below_sections",
        store=True,
        readonly=False,
        help="When ticked, totals and subtotals appear below the sections of the report.",
    )

    account_return_periodicity = fields.Selection(
        selection=PERIODS,
        string="Delay units",
        default="monthly",
        required=True,
        help="Periodicity",
    )
    account_return_reminder_day = fields.Integer(
        string="Start from",
        default=7,
        required=True,
    )
    account_tax_return_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        domain=[("type", "=", "general")],
        check_company=True,
    )
    account_revaluation_journal_id = fields.Many2one(
        comodel_name="account.journal",
        domain=[("type", "=", "general")],
        check_company=True,
    )
    account_revaluation_expense_provision_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Expense Provision Account",
        check_company=True,
    )
    account_revaluation_income_provision_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Income Provision Account",
        check_company=True,
    )
    account_tax_unit_ids = fields.Many2many(
        comodel_name="account.tax.unit",
        string="Tax Units",
        help="The tax units this company belongs to.",
    )
    account_representative_id = fields.Many2one(
        comodel_name="res.partner",
        string="Accounting Firm",
        index="btree_not_null",
        help="Specify an Accounting Firm that will act as a representative when exporting reports.",
    )
    account_display_representative_field = fields.Boolean(
        compute="_compute_account_display_representative_field"
    )
    account_last_return_cron_refresh = fields.Datetime()

    @api.depends("account_fiscal_country_id.code")
    def _compute_account_display_representative_field(self):
        country_set = self._get_countries_allowing_tax_representative()
        for record in self:
            record.account_display_representative_field = (
                record.account_fiscal_country_id.code in country_set
            )

    @api.depends("anglo_saxon_accounting")
    def _compute_totals_below_sections(self):
        for company in self:
            company.totals_below_sections = company.anglo_saxon_accounting

    def _get_countries_allowing_tax_representative(self):
        return set()

    @_debug.perf.timed
    def _get_tax_closing_journal(self):
        if not self.account_tax_return_journal_id:
            closing_journal = self.env["account.journal"]
            for company in reversed(self.sudo().parent_ids):
                if journal := company.account_tax_return_journal_id:
                    closing_journal = journal
                    break
            if not closing_journal:
                closing_journal = (
                    self.env["account.journal"]
                    .sudo()
                    .search(
                        [
                            *self.env["account.journal"]._check_company_domain(self),
                            (
                                "code",
                                "in",
                                ("TAX", "TRTRN"),
                            ),  # TRTRN for Backward compatibility
                            ("type", "=", "general"),
                        ],
                        limit=1,
                    )
                )
            if not closing_journal:
                _debug.logic(
                    "tax_closing_journal_loaded_from_chart",
                    company=self,
                    chart=self.chart_template,
                )
                ChartTemplate = self.env["account.chart.template"].with_company(self)
                ChartTemplate._load_data(
                    {
                        "account.journal": ChartTemplate._get_account_reports_journal(
                            self.chart_template
                        ),
                        "res.company": ChartTemplate._get_account_reports_res_company(
                            self.chart_template
                        ),
                    }
                )
                closing_journal = ChartTemplate.ref("tax_returns")
            _debug.logic(
                "tax_closing_journal_resolved",
                company=self,
                journal=closing_journal,
            )
            self.account_tax_return_journal_id = closing_journal

        return self.account_tax_return_journal_id

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
        companies = super().create(vals_list)
        companies._initiate_account_onboardings()

        self.env["account.return.type"].sudo().search([])._set_default_values(companies)
        self.env["account.return.type"]._sync_all_returns(companies.root_id)
        return companies

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        companies = self.exists()
        root_companies_before = companies.root_id
        res = super().write(vals)

        roots_to_recompute = root_companies_before | companies.root_id
        if "account_opening_date" in vals:
            _debug.logic(
                "returns_sync_decided",
                companies=companies,
                roots=roots_to_recompute,
                reason="opening_date",
            )
            self.env["account.return.type"].with_context(
                # 2 years to make sure we cover all cases, such as yearly returns with a deadline of more than 1 year.
                forced_date_from=self.account_opening_date - relativedelta(years=2),
                forced_date_to=datetime.date.today() + relativedelta(years=1),
            )._sync_all_returns(roots_to_recompute)

        elif (
            set(vals)
            & {
                "account_return_periodicity",
                "account_return_reminder_day",
                "child_ids",
                "parent_id",
            }
            and self.account_opening_date
        ):
            _debug.logic(
                "returns_sync_decided",
                companies=companies,
                roots=roots_to_recompute,
                reason="periodicity_or_hierarchy",
            )
            self.env["account.return.type"]._sync_all_returns(roots_to_recompute)

        return res

    def _get_available_tax_units(self, report, limit=None):
        self.check_singleton()
        return self.env["account.tax.unit"].search(
            [
                ("company_ids", "in", self.id),
                ("country_id", "=", report.country_id.id),
            ],
            limit=limit,
        )

    def _get_branches_with_same_vat(self, accessible_only=False):
        self.check_singleton()

        current = self.sudo()
        same_vat_branch_ids = [current.id]  # Current is always available
        current_strict_parents = current.parent_ids - current
        if accessible_only:
            candidate_branches = current.root_id._get_accessible_branches()
        else:
            candidate_branches = (
                self.env["res.company"]
                .sudo()
                .search([("id", "child_of", current.root_id.ids)])
            )

        current_vat_check_set = {current.vat} if current.vat else set()
        for branch in candidate_branches - current:
            parents_vat_set = set(
                filter(None, (branch.parent_ids - current_strict_parents).mapped("vat"))
            )
            if parents_vat_set == current_vat_check_set:
                same_vat_branch_ids.append(branch.id)

        _debug.logic(
            "same_vat_branches_found",
            company=self,
            accessible_only=accessible_only,
            candidates=len(candidate_branches),
            matched=len(same_vat_branch_ids),
        )
        return self.browse(same_vat_branch_ids)
