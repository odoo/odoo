from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    fiscalyear_last_day = fields.Integer(
        related="company_id.account_config_id.fiscalyear_last_day",
        readonly=False,
        required=True,
    )
    fiscalyear_last_month = fields.Selection(
        related="company_id.account_config_id.fiscalyear_last_month",
        readonly=False,
        required=True,
    )
    use_anglo_saxon = fields.Boolean(
        related="company_id.account_config_id.anglo_saxon_accounting",
        string="Anglo-Saxon Accounting",
        readonly=False,
    )
    invoicing_switch_threshold = fields.Date(
        related="company_id.account_config_id.invoicing_switch_threshold",
        string="Invoicing Switch Threshold",
        readonly=False,
    )
    group_fiscal_year = fields.Boolean(
        string="Fiscal Years",
        implied_group="account.group_fiscal_year",
    )
    predict_bill_product = fields.Boolean(
        related="company_id.account_config_id.predict_bill_product",
        string="Predict Bill Product",
        readonly=False,
    )

    sign_invoice = fields.Boolean(
        related="company_id.account_config_id.sign_invoice",
        string="Authorized Signatory on invoice",
        readonly=False,
    )
    signing_user = fields.Many2one(
        comodel_name="res.users",
        related="company_id.account_config_id.signing_user",
        string="Signature used to sign all the invoice",
        readonly=False,
        help="Select a user here to override every signature on invoice by this user's signature",
    )
    module_sign = fields.Boolean(
        string="Sign",
        compute="_compute_module_sign",
    )

    deferred_expense_journal_id = fields.Many2one(
        comodel_name="account.journal",
        related="company_id.account_config_id.deferred_expense_journal_id",
        readonly=False,
        help="Journal used for deferred entries",
    )
    deferred_expense_account_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.account_config_id.deferred_expense_account_id",
        readonly=False,
        help="Account used for deferred expenses",
    )
    generate_deferred_expense_entries_method = fields.Selection(
        related="company_id.account_config_id.generate_deferred_expense_entries_method",
        readonly=False,
        required=True,
        help="Method used to generate deferred entries",
    )
    deferred_expense_amount_computation_method = fields.Selection(
        related="company_id.account_config_id.deferred_expense_amount_computation_method",
        readonly=False,
        required=True,
        help="Method used to compute the amount of deferred entries",
    )

    deferred_revenue_journal_id = fields.Many2one(
        comodel_name="account.journal",
        related="company_id.account_config_id.deferred_revenue_journal_id",
        readonly=False,
        help="Journal used for deferred entries",
    )
    deferred_revenue_account_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.account_config_id.deferred_revenue_account_id",
        readonly=False,
        help="Account used for deferred revenues",
    )
    generate_deferred_revenue_entries_method = fields.Selection(
        related="company_id.account_config_id.generate_deferred_revenue_entries_method",
        readonly=False,
        required=True,
        help="Method used to generate deferred entries",
    )
    deferred_revenue_amount_computation_method = fields.Selection(
        related="company_id.account_config_id.deferred_revenue_amount_computation_method",
        readonly=False,
        required=True,
        help="Method used to compute the amount of deferred entries",
    )

    module_account_auto_transfer = fields.Boolean(string="Enable Auto Transfer")

    @api.depends("sign_invoice")
    def _compute_module_sign(self):
        sign_installed = (
            "sign" in self.env["ir.module.module"]._get_installed_module_ids()
        )
        for settings in self:
            settings.module_sign = (
                sign_installed or settings.company_id.account_config_id.sign_invoice
            )

    @api.constrains("fiscalyear_last_day", "fiscalyear_last_month")
    @_debug.perf.timed
    def _check_fiscalyear(self):
        for wiz in self:
            try:
                date(2020, int(wiz.fiscalyear_last_month), wiz.fiscalyear_last_day)
            except ValueError as e:
                raise ValidationError(
                    _(
                        "Incorrect fiscal year date: day is out of range for month. Month: %(month)s; Day: %(day)s",
                        month=wiz.fiscalyear_last_month,
                        day=wiz.fiscalyear_last_day,
                    ),
                ) from e

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
            fiscalyear_last_day = (
                vals.pop("fiscalyear_last_day", False)
                or self.env.company.account_config_id.fiscalyear_last_day
            )
            fiscalyear_last_month = (
                vals.pop("fiscalyear_last_month", False)
                or self.env.company.account_config_id.fiscalyear_last_month
            )
            vals = {}
            if (
                fiscalyear_last_day
                != self.env.company.account_config_id.fiscalyear_last_day
            ):
                vals["fiscalyear_last_day"] = fiscalyear_last_day
            if (
                fiscalyear_last_month
                != self.env.company.account_config_id.fiscalyear_last_month
            ):
                vals["fiscalyear_last_month"] = fiscalyear_last_month
            if vals:
                _debug.logic(
                    "company_fiscalyear_updated",
                    company=self.env.company,
                    day_changed="fiscalyear_last_day" in vals,
                    month_changed="fiscalyear_last_month" in vals,
                )
                self.env.company.write(vals)
        return super().create(vals_list)
