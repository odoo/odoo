from datetime import timedelta

from odoo import _, api, exceptions, fields, models
from odoo.tools import format_list
from odoo.tools.date_utils import get_timedelta, time_unit_selection


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_use_lead = fields.Boolean(
        string="Leads",
        implied_group="crm.group_use_lead",
    )
    group_use_recurring_revenues = fields.Boolean(
        string="Recurring Revenues",
        implied_group="crm.group_use_recurring_revenues",
    )
    module_partnership = fields.Boolean(string="Membership / Partnership")
    crm_use_auto_assignment = fields.Boolean(
        string="Rule-Based Assignment",
        config_parameter="crm.lead.auto.assignment",
    )
    crm_auto_assignment_action = fields.Selection(
        selection=[("manual", "Manually"), ("auto", "Repeatedly")],
        string="Auto Assignment Action",
        compute="_compute_crm_auto_assignment_data",
        store=True,
        readonly=False,
        help="Manual assign allow to trigger assignment from team form view using an action button. Automatic configures a cron running repeatedly assignment in all teams.",
    )
    crm_auto_assignment_repeat_unit = fields.Selection(
        selection=time_unit_selection("minute", "hour", "day", "week"),
        string="Auto Assignment Interval Unit",
        compute="_compute_crm_auto_assignment_data",
        store=True,
        readonly=False,
        help="Interval type between each cron run (e.g. each 2 days or each 2 hours)",
    )
    crm_auto_assignment_repeat_interval = fields.Integer(
        string="Repeat every",
        compute="_compute_crm_auto_assignment_data",
        store=True,
        readonly=False,
        help="Number of interval type between each cron run (e.g. each 2 days or each 4 days)",
    )
    crm_auto_assignment_run_datetime = fields.Datetime(
        string="Auto Assignment Next Execution Date",
        compute="_compute_crm_auto_assignment_data",
        store=True,
        readonly=False,
    )
    module_crm_iap_mine = fields.Boolean(
        string="Generate new leads based on their country, industries, size, etc."
    )
    module_crm_iap_enrich = fields.Boolean(
        string="Enrich your leads automatically with company data based on their email address."
    )
    module_website_crm_iap_reveal = fields.Boolean(
        string="Create Leads/Opportunities from your website's traffic"
    )
    lead_enrich_auto = fields.Selection(
        selection=[
            ("manual", "Enrich leads on demand only"),
            ("auto", "Enrich all leads automatically"),
        ],
        string="Enrich lead automatically",
        default="auto",
        config_parameter="crm.iap.lead.enrich.setting",
    )
    lead_mining_in_pipeline = fields.Boolean(
        string="Create a lead mining request directly from the opportunity pipeline.",
        config_parameter="crm.lead_mining_in_pipeline",
    )
    predictive_lead_scoring_start_date = fields.Date(
        string="Lead Scoring Starting Date",
        compute="_compute_pls_start_date",
        inverse="_inverse_predictive_lead_scoring_start_date",
    )
    predictive_lead_scoring_start_date_str = fields.Char(
        string="Lead Scoring Starting Date in String",
        config_parameter="crm.pls_start_date",
    )
    predictive_lead_scoring_fields = fields.Many2many(
        comodel_name="crm.lead.scoring.frequency.field",
        string="Lead Scoring Frequency Fields",
        compute="_compute_pls_fields",
        inverse="_inverse_predictive_lead_scoring_fields",
    )
    predictive_lead_scoring_fields_str = fields.Char(
        string="Lead Scoring Frequency Fields in String",
        config_parameter="crm.pls_fields",
    )
    predictive_lead_scoring_field_labels = fields.Char(
        compute="_compute_predictive_lead_scoring_field_labels"
    )

    @api.depends("crm_use_auto_assignment")
    def _compute_crm_auto_assignment_data(self):
        assign_cron = self.sudo().env.ref(
            "crm.ir_cron_crm_lead_assign", raise_if_not_found=False
        )
        for setting in self:
            if setting.crm_use_auto_assignment and assign_cron:
                setting.crm_auto_assignment_action = (
                    "auto" if assign_cron.active else "manual"
                )
                setting.crm_auto_assignment_repeat_unit = (
                    assign_cron.repeat_unit or "day"
                )
                setting.crm_auto_assignment_repeat_interval = (
                    assign_cron.repeat_interval or 1
                )
                setting.crm_auto_assignment_run_datetime = assign_cron.nextcall
            else:
                setting.crm_auto_assignment_action = "manual"
                setting.crm_auto_assignment_repeat_unit = "day"
                setting.crm_auto_assignment_run_datetime = False
                setting.crm_auto_assignment_repeat_interval = 1

    @api.onchange(
        "crm_auto_assignment_repeat_unit", "crm_auto_assignment_repeat_interval"
    )
    def _onchange_crm_auto_assignment_run_datetime(self):
        if self.crm_auto_assignment_repeat_interval <= 0:
            raise exceptions.UserError(_("Repeat frequency should be positive."))
        if self.crm_auto_assignment_repeat_interval >= 100:
            raise exceptions.UserError(
                _(
                    "Invalid repeat frequency. Consider changing frequency type instead of using large numbers."
                )
            )
        self.crm_auto_assignment_run_datetime = (
            self._get_crm_auto_assignmment_run_datetime(
                self.crm_auto_assignment_run_datetime,
                self.crm_auto_assignment_repeat_unit,
                self.crm_auto_assignment_repeat_interval,
            )
        )

    @api.depends("predictive_lead_scoring_fields_str")
    def _compute_pls_fields(self):
        for setting in self:
            if setting.predictive_lead_scoring_fields_str:
                names = setting.predictive_lead_scoring_fields_str.split(",")
                fields = self.env["ir.model.fields"].search(  # noqa: E8507 - a transient settings wizard: one record
                    [("name", "in", names), ("model", "=", "crm.lead")]
                )
                setting.predictive_lead_scoring_fields = self.env[
                    "crm.lead.scoring.frequency.field"
                ].search([("field_id", "in", fields.ids)])  # noqa: E8507 - a transient settings wizard: one record
            else:
                setting.predictive_lead_scoring_fields = None

    def _inverse_predictive_lead_scoring_fields(self):
        for setting in self:
            if setting.predictive_lead_scoring_fields:
                setting.predictive_lead_scoring_fields_str = ",".join(
                    setting.predictive_lead_scoring_fields.mapped("field_id.name")
                )
            else:
                setting.predictive_lead_scoring_fields_str = ""

    @api.depends("predictive_lead_scoring_start_date_str")
    def _compute_pls_start_date(self):
        for setting in self:
            lead_scoring_start_date = setting.predictive_lead_scoring_start_date_str
            if not lead_scoring_start_date:
                setting.predictive_lead_scoring_start_date = fields.Date.to_date(
                    fields.Date.today() - timedelta(days=8)
                )
            else:
                try:
                    setting.predictive_lead_scoring_start_date = fields.Date.to_date(
                        lead_scoring_start_date
                    )
                except ValueError:
                    setting.predictive_lead_scoring_start_date = fields.Date.to_date(
                        fields.Date.today() - timedelta(days=8)
                    )

    def _inverse_predictive_lead_scoring_start_date(self):
        for setting in self:
            if setting.predictive_lead_scoring_start_date:
                setting.predictive_lead_scoring_start_date_str = fields.Date.to_string(
                    setting.predictive_lead_scoring_start_date
                )

    @api.depends("predictive_lead_scoring_fields")
    def _compute_predictive_lead_scoring_field_labels(self):
        for setting in self:
            if setting.predictive_lead_scoring_fields:
                field_names = [_("Stage")] + [
                    field.name for field in setting.predictive_lead_scoring_fields
                ]
                setting.predictive_lead_scoring_field_labels = format_list(
                    self.env, field_names
                )
            else:
                setting.predictive_lead_scoring_field_labels = _("Stage")

    def set_values(self):
        group_use_lead_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "crm.group_use_lead"
        )
        has_group_lead_before = group_use_lead_id in self.env.user.all_group_ids.ids
        super().set_values()
        has_group_lead_after = group_use_lead_id in self.env.user.all_group_ids.ids
        if has_group_lead_before != has_group_lead_after:
            teams = self.env["team.team"].search([("use_sale", "=", True)])
            teams.filtered("use_opportunities").use_leads = has_group_lead_after
            teams._refresh_usage_aliases(["sale"])
        assign_cron = self.sudo().env.ref(
            "crm.ir_cron_crm_lead_assign", raise_if_not_found=False
        )
        if assign_cron:
            cron_vals = {
                "active": self.crm_use_auto_assignment
                and self.crm_auto_assignment_action == "auto",
                "repeat_unit": self.crm_auto_assignment_repeat_unit,
                "repeat_interval": self.crm_auto_assignment_repeat_interval,
                "nextcall": self.crm_auto_assignment_run_datetime
                or assign_cron.nextcall,
            }
            cron_vals = {
                field_name: value
                for field_name, value in cron_vals.items()
                if assign_cron[field_name] != value
            }
            if cron_vals:
                assign_cron.write(cron_vals)

    def _get_crm_auto_assignmment_run_datetime(
        self, run_datetime, run_interval, run_interval_number
    ):
        if not run_interval:
            return False
        if run_interval == "manual":
            return run_datetime or False
        return fields.Datetime.now() + get_timedelta(run_interval_number, run_interval)

    def action_crm_assign_leads(self):
        self.check_singleton()
        return (
            self.env["team.team"]
            .search([("use_sale", "=", True), ("lead_assignment_optout", "=", False)])
            .action_assign_leads()
        )
