import logging
import typing
from collections.abc import Collection, Iterable, Mapping, Sequence
from datetime import UTC, date, datetime
from types import NotImplementedType
from typing import Any, Literal

from odoo import api, fields, models
from odoo.api import DomainType, ValuesType
from odoo.fields import Domain, Field
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, Query, partition

if typing.TYPE_CHECKING:
    from .mail_activity import MailActivity
    from .mail_activity_type import MailActivityType
    from odoo.addons.bus.models.res_users import ResUsers

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_DEADLINE_LAST = date.max


class MixinMailActivity(models.AbstractModel):
    _name = "mixin.mail.activity"
    _description = "Activity Mixin"

    def _get_default_activity_type(self) -> MailActivityType:
        return self.env["mail.activity"]._default_activity_type_for_model(self._name)

    activity_ids: MailActivity = fields.One2many(
        comodel_name="mail.activity",
        inverse_name="res_id",
        string="Activities",
        bypass_search_access=True,
        groups="base.group_user",
    )
    activity_state = fields.Selection(
        selection=[("overdue", "Overdue"), ("today", "Today"), ("planned", "Planned")],
        compute="_compute_activity_state",
        search="_search_activity_state",
        group_by_sql="_activity_state_group_sql",
        order_by_sql="_activity_order_sql",
        groups="base.group_user",
        help="Status based on activities\nOverdue: Due date is already passed\n"
        "Today: Activity date is today\nPlanned: Future activities.",
    )
    activity_user_id: ResUsers = fields.Many2one(
        comodel_name="res.users",
        string="Responsible User",
        compute="_compute_activity_user_id",
        search="_search_activity_user_id",
        readonly=True,
        groups="base.group_user",
    )
    activity_type_id: MailActivityType = fields.Many2one(
        comodel_name="mail.activity.type",
        string="Next Activity Type",
        compute="_compute_activity_next",
        inverse="_inverse_activity_type_id",
        search="_search_activity_type_id",
        readonly=False,
        groups="base.group_user",
    )
    activity_type_icon = fields.Char(
        compute="_compute_activity_next",
        groups="base.group_user",
    )
    activity_date_deadline = fields.Date(
        string="Next Activity Deadline",
        compute="_compute_activity_date_deadline",
        search="_search_activity_date_deadline",
        readonly=True,
        order_by_sql="_activity_order_sql",
        groups="base.group_user",
    )
    my_activity_date_deadline = fields.Date(
        string="My Activity Deadline",
        compute="_compute_my_activity_date_deadline",
        search="_search_my_activity_date_deadline",
        readonly=True,
        order_by_sql="_activity_order_sql",
        groups="base.group_user",
    )
    activity_summary = fields.Char(
        string="Next Activity Summary",
        compute="_compute_activity_next",
        inverse="_inverse_activity_summary",
        search="_search_activity_summary",
        readonly=False,
        groups="base.group_user",
    )
    activity_exception_decoration = fields.Selection(
        selection=[("warning", "Alert"), ("danger", "Error")],
        compute="_compute_activity_exception_type",
        search="_search_activity_exception_decoration",
        groups="base.group_user",
        help="Type of the exception activity on record.",
    )
    activity_exception_icon = fields.Char(
        string="Icon",
        compute="_compute_activity_exception_type",
        groups="base.group_user",
        help="Icon to indicate an exception activity.",
    )

    ACTIVITY_STATE_URGENCY = ("overdue", "today", "planned")

    @api.model
    def _most_urgent_activity_state(
        self,
        states: Iterable[str | Literal[False]],
        among: Sequence[str] | None = None,
        fallback: Any = False,
    ) -> Any:
        present = {state for state in states if state}
        order = among if among is not None else self.ACTIVITY_STATE_URGENCY
        return next((state for state in order if state in present), fallback)

    def _open_activities(self) -> MailActivity:
        activities = self.activity_ids
        return activities.filtered("active").with_prefetch(activities._prefetch_ids)

    def _next_activity(self, user_id: int | None = None) -> MailActivity:
        self.check_singleton()
        activities = self._open_activities()
        if user_id is not None:
            activities = (
                activity for activity in activities if activity.user_id.id == user_id
            )
        return min(
            activities,
            key=lambda activity: (
                activity.date_deadline or _DEADLINE_LAST,
                activity.id,
            ),
            default=self.env["mail.activity"],
        )

    @api.depends(
        "activity_ids.active",
        "activity_ids.activity_type_id.decoration_type",
        "activity_ids.activity_type_id.icon",
    )
    def _compute_activity_exception_type(self) -> None:
        ActivityType = self.env["mail.activity.type"]
        for record in self:
            by_decoration = record._open_activities().activity_type_id.grouped(
                "decoration_type"
            )
            exception_type = (
                by_decoration.get("danger", ActivityType)
                or by_decoration.get("warning", ActivityType)
            )[:1]
            record.activity_exception_decoration = exception_type.decoration_type
            record.activity_exception_icon = exception_type.icon

    @api.depends(
        "activity_ids.active", "activity_ids.date_deadline", "activity_ids.user_id"
    )
    def _compute_activity_user_id(self) -> None:
        for record in self:
            record.activity_user_id = record._next_activity().user_id

    @api.depends(
        "activity_ids.active",
        "activity_ids.date_deadline",
        "activity_ids.summary",
        "activity_ids.activity_type_id.icon",
    )
    def _compute_activity_next(self) -> None:
        for record in self:
            activity = record._next_activity()
            record.activity_summary = activity.summary
            record.activity_type_id = activity.activity_type_id
            record.activity_type_icon = activity.activity_type_id.icon

    def _inverse_activity_summary(self) -> None:
        for record in self:
            record._next_activity().summary = record.activity_summary

    def _inverse_activity_type_id(self) -> None:
        for record in self:
            record._next_activity().activity_type_id = record.activity_type_id

    @api.depends("activity_ids.active", "activity_ids.state")
    def _compute_activity_state(self) -> None:
        for record in self:
            record.activity_state = self._most_urgent_activity_state(
                record._open_activities().mapped("state")
            )

    def _get_domain_open_activity(
        self,
        subdomain: Domain | Sequence[tuple] = (),
        user_id: int | None = None,
    ) -> Domain:
        domain = Domain("active", "=", True) & Domain(subdomain)
        if user_id is not None:
            domain &= Domain("user_id", "=", user_id)
        return Domain("activity_ids", "any", domain)

    def _get_domain_next_activity(
        self, subdomain: Sequence[tuple], user_id: int | None = None
    ) -> Domain:
        return Domain(
            "activity_ids",
            "any",
            self.env["mail.activity"]._next_activity_query(
                self._name, subdomain, user_id=user_id
            ),
        )

    def _search_next_activity_field(
        self,
        fname: str,
        operator: str,
        operand: Any,
        user_id: int | None = None,
    ) -> Domain | NotImplementedType:
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        domain = self._get_domain_next_activity(
            [(fname, operator, operand)], user_id=user_id
        )
        if operator == "in" and False in operand:
            domain |= ~self._get_domain_open_activity(user_id=user_id)
        return domain

    def _activity_state_domains(self, states: Collection[str]) -> list[Domain]:
        Activity = self.env["mail.activity"]
        moment = datetime.now(UTC)
        overdue = (
            self._get_domain_open_activity(Activity._domain_deadline_today("<", moment))
            if not states.isdisjoint(("overdue", "today"))
            else Domain.FALSE
        )
        domains = []
        if "overdue" in states:
            domains.append(overdue)
        if "today" in states:
            domains.append(
                self._get_domain_open_activity(
                    Activity._domain_deadline_today("=", moment)
                )
                & ~overdue
            )
        if "planned" in states:
            domains.append(
                self._get_domain_open_activity()
                & ~self._get_domain_open_activity(
                    Activity._domain_deadline_today("<=", moment)
                )
            )
        return domains

    def _search_activity_state(
        self, operator: str, value: Any
    ) -> Domain | NotImplementedType:
        all_states = {"overdue", "today", "planned", False}
        if operator == "in":
            search_states = set(value) & all_states
        elif operator == "not in":
            search_states = all_states - set(value)
        else:
            return NotImplemented

        reverse_search = False
        if False in search_states:
            reverse_search = True
            search_states = all_states - search_states

        if not search_states:
            matching = Domain.FALSE
        elif search_states == all_states - {False}:
            matching = self._get_domain_open_activity()
        else:
            matching = Domain.OR(self._activity_state_domains(search_states))

        return ~matching if reverse_search else matching

    @api.depends("activity_ids.active", "activity_ids.date_deadline")
    def _compute_activity_date_deadline(self) -> None:
        for record in self:
            record.activity_date_deadline = record._next_activity().date_deadline

    def _first_deadline_domain(
        self, operator: str, operand: Any, user_id: int | None = None
    ) -> Domain | NotImplementedType:
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented

        def open_activities(subdomain: Domain | Sequence[tuple] = ()) -> Domain:
            return self._get_domain_open_activity(subdomain, user_id=user_id)

        if operator in ("<", "<="):
            return open_activities([("date_deadline", operator, operand)])
        if operator in (">", ">="):
            earlier = "<=" if operator == ">" else "<"
            return open_activities() & ~open_activities(
                [("date_deadline", earlier, operand)]
            )
        if operator != "in":
            return NotImplemented

        domain = Domain.FALSE
        for value in operand:
            if value is False:
                domain |= ~open_activities()
            else:
                domain |= open_activities(
                    [("date_deadline", "=", value)]
                ) & ~open_activities([("date_deadline", "<", value)])
        return domain

    def _search_activity_date_deadline(
        self, operator: str, operand: Any
    ) -> Domain | NotImplementedType:
        return self._first_deadline_domain(operator, operand)

    def _search_activity_user_id(
        self, operator: str, operand: Any
    ) -> Domain | NotImplementedType:
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        if operator != "in":
            return self._search_next_activity_field("user_id", operator, operand)
        bools, values = partition(lambda v: isinstance(v, bool), operand)
        domain = Domain.FALSE
        if True in bools:
            domain |= self._get_domain_next_activity([("user_id", "!=", False)])
        if False in bools:
            domain |= (
                self._get_domain_next_activity([("user_id", "=", False)])
                | ~self._get_domain_open_activity()
            )
        if values:
            domain |= self._search_next_activity_field("user_id", "in", values)
        return domain

    def _search_activity_type_id(
        self, operator: str, operand: Any
    ) -> Domain | NotImplementedType:
        return self._search_next_activity_field("activity_type_id", operator, operand)

    def _search_activity_summary(
        self, operator: str, operand: Any
    ) -> Domain | NotImplementedType:
        return self._search_next_activity_field("summary", operator, operand)

    def _search_activity_exception_decoration(
        self, operator: str, operand: Any
    ) -> Domain | NotImplementedType:
        if operator != "in":
            return NotImplemented
        danger = self._get_domain_open_activity(
            [("activity_type_id.decoration_type", "=", "danger")]
        )
        warning = self._get_domain_open_activity(
            [("activity_type_id.decoration_type", "=", "warning")]
        )
        domain_by_value = {
            "danger": danger,
            "warning": warning & ~danger,
            False: ~danger & ~warning,
        }
        domain = Domain.FALSE
        for value in set(operand):
            domain |= domain_by_value.get(value or False, Domain.FALSE)
        return domain

    @api.depends(
        "activity_ids.active", "activity_ids.date_deadline", "activity_ids.user_id"
    )
    @api.depends_context("uid")
    def _compute_my_activity_date_deadline(self) -> None:
        for record in self:
            record.my_activity_date_deadline = record._my_next_activity().date_deadline

    def _search_my_activity_date_deadline(
        self, operator: str, operand: Any
    ) -> Domain | NotImplementedType:
        return self._first_deadline_domain(operator, operand, user_id=self.env.uid)

    def write(self, vals: ValuesType) -> Literal[True]:
        result = super().write(vals)
        if not self._display_name_field_names().isdisjoint(vals):
            activities = self.sudo().with_context(active_test=False).activity_ids
            _debug.logic(
                "res_name_recompute_queued",
                model=self._name,
                records=len(self),
                activities=len(activities),
            )
            if activities:
                self.env.add_to_compute(
                    self.env["mail.activity"]._fields["res_name"], activities
                )
        return result

    def _activity_aggregate_join(
        self, alias: str, query: Query, user_id: int | None = None
    ) -> str:
        link = "next_activity" if user_id is None else "my_next_activity"
        join_alias = Query.get_table_alias(alias, link)
        if join_alias in query._joins:
            return join_alias
        Activity = self.env["mail.activity"]
        Activity.flush_model(
            ["active", "date_deadline", "res_id", "res_model", "user_id", "user_tz"]
        )
        condition = SQL("res_model = %s AND active = true", self._name)
        if user_id is not None:
            condition = SQL("%s AND user_id = %s", condition, user_id)
        sql_join = SQL(
            "(SELECT res_id, MIN(%s) AS state, MIN(date_deadline) AS date_deadline"
            " FROM mail_activity WHERE %s GROUP BY res_id)",
            Activity._sql_state(),
            condition,
        )
        return query.left_join(alias, "id", sql_join, "res_id", link)

    def _activity_state_join(self, alias: str, query: Query) -> SQL:
        return SQL.identifier(self._activity_aggregate_join(alias, query), "state")

    def _activity_state_group_sql(self, field: Field, alias: str, query: Query) -> SQL:
        return SQL(
            """CASE %s
                    WHEN -1 THEN 'overdue'
                    WHEN 0 THEN 'today'
                    WHEN 1 THEN 'planned'
               END""",
            self._activity_state_join(alias, query),
        )

    def _activity_order_sql(
        self, field: Field, alias: str, direction: SQL, nulls: SQL, query: Query
    ) -> SQL:
        if field.name == "activity_state":
            sql_value = self._activity_state_join(alias, query)
        else:
            join_alias = self._activity_aggregate_join(
                alias,
                query,
                user_id=self.env.uid if field.name.startswith("my_") else None,
            )
            sql_value = SQL.identifier(join_alias, "date_deadline")
        # a record with no activity sorts last whichever way the deadline goes
        return self._order_value_to_sql(
            sql_value, direction, nulls if nulls.code else SQL("NULLS LAST"), query
        )

    def _my_next_activity(self) -> MailActivity:
        return self._next_activity(self.env.uid)

    def _my_next_activities(self) -> MailActivity:
        return self.env["mail.activity"].browse(
            activity_id
            for record in self
            if (activity_id := record._my_next_activity().id)
        )

    def action_reschedule_my_next_today(self) -> None:
        self._my_next_activities().action_reschedule_today()

    def action_reschedule_my_next_tomorrow(self) -> None:
        self._my_next_activities().action_reschedule_tomorrow()

    def action_reschedule_my_next_nextweek(self) -> None:
        self._my_next_activities().action_reschedule_nextweek()

    def _activity_type_from_xmlid(self, xmlid: str) -> MailActivityType:
        ModelData = self.env["ir.model.data"].sudo()
        model, res_id = ModelData._xmlid_to_res_model_res_id(xmlid)
        if model and model != "mail.activity.type":
            _logger.warning("Xml id %s names a %s, not an activity type", xmlid, model)
            return self.env["mail.activity.type"]
        return self.env["mail.activity.type"].browse(res_id or ())

    def _get_activity_type_ids(self, act_type_xmlids: Sequence[str]) -> list[int]:
        return [
            activity_type.id
            for xmlid in act_type_xmlids
            if (activity_type := self._activity_type_from_xmlid(xmlid))
        ]

    def activity_search(
        self,
        act_type_xmlids: Sequence[str] = (),
        user_id: int | None = None,
        additional_domain: DomainType | None = None,
        only_automated: bool = True,
    ) -> MailActivity:
        if self.env.context.get("mail_activity_automation_skip"):
            _debug.logic(
                "activity_search_skipped", model=self._name, reason="automation_skip"
            )
            return self.env["mail.activity"]

        activity_types_ids = self._get_activity_type_ids(act_type_xmlids)
        if not activity_types_ids:
            _debug.logic(
                "activity_search_skipped",
                model=self._name,
                reason="no_type",
                xmlids=list(act_type_xmlids),
            )
            return self.env["mail.activity"]

        domain = Domain(
            [
                ("res_model", "=", self._name),
                ("res_id", "in", self.ids),
                ("activity_type_id", "in", activity_types_ids),
            ]
        )

        if only_automated:
            domain &= Domain("automated", "=", True)
        if user_id is not None:
            domain &= Domain("user_id", "=", user_id)
        if additional_domain:
            domain &= Domain(additional_domain)

        return self.env["mail.activity"].search(domain)

    def activity_schedule(
        self,
        act_type_xmlid: str = "",
        date_deadline: date | None = None,
        summary: str = "",
        note: str = "",
        **act_values,
    ) -> MailActivity:
        if self.env.context.get("mail_activity_automation_skip"):
            return self.env["mail.activity"]

        return self._activity_create(
            self._activity_type_for_schedule(act_type_xmlid, act_values),
            date_deadline,
            summary,
            dict.fromkeys(self._ids, note),
            act_values,
        )

    def _activity_type_for_schedule(
        self, act_type_xmlid: str, act_values: dict
    ) -> MailActivityType:
        if act_type_xmlid:
            activity_type = self._activity_type_from_xmlid(act_type_xmlid)
            if not activity_type:
                _debug.logic(
                    "activity_type_fallback",
                    model=self._name,
                    xmlid=act_type_xmlid,
                    reason="unknown_xmlid",
                )
                _logger.warning(
                    "Unknown activity type xml id %s on %s, falling back on the "
                    "model's default type",
                    act_type_xmlid,
                    self._name,
                )
        else:
            activity_type = self.env["mail.activity.type"].browse(
                act_values.get("activity_type_id") or ()
            )
        if activity_type.res_model and activity_type.res_model != self._name:
            _debug.logic(
                "activity_type_fallback",
                model=self._name,
                xmlid=act_type_xmlid or None,
                reason="model_mismatch",
            )
            _logger.warning(
                "Invalid activity type model %s used on %s (tried with xml id "
                "%s), falling back on the model's default type",
                activity_type.res_model,
                self._name,
                act_type_xmlid or "",
            )
            activity_type = self.env["mail.activity.type"]
        return activity_type or self._get_default_activity_type()

    def _activity_create(
        self,
        activity_type: MailActivityType,
        date_deadline: date | None,
        summary: str,
        notes: Mapping[int, str],
        act_values: dict,
    ) -> MailActivity:
        assignee = (
            self.env["mail.activity"]._assignee_of(act_values)
            or activity_type.default_user_id
        )
        if not date_deadline:
            date_deadline = self.env["mail.activity"]._today_for(assignee)
        if isinstance(date_deadline, datetime):
            _debug.logic("deadline_is_datetime", model=self._name)
            _logger.warning(
                "Scheduled deadline should be a date (got %s)", date_deadline
            )
        shared = {
            "summary": summary or activity_type.summary,
            "automated": True,
            "date_deadline": date_deadline,
            "res_model_id": self.env["ir.model"]._get(self._name).id,
            **act_values,
            "activity_type_id": activity_type.id,
        }
        if assignee and not shared.get("user_id"):
            shared["user_id"] = assignee.id
        default_note = activity_type.default_note
        _debug.lifecycle(
            "activity_scheduled",
            model=self._name,
            records=len(self),
            activity_type=activity_type.id,
            user=shared.get("user_id"),
            deadline=date_deadline,
        )
        return self.env["mail.activity"].create(
            [
                {
                    **shared,
                    "note": notes.get(record.id) or default_note,
                    "res_id": record.id,
                }
                for record in self
            ]
        )

    def _activity_schedule_with_view(
        self,
        act_type_xmlid: str = "",
        date_deadline: date | None = None,
        summary: str = "",
        views_or_xmlid: models.BaseModel | str = "",
        render_context: dict | None = None,
        **act_values,
    ) -> MailActivity:
        if self.env.context.get("mail_activity_automation_skip"):
            return self.env["mail.activity"]

        view_ref = (
            views_or_xmlid.id
            if isinstance(views_or_xmlid, models.BaseModel)
            else views_or_xmlid
        )
        base_context = render_context or {}
        notes = {
            record.id: self.env["ir.qweb"]._render(
                view_ref,
                {**base_context, "object": record},
                minimal_qcontext=True,
                raise_if_not_found=False,
            )
            for record in self
        }
        return self._activity_create(
            self._activity_type_for_schedule(act_type_xmlid, act_values),
            date_deadline,
            summary,
            notes,
            act_values,
        )

    def activity_reschedule(
        self,
        act_type_xmlids: Sequence[str],
        user_id: int | None = None,
        date_deadline: date | None = None,
        new_user_id: int | None = None,
        only_automated: bool = True,
    ) -> MailActivity:
        activities = self.activity_search(
            act_type_xmlids, user_id=user_id, only_automated=only_automated
        )
        write_vals = {}
        if date_deadline:
            write_vals["date_deadline"] = date_deadline
        if new_user_id:
            write_vals["user_id"] = new_user_id
        _debug.lifecycle(
            "activity_rescheduled",
            model=self._name,
            activities=len(activities),
            fields=list(write_vals),
        )
        if activities and write_vals:
            activities.write(write_vals)
        return activities

    def activity_feedback(
        self,
        act_type_xmlids: Sequence[str],
        user_id: int | None = None,
        feedback: str | None = None,
        attachment_ids: list[int] | None = None,
        only_automated: bool = True,
    ) -> MailActivity:
        activities = self.activity_search(
            act_type_xmlids, user_id=user_id, only_automated=only_automated
        )
        _debug.lifecycle(
            "activity_feedback", model=self._name, activities=len(activities)
        )
        if activities:
            activities.action_feedback(feedback=feedback, attachment_ids=attachment_ids)
        return activities

    def activity_unlink(
        self,
        act_type_xmlids: Sequence[str],
        user_id: int | None = None,
        only_automated: bool = True,
    ) -> MailActivity:
        activities = self.activity_search(
            act_type_xmlids, user_id=user_id, only_automated=only_automated
        )
        _debug.lifecycle(
            "activity_unlinked", model=self._name, activities=len(activities)
        )
        activities.unlink()
        return activities
