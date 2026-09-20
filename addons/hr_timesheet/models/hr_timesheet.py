from collections import defaultdict
from datetime import datetime, time
from statistics import mode

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools.translate import _
from odoo.tools.view_ir import Node

_debug = DebugLog(__name__)


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    def _get_domain_favorite_project_id(self, employee_id=False):
        employee_id = employee_id or self.env.user.employee_id.id
        return [
            ("employee_id", "=", employee_id),
            ("project_id", "!=", False),
            ("project_id.active", "=", True),
            ("project_id.allow_timesheets", "=", True),
        ]

    @api.model
    def _get_favorite_project_id(self, employee_id=False):
        last_timesheets = self.search_fetch(
            self._get_domain_favorite_project_id(employee_id), ["project_id"], limit=5
        )
        if not last_timesheets:
            internal_project = self.env.company.internal_project_id
            _debug.logic(
                "favorite_project", by="internal_project", project=internal_project
            )
            return (
                internal_project.has_access("read")
                and internal_project.active
                and internal_project.allow_timesheets
                and internal_project.id
            )
        _debug.logic("favorite_project", by="recent_mode", sampled=len(last_timesheets))
        return mode([t.project_id.id for t in last_timesheets])

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        if (
            not self.env.context.get("default_employee_id")
            and "employee_id" in fields
            and result.get("user_id")
        ):
            result["employee_id"] = (
                self.env["hr.employee"]
                .search(
                    [
                        ("user_id", "=", result["user_id"]),
                        (
                            "company_id",
                            "=",
                            result.get("company_id", self.env.company.id),
                        ),
                    ],
                    limit=1,
                )
                .id
            )
        if not self.env.context.get("default_project_id") and self.env.context.get(
            "is_timesheet"
        ):
            employee_id = result.get(
                "employee_id", self.env.context.get("default_employee_id", False)
            )
            favorite_project_id = self._get_favorite_project_id(employee_id)
            if favorite_project_id:
                result["project_id"] = favorite_project_id
        return result

    def _domain_project_id(self):
        domain = Domain([("allow_timesheets", "=", True), ("is_template", "=", False)])
        if not self.env.user.has_group("hr_timesheet.group_timesheet_manager"):
            domain &= Domain("user_has_access", "=", True)
        return domain

    def _domain_employee_id(self):
        domain = Domain("company_id", "in", self.env.context.get("allowed_company_ids"))
        if not self.env.user.has_group("hr_timesheet.group_hr_timesheet_approver"):
            domain &= Domain("user_id", "=", self.env.user.id)
        return domain

    task_id = fields.Many2one(
        comodel_name="project.task",
        compute="_compute_task_id",
        store=True,
        index="btree_not_null",
        readonly=False,
        domain="[('allow_timesheets', '=', True), ('project_id', '=?', project_id), ('has_template_ancestor', '=', False)]",
    )
    parent_task_id = fields.Many2one(  # noqa: E8529  measured: grouping 1.8 M timesheets by parent task is 2-2.7x slower through project_task
        comodel_name="project.task",
        related="task_id.parent_id",
        store=True,
        index="btree_not_null",
    )
    project_id = fields.Many2one(
        comodel_name="project.project",
        compute="_compute_project_id",
        store=True,
        index=True,
        readonly=False,
        domain=_domain_project_id,
    )
    user_id = fields.Many2one(
        compute="_compute_user_id",
        store=True,
        readonly=False,
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        index=True,
        domain=_domain_employee_id,
        context={"active_test": False},
        help="Define an 'hourly cost' on the employee to track the cost of their time.",
    )
    job_title = fields.Char(
        related="employee_id.job_title",
        export_string_translation=False,
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        compute="_compute_department_id",
        compute_sudo=True,
        store=True,
    )
    manager_id = fields.Many2one(
        comodel_name="hr.employee",
        related="employee_id.parent_id",
        string="Manager",
    )
    encoding_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        export_string_translation=False,
        compute="_compute_encoding_uom_id",
    )
    partner_id = fields.Many2one(
        compute="_compute_partner_id",
        store=True,
        readonly=False,
    )
    readonly_timesheet = fields.Boolean(
        export_string_translation=False,
        compute="_compute_readonly_timesheet",
        compute_sudo=True,
    )
    milestone_id = fields.Many2one(
        comodel_name="project.milestone",
        related="task_id.milestone_id",
    )
    message_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        compute="_compute_message_partner_ids",
        search="_search_message_partner_ids",
    )
    calendar_display_name = fields.Char(
        export_string_translation=False,
        compute="_compute_calendar_display_name",
    )

    def _search_message_partner_ids(self, operator, value):
        followed_ids_by_model = dict(
            self.env["mail.followers"]._read_group(
                [
                    ("partner_id", operator, value),
                    ("res_model", "=", "project.task"),
                ],
                ["res_model"],
                ["res_id:array_agg"],
            )
        )
        if task_ids := followed_ids_by_model.get("project.task"):
            return Domain("task_id", "in", task_ids)
        return Domain.FALSE

    @api.depends("task_id.message_partner_ids")
    def _compute_message_partner_ids(self):
        for line in self:
            line.message_partner_ids = line.task_id.message_partner_ids

    @api.depends("project_id", "task_id")
    def _compute_display_name(self):
        analytic_line_with_project = self.filtered("project_id")
        super(
            AccountAnalyticLine, self - analytic_line_with_project
        )._compute_display_name()
        for analytic_line in analytic_line_with_project:
            if analytic_line.task_id:
                analytic_line.display_name = f"{analytic_line.project_id.sudo().display_name} - {analytic_line.task_id.sudo().display_name}"
            else:
                analytic_line.display_name = analytic_line.project_id.display_name

    def _is_readonly(self):
        self.check_singleton()
        return False

    def _compute_readonly_timesheet(self):
        if not self.env.user.has_group("base.group_user"):
            self.readonly_timesheet = True
        else:
            readonly_timesheets = self.filtered(
                lambda timesheet: timesheet._is_readonly()
            )
            readonly_timesheets.readonly_timesheet = True
            (self - readonly_timesheets).readonly_timesheet = False

    @api.depends("company_id.timesheet_encode_uom_id")
    def _compute_encoding_uom_id(self):
        for analytic_line in self:
            analytic_line.encoding_uom_id = (
                analytic_line.company_id.timesheet_encode_uom_id
            )

    @api.depends("task_id.partner_id", "project_id.partner_id")
    def _compute_partner_id(self):
        super()._compute_partner_id()
        for timesheet in self:
            if timesheet.project_id:
                timesheet.partner_id = (
                    timesheet.task_id.partner_id or timesheet.project_id.partner_id
                )

    @api.depends("task_id.project_id")
    def _compute_project_id(self):
        for line in self:
            if (
                not line.task_id.project_id
                or line.project_id == line.task_id.project_id
            ):
                continue
            line.project_id = line.task_id.project_id

    @api.depends("project_id")
    def _compute_task_id(self):
        self.filtered(lambda t: not t.project_id).task_id = False

    @api.onchange("project_id")
    def _onchange_project_id(self):
        if self.project_id != self.task_id.project_id:
            self.task_id = False

    @api.depends("employee_id.user_id")
    def _compute_user_id(self):
        for line in self:
            line.user_id = (
                line.employee_id.user_id
                if line.employee_id
                else self._get_default_user_id()
            )

    @api.depends("employee_id")
    def _compute_department_id(self):
        for line in self:
            line.department_id = line.employee_id.department_id

    @api.depends(
        "company_id.timesheet_encode_uom_id",
        "display_name",
        "project_id",
        "unit_amount",
    )
    def _compute_calendar_display_name(self):
        companies = self.company_id
        encoding_in_days_per_company = dict(
            zip(
                companies,
                [
                    company.timesheet_encode_uom_id
                    == self.env.ref("uom.product_uom_day")
                    for company in companies
                ],
                strict=True,
            )
        )
        for line in self:
            if not line.project_id:
                line.calendar_display_name = ""
                continue
            if encoding_in_days_per_company[line.company_id]:
                days = line._get_timesheet_time_day()
                if days == int(days):
                    days = int(days)
                line.calendar_display_name = self.env._(
                    "%(project_name)s (%(days)sd)",
                    project_name=line.project_id.display_name,
                    days=days,
                )
            else:
                minutes = round(line.unit_amount * 60)
                hours, minutes = divmod(minutes, 60)
                if minutes:
                    line.calendar_display_name = self.env._(
                        "%(project_name)s (%(hours)sh%(minutes)s)",
                        project_name=line.project_id.display_name,
                        hours=hours,
                        minutes=minutes,
                    )
                else:
                    line.calendar_display_name = self.env._(
                        "%(project_name)s (%(hours)sh)",
                        project_name=line.project_id.display_name,
                        hours=hours,
                    )

    def _check_can_write(self, values):
        if not (
            self.env.user.has_group("hr_timesheet.group_hr_timesheet_approver")
            or self.env.su
        ) and any(analytic_line.user_id != self.env.user for analytic_line in self):
            _debug.logic(
                "write_denied",
                reason="not_own_timesheet",
                user=self.env.user,
                lines=self,
            )
            raise AccessError(_("You cannot access timesheets that are not yours."))

    def _check_can_create(self):
        pass

    @api.model_create_multi
    def create(self, vals_list):
        user_timezone = self.env.tz
        default_user_id = self._get_default_user_id()
        user_ids = []
        employee_ids = []
        if self.env.context.get("timesheet_calendar"):
            self.env["hr.employee"].browse(
                [vals.get("employee_id") for vals in vals_list]
            )
        skipped_vals = 0
        valid_vals = 0
        for vals in vals_list[:]:
            if self.env.context.get("timesheet_calendar"):
                if "employee_id" not in vals:
                    vals["employee_id"] = self.env.user.employee_id.id
                employee = self.env["hr.employee"].browse(vals["employee_id"])
                date = fields.Date.from_string(
                    vals.get(
                        "date", fields.Date.to_string(fields.Date.context_today(self))
                    )
                )
                if not any(
                    employee.resource_id._get_valid_work_intervals(
                        datetime.combine(date, time.min, tzinfo=user_timezone),
                        datetime.combine(date, time.max, tzinfo=user_timezone),
                    )[0][employee.resource_id.id]
                ):
                    vals_list.remove(vals)
                    skipped_vals += 1
                    continue
            task = self.env["project.task"].sudo().browse(vals.get("task_id"))
            project = self.env["project.project"].sudo().browse(vals.get("project_id"))
            if not (task or project):
                continue
            if task:
                if not task.project_id:
                    _debug.logic("create_refused", reason="private_task", task=task)
                    raise ValidationError(
                        _("Timesheets cannot be created on a private task.")
                    )
                if not project:
                    vals["project_id"] = task.project_id.id

            company = (
                task.company_id
                or project.company_id
                or self.env["res.company"].browse(vals.get("company_id"))
            )
            vals["company_id"] = company.id
            vals.update(
                {
                    fname: account_id
                    for fname, account_id in self._timesheet_preprocess_get_accounts(
                        vals
                    ).items()
                    if fname not in vals
                }
            )

            if not vals.get("product_uom_id"):
                vals["product_uom_id"] = company.project_time_mode_id.id

            if not vals.get("name"):
                vals["name"] = "/"
            employee_id = vals.get(
                "employee_id", self.env.context.get("default_employee_id", False)
            )
            if employee_id and employee_id not in employee_ids:
                employee_ids.append(employee_id)
            else:
                user_id = vals.get("user_id", default_user_id)
                if user_id not in user_ids:
                    user_ids.append(user_id)
            valid_vals += 1

        HrEmployee_sudo = self.env["hr.employee"].sudo()
        employees = HrEmployee_sudo.search(
            [
                "&",
                "|",
                ("user_id", "in", user_ids),
                ("id", "in", employee_ids),
                ("company_id", "in", self.env.companies.ids),
            ]
        )

        valid_employee_per_id = {}
        employee_id_per_company_per_user = defaultdict(dict)
        for employee in employees:
            if employee.id in employee_ids:
                valid_employee_per_id[employee.id] = employee
            else:
                employee_id_per_company_per_user[employee.user_id.id][
                    employee.company_id.id
                ] = employee.id

        error_msg = _(
            "Timesheets must be created with an active employee in the selected companies."
        )
        for vals in vals_list:
            if not vals.get("project_id"):
                continue
            employee_in_id = vals.get(
                "employee_id", self.env.context.get("default_employee_id", False)
            )
            if employee_in_id:
                company = False
                if not vals.get("company_id"):
                    company = HrEmployee_sudo.browse(employee_in_id).company_id
                    vals["company_id"] = company.id
                if not vals.get("product_uom_id"):
                    vals["product_uom_id"] = (
                        company.project_time_mode_id.id
                        if company
                        else self.env["res.company"]
                        .browse(vals.get("company_id", self.env.company.id))
                        .project_time_mode_id.id
                    )
                if employee_in_id in valid_employee_per_id:
                    vals["user_id"] = (
                        valid_employee_per_id[employee_in_id].sudo().user_id.id
                    )
                    continue
                _debug.logic("create_refused", by="employee", id=employee_in_id)
                raise ValidationError(error_msg)
            user_id = vals.get("user_id", default_user_id)

            employee_per_company = employee_id_per_company_per_user.get(user_id)
            employee_out_id = False
            if employee_per_company:
                company_id = (
                    next(iter(employee_per_company))
                    if len(employee_per_company) == 1
                    else vals.get("company_id") or self.env.company.id
                )
                employee_out_id = employee_per_company.get(company_id, False)

            if employee_out_id:
                vals["employee_id"] = employee_out_id
                vals["user_id"] = user_id
                company = False
                if not vals.get("company_id"):
                    company = HrEmployee_sudo.browse(employee_out_id).company_id
                    vals["company_id"] = company.id
                if not vals.get("product_uom_id"):
                    vals["product_uom_id"] = (
                        company.project_time_mode_id.id
                        if company
                        else self.env["res.company"]
                        .browse(vals.get("company_id", self.env.company.id))
                        .project_time_mode_id.id
                    )
            else:
                _debug.logic("create_refused", by="user", id=user_id)
                raise ValidationError(error_msg)

        _debug.pipeline("create_resolved", rows=valid_vals, skipped=skipped_vals)
        lines = super().create(vals_list)
        _debug.lifecycle("create", lines=lines, count=len(vals_list))
        lines._check_can_create()
        for line, values in zip(lines, vals_list, strict=True):
            if line.project_id:
                line._timesheet_postprocess(values)

        if self.env.context.get("timesheet_calendar"):
            if skipped_vals:
                type = "danger"
                if valid_vals:
                    message = self.env._(
                        "Some timesheets were not created: employees aren’t working on the selected days"
                    )
                else:
                    message = self.env._(
                        "No timesheets created: employees aren’t working on the selected days"
                    )
            else:
                type = "success"
                message = self.env._("Timesheets successfully created")

            self.env.user._bus_send(
                "simple_notification",
                {
                    "type": type,
                    "message": message,
                },
            )

        return lines

    def write(self, vals):
        values = vals
        _debug.lifecycle("write", lines=self, fields=list(vals))
        self._check_can_write(values)

        task = self.env["project.task"].sudo().browse(values.get("task_id"))
        project = self.env["project.project"].sudo().browse(values.get("project_id"))
        if task and not task.project_id:
            _debug.logic("write_refused", reason="private_task", task=task)
            raise ValidationError(_("Timesheets cannot be created on a private task."))
        if project or task:
            values["company_id"] = task.company_id.id or project.company_id.id
        values.update(
            {
                fname: account_id
                for fname, account_id in self._timesheet_preprocess_get_accounts(
                    values
                ).items()
                if fname not in values
            }
        )

        if values.get("employee_id"):
            employee = self.env["hr.employee"].browse(values["employee_id"])
            if not employee.active:
                _debug.logic(
                    "write_refused", reason="archived_employee", employee=employee
                )
                raise UserError(
                    _("You cannot set an archived employee on existing timesheets.")
                )
        if "name" in values and not values.get("name"):
            values["name"] = "/"
        if "company_id" in values and not values.get("company_id"):
            del values["company_id"]
        result = super().write(values)
        self.filtered(lambda t: t.project_id)._timesheet_postprocess(values)
        return result

    @api.model
    def get_views(self, views, options=None):
        res = super().get_views(views, options)
        if options and options.get("toolbar"):
            wip_report_id = None

            def get_wip_report_id():
                return self.env["ir.model.data"]._xmlid_to_res_id(
                    "mrp_account.wip_report", raise_if_not_found=False
                )

            for view_data in res["views"].values():
                print_data_list = view_data.get("toolbar", {}).get("print")
                if print_data_list:
                    if wip_report_id is None and any(
                        node.attrs.get("widget", "").startswith("timesheet_uom")
                        for _path, node in Node.from_dict(view_data["ir"]).walk()
                    ):
                        wip_report_id = get_wip_report_id()
                    if wip_report_id:
                        view_data["toolbar"]["print"] = [
                            print_data
                            for print_data in print_data_list
                            if print_data["id"] != wip_report_id
                        ]
        return res

    def _timesheet_get_portal_domain(self):
        if self.env.user.has_group("hr_timesheet.group_hr_timesheet_user"):
            _debug.logic("portal_domain", by="timesheet_user", user=self.env.user)
            return self.env["ir.rule"]._get_domain_accessible_records(self._name)
        _debug.logic("portal_domain", by="portal_partner", user=self.env.user)
        commercial_partner_id = self.env.user.partner_id.commercial_partner_id.id
        accessible_projects = (
            self.env["project.project"].sudo()._search([("user_has_access", "=", True)])
        )
        return (
            Domain("project_id", "in", accessible_projects)
            | Domain("message_partner_ids", "child_of", [commercial_partner_id])
            | Domain("partner_id", "child_of", [commercial_partner_id])
        ) & Domain("project_id.privacy_visibility", "in", ["invited_users", "portal"])

    def _timesheet_preprocess_get_accounts(self, vals):
        project = self.env["project.project"].sudo().browse(vals.get("project_id"))
        if not project:
            return {}
        company = self.env["res.company"].browse(vals.get("company_id"))
        mandatory_plans = [
            plan
            for plan in self._get_mandatory_plans(company, business_domain="timesheet")
            if plan["column_name"] != "account_id"
        ]
        missing_plan_names = [
            plan["name"] for plan in mandatory_plans if not project[plan["column_name"]]
        ]
        if missing_plan_names:
            _debug.logic(
                "mandatory_plans_missing",
                project=project,
                plans=",".join(missing_plan_names),
            )
            raise ValidationError(
                _(
                    "'%(missing_plan_names)s' analytic plan(s) required on the project '%(project_name)s' linked to the timesheet.",
                    missing_plan_names=missing_plan_names,
                    project_name=project.name,
                )
            )
        return {fname: project[fname].id for fname in self._get_plan_fnames()}

    def _timesheet_postprocess(self, values):
        sudo_self = self.sudo()
        values_to_write = self._timesheet_postprocess_values(values)
        _debug.pipeline(
            "postprocess",
            lines=self,
            fields=list(values),
            candidates=len(values_to_write),
        )
        for timesheet in sudo_self:
            if values_to_write[timesheet.id]:
                timesheet.write(values_to_write[timesheet.id])
        return values

    def _timesheet_postprocess_values(self, values):
        result = {id_: {} for id_ in self.ids}
        sudo_self = self.sudo()
        if any(
            field_name in values
            for field_name in ["unit_amount", "employee_id", "account_id"]
        ):
            for timesheet in sudo_self:
                if not timesheet.account_id.active:
                    project_plan, _other_plans = self.env[
                        "account.analytic.plan"
                    ]._get_all_plans()
                    raise ValidationError(
                        _(
                            "Timesheets must be created with at least an active analytic account defined in the plan '%(plan_name)s'.",
                            plan_name=project_plan.name,
                        )
                    )
                accounts = timesheet._get_analytic_accounts()
                companies = (
                    timesheet.company_id
                    | accounts.company_id
                    | timesheet.task_id.company_id
                    | timesheet.project_id.company_id
                )
                if len(companies) > 1:
                    raise ValidationError(
                        _(
                            "The project, the task and the analytic accounts of the timesheet must belong to the same company."
                        )
                    )

                cost = timesheet._hourly_cost()
                amount = -timesheet.unit_amount * cost
                amount_converted = timesheet.employee_id.currency_id._convert(
                    amount,
                    timesheet.account_id.currency_id or timesheet.currency_id,
                    self.env.company,
                    timesheet.date,
                )
                result[timesheet.id].update(
                    {
                        "amount": amount_converted,
                    }
                )
        return result

    def _split_amount_fname(self):
        return "unit_amount" if self.project_id else super()._split_amount_fname()

    def _is_timesheet_encode_uom_day(self):
        company_uom = self.env.company.timesheet_encode_uom_id
        return company_uom == self.env.ref("uom.product_uom_day")

    def _is_updatable_timesheet(self):
        return True

    @api.model
    def _convert_hours_to_days(self, time):
        uom_hour = self.env.ref("uom.product_uom_hour")
        uom_day = self.env.ref("uom.product_uom_day")
        return round(
            uom_hour._get_quantity_in_unit(time, uom_day, raise_if_failure=False), 2
        )

    def _get_timesheet_time_day(self):
        return self._convert_hours_to_days(self.unit_amount)

    def _hourly_cost(self):
        self.check_singleton()
        return self.employee_id.hourly_cost

    def _get_report_base_filename(self):
        task_ids = self.task_id
        if len(task_ids) == 1:
            return _("Timesheets - %s", task_ids.name)
        return _("Timesheets")

    def _get_default_user_id(self):
        return self.env.context.get("user_id", self.env.user.id)

    @api.model
    def _create_missing_uom_hours(self):
        uom_hours = self.env.ref("uom.product_uom_hour", raise_if_not_found=False)
        if not uom_hours:
            uom_hours = self.env["uom.uom"].create(
                {
                    "name": "Hours",
                    "relative_factor": 1,
                }
            )
            _debug.lifecycle("uom_hours_created", uom=uom_hours)
            self.env["ir.model.data"].create(
                {
                    "name": "product_uom_hour",
                    "model": "uom.uom",
                    "module": "uom",
                    "res_id": uom_hours.id,
                    "noupdate": True,
                }
            )

    @api.model
    def _show_portal_timesheets(self):
        return True

    def action_view_timesheet_view_portal(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "res_id": self.id,
            "res_model": "account.analytic.line",
            "views": [
                (
                    self.env.ref("hr_timesheet.timesheet_view_form_portal_user").id,
                    "form",
                )
            ],
            "context": self.env.context,
        }

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        return self.env.user.employee_id._get_unusual_days(date_from, date_to)

    @api.model
    def get_import_templates(self):
        if self.env.context.get("is_timesheet"):
            return [
                {
                    "label": _("Import Template for Timesheets"),
                    "template": "/hr_timesheet/static/xls/timesheets_import_template.xlsx",
                }
            ]
        return []
