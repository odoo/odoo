from odoo import _, api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class OnboardingOnboardingStep(models.Model):
    _inherit = "onboarding.onboarding.step"

    @api.model
    @_debug.perf.timed
    def action_view_step_company_data(self):
        _debug.lifecycle("action_view_step_company_data", records=self)
        company = (
            self.env["account.journal"]
            .browse(self.env.context.get("journal_id", None))
            .company_id
            or self.env.company
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Set your company data"),
            "res_model": "res.company",
            "res_id": company.id,
            "views": [
                (self.env.ref("account.res_company_form_view_onboarding").id, "form")
            ],
            "target": "new",
        }

    @api.model
    @_debug.perf.timed
    def action_view_step_base_document_layout(self):
        _debug.lifecycle("action_view_step_base_document_layout", records=self)
        view_id = self.env.ref("web.view_base_document_layout").id
        return {
            "name": _("Configure your document layout"),
            "type": "ir.actions.act_window",
            "res_model": "base.document.layout",
            "target": "new",
            "views": [(view_id, "form")],
            "context": {"dialog_size": "extra-large"},
        }

    @api.model
    @_debug.perf.timed
    def action_validate_step_base_document_layout(self):
        _debug.lifecycle("action_validate_step_base_document_layout", records=self)
        step = self.env.ref(
            "account.onboarding_onboarding_step_base_document_layout",
            raise_if_not_found=False,
        )
        if not step or not self.env.company.external_report_layout_id:
            return False
        return self.action_validate_step(
            "account.onboarding_onboarding_step_base_document_layout"
        )

    @api.model
    @_debug.perf.timed
    def action_view_step_bank_account(self):
        _debug.lifecycle("action_view_step_bank_account", records=self)
        return self.env.company.setting_init_bank_account_action()

    @api.model
    @_debug.perf.timed
    def action_view_step_create_invoice(self):
        _debug.lifecycle("action_view_step_create_invoice", records=self)
        return {
            "type": "ir.actions.act_window",
            "name": _("Create first invoice"),
            "views": [(self.env.ref("account.view_move_form").id, "form")],
            "res_model": "account.move",
            "context": {"default_move_type": "out_invoice"},
        }

    @api.model
    @_debug.perf.timed
    def action_view_step_fiscal_year(self):
        _debug.lifecycle("action_view_step_fiscal_year", records=self)
        company = (
            self.env["account.journal"]
            .browse(self.env.context.get("journal_id", None))
            .company_id
            or self.env.company
        )
        new_wizard = self.env["account.financial.year.op"].create(
            {"company_id": company.id}
        )
        view_id = self.env.ref("account.setup_financial_year_opening_form").id

        return {
            "type": "ir.actions.act_window",
            "name": _("Accounting Periods"),
            "view_mode": "form",
            "res_model": "account.financial.year.op",
            "target": "new",
            "res_id": new_wizard.id,
            "views": [[view_id, "form"]],
            "context": {
                "dialog_size": "medium",
            },
        }

    @api.model
    @_debug.perf.timed
    def action_view_step_chart_of_accounts(self):
        _debug.lifecycle("action_view_step_chart_of_accounts", records=self)
        company = (
            self.env["account.journal"]
            .browse(self.env.context.get("journal_id", None))
            .company_id
            or self.env.company
        )
        self.sudo().with_company(company).action_validate_step(
            "account.onboarding_onboarding_step_chart_of_accounts"
        )

        if company.opening_move_posted():
            return "account.action_account_form"

        view_id = self.env.ref("account.init_accounts_tree").id
        domain = [
            *self.env["account.account"]._check_company_domain(company),
            ("account_type", "!=", "equity_unaffected"),
        ]
        return {
            "type": "ir.actions.act_window",
            "name": _("Chart of Accounts"),
            "res_model": "account.account",
            "view_mode": "list",
            "limit": 99999999,
            "search_view_id": [self.env.ref("account.view_account_search").id],
            "views": [[view_id, "list"], [False, "form"]],
            "domain": domain,
        }

    @api.model
    @_debug.perf.timed
    def action_view_step_sales_tax(self):
        _debug.lifecycle("action_view_step_sales_tax", records=self)
        view_id = self.env.ref("account.res_company_form_view_onboarding_sale_tax").id

        return {
            "type": "ir.actions.act_window",
            "name": _("Sales tax"),
            "res_id": self.env.company.id,
            "res_model": "res.company",
            "target": "new",
            "view_mode": "form",
            "views": [[view_id, "form"]],
        }
