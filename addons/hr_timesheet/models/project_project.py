from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import RedirectWarning, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, float_round
from odoo.tools.translate import _

_debug = DebugLog(__name__)


class ProjectProject(models.Model):
    _name = "project.project"
    _inherit = "project.project"

    allow_timesheets = fields.Boolean(
        string="Timesheets",
        compute="_compute_allow_timesheets",
        default=True,
        store=True,
        readonly=False,
    )
    account_id = fields.Many2one(
        domain="""[
            '|', ('company_id', '=', False), ('company_id', '=?', company_id),
            ('partner_id', '=?', partner_id),
        ]"""
    )
    analytic_account_active = fields.Boolean(
        related="account_id.active",
        string="Active Account",
        export_string_translation=False,
    )

    timesheet_ids = fields.One2many(
        comodel_name="account.analytic.line",
        inverse_name="project_id",
        string="Associated Timesheets",
        export_string_translation=False,
    )
    timesheet_encode_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        export_string_translation=False,
        compute="_compute_timesheet_encode_uom_id",
    )
    total_timesheet_time = fields.Float(
        string="Total amount of time (in the proper unit) recorded in the project, rounded to the unit.",
        export_string_translation=False,
        compute="_compute_total_timesheet_time",
        groups="hr_timesheet.group_hr_timesheet_user",
    )
    encode_uom_in_days = fields.Boolean(
        export_string_translation=False,
        compute="_compute_encode_uom_in_days",
    )
    is_internal_project = fields.Boolean(
        export_string_translation=False,
        compute="_compute_is_internal_project",
        search="_search_is_internal_project",
    )
    remaining_hours = fields.Float(
        string="Time Remaining",
        compute="_compute_remaining_hours",
        compute_sudo=True,
    )
    is_project_overtime = fields.Boolean(
        string="Project in Overtime",
        export_string_translation=False,
        compute="_compute_remaining_hours",
        search="_search_is_project_overtime",
        compute_sudo=True,
    )
    allocated_hours = fields.Float(
        string="Allocated Time",
        tracking=True,
    )
    effective_hours = fields.Float(
        string="Time Spent",
        compute="_compute_remaining_hours",
        compute_sudo=True,
    )

    def _compute_encode_uom_in_days(self):
        self.encode_uom_in_days = (
            self.env.company.timesheet_encode_uom_id
            == self.env.ref("uom.product_uom_day")
        )

    @api.depends("company_id", "company_id.timesheet_encode_uom_id")
    @api.depends_context("company")
    def _compute_timesheet_encode_uom_id(self):
        for project in self:
            project.timesheet_encode_uom_id = (
                project.company_id.timesheet_encode_uom_id
                or self.env.company.timesheet_encode_uom_id
            )

    @api.depends("account_id")
    def _compute_allow_timesheets(self):
        without_account = self.filtered(lambda t: t._origin and not t.account_id)
        _debug.logic("timesheets_disabled_no_account", projects=without_account)
        without_account.update({"allow_timesheets": False})

    @api.depends("company_id")
    def _compute_is_internal_project(self):
        for project in self:
            project.is_internal_project = (
                project == project.company_id.internal_project_id
            )

    @api.model
    def _search_is_internal_project(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented

        Company = self.env["res.company"]
        sql = Company._search(
            [("internal_project_id", "!=", False)],
            active_test=False,
            bypass_access=True,
        ).subselect("internal_project_id")
        return [("id", operator, sql)]

    @api.depends("allow_timesheets", "timesheet_ids.unit_amount", "allocated_hours")
    def _compute_remaining_hours(self):
        timesheets_read_group = self.env["account.analytic.line"]._read_group(
            [("project_id", "in", self.ids)],
            ["project_id"],
            ["unit_amount:sum"],
        )
        timesheet_time_dict = {
            project.id: unit_amount_sum
            for project, unit_amount_sum in timesheets_read_group
        }
        _debug.perf.count("remaining_hours_grouped", projects=self)
        for project in self:
            project.effective_hours = round(timesheet_time_dict.get(project.id, 0.0), 2)
            project.remaining_hours = project.allocated_hours - project.effective_hours
            project.is_project_overtime = project.remaining_hours < 0

    @api.model
    def _search_is_project_overtime(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented

        sql = SQL("""(
            SELECT Project.id
              FROM project_project AS Project
              JOIN project_task AS Task
                ON Project.id = Task.project_id
             WHERE Project.allocated_hours > 0
               AND Project.allow_timesheets = TRUE
               AND Task.parent_id IS NULL
               AND Task.state IN ('in_progress', 'changes_requested', 'approved', 'blocked')
          GROUP BY Project.id
            HAVING Project.allocated_hours - SUM(Task.effective_hours) < 0
        )""")
        return [("id", operator, sql)]

    @api.constrains("allow_timesheets", "account_id")
    def _check_allow_timesheet(self):
        for project in self:
            if (
                project.allow_timesheets
                and not project.account_id
                and not project.is_template
            ):
                project_plan, _other_plans = self.env[
                    "account.analytic.plan"
                ]._get_all_plans()
                _debug.logic(
                    "allow_timesheets_refused",
                    reason="no_analytic_account",
                    project=project,
                    plan=project_plan,
                )
                raise ValidationError(
                    _(
                        "To use the timesheets feature, you need an analytic account for your project. Please set one up in the plan '%(plan_name)s' or turn off the timesheets feature.",
                        plan_name=project_plan.name,
                    )
                )

    @api.depends("timesheet_ids", "timesheet_encode_uom_id")
    def _compute_total_timesheet_time(self):
        timesheets_read_group = self.env["account.analytic.line"]._read_group(
            [("project_id", "in", self.ids)],
            ["project_id", "product_uom_id"],
            ["unit_amount:sum"],
        )
        timesheet_time_dict = defaultdict(list)
        for project, product_uom_id, unit_amount_sum in timesheets_read_group:
            timesheet_time_dict[project.id].append((product_uom_id, unit_amount_sum))

        for project in self:
            total_time = 0.0
            for product_uom_id, unit_amount in timesheet_time_dict[project.id]:
                factor = (product_uom_id or project.timesheet_encode_uom_id).factor
                total_time += unit_amount * (
                    1.0 if project.encode_uom_in_days else factor
                )
            total_time /= project.timesheet_encode_uom_id.factor
            project.total_timesheet_time = float_round(total_time, precision_digits=2)

    @api.model_create_multi
    def create(self, vals_list):
        defaults = self.default_get(["allow_timesheets", "account_id", "is_template"])
        analytic_accounts_vals = [
            vals
            for vals in vals_list
            if (
                vals.get("allow_timesheets", defaults.get("allow_timesheets"))
                and not vals.get("account_id", defaults.get("account_id"))
                and not vals.get("is_template", defaults.get("is_template"))
            )
        ]

        if analytic_accounts_vals:
            analytic_accounts = self.env["account.analytic.account"].create(
                self._prepare_analytic_account_vals_list(analytic_accounts_vals)
            )
            _debug.lifecycle(
                "analytic_accounts_created",
                projects=len(vals_list),
                accounts=analytic_accounts,
            )
            for vals, analytic_account in zip(
                analytic_accounts_vals, analytic_accounts, strict=True
            ):
                vals["account_id"] = analytic_account.id
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("allow_timesheets") and not vals.get("account_id"):
            project_wo_account = self.filtered(
                lambda project: not project.account_id and not project.is_template
            )
            if project_wo_account:
                _debug.lifecycle(
                    "analytic_account_created_on_write", projects=project_wo_account
                )
                project_wo_account._create_analytic_account()
        return super().write(vals)

    @api.depends("is_internal_project", "company_id")
    @api.depends_context("allowed_company_ids")
    def _compute_display_name(self):
        super()._compute_display_name()
        if len(self.env.context.get("allowed_company_ids") or []) <= 1:
            return

        for project in self:
            if project.is_internal_project:
                project.display_name = (
                    f"{project.display_name} - {project.company_id.name}"
                )

    @api.model
    def _init_data_analytic_account(self):
        self.search(
            [
                ("account_id", "=", False),
                ("allow_timesheets", "=", True),
                ("is_template", "=", False),
            ]
        )._create_analytic_account()

    @api.ondelete(at_uninstall=False)
    def _unlink_except_contains_entries(self):
        projects_with_timesheets = self.filtered(lambda p: p.timesheet_ids)
        if projects_with_timesheets:
            if len(projects_with_timesheets) > 1:
                warning_msg = _(
                    "These projects have some timesheet entries referencing them. Before removing these projects, you have to remove these timesheet entries."
                )
            else:
                warning_msg = _(
                    "This project has some timesheet entries referencing it. Before removing this project, you have to remove these timesheet entries."
                )
            _debug.logic(
                "project_unlink_refused",
                reason="has_timesheets",
                projects=projects_with_timesheets,
            )
            raise RedirectWarning(
                warning_msg,
                self.env.ref("hr_timesheet.timesheet_action_project").id,
                _("See timesheet entries"),
                {"active_ids": projects_with_timesheets.ids},
            )

    @api.model
    def get_create_edit_project_ids(self):
        return []

    def _convert_project_uom_to_timesheet_encode_uom(self, time):
        uom_from = self.company_id.project_time_mode_id
        uom_to = self.env.company.timesheet_encode_uom_id
        return round(
            uom_from._get_quantity_in_unit(time, uom_to, raise_if_failure=False), 2
        )

    def action_project_timesheets(self):
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "hr_timesheet.act_hr_timesheet_line_by_project"
        )
        if not self.env.context.get("from_embedded_action"):
            action["display_name"] = _("%(name)s's Timesheets", name=self.name)
        return action

    def _get_stat_buttons(self):
        buttons = super()._get_stat_buttons()
        if not self.allow_timesheets or not self.env.user.has_group(
            "hr_timesheet.group_hr_timesheet_user"
        ):
            return buttons

        encode_uom = self.env.company.timesheet_encode_uom_id
        uom_ratio = self.env.ref("uom.product_uom_hour").factor / encode_uom.factor

        allocated = self.allocated_hours * uom_ratio
        effective = self.total_timesheet_time
        color = ""
        if allocated:
            number = f"{round(effective)} / {round(allocated)} {encode_uom.name}"
            success_rate = round(100 * effective / allocated)
            if success_rate > 100:
                number = self.env._(
                    "%(effective)s / %(allocated)s %(uom_name)s",
                    effective=round(effective),
                    allocated=round(allocated),
                    uom_name=encode_uom.name,
                )
                color = "text-danger"
            else:
                number = self.env._(
                    "%(effective)s / %(allocated)s %(uom_name)s (%(success_rate)s%%)",
                    effective=round(effective),
                    allocated=round(allocated),
                    uom_name=encode_uom.name,
                    success_rate=success_rate,
                )
                if success_rate >= 80:
                    color = "text-warning"
                else:
                    color = "text-success"
        else:
            number = self.env._(
                "%(effective)s %(uom_name)s",
                effective=round(effective),
                uom_name=encode_uom.name,
            )

        buttons.append(
            {
                "icon": f"clock-o {color}",
                "text": self.env._("Timesheets"),
                "number": number,
                "action_type": "object",
                "action": "action_project_timesheets",
                "show": True,
                "sequence": 2,
            }
        )
        if allocated and success_rate > 100:
            buttons.append(
                {
                    "icon": f"warning {color}",
                    "text": self.env._("Extra Time"),
                    "number": self.env._(
                        "%(exceeding_hours)s %(uom_name)s (+%(exceeding_rate)s%%)",
                        exceeding_hours=round(effective - allocated),
                        uom_name=encode_uom.name,
                        exceeding_rate=round(100 * (effective - allocated) / allocated),
                    ),
                    "action_type": "object",
                    "action": "action_project_timesheets",
                    "show": True,
                    "sequence": 3,
                }
            )

        return buttons

    def action_view_tasks(self):
        action = super().action_view_tasks()
        action["context"]["allow_timesheets"] = self.allow_timesheets
        return action

    def _update_template_mode(self, is_template):
        if not is_template and self.allow_timesheets and not self.account_id:
            self._create_analytic_account()
        super()._update_template_mode(is_template)
