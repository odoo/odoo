from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    account_representative_id = fields.Many2one(
        related="account_config_id.account_representative_id",
        readonly=False,
    )
    account_display_representative_field = fields.Boolean(
        related="account_config_id.account_display_representative_field"
    )

    def _get_countries_allowing_tax_representative(self):
        return set()

    @_debug.perf.timed
    def _get_tax_closing_journal(self):
        if not self.account_config_id.account_tax_return_journal_id:
            closing_journal = self.env["account.journal"]
            for company in reversed(self.sudo().parent_ids):
                if journal := company.account_config_id.account_tax_return_journal_id:
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
                    chart=self.account_config_id.chart_template,
                )
                ChartTemplate = self.env["account.chart.template"].with_company(self)
                ChartTemplate._load_data(
                    {
                        "account.journal": ChartTemplate._get_account_reports_journal(
                            self.account_config_id.chart_template
                        ),
                        "res.company": ChartTemplate._get_account_reports_res_company(
                            self.account_config_id.chart_template
                        ),
                    }
                )
                closing_journal = ChartTemplate.ref("tax_returns")
            _debug.logic(
                "tax_closing_journal_resolved",
                company=self,
                journal=closing_journal,
            )
            self.account_config_id.account_tax_return_journal_id = closing_journal

        return self.account_config_id.account_tax_return_journal_id

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

    def write(self, vals):
        companies = self.exists()
        root_companies_before = companies.root_id
        res = super().write(vals)
        if (
            set(vals) & {"child_ids", "parent_id"}
            and self.account_config_id.account_opening_date
        ):
            self.env["account.return.type"]._sync_all_returns(
                root_companies_before | companies.root_id
            )
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
