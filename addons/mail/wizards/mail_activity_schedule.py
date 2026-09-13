import logging
import typing
from collections import defaultdict
from typing import Literal

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.api import ValuesType
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import html2plaintext
from odoo.tools.misc import format_date

from odoo.addons.mail.tools.parser import parse_res_ids

if typing.TYPE_CHECKING:
    from ..models.mail_activity import MailActivity
    from ..models.mail_activity_plan import MailActivityPlan
    from ..models.mail_activity_plan_template import MailActivityPlanTemplate
    from ..models.mail_activity_type import MailActivityType
    from .mail_activity_schedule_summary import MailActivityScheduleSummary
    from odoo.addons.base.models.ir_model import IrModel
    from odoo.addons.base.models.res_company import ResCompany
    from odoo.addons.bus.models.res_users import ResUsers

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class MailActivitySchedule(models.TransientModel):
    _name = "mail.activity.schedule"
    _description = "Activity schedule plan Wizard"
    _batch_size = 500

    @api.model
    def default_get(self, fields: list[str]) -> ValuesType:
        res = super().default_get(fields)
        context = self.env.context
        active_res_ids = parse_res_ids(context.get("active_ids"), self.env)
        if "res_ids" in fields:
            if active_res_ids and len(active_res_ids) <= self._batch_size:
                res["res_ids"] = f"{context['active_ids']}"
            elif not active_res_ids and context.get("active_id"):
                res["res_ids"] = f"{[context['active_id']]}"
        res_model = context.get("active_model") or context.get("params", {}).get(
            "active_model", False
        )
        if "res_model" in fields:
            res["res_model"] = res_model
        return res

    res_model_id: IrModel = fields.Many2one(
        comodel_name="ir.model",
        string="Applies to",
        compute="_compute_res_model_id",
        precompute=True,
        compute_sudo=True,
        store=True,
        readonly=False,
        required=False,
        ondelete="cascade",
    )
    res_model = fields.Char(
        string="Model",
        readonly=False,
        required=False,
    )
    res_ids = fields.Text(
        string="Document IDs",
        compute="_compute_res_ids",
        precompute=True,
        store=True,
        readonly=False,
    )
    is_batch_mode = fields.Boolean(
        string="Use in batch",
        compute="_compute_is_batch_mode",
    )
    company_id: ResCompany = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
        required=False,
    )
    error = fields.Html(compute="_compute_error_and_warning")
    has_error = fields.Boolean(compute="_compute_error_and_warning")
    warning = fields.Html(compute="_compute_error_and_warning")
    has_warning = fields.Boolean(compute="_compute_error_and_warning")
    plan_available_ids: MailActivityPlan = fields.Many2many(
        comodel_name="mail.activity.plan",
        compute="_compute_plan_available_ids",
        compute_sudo=True,
        store=True,
    )
    plan_id: MailActivityPlan = fields.Many2one(
        comodel_name="mail.activity.plan",
        compute="_compute_plan_id",
        store=True,
        readonly=False,
        domain="[('id', 'in', plan_available_ids)]",
    )
    plan_has_user_on_demand = fields.Boolean(related="plan_id.has_user_on_demand")
    plan_schedule_line_ids: MailActivityScheduleSummary = fields.One2many(
        comodel_name="mail.activity.schedule.line",
        inverse_name="activity_schedule_id",
        string="Schedule Lines",
        compute="_compute_plan_schedule_line_ids",
    )
    plan_on_demand_user_id: ResUsers = fields.Many2one(
        comodel_name="res.users",
        string="Assigned To",
        default=lambda self: self.env.user,
        help="Choose assignation for activities with on demand assignation.",
    )
    plan_date = fields.Date(
        compute="_compute_plan_date",
        store=True,
        readonly=False,
    )
    activity_type_id: MailActivityType = fields.Many2one(
        comodel_name="mail.activity.type",
        compute="_compute_activity_type_id",
        store=True,
        readonly=False,
        domain="['|', ('res_model', '=', False), ('res_model', '=', res_model)]",
        ondelete="set null",
    )
    activity_category = fields.Selection(
        related="activity_type_id.category",
        readonly=True,
    )
    date_deadline = fields.Date(
        string="Due Date",
        compute="_compute_date_deadline",
        store=True,
        readonly=False,
    )
    summary = fields.Char(
        compute="_compute_summary",
        store=True,
        readonly=False,
    )
    note = fields.Html(
        sanitize_style=True,
        compute="_compute_note",
        store=True,
        readonly=False,
    )
    activity_user_id: ResUsers = fields.Many2one(
        comodel_name="res.users",
        string="Assigned to",
        compute="_compute_activity_user_id",
        store=True,
        readonly=False,
    )
    chaining_type = fields.Selection(
        related="activity_type_id.chaining_type",
        readonly=True,
    )

    @api.depends("res_model")
    def _compute_res_model_id(self) -> None:
        self.filtered(lambda a: not a.res_model).res_model_id = False
        for scheduler in self.filtered("res_model"):
            scheduler.res_model_id = self.env["ir.model"]._get_id(scheduler.res_model)

    @api.depends_context("active_ids")
    def _compute_res_ids(self) -> None:
        context = self.env.context
        for scheduler in self.filtered(lambda scheduler: not scheduler.res_ids):
            active_res_ids = parse_res_ids(context.get("active_ids"), self.env)
            if active_res_ids and len(active_res_ids) <= self._batch_size:
                scheduler.res_ids = f"{context['active_ids']}"
            elif not active_res_ids and context.get("active_id"):
                scheduler.res_ids = f"{[context['active_id']]}"

    @api.depends("res_model_id", "res_ids")
    def _compute_company_id(self) -> None:
        self.filtered(lambda a: not a.res_model).company_id = False
        for scheduler in self.filtered("res_model"):
            applied_on = scheduler._get_applied_on_records()
            scheduler.company_id = (
                applied_on
                and "company_id" in applied_on[0]._fields
                and applied_on[0].company_id
            ) or self.env.company

    @api.depends(
        "company_id",
        "res_model_id",
        "res_ids",
        "plan_id",
        "plan_on_demand_user_id",
        "plan_available_ids",
        "activity_type_id",
        "activity_user_id",
    )
    def _compute_error_and_warning(self) -> None:
        for scheduler in self:
            errors = set()
            warnings = set()
            applied_on = scheduler._get_applied_on_records()
            if scheduler.res_model:
                if applied_on and (
                    "company_id" in scheduler.env[applied_on._name]._fields
                    and len(applied_on.mapped("company_id")) > 1
                ):
                    errors.add(_("The records must belong to the same company."))
            if scheduler.plan_id:
                if applied_on:
                    plan_errors, plan_warnings = (
                        scheduler._get_plan_template_errors_and_warnings(applied_on)
                    )
                    errors |= plan_errors
                    warnings |= plan_warnings
                if not scheduler.res_ids:
                    errors.add(_("Can't launch a plan without a record."))
            if not scheduler.res_ids and not scheduler.activity_user_id:
                errors.add(
                    _("Can't schedule activities without either a record or a user.")
                )
            if _debug.logic.enabled and (errors or warnings):
                _debug.logic(
                    "schedule_complaints",
                    wizard=scheduler.id,
                    plan=scheduler.plan_id.id or None,
                    model=scheduler.res_model or None,
                    errors=len(errors),
                    warnings=len(warnings),
                )
            if errors:
                error_header = (
                    _(
                        'The plan "%(plan_name)s" cannot be launched:',
                        plan_name=scheduler.plan_id.name,
                    )
                    if scheduler.plan_id
                    else _("The activity cannot be launched:")
                )
                error_body = Markup("<ul>%s</ul>") % (
                    Markup().join(Markup("<li>%s</li>") % error for error in errors)
                )
                scheduler.error = f"{error_header}{error_body}"
                scheduler.has_error = True
            else:
                scheduler.error = False
                scheduler.has_error = False

            if warnings:
                warning_header = (
                    _(
                        'The plan "%(plan_name)s" can be launched, with these additional effects:',
                        plan_name=scheduler.plan_id.name,
                    )
                    if scheduler.plan_id
                    else _(
                        "The activity can be launched, with these additional effects:"
                    )
                )
                warning_body = Markup("<ul>%s</ul>") % (
                    Markup().join(
                        Markup("<li>%s</li>") % warning for warning in warnings
                    )
                )
                scheduler.warning = f"{warning_header}{warning_body}"
                scheduler.has_warning = True
            else:
                scheduler.warning = False
                scheduler.has_warning = False

    @api.depends("res_ids")
    def _compute_is_batch_mode(self) -> None:
        for scheduler in self:
            scheduler.is_batch_mode = len(scheduler._evaluate_res_ids()) > 1

    @api.depends("company_id", "res_model")
    def _compute_plan_available_ids(self) -> None:
        domains = {
            scheduler: scheduler._get_domain_plan_available_base() for scheduler in self
        }
        plans = self.env["mail.activity.plan"].search(Domain.OR(domains.values()))
        for scheduler, domain in domains.items():
            scheduler.plan_available_ids = plans.filtered_domain(domain)

    @api.depends_context("plan_mode")
    @api.depends("plan_available_ids")
    def _compute_plan_id(self) -> None:
        for scheduler in self:
            if self.env.context.get("plan_mode"):
                scheduler.plan_id = scheduler.plan_available_ids.sorted("id")[:1]
            else:
                scheduler.plan_id = False

    @api.onchange("plan_id")
    def _onchange_plan_id(self) -> None:
        if self.plan_id:
            self.activity_type_id = False

    @api.depends("res_model", "res_ids")
    def _compute_plan_date(self) -> None:
        self.plan_date = fields.Date.context_today(self)

    @api.depends(
        "plan_date", "plan_id", "plan_on_demand_user_id", "res_model", "res_ids"
    )
    def _compute_plan_schedule_line_ids(self) -> None:
        self.plan_schedule_line_ids = False
        for scheduler in self:
            schedule_line_values_list = []
            templates = scheduler.plan_id.template_ids
            applied_on = scheduler._plan_preview_record() if templates else None
            for template in templates:
                schedule_line_values = {
                    "line_description": template.summary
                    or template.activity_type_id.name,
                }

                responsible_user = scheduler._plan_preview_responsible(
                    template, applied_on
                )
                if responsible_user:
                    schedule_line_values["responsible_user_id"] = responsible_user.id

                activity_date_deadline = False
                if scheduler.plan_date:
                    activity_date_deadline = template._get_date_deadline(
                        scheduler.plan_date
                    )
                    schedule_line_values["line_date_deadline"] = activity_date_deadline

                schedule_line_values_list.append(schedule_line_values)

                activity_type = template.activity_type_id
                if activity_type.triggered_next_type_id:
                    next_activity = activity_type.triggered_next_type_id
                    schedule_line_values = {
                        "line_description": next_activity.summary or next_activity.name,
                        "responsible_user_id": next_activity.default_user_id.id
                        or False,
                    }
                    if activity_date_deadline:
                        schedule_line_values["line_date_deadline"] = (
                            next_activity.with_context(
                                activity_previous_deadline=activity_date_deadline
                            )._get_date_deadline()
                        )

                    schedule_line_values_list.append(schedule_line_values)
                elif activity_type.suggested_next_type_ids:
                    for suggested in activity_type.suggested_next_type_ids:
                        schedule_line_values = {
                            "line_description": suggested.summary or suggested.name,
                            "responsible_user_id": suggested.default_user_id.id
                            or False,
                        }
                        if activity_date_deadline:
                            schedule_line_values["line_date_deadline"] = (
                                suggested.with_context(
                                    activity_previous_deadline=activity_date_deadline
                                )._get_date_deadline()
                            )

                        schedule_line_values_list.append(schedule_line_values)

            scheduler.plan_schedule_line_ids = [(5,)] + [
                (0, 0, values) for values in schedule_line_values_list
            ]

    def _plan_preview_record(self) -> models.BaseModel:
        self.check_singleton()
        model = self.env[self.plan_id.res_model or self.res_model]
        res_ids = self._evaluate_res_ids()
        return model.browse(res_ids).exists() if len(res_ids) == 1 else model

    def _plan_preview_responsible(
        self, template: MailActivityPlanTemplate, applied_on: models.BaseModel
    ) -> ResUsers | Literal[False]:
        result = template._get_responsible_and_complaints(
            self.plan_on_demand_user_id, applied_on
        )
        if not applied_on and (result["error"] or result["warning"]):
            return False
        return result["responsible"]

    @api.depends("res_model")
    def _compute_activity_type_id(self) -> None:
        for scheduler in self:
            if not scheduler.activity_type_id or (
                scheduler.activity_type_id.res_model
                and scheduler.res_model
                and scheduler.activity_type_id.res_model != scheduler.res_model
            ):
                scheduler.activity_type_id = scheduler.env[
                    "mail.activity"
                ]._default_activity_type_for_model(scheduler.res_model)

    @api.onchange("activity_type_id")
    def _onchange_activity_type_id(self) -> None:
        if self.activity_type_id:
            self.plan_id = False

    @api.depends("activity_type_id", "activity_user_id")
    def _compute_date_deadline(self) -> None:
        for scheduler in self:
            if scheduler.activity_type_id:
                scheduler.date_deadline = scheduler.activity_type_id._get_date_deadline(
                    scheduler.activity_user_id
                )
            elif not scheduler.date_deadline:
                scheduler.date_deadline = self.env["mail.activity"]._today_for(
                    scheduler.activity_user_id
                )

    @api.depends("activity_type_id")
    def _compute_summary(self) -> None:
        for scheduler in self:
            scheduler.summary = scheduler.activity_type_id.summary

    @api.depends("activity_type_id")
    def _compute_note(self) -> None:
        for scheduler in self:
            scheduler.note = scheduler.activity_type_id.default_note

    @api.depends("activity_type_id", "res_model")
    @api.depends_context("uid")
    def _compute_activity_user_id(self) -> None:
        for scheduler in self:
            if scheduler.activity_type_id.default_user_id:
                scheduler.activity_user_id = scheduler.activity_type_id.default_user_id
            else:
                scheduler.activity_user_id = self.env.user

    @api.constrains(
        "res_model_id",
        "res_ids",
        "plan_id",
        "plan_on_demand_user_id",
        "activity_type_id",
        "activity_user_id",
    )
    def _check_consistency(self) -> None:
        for scheduler in self.filtered("error"):
            raise ValidationError(html2plaintext(scheduler.error))

    @api.constrains("res_ids")
    def _check_res_ids(self) -> None:
        for scheduler in self:
            scheduler._evaluate_res_ids()

    @api.readonly
    @api.model
    def get_model_options(self) -> list:
        described = (
            self.env["ir.model"]
            .sudo()
            .search(
                [
                    ("is_mail_activity", "=", True),
                    ("transient", "=", False),
                    ("abstract", "=", False),
                ]
            )
        )
        return [
            model.model
            for model in described
            if model.model in self.env and self.env[model.model].has_access("read")
        ]

    def action_schedule_plan(self) -> dict:
        if not self.res_model:
            raise UserError(_("Plan-based scheduling is available only on documents."))
        applied_on = self._get_applied_on_records()
        templates = self._plan_filtered_activity_templates_to_schedule()

        descriptions = defaultdict(list)
        record_ids_by_group = defaultdict(list)
        for template in templates:
            date_deadline = template._get_date_deadline(self.plan_date)
            for record in applied_on:
                responsible = template._get_responsible_and_complaints(
                    self.plan_on_demand_user_id, record
                )["responsible"]
                record_ids_by_group[(template, responsible, date_deadline)].append(
                    record.id
                )
                descriptions[record.id].append(
                    _(
                        "%(activity)s, assigned to %(name)s, due on the %(deadline)s",
                        activity=template.summary or template.activity_type_id.name,
                        name=responsible.name,
                        deadline=format_date(self.env, date_deadline),
                    )
                )

        _debug.pipeline(
            "plan_scheduled",
            wizard=self.id,
            plan=self.plan_id.id,
            model=self.res_model,
            records=len(applied_on),
            templates=len(templates),
            groups=len(record_ids_by_group),
        )
        for (
            template,
            responsible,
            date_deadline,
        ), record_ids in record_ids_by_group.items():
            applied_on.browse(record_ids).activity_schedule(
                activity_type_id=template.activity_type_id.id,
                automated=False,
                summary=template.summary,
                note=template.note,
                user_id=responsible.id,
                date_deadline=date_deadline,
            )

        started = _(
            'The plan "%(plan_name)s" has been started', plan_name=self.plan_id.name
        )
        applied_on._message_post_values_all(
            {
                record.id: {
                    "body": started
                    + (
                        Markup("<ul>%s</ul>")
                        % Markup().join(
                            Markup("<li>%s</li>") % description
                            for description in descriptions[record.id]
                        )
                        if descriptions[record.id]
                        else ""
                    )
                }
                for record in applied_on
            }
        )

        if len(applied_on) == 1:
            return {"type": "ir.actions.client", "tag": "soft_reload"}

        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "name": _("Launch Plans"),
            "view_mode": "list,form",
            "target": "current",
            "domain": [("id", "in", applied_on.ids)],
        }

    def _get_plan_template_errors_and_warnings(
        self, applied_on: models.BaseModel
    ) -> tuple[set, set]:
        self.check_singleton()
        errors, warnings = set(), set()
        for activity_template in self.plan_id.template_ids:
            for record in applied_on:
                responsible = activity_template._get_responsible_and_complaints(
                    self.plan_on_demand_user_id, record
                )
                if responsible["error"]:
                    errors.add(responsible["error"])
                if responsible["warning"]:
                    warnings.add(responsible["warning"])
        return errors, warnings

    def action_schedule_activities(self) -> None:
        self._action_schedule_activities()

    def action_schedule_activities_done(self) -> None:
        self._action_schedule_activities().action_done()

    def _action_schedule_activities(self) -> MailActivity:
        if not self.res_model:
            return self._action_schedule_activities_personal()
        self._check_assignee_can_upload()
        _debug.lifecycle(
            "activities_scheduled",
            wizard=self.id,
            model=self.res_model,
            activity_type=self.activity_type_id.id,
            user=self.activity_user_id.id,
            by="wizard",
        )
        return self._get_applied_on_records().activity_schedule(
            activity_type_id=self.activity_type_id.id,
            automated=False,
            summary=self.summary,
            note=self.note,
            user_id=self.activity_user_id.id,
            date_deadline=self.date_deadline,
        )

    def _action_schedule_activities_personal(self) -> MailActivity:
        if not self.activity_user_id:
            raise UserError(
                _("Scheduling personal activities requires an assigned user.")
            )
        _debug.lifecycle(
            "activities_scheduled",
            wizard=self.id,
            activity_type=self.activity_type_id.id,
            user=self.activity_user_id.id,
            by="personal",
        )
        return self.env["mail.activity"].create(
            {
                "activity_type_id": self.activity_type_id.id,
                "automated": False,
                "date_deadline": self.date_deadline,
                "note": self.note,
                "res_id": False,
                "res_model_id": False,
                "summary": self.summary,
                "user_id": self.activity_user_id.id,
            }
        )

    def _evaluate_res_ids(self) -> list[int]:
        self.check_singleton()
        return parse_res_ids(self.res_ids, self.env) or []

    def _get_applied_on_records(self) -> models.Model | None:
        if not self.res_model:
            return None
        return self.env[self.res_model].browse(self._evaluate_res_ids())

    def _get_domain_plan_available_base(self) -> Domain:
        self.check_singleton()
        return Domain.AND(
            [
                [
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "=", self.company_id.id),
                ],
                ["|", ("res_model", "=", False), ("res_model", "=", self.res_model)],
                [("template_ids", "!=", False)],
            ]
        )

    def _plan_filtered_activity_templates_to_schedule(self) -> MailActivityPlanTemplate:
        return self.plan_id.template_ids

    @api.onchange("activity_user_id", "activity_type_id")
    def _onchange_activity_user_id(self) -> None:
        self._check_assignee_can_upload()

    def _check_assignee_can_upload(self) -> None:
        self.check_singleton()
        activity_user = self.activity_user_id
        model = self.res_model
        if self.activity_category != "upload_file" or not (model and activity_user):
            return
        try:
            thread = (
                self.with_user(activity_user)
                .env[model]
                .browse(self._evaluate_res_ids())
            )
            operations = thread._mail_group_by_operation_for_mail_message_operation(
                "create"
            )
            for operation, records in operations.items():
                records.check_access(operation)
        except AccessError as err:
            _debug.logic(
                "assignee_cannot_upload",
                wizard=self.id,
                model=model,
                user=activity_user.id,
            )
            raise UserError(
                _(
                    "Selected user '%(user)s' cannot upload documents on model '%(model)s'",
                    model=model,
                    user=activity_user.display_name,
                )
            ) from err
