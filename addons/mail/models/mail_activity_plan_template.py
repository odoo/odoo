import typing
from datetime import date
from typing import Literal

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

if typing.TYPE_CHECKING:
    from .mail_activity_plan import MailActivityPlan
    from .mail_activity_type import MailActivityType
    from odoo.addons.base.models.res_company import ResCompany
    from odoo.addons.bus.models.res_users import ResUsers

_debug = DebugLog(__name__)


class MailActivityPlanTemplate(models.Model):
    _name = "mail.activity.plan.template"
    _inherit = ["mixin.delay"]
    _description = "Activity plan template"
    _order = "sequence, id"
    _rec_name = "summary"

    plan_id: MailActivityPlan = fields.Many2one(
        comodel_name="mail.activity.plan",
        index=True,
        required=True,
        ondelete="cascade",
    )
    res_model = fields.Selection(related="plan_id.res_model")
    company_id: ResCompany = fields.Many2one(related="plan_id.company_id")
    sequence = fields.Integer(default=10)
    activity_type_id: MailActivityType = fields.Many2one(
        comodel_name="mail.activity.type",
        default=lambda self: self.env.ref("mail.mail_activity_data_todo"),
        required=True,
        domain="['|', ('res_model', '=', False), '&', ('res_model', '!=', False), ('res_model', '=', parent.res_model)]",
        ondelete="restrict",
    )
    delay_count = fields.Integer(
        string="Interval",
        help="Number of days/week/month before executing the action after or before the scheduled plan date.",
    )
    delay_from = fields.Selection(
        selection=[
            ("before_plan_date", "Before Plan Date"),
            ("after_plan_date", "After Plan Date"),
        ],
        string="Trigger",
        default="before_plan_date",
        required=True,
    )
    icon = fields.Char(
        related="activity_type_id.icon",
        string="Icon",
        readonly=True,
    )
    summary = fields.Char(
        compute="_compute_summary",
        store=True,
        readonly=False,
    )
    responsible_type = fields.Selection(
        selection=[
            ("on_demand", "Ask at launch"),
            ("other", "Default user"),
        ],
        string="Assignment",
        compute="_compute_responsible_type",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )
    responsible_id: ResUsers = fields.Many2one(
        comodel_name="res.users",
        string="Assigned to",
        compute="_compute_responsible_id",
        store=True,
        readonly=False,
        check_company=True,
    )
    note = fields.Html(
        compute="_compute_note",
        store=True,
        readonly=False,
    )
    next_activity_ids: MailActivityType = fields.Many2many(
        comodel_name="mail.activity.type",
        string="Next Activities",
        compute="_compute_next_activity_ids",
        store=True,
        readonly=False,
    )

    @api.constrains("activity_type_id", "plan_id")
    def _check_activity_type_res_model(self) -> None:
        for template in self.filtered(lambda tpl: tpl.activity_type_id.res_model):
            if template.activity_type_id.res_model != template.plan_id.res_model:
                raise ValidationError(
                    _(
                        'The activity type "%(activity_type_name)s" is not compatible with the plan "%(plan_name)s"'
                        ' because it is limited to the model "%(activity_type_model)s".',
                        activity_type_name=template.activity_type_id.name,
                        activity_type_model=template.activity_type_id.res_model,
                        plan_name=template.plan_id.name,
                    )
                )

    @api.constrains("responsible_id", "responsible_type")
    def _check_responsible(self) -> None:
        for template in self:
            if template.responsible_type == "other" and not template.responsible_id:
                raise ValidationError(
                    _(
                        'When selecting "Default user" assignment, you must specify a responsible.'
                    )
                )

    @api.depends("activity_type_id")
    def _compute_next_activity_ids(self) -> None:
        for template in self:
            activity_type = template.activity_type_id
            if activity_type.triggered_next_type_id:
                template.next_activity_ids = activity_type.triggered_next_type_id.ids
            elif activity_type.suggested_next_type_ids:
                template.next_activity_ids = activity_type.suggested_next_type_ids.ids
            else:
                template.next_activity_ids = False

    @api.depends("activity_type_id")
    def _compute_note(self) -> None:
        for template in self:
            template.note = template.activity_type_id.default_note

    @api.depends("activity_type_id", "responsible_type")
    def _compute_responsible_id(self) -> None:
        for template in self:
            template.responsible_id = template.activity_type_id.default_user_id
            if template.responsible_type != "other" and template.responsible_id:
                template.responsible_id = False

    @api.depends("activity_type_id")
    def _compute_responsible_type(self) -> None:
        for template in self:
            if template.activity_type_id.default_user_id:
                template.responsible_type = "other"
            else:
                template.responsible_type = "on_demand"

    @api.depends("activity_type_id")
    def _compute_summary(self) -> None:
        for template in self:
            template.summary = template.activity_type_id.summary

    def _get_date_deadline(self, base_date: date | Literal[False] = False) -> date:
        self.check_singleton()
        base_date = base_date or fields.Date.context_today(self)
        delta = self._get_delay_delta()
        if self.delay_from == "after_plan_date":
            return base_date + delta
        return base_date - delta

    def _get_responsible_and_complaints(
        self, on_demand_responsible: ResUsers, applied_on_record: models.BaseModel
    ) -> dict:
        self.check_singleton()
        error = False
        warning = False
        if self.responsible_type == "other":
            responsible = self.responsible_id
        elif self.responsible_type == "on_demand":
            responsible = on_demand_responsible
            if not responsible:
                error = _(
                    "No responsible specified for %(activity_type_name)s: %(activity_summary)s.",
                    activity_type_name=self.activity_type_id.name,
                    activity_summary=self.summary or "-",
                )
        else:
            raise ValueError(f"Invalid responsible value {self.responsible_type}.")
        _debug.logic(
            "plan_responsible",
            template=self.id,
            record=applied_on_record.id,
            by=self.responsible_type,
            responsible=responsible.id or None,
            error=bool(error),
        )
        return {
            "responsible": responsible,
            "error": error,
            "warning": warning,
        }
