import logging
import typing
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from datetime import UTC, date, datetime, timedelta
from operator import eq, ge, gt, le, lt
from types import NotImplementedType
from typing import Literal, Self

from dateutil.relativedelta import MO, relativedelta

from odoo import _, api, fields, models
from odoo.api import DomainType, ValuesType
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, Query, is_html_empty
from odoo.tools.misc import clean_context, get_lang

from odoo.addons.mail.tools import activity_calendar
from odoo.addons.mail.tools.access_scan import (
    get_accessible_query,
    prepare_column_fetcher,
    prepare_document_access_error,
    stable_order,
)
from odoo.addons.mail.tools.discuss import Store, StoreFieldsInput

if typing.TYPE_CHECKING:
    from .mail_activity_type import MailActivityType
    from .mail_message import MailMessage
    from .mail_template import MailTemplate
    from .res_partner import ResPartner
    from odoo.addons.base.models.ir_model import IrModel
    from odoo.addons.bus.models.ir_attachment import IrAttachment
    from odoo.addons.bus.models.res_users import ResUsers

type TodoKey = tuple[str, int]
type TodoKeys = set[TodoKey]
type TodoKeysByUser = dict[ResUsers, TodoKeys]
type AccessRow = tuple[
    int, str | Literal[False] | None, int | None, int | Literal[False] | None
]

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

ORPHAN_BUCKET = "mail.activity"


class MailActivity(models.Model):
    _name = "mail.activity"
    _description = "Activity"
    _order = "date_deadline ASC, id ASC"
    _rec_name = "summary"
    _search_visibility_fields = (
        "res_model",
        "res_id",
        "user_id",
    )

    @api.model
    def default_get(self, fields: list[str]) -> ValuesType:
        res = super().default_get(fields)
        if "res_model_id" in fields and res.get("res_model"):
            res["res_model_id"] = self.env["ir.model"]._get(res["res_model"]).id
        return res

    @api.model
    def _default_activity_type_id(self) -> MailActivityType:
        default_vals = self.default_get(["res_model_id", "res_model"])
        current_model = default_vals.get("res_model")
        if not current_model and default_vals.get("res_model_id"):
            current_model = (
                self.env["ir.model"].sudo().browse(default_vals["res_model_id"]).model
            )
        return self._default_activity_type_for_model(current_model)

    @api.model
    def _default_date_deadline(self) -> date:
        return self._today_for(self._assignee_of({}))

    @api.model
    def _default_activity_type_for_model(self, model: str) -> MailActivityType:
        if model:
            return self.env["mail.activity.type"].search(
                ["|", ("res_model", "=", model), ("res_model", "=", False)], limit=1
            )
        return self.env["mail.activity.type"].search(
            [("res_model", "=", False)], limit=1
        )

    res_model_id: IrModel = fields.Many2one(
        comodel_name="ir.model",
        string="Document Model",
        index=True,
        required=False,
        ondelete="cascade",
    )
    res_model = fields.Char(  # noqa: E8529  CHECK mail_activity_check_res_id_is_set_if_model; CHECK mail_activity_check_user_id_is_set_if_model; index (res_model, res_id)
        related="res_model_id.model",
        string="Related Document Model",
        precompute=True,
        store=True,
        readonly=True,
    )
    res_id = fields.Many2oneReference(
        model_field="res_model",
        string="Related Document ID",
    )
    res_name = fields.Char(
        string="Document Name",
        compute="_compute_res_name",
        compute_sudo=True,
        store=True,
        readonly=True,
    )
    activity_type_id: MailActivityType = fields.Many2one(
        comodel_name="mail.activity.type",
        default=_default_activity_type_id,
        domain="['|', ('res_model', '=', False), ('res_model', '=', res_model)]",
        ondelete="restrict",
    )
    activity_category = fields.Selection(
        related="activity_type_id.category",
        readonly=True,
    )
    activity_decoration = fields.Selection(
        related="activity_type_id.decoration_type",
        readonly=True,
    )
    icon = fields.Char(
        related="activity_type_id.icon",
        string="Icon",
        readonly=True,
    )
    summary = fields.Char()
    note = fields.Html(sanitize_style=True)
    date_deadline = fields.Date(
        string="Due Date",
        default=_default_date_deadline,
        index=True,
        required=True,
    )
    date_done = fields.Date(
        string="Done Date",
        compute="_compute_date_done",
        store=True,
    )
    feedback = fields.Text()
    automated = fields.Boolean(
        string="Automated activity",
        readonly=True,
        help="Indicates this activity has been created automatically and not by any user.",
    )
    attachment_ids: IrAttachment = fields.Many2many(
        comodel_name="ir.attachment",
        relation="activity_attachment_rel",
        column1="activity_id",
        column2="attachment_id",
        string="Attachments",
        bypass_search_access=True,
    )
    user_id: ResUsers = fields.Many2one(
        comodel_name="res.users",
        string="Assigned to",
        index=True,
        required=False,
        ondelete="cascade",
    )
    user_tz = fields.Selection(  # noqa: E8529  _sql_today builds a CASE on alias.user_tz; the source is two joins away (res_users, res_partner)
        related="user_id.tz",
        string="Timezone",
        store=True,
    )
    state = fields.Selection(
        selection=[
            ("overdue", "Overdue"),
            ("today", "Today"),
            ("planned", "Planned"),
            ("done", "Done"),
        ],
        compute="_compute_state",
        search="_search_state",
    )
    recommended_activity_type_id: MailActivityType = fields.Many2one(
        comodel_name="mail.activity.type"
    )
    previous_activity_type_id: MailActivityType = fields.Many2one(
        comodel_name="mail.activity.type",
        readonly=True,
    )
    has_recommended_activities = fields.Boolean(
        string="Next activities available",
        compute="_compute_has_recommended_activities",
    )
    mail_template_ids: MailTemplate = fields.Many2many(
        related="activity_type_id.mail_template_ids",
        readonly=True,
    )
    chaining_type = fields.Selection(
        related="activity_type_id.chaining_type",
        readonly=True,
    )
    can_write = fields.Boolean(compute="_compute_can_write")
    active = fields.Boolean(default=True)

    _SEARCH_ACCESS_CHUNK_MIN = 80
    _SEARCH_ACCESS_CHUNK_MAX = 8192
    _GC_BATCH = 10_000
    _VIEW_DATA_MAX_LIMIT = 1_000

    _DEADLINE_OPERATORS = {
        "<": (lt, SQL("<")),
        "<=": (le, SQL("<=")),
        "=": (eq, SQL("=")),
        ">=": (ge, SQL(">=")),
        ">": (gt, SQL(">")),
    }

    _res_model_res_id_index = models.Index("(res_model, res_id)")

    _check_res_id_is_set_if_model = models.Constraint(
        """CHECK(
            (COALESCE(res_model, '') <> '' AND (res_id IS NOT NULL AND res_id != 0)) OR
            (COALESCE(res_model, '') = '' AND (res_id IS NULL OR res_id = 0))
        )""",
        "Activities have to be linked to records with a not null res_id.",
    )
    _check_user_id_is_set_if_model = models.Constraint(
        """CHECK(
            (COALESCE(res_model, '') <> '' OR user_id IS NOT NULL)
        )""",
        "Activities must be assigned if not attached to a document.",
    )

    @api.depends("previous_activity_type_id.suggested_next_type_ids")
    @api.onchange("previous_activity_type_id")
    def _compute_has_recommended_activities(self) -> None:
        for record in self:
            record.has_recommended_activities = bool(
                record.previous_activity_type_id.suggested_next_type_ids
            )

    @api.onchange("previous_activity_type_id")
    def _onchange_previous_activity_type_id(self) -> None:
        for record in self:
            if record.previous_activity_type_id.triggered_next_type_id:
                record.activity_type_id = (
                    record.previous_activity_type_id.triggered_next_type_id
                )

    @api.depends("active")
    def _compute_date_done(self) -> None:
        unarchived = self.filtered("active")
        unarchived.date_done = False
        toupdate = (self - unarchived).filtered(lambda act: not act.date_done)
        by_tz = toupdate.grouped("user_tz")
        today_by_tz = self._today_by_tz(by_tz)
        for tz, activities in by_tz.items():
            activities.date_done = today_by_tz[tz]

    @api.depends("res_model", "res_id")
    def _compute_res_name(self) -> None:
        linked = self._filtered_document_backed()
        (self - linked).res_name = False
        if not linked:
            return
        for model, activities, res_ids in linked._activities_with_records():
            records = self.env[model].browse(res_ids)
            try:
                name_by_id = self._names_by_id(records)
            except MissingError:
                name_by_id = self._names_by_id(records.exists())
            for activity in activities:
                activity.res_name = name_by_id.get(activity.res_id, False)

    @api.model
    def _names_by_id(self, records: models.BaseModel) -> dict[int, str]:
        return dict(records.mapped(lambda record: (record.id, record.display_name)))

    @api.depends("active", "date_deadline", "user_tz")
    def _compute_state(self) -> None:
        self.state = False
        dated = self.filtered("date_deadline")
        done = dated.filtered(lambda activity: not activity.active)
        done.state = "done"
        by_tz = (dated - done).grouped("user_tz")
        today_by_tz = self._today_by_tz(by_tz)
        for tz, activities in by_tz.items():
            today = today_by_tz[tz]
            for activity in activities:
                activity.state = self._state_for(activity.date_deadline, today)

    @api.model
    def _state_for(self, date_deadline: date, today: date) -> str:
        return activity_calendar.state_for(date_deadline, today)

    @api.model
    def _today_in_tz(
        self, tz: str | Literal[False] = False, moment: datetime | None = None
    ) -> date:
        return activity_calendar.today_in_tz(tz, moment)

    @api.model
    def _today_by_tz(
        self,
        tzs: Iterable[str | Literal[False]],
        moment: datetime | None = None,
    ) -> dict[str | Literal[False], date]:
        return activity_calendar.today_by_tz(tzs, moment)

    @api.model
    def _today_for(self, user: ResUsers | None = None) -> date:
        return self._today_in_tz(user.sudo().tz if user else False)

    @api.model
    def _days_elsewhere(
        self, moment: datetime | None = None
    ) -> list[tuple[date, tuple[str, ...]]]:
        return activity_calendar.days_elsewhere(moment)

    @api.model
    def _domain_deadline_today(
        self, operator: str, moment: datetime | None = None
    ) -> Domain:
        moment = moment or datetime.now(UTC)
        compare, sql_operator = self._DEADLINE_OPERATORS[operator]

        def to_sql(model: models.BaseModel, alias: str, query: Query) -> SQL:
            return SQL(
                "%s %s %s",
                SQL.identifier(alias, "date_deadline"),
                sql_operator,
                model._sql_today(alias, moment),
            )

        def predicate(record: models.BaseModel) -> bool:
            deadline = record.date_deadline
            return bool(deadline) and compare(
                deadline, record._today_in_tz(record.user_tz, moment)
            )

        return Domain.custom(to_sql=to_sql, predicate=predicate)

    @api.model
    def _search_state(
        self, operator: str, value: typing.Any
    ) -> Domain | NotImplementedType:
        states = ("done", "overdue", "today", "planned")
        if operator == "in":
            wanted = set(states) & set(value)
        elif operator == "not in":
            wanted = set(states) - set(value)
        else:
            return NotImplemented
        if not wanted:
            return Domain.FALSE
        moment = datetime.now(UTC)
        open_ = Domain("active", "=", True)
        by_state = {
            "done": lambda: Domain("active", "=", False),
            "overdue": lambda: open_ & self._domain_deadline_today("<", moment),
            "today": lambda: open_ & self._domain_deadline_today("=", moment),
            "planned": lambda: open_ & self._domain_deadline_today(">", moment),
        }
        return Domain.OR(by_state[state]() for state in states if state in wanted)

    @api.model
    def _domain_todo(self, user: ResUsers | None = None) -> Domain:
        assignee = (
            Domain("user_id", "=", user.id) if user else Domain("user_id", "!=", False)
        )
        return (
            Domain("active", "=", True) & assignee & self._domain_deadline_today("<=")
        )

    @api.model
    def _sql_today(
        self, alias: str = "mail_activity", moment: datetime | None = None
    ) -> SQL:
        moment = moment or datetime.now(UTC)
        fallback = self._today_in_tz(False, moment)
        other_days = self._days_elsewhere(moment)
        if not other_days:
            return SQL("%s::date", fallback)
        user_tz = SQL("%s::text", SQL.identifier(alias, "user_tz"))
        branches = SQL(" ").join(
            SQL("WHEN %s = ANY(%s::text[]) THEN %s::date", user_tz, list(names), day)
            for day, names in other_days
        )
        return SQL("(CASE %s ELSE %s::date END)", branches, fallback)

    @api.model
    def _sql_state(self, alias: str = "mail_activity") -> SQL:
        return SQL(
            "SIGN(%s - %s)::int",
            SQL.identifier(alias, "date_deadline"),
            self._sql_today(alias),
        )

    @api.model
    def _next_activity_query(
        self,
        res_model: str,
        subdomain: DomainType = (),
        user_id: int | None = None,
    ) -> Query:
        self.flush_model(["active", "date_deadline", "res_id", "res_model", "user_id"])
        domain = (
            Domain("res_model", "=", res_model)
            & Domain("active", "=", True)
            & Domain(subdomain)
        )
        if user_id is not None:
            domain &= Domain("user_id", "=", user_id)
        query = self._search(domain, bypass_access=True)
        query.add_where(self._sql_no_earlier_activity(query.table, user_id))
        return query

    @api.model
    def _sql_no_earlier_activity(self, alias: str, user_id: int | None = None) -> SQL:
        same_document = SQL(
            "earlier.res_model = %s AND earlier.res_id = %s AND earlier.active",
            SQL.identifier(alias, "res_model"),
            SQL.identifier(alias, "res_id"),
        )
        if user_id is not None:
            same_document = SQL("%s AND earlier.user_id = %s", same_document, user_id)
        return SQL(
            "NOT EXISTS (SELECT 1 FROM mail_activity AS earlier WHERE %s"
            " AND (earlier.date_deadline, earlier.id) < (%s, %s))",
            same_document,
            SQL.identifier(alias, "date_deadline"),
            SQL.identifier(alias, "id"),
        )

    def _filtered_todo(self) -> Self:
        return self.filtered_domain(self._domain_todo())

    def _todo_key(self) -> tuple[str, int]:
        self.check_singleton()
        return (
            (self.res_model, self.res_id)
            if self.res_model
            else (ORPHAN_BUCKET, self.id)
        )

    def _todo_keys(self, within: TodoKeys | None = None) -> TodoKeysByUser:
        result = defaultdict(set)
        for activity in self._filtered_todo():
            key = activity._todo_key()
            if within is None or key in within:
                result[activity.user_id].add(key)
        return result

    def _todo_keys_elsewhere(self, keys: TodoKeys) -> TodoKeysByUser:
        if not keys:
            return {}
        documents = Domain.FALSE
        modelless_ids = []
        by_model = defaultdict(list)
        for res_model, res_id in sorted(keys):
            by_model[res_model].append(res_id)
            if res_model == ORPHAN_BUCKET:
                modelless_ids.append(res_id)
        for res_model, res_ids in by_model.items():
            documents |= Domain("res_model", "=", res_model) & Domain(
                "res_id", "in", res_ids
            )
        if modelless_ids:
            documents |= Domain("id", "in", modelless_ids) & Domain(
                "res_model", "=", False
            )
        domain = self._domain_todo() & documents
        if self.ids:
            domain &= Domain("id", "not in", self.ids)
        return self.sudo().search(domain)._todo_keys(within=keys)

    @staticmethod
    def _merged_todo_keys(*mappings: TodoKeysByUser) -> TodoKeysByUser:
        return {
            user: set().union(*(m.get(user, ()) for m in mappings))
            for user in set().union(*(m.keys() for m in mappings))
        }

    def _notify_todo_count_change(
        self, before: TodoKeysByUser, after: TodoKeysByUser
    ) -> None:
        for user in sorted(before.keys() | after.keys(), key=lambda u: u.id):
            count_diff = len(after.get(user, ())) - len(before.get(user, ()))
            if _debug.logic.enabled and count_diff:
                _debug.logic("todo_count_changed", user=user.id, diff=count_diff)
            if count_diff > 0:
                user._bus_send(
                    "mail.activity/updated",
                    {"activity_created": True, "count_diff": count_diff},
                )
            elif count_diff < 0:
                user._bus_send(
                    "mail.activity/updated",
                    {"activity_deleted": True, "count_diff": count_diff},
                )

    @api.depends("res_model", "res_id", "user_id")
    @api.depends_context("uid")
    def _compute_can_write(self) -> None:
        valid_ids = set(self._filtered_access("write")._ids)
        for record in self:
            record.can_write = record.id in valid_ids

    @api.onchange("activity_type_id")
    def _onchange_activity_type_id(self) -> None:
        if self.activity_type_id:
            if self.activity_type_id.summary:
                self.summary = self.activity_type_id.summary

            self.user_id = self.activity_type_id.default_user_id or self.env.user
            self.date_deadline = self.activity_type_id._get_date_deadline(self.user_id)
            if self.activity_type_id.default_note:
                self.note = self.activity_type_id.default_note

    @api.onchange("recommended_activity_type_id")
    def _onchange_recommended_activity_type_id(self) -> None:
        if self.recommended_activity_type_id:
            self.activity_type_id = self.recommended_activity_type_id

    def _accessible_ids(self, rows: Iterable[AccessRow], operation: str) -> set[int]:
        rows = list(rows)
        env = self.env
        own_reaches = operation != "create"
        doc_ids, own_doc_ids = self._documents_to_ask(rows, own_reaches)
        reachable = {}
        for res_model, res_ids in doc_ids.items():
            allowed = set(
                env["mail.message"]
                ._get_accessible_documents(res_model, res_ids, operation)
                ._ids
            )
            if mine := own_doc_ids.get(res_model, set()) - allowed:
                allowed |= self._subscribable_by_self(res_model, mine)
            reachable[res_model] = allowed
        return {
            id_
            for id_, res_model, res_id, user_id in rows
            if (
                user_id == env.uid
                and (own_reaches or not self._has_document(res_model))
            )
            or res_id in reachable.get(res_model, ())
        }

    def _has_document(self, res_model: str | Literal[False]) -> bool:
        return bool(res_model) and res_model in self.env

    def _documents_to_ask(
        self, rows: Iterable[AccessRow], own_reaches: bool
    ) -> tuple[dict[str, set[int]], dict[str, set[int]]]:
        doc_ids = defaultdict(set)
        own_doc_ids = defaultdict(set)
        for __, res_model, res_id, user_id in rows:
            if not self._has_document(res_model):
                continue
            own = user_id == self.env.uid
            if own and own_reaches:
                continue
            doc_ids[res_model].add(res_id)
            if own:
                own_doc_ids[res_model].add(res_id)
        return doc_ids, own_doc_ids

    @api.model
    def _subscribable_by_self(self, res_model: str, res_ids: set[int]) -> set[int]:
        if not res_ids:
            return set()
        Message = self.env["mail.message"]
        readable = set(
            Message._get_accessible_documents(res_model, res_ids, "read")._ids
        )
        return readable | Message._get_followed_res_ids(res_model, res_ids - readable)

    def _access_rows(self) -> list[AccessRow]:
        return [
            (activity.id, activity.res_model, activity.res_id, activity.user_id.id)
            for activity in self.sudo()
        ]

    def _check_access(self, operation: str) -> tuple | None:
        result = super()._check_access(operation)
        if not self:
            return result

        if operation == "read":
            activities = self - result[0] if result else self
            activities -= activities.sudo().filtered_domain(
                [("user_id", "=", self.env.uid)]
            )
        elif operation == "create":
            activities = self - result[0] if result else self
        elif operation in ("write", "unlink"):
            if self.browse()._check_access(operation):
                return result
            activities = result[0] if result else self.browse()
            result = None
        else:
            raise ValueError(f"Unexpected operation {operation!r}")

        if not activities:
            return result

        reachable = activities._accessible_ids(activities._access_rows(), operation)
        forbidden_ids = [id_ for id_ in activities._ids if id_ not in reachable]

        _debug.logic(
            "access_checked",
            operation=operation,
            asked=len(activities),
            forbidden=len(forbidden_ids),
        )
        if forbidden_ids:
            forbidden = self.browse(forbidden_ids)
            if result:
                result = (result[0] + forbidden, result[1])
            else:
                result = (forbidden, lambda: forbidden._prepare_access_error(operation))
        return result

    def _prepare_access_error(self, operation: str) -> AccessError:
        if (
            operation == "create"
            and self
            and all(
                not activity.res_model and activity.user_id.id != self.env.uid
                for activity in self.sudo()
            )
        ):
            return AccessError(
                self.env._(
                    "A personal activity -- one with no document -- can only be "
                    "assigned to yourself. Give it a document to assign it to "
                    "somebody else."
                )
            )
        return prepare_document_access_error(self, operation)

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        vals_list = [self._deadline_in_assignee_day(vals) for vals in vals_list]
        activities = super().create(vals_list)
        if activities.user_id - self.env.user:
            user_partners = activities.user_id.partner_id
            readable_user_partners = user_partners._filtered_access("read")
        else:
            readable_user_partners = self.env.user.partner_id
        if self.env.context.get("mail_activity_quick_update"):
            activities_to_notify = self.browse()
        else:
            activities_to_notify = activities.filtered(
                lambda act: act.user_id and act.user_id != self.env.user
            )
        _debug.lifecycle(
            "create",
            count=len(activities),
            notify=len(activities_to_notify),
            quick_update=bool(self.env.context.get("mail_activity_quick_update")),
            models=sorted(model or "" for model in activities.mapped("res_model")),
        )
        if activities_to_notify:
            readable_ids = set(readable_user_partners._ids)
            to_sudo = activities_to_notify.filtered(
                lambda act: act.user_id.partner_id.id not in readable_ids
            )
            other = activities_to_notify - to_sudo
            to_sudo.sudo().action_notify()
            other.action_notify()

        activities._subscribe_assignees(readable_user_partners)

        mine = activities._todo_keys()
        if mine:
            keys = set().union(*mine.values())
            elsewhere = activities._todo_keys_elsewhere(keys)
            self._notify_todo_count_change(
                elsewhere, self._merged_todo_keys(elsewhere, mine)
            )
        return activities

    @api.model
    def _assignee_of(self, vals: ValuesType) -> ResUsers:
        user_id = vals.get("user_id", self.env.context.get("default_user_id"))
        return self.env["res.users"].browse(user_id or ())

    @api.model
    def _deadline_in_assignee_day(self, vals: ValuesType) -> ValuesType:
        if vals.get("date_deadline") or self.env.context.get("default_date_deadline"):
            return vals
        return {
            **vals,
            "date_deadline": self._today_for(self._assignee_of(vals)),
        }

    def _filtered_postable(self) -> Self:
        backed = self._filtered_document_backed()
        postable = backed._accessible_ids(backed._access_rows(), "create")
        return backed.filtered(lambda activity: activity.id in postable)

    def _subscribe_assignees(self, readable_user_partners: ResPartner) -> None:
        readable_ids = set(readable_user_partners._ids)
        for model, activities in self._thread_backed().grouped("res_model").items():
            per_user = defaultdict(set)
            for activity in activities.filtered("user_id"):
                per_user[activity.user_id].add(activity.res_id)
            _debug.lifecycle(
                "assignees_subscribed",
                model=model,
                activities=len(activities),
                users=len(per_user),
            )
            for user, res_ids in per_user.items():
                pids = (
                    user.partner_id.ids
                    if user.partner_id.id in readable_ids
                    else user.sudo().partner_id.ids
                )
                self.env[model].browse(res_ids)._message_subscribe(partner_ids=pids)

    def _prospective_todo_keys(self, vals: ValuesType) -> TodoKeys:
        res_model = None
        if "res_model_id" in vals:
            res_model = (
                self.env["ir.model"].sudo().browse(vals["res_model_id"]).model
                if vals["res_model_id"]
                else False
            )
        keys = set()
        for activity in self:
            model = activity.res_model if res_model is None else res_model
            res_id = vals.get("res_id", activity.res_id)
            keys.add((model, res_id) if model else (ORPHAN_BUCKET, activity.id))
        return keys

    def write(self, vals: ValuesType) -> Literal[True]:
        if "res_model" in vals:
            raise UserError(
                self.env._(
                    "The document model of an activity is set through "
                    "'res_model_id', not 'res_model'."
                )
            )
        moves_count = {
            "date_deadline",
            "active",
            "user_id",
            "res_id",
            "res_model_id",
        } & vals.keys()
        bookkeeping = self.sudo()
        keys = elsewhere = mine_before = None
        if moves_count:
            keys = {activity._todo_key() for activity in bookkeeping}
            keys |= bookkeeping._prospective_todo_keys(vals)
            elsewhere = self._todo_keys_elsewhere(keys)
            mine_before = bookkeeping._todo_keys(within=keys)
        reassigned = self.browse()
        if vals.get("user_id"):
            reassigned = bookkeeping.filtered(
                lambda activity: activity.user_id.id != vals["user_id"]
            ).with_env(self.env)
        moved = self.browse()
        if "res_id" in vals or "res_model_id" in vals:
            moved = bookkeeping.filtered("user_id").with_env(self.env)

        res = super().write(vals)

        _debug.lifecycle(
            "write",
            count=len(self),
            fields=list(vals),
            reassigned=len(reassigned),
            moved=len(moved),
            recounted=bool(moves_count),
        )
        if (
            reassigned
            and vals["user_id"] != self.env.uid
            and not self.env.context.get("mail_activity_quick_update")
        ):
            reassigned.action_notify()
        if to_subscribe := (reassigned | moved)._filtered_postable():
            partners = to_subscribe.user_id.partner_id
            to_subscribe._subscribe_assignees(partners._filtered_access("read"))

        if moves_count:
            self._notify_todo_count_change(
                self._merged_todo_keys(elsewhere, mine_before),
                self._merged_todo_keys(elsewhere, bookkeeping._todo_keys(within=keys)),
            )

        return res

    def unlink(self) -> Literal[True]:
        mine = self.sudo()._todo_keys()
        _debug.lifecycle("unlink", count=len(self), todo_users=len(mine))
        if not mine:
            return super().unlink()
        keys = set().union(*mine.values())
        elsewhere = self._todo_keys_elsewhere(keys)
        before = self._merged_todo_keys(elsewhere, mine)
        res = super().unlink()
        self._notify_todo_count_change(before, elsewhere)
        return res

    @api.model
    def _searching_by_state(self, domain: DomainType) -> bool:
        return any(
            leaf.field_expr == "state" for leaf in Domain(domain).iter_conditions()
        )

    @api.model
    def _domain_is_mine(self, domain: DomainType) -> bool:
        if not any(
            leaf.field_expr == "user_id" for leaf in Domain(domain).iter_conditions()
        ):
            return False
        not_mine = Domain("user_id", "!=", self.env.uid)
        return (Domain(domain) & not_mine).optimize_full(self).is_false()

    @api.model
    def _search(
        self,
        domain: DomainType,
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
        *,
        bypass_access: bool = False,
        **kwargs,
    ) -> Query:
        if kwargs.get("active_test", True) and self._searching_by_state(domain):
            kwargs["active_test"] = False
        if self.env.is_superuser() or bypass_access:
            return super()._search(
                domain, offset, limit, stable_order(order), bypass_access=True, **kwargs
            )
        if self._domain_is_mine(domain):
            _debug.logic("search_by", by="mine", limit=limit)
            return super()._search(domain, offset, limit, stable_order(order), **kwargs)

        _debug.logic("search_by", by="access_scan", limit=limit)

        def allowed(rows: list[tuple]) -> set[int]:
            return self._accessible_ids(rows, "read")

        return get_accessible_query(
            self,
            domain,
            offset,
            limit,
            order,
            super()._search,
            fetch=prepare_column_fetcher(
                self, ("id", "res_model", "res_id", "user_id")
            ),
            allowed=allowed,
            chunk_min=self._SEARCH_ACCESS_CHUNK_MIN,
            chunk_max=self._SEARCH_ACCESS_CHUNK_MAX,
            **kwargs,
        )

    @api.depends("summary", "activity_type_id")
    def _compute_display_name(self) -> None:
        for record in self:
            name = record.summary or record.activity_type_id.display_name
            record.display_name = name

    def action_notify(self) -> None:
        notifiable = self._thread_backed().filtered("user_id")
        author_id = self.env.user.partner_id.id
        for model, activities in notifiable.grouped("res_model").items():
            records_sudo = self.env[model].sudo().browse(activities.mapped("res_id"))
            existing = records_sudo.exists()
            if not existing:
                continue
            batches = activities._notify_batches(model, set(existing._ids))
            _debug.pipeline(
                "assignees_notified",
                model=model,
                activities=len(activities),
                existing=len(existing),
                batches=len(batches),
            )
            for (user, *_key), batch in batches.items():
                self._notify_assignee_batch(
                    self.env[model].sudo(), batch, user, author_id
                )

    def _notify_batches(self, model: str, existing_ids: set[int]) -> dict[tuple, dict]:
        descriptions = {}
        batches = {}
        for activity in self:
            if activity.res_id not in existing_ids:
                continue
            lang = activity.user_id.lang or False
            localized = activity.with_context(lang=lang) if lang else activity
            if lang not in descriptions:
                descriptions[lang] = localized.env["ir.model"]._get(model).display_name
            model_description = descriptions[lang]
            key = (
                activity.user_id,
                lang,
                activity.activity_type_id,
                activity.date_deadline,
            )
            if key not in batches:
                batches[key] = {
                    "model_description": model_description,
                    "subtitles": [
                        localized.env._(
                            "Activity: %s",
                            localized.activity_type_id.name or localized.env._("Todo"),
                        ),
                        localized.env._(
                            "Deadline: %s",
                            localized.date_deadline.strftime(
                                get_lang(localized.env).date_format
                            ),
                        ),
                    ],
                    "entries": [],
                }
            batches[key]["entries"].append(
                (
                    activity.res_id,
                    localized.env["ir.qweb"]._render(
                        "mail.message_activity_assigned",
                        {
                            "activity": localized,
                            "model_description": model_description,
                            "is_html_empty": is_html_empty,
                        },
                        minimal_qcontext=True,
                    ),
                    localized.env._(
                        '"%(activity_name)s: %(summary)s" assigned to you',
                        activity_name=localized.res_name,
                        summary=localized.summary
                        or localized.activity_type_id.name
                        or "",
                    ),
                )
            )
        return batches

    def _notify_assignee_batch(
        self,
        documents_sudo: models.BaseModel,
        batch: dict,
        user: ResUsers,
        author_id: int,
    ) -> None:
        entries = batch["entries"]
        while entries:
            bodies, subjects, deferred = {}, {}, []
            for res_id, body, subject in entries:
                if res_id in bodies:
                    deferred.append((res_id, body, subject))
                    continue
                bodies[res_id] = body
                subjects[res_id] = subject
            documents_sudo.browse(list(bodies))._message_notify_batch(
                bodies,
                subjects=subjects,
                author_id=author_id,
                partner_ids=user.partner_id.ids,
                model_description=batch["model_description"],
                email_layout_xmlid="mail.mail_notification_layout",
                subtitles=batch["subtitles"],
            )
            entries = deferred

    def action_done(self) -> int | Literal[False]:
        return self.filtered(lambda r: r.active).action_feedback()

    def action_done_redirect_to_other(self) -> dict:
        self.action_done()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "mail.mail_activity_without_access_action"
        )
        action_context = self.env["ir.actions.actions"]._eval_action_context(
            action.get("context", "{}")
        )
        if self.env.context.get("active_model") == "mail.activity":
            active_ids = self.env.context.get("active_ids", [])
        else:
            activity_groups = self.env["res.users"]._get_activity_groups()
            activity_model_id = self.env["ir.model"]._get_id("mail.activity")
            active_ids = next(
                (
                    g["activity_ids"]
                    for g in activity_groups
                    if g["id"] == activity_model_id
                ),
                [],
            )
        action["context"] = {
            **action_context,
            "active_ids": active_ids,
            "active_model": "mail.activity",
        }
        return action

    def action_feedback(
        self,
        feedback: str | Literal[False] = False,
        attachment_ids: list[int] | None = None,
    ) -> int | Literal[False]:
        messages, _next_activities = self.with_context(
            clean_context(self.env.context)
        )._action_done(feedback=feedback, attachment_ids=attachment_ids)
        return messages[0].id if messages else False

    def action_feedback_schedule_next(
        self,
        feedback: str | Literal[False] = False,
        attachment_ids: list[int] | None = None,
    ) -> dict | Literal[False]:
        self.check_singleton()
        ctx = dict(
            clean_context(self.env.context),
            default_previous_activity_type_id=self.activity_type_id.id,
            activity_previous_deadline=self.date_deadline,
            default_res_id=self.res_id,
            default_res_model=self.res_model,
        )
        _messages, next_activities = self._action_done(
            feedback=feedback, attachment_ids=attachment_ids
        )
        _debug.logic(
            "feedback_schedule_next",
            activities=self.ids,
            chained=len(next_activities),
            by="triggered" if next_activities else "wizard",
        )
        if next_activities:
            return False
        return {
            "name": _("Schedule an Activity"),
            "context": ctx,
            "view_mode": "form",
            "res_model": "mail.activity",
            "views": [(False, "form")],
            "type": "ir.actions.act_window",
            "target": "new",
        }

    def _action_done(
        self,
        feedback: str | Literal[False] = False,
        attachment_ids: list[int] | None = None,
    ) -> tuple[MailMessage, Self]:
        open_activities = self.filtered("active")
        if not open_activities:
            return self.env["mail.message"], self.browse()

        gone = open_activities._vanished_documents()
        with _debug.perf(
            "done_messages_posted",
            cr=self.env.cr,
            activities=len(open_activities),
            gone=len(gone),
            attachments=len(attachment_ids or ()),
        ) as span:
            messages, attachments_to_remove = open_activities._post_done_messages(
                feedback, attachment_ids, gone
            )
            span.set(messages=len(messages), removed=len(attachments_to_remove))
        next_values = [
            activity.with_context(
                activity_previous_deadline=activity.date_deadline
            )._prepare_next_activity_values()
            for activity in open_activities - gone
            if activity.chaining_type == "trigger"
        ]
        next_activities = (
            self.sudo().create(next_values).with_env(self.env)
            if next_values
            else self.browse()
        )

        if attachments_to_remove:
            attachments_to_remove.unlink()
        if gone:
            gone.unlink()

        done = open_activities - gone
        _debug.lifecycle(
            "done",
            activities=done.ids,
            gone=len(gone),
            next_activities=len(next_activities),
            feedback=bool(feedback),
        )
        done.write({"active": False, **({"feedback": feedback} if feedback else {})})
        return messages, next_activities

    def _vanished_documents(self) -> Self:
        gone = self.browse()
        for model, activities, res_ids in self._activities_with_records():
            existing = set(self.env[model].sudo().browse(res_ids).exists()._ids)
            gone |= activities.filtered(
                lambda act, alive=existing: act.res_id not in alive
            )
        return gone

    def _post_done_messages(
        self,
        feedback: str | Literal[False],
        attachment_ids: list[int] | None,
        gone: Self,
    ) -> tuple[MailMessage, IrAttachment]:
        activity_attachments = (
            self.env["ir.attachment"]
            .sudo()
            .search_fetch(
                [("res_model", "=", self._name), ("res_id", "in", self.ids)],
                ["res_id"],
            )
            .grouped("res_id")
        )
        shared_attachments = self.env["ir.attachment"].browse(attachment_ids or ())
        shared_origin = [
            {"res_model": attachment.res_model, "res_id": attachment.res_id}
            for attachment in shared_attachments.sudo()
        ]
        attachments_to_remove = self.env["ir.attachment"]
        message_ids = []
        posted = 0

        gone_ids = set(gone._ids)
        for (
            model,
            activities,
            res_ids,
        ) in self._thread_backed()._activities_with_records():
            records_sudo = self.env[model].sudo().browse(res_ids)
            plan = []
            for record_sudo, activity in zip(records_sudo, activities, strict=True):
                own_attachment_ids = self._attachments_for_post(
                    activity,
                    gone_ids,
                    attachment_ids,
                    shared_attachments,
                    shared_origin,
                    posted,
                )
                post_values = None
                if activity.id not in gone_ids:
                    post_values = self._prepare_done_post_values(
                        record_sudo, activity, feedback, own_attachment_ids
                    )
                    posted += 1
                if own_attachment_ids:
                    activity.attachment_ids = own_attachment_ids
                plan.append((activity, post_values))
            message_by_activity = self._post_done_rounds(records_sudo, plan)
            for activity, _post_values in plan:
                activity_message = message_by_activity.get(
                    activity.id, self.env["mail.message"]
                )
                attachments_to_remove += self._rehome_own_attachments(
                    activity, activity_message, activity_attachments
                )
                message_ids.extend(activity_message._ids)
        return self.env["mail.message"].browse(message_ids), attachments_to_remove

    def _prepare_done_post_values(
        self,
        record: models.BaseModel,
        activity: Self,
        feedback: str | Literal[False],
        attachment_ids: list[int] | None,
    ) -> dict:
        body = self.env["mixin.mail.render"]._render_template_qweb_view(
            "mail.message_activity_done",
            record._name,
            record.ids,
            add_context={
                "activity": activity,
                "feedback": feedback,
                "display_assignee": activity.user_id != self.env.user,
            },
        )[record.id]
        return {
            "attachment_ids": attachment_ids,
            "author_id": self.env.user.partner_id.id,
            "body": body,
            "mail_activity_type_id": activity.activity_type_id.id,
            "message_type": "notification",
            "subtype_xmlid": "mail.mt_activities",
        }

    @api.model
    def _post_done_rounds(
        self, records: models.BaseModel, plan: list[tuple[Self, dict | None]]
    ) -> dict[int, MailMessage]:
        rounds: list[dict[int, tuple[int, dict]]] = []
        for activity, post_values in plan:
            if post_values is None:
                continue
            for round_ in rounds:
                if activity.res_id not in round_:
                    round_[activity.res_id] = (activity.id, post_values)
                    break
            else:
                rounds.append({activity.res_id: (activity.id, post_values)})
        _debug.pipeline(
            "done_messages",
            model=records._name,
            activities=len(plan),
            posted=sum(len(round_) for round_ in rounds),
            rounds=len(rounds),
        )
        message_by_activity = {}
        for round_ in rounds:
            messages = records._message_post_values_all(
                {res_id: values for res_id, (_aid, values) in round_.items()}
            )
            for (activity_id, _values), message in zip(
                round_.values(), messages, strict=True
            ):
                message_by_activity[activity_id] = message
        return message_by_activity

    def _attachments_for_post(
        self,
        activity: Self,
        gone_ids: set[int],
        attachment_ids: list[int] | None,
        shared_attachments: IrAttachment,
        shared_origin: list[dict],
        posted: int,
    ) -> list[int] | None:
        if activity.id in gone_ids:
            return None
        if not (shared_attachments and posted):
            return attachment_ids
        return [
            attachment.copy(default=origin).id
            for attachment, origin in zip(
                shared_attachments, shared_origin, strict=True
            )
        ]

    def _rehome_own_attachments(
        self,
        activity: Self,
        activity_message: MailMessage,
        activity_attachments: dict[int, IrAttachment],
    ) -> IrAttachment:
        message_attachments = activity_attachments.get(activity.id)
        if not message_attachments:
            return self.env["ir.attachment"]
        if not activity_message:
            return message_attachments
        message_attachments.write(
            {"res_id": activity_message.id, "res_model": activity_message._name}
        )
        activity_message.attachment_ids |= message_attachments
        return self.env["ir.attachment"]

    @api.readonly
    def action_close_dialog(self) -> dict:
        return {"type": "ir.actions.act_window_close"}

    @api.readonly
    def action_view_document(self) -> dict:
        self.check_singleton()
        if not self.res_model:
            view_id = self.env.ref("mail.mail_activity_view_form_popup").id
            return {
                "res_id": self.id,
                "type": "ir.actions.act_window",
                "view_mode": "form",
                "res_model": "mail.activity",
                "view_id": view_id,
                "views": [(view_id, "form")],
                "target": "new",
            }
        document = (
            self.env[self.res_model].browse(self.res_id)
            if (self.res_model in self.env)
            else None
        )
        if document is None or not document.exists() or not document.has_access("read"):
            return {
                "res_id": self.id,
                "res_model": "mail.activity",
                "target": "current",
                "type": "ir.actions.act_window",
                "view_mode": "form",
                "views": [
                    (
                        self.env.ref(
                            "mail.mail_activity_view_form_without_record_access"
                        ).id,
                        "form",
                    )
                ],
            }
        return {
            "res_id": self.res_id,
            "res_model": self.res_model,
            "target": "current",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "views": [(False, "form")],
        }

    def _action_reschedule_from_today(
        self, offset: timedelta | relativedelta | None = None
    ) -> None:
        by_tz = self.filtered("active").grouped("user_tz")
        today_by_tz = self._today_by_tz(by_tz)
        _debug.lifecycle(
            "rescheduled", activities=self.ids, offset=str(offset), timezones=len(by_tz)
        )
        for tz, activities in by_tz.items():
            today = today_by_tz[tz]
            activities.date_deadline = today + offset if offset else today

    def action_reschedule_today(self) -> None:
        self._action_reschedule_from_today()

    def action_reschedule_tomorrow(self) -> None:
        self._action_reschedule_from_today(timedelta(days=1))

    def action_reschedule_nextweek(self) -> None:
        self._action_reschedule_from_today(relativedelta(weeks=1, weekday=MO(-1)))

    def action_cancel(self) -> None:
        self.filtered("active").unlink()

    @api.readonly
    def activity_format(self) -> dict:
        return Store().add(self).get_result()

    def _to_store_defaults(self, target: Store.Target) -> StoreFieldsInput:
        return [
            "activity_category",
            Store.One("activity_type_id", "name"),
            "can_write",
            "chaining_type",
            "create_date",
            Store.One("create_uid", Store.One("partner_id", "name"), sudo=True),
            "date_deadline",
            "date_done",
            "display_name",
            "icon",
            "note",
            "res_id",
            "res_model",
            "state",
            "summary",
            Store.One(
                "user_id", Store.One("partner_id", ["name", "avatar_128"]), sudo=True
            ),
            Store.Many("attachment_ids", ["name"]),
            Store.Many("mail_template_ids", ["name"]),
        ]

    @api.readonly
    @api.model
    def get_activity_data(
        self,
        res_model: str,
        domain: DomainType,
        limit: int | None = None,
        offset: int = 0,
        fetch_done: bool = False,
    ) -> dict:
        self._check_activity_view_model(res_model)
        limit = min(limit or self._VIEW_DATA_MAX_LIMIT, self._VIEW_DATA_MAX_LIMIT)
        with _debug.perf(
            "activity_data",
            cr=self.env.cr,
            model=res_model,
            limit=limit,
            offset=offset,
            fetch_done=fetch_done,
        ) as span:
            all_ongoing, all_completed = self._get_activity_data_activities(
                res_model, domain, limit, offset, fetch_done
            )
            grouped_activities = self._get_activity_data_cells(
                all_ongoing, all_completed
            )
            span.set(
                ongoing=len(all_ongoing),
                completed=len(all_completed),
                cells=len(grouped_activities),
            )
        return {
            "activity_res_ids": self._get_activity_data_order(grouped_activities),
            "activity_types": [
                {
                    "id": activity_type.id,
                    "name": activity_type.name,
                    "template_ids": [
                        {"id": mail_template_id.id, "name": mail_template_id.name}
                        for mail_template_id in activity_type.mail_template_ids
                    ],
                }
                for activity_type in self.env["mail.activity.type"].search(
                    [("res_model", "in", (res_model, False))]
                )
            ],
            "grouped_activities": grouped_activities,
        }

    @api.model
    def _selection_activity_models(self) -> list[tuple[str, str]]:
        return [
            (model.model, model.name)
            for model in self.env["ir.model"]
            .sudo()
            .search([("is_mail_activity", "=", True), ("transient", "=", False)])
        ]

    @api.model
    def _check_activity_view_model(self, res_model: str) -> None:
        if res_model not in self.env or not isinstance(
            self.env[res_model], self.pool["mixin.mail.activity"]
        ):
            raise UserError(
                self.env._(
                    "%(model)s does not have activities, so it has no activity "
                    "view to fill.",
                    model=res_model,
                )
            )

    @api.model
    def _get_activity_data_activities(
        self,
        res_model: str,
        domain: DomainType,
        limit: int,
        offset: int,
        fetch_done: bool,
    ) -> tuple[MailActivity, MailActivity]:
        DocModel = self.env[res_model]
        activity_domain = [
            ("res_model", "=", res_model),
            (
                "res_id",
                "in",
                DocModel._search(domain or [], offset, limit, DocModel._order),
            ),
        ]
        all_activities = self.with_context(active_test=not fetch_done).search(
            activity_domain, order="date_done DESC, date_deadline ASC"
        )
        by_open = all_activities.grouped("active")
        empty = self.browse()
        return by_open.get(True, empty), by_open.get(False, empty)

    @api.model
    def _get_activity_data_cells(
        self,
        all_ongoing: MailActivity,
        all_completed: MailActivity,
    ) -> dict:
        attachments_by_id = {}
        if attachment_ids := all_completed.attachment_ids.ids:
            attachments_by_id = {
                a["id"]: a
                for a in self.env["ir.attachment"].search_read(
                    [["id", "in", attachment_ids]], ["create_date", "name"]
                )
            }

        def by_cell(activities: MailActivity) -> dict:
            return activities.grouped(lambda a: (a.res_id, a.activity_type_id))

        grouped_ongoing = by_cell(all_ongoing)
        grouped_completed = by_cell(all_completed)

        cells = sorted(
            grouped_ongoing.keys() | grouped_completed.keys(),
            key=lambda cell: (cell[0], cell[1].id),
        )

        today_by_tz = self._today_by_tz((all_ongoing | all_completed).mapped("user_tz"))

        grouped_activities = defaultdict(dict)
        for cell in cells:
            res_id, activity_type = cell
            ongoing = grouped_ongoing.get(cell, self.browse())
            completed = grouped_completed.get(cell, self.browse())
            activities = ongoing | completed

            date_done = completed and completed[0].date_done
            date_deadline = ongoing and ongoing[0].date_deadline

            cell_data = {
                "count_by_state": dict(
                    Counter(
                        self._state_for(act.date_deadline, today_by_tz[act.user_tz])
                        if act.active
                        else "done"
                        for act in activities
                    )
                ),
                "ids": activities.ids,
                "reporting_date": (ongoing and date_deadline) or date_done or None,
                "state": self._state_for(date_deadline, today_by_tz[ongoing[0].user_tz])
                if ongoing
                else "done",
                "user_assigned_ids": ongoing.user_id.ids,
                "summaries": [act.summary or "" for act in activities],
            }
            attachments = [
                attachment
                for attach in completed.attachment_ids
                if (attachment := attachments_by_id.get(attach.id))
            ]
            if attachments:
                most_recent = max(
                    attachments, key=lambda a: (a["create_date"], a["id"])
                )
                cell_data["attachments_info"] = {
                    "most_recent_id": most_recent["id"],
                    "most_recent_name": most_recent["name"],
                    "count": len(attachments),
                }
            grouped_activities[res_id][activity_type.id] = cell_data
        return grouped_activities

    @api.model
    def _get_activity_data_order(self, grouped_activities: dict) -> list[int]:
        deadline_by_res_id = {}
        done_by_res_id = {}
        for res_id, cells in grouped_activities.items():
            for cell in cells.values():
                date = cell["reporting_date"]
                if not date:
                    continue
                if cell["state"] == "done":
                    previous = done_by_res_id.get(res_id)
                    if previous is None or date > previous:
                        done_by_res_id[res_id] = date
                else:
                    previous = deadline_by_res_id.get(res_id)
                    if previous is None or date < previous:
                        deadline_by_res_id[res_id] = date
        ongoing_res_ids = sorted(
            deadline_by_res_id, key=lambda res_id: (deadline_by_res_id[res_id], res_id)
        )
        completed_res_ids = [
            res_id
            for res_id in sorted(
                done_by_res_id,
                key=lambda res_id: (done_by_res_id[res_id], res_id),
                reverse=True,
            )
            if res_id not in deadline_by_res_id
        ]
        return ongoing_res_ids + completed_res_ids

    def _filtered_document_backed(self) -> Self:
        return self.filtered(
            lambda act: act.res_model and act.res_id and act.res_model in self.env
        )

    def _thread_backed(self) -> Self:
        thread = self.pool["mixin.mail.thread"]
        return self._filtered_document_backed().filtered(
            lambda act: isinstance(self.env[act.res_model], thread)
        )

    def _activities_with_records(self) -> Iterator[tuple[str, Self, list[int]]]:
        for model, activities in (
            self._filtered_document_backed().grouped("res_model").items()
        ):
            yield model, activities, activities.mapped("res_id")

    def _prepare_next_activity_values(self) -> ValuesType:
        self.check_singleton()
        vals = self.default_get(list(self._fields))

        vals.update(
            {
                "previous_activity_type_id": self.activity_type_id.id,
                "res_id": self.res_id,
                "res_model_id": self.res_model_id.id,
            }
        )
        virtual_activity = self.new(vals)
        virtual_activity._onchange_previous_activity_type_id()
        virtual_activity._onchange_activity_type_id()
        written = virtual_activity._convert_to_write(virtual_activity._cache)
        written.pop("res_model", None)
        return written

    def _gc_retention_years(self, parameter: str) -> int:
        years = self.env["ir.config_parameter"]._get_int_param(parameter, 0)
        if years < 0:
            _debug.logic("gc_skipped", parameter=parameter, reason="negative")
            _logger.warning(
                "The ir.config_parameter %r is set to a negative number which is "
                "invalid. Skipping gc routine.",
                parameter,
            )
            return 0
        if years == 0:
            _logger.debug("%r missing or 0; skipping gc routine.", parameter)
        return years

    @api.autovacuum
    def _gc_remove_old_overdue_activities(self) -> tuple[int, bool]:
        years = self._gc_retention_years("mail.activity.gc.delete_overdue_years")
        if not years:
            return 0, False
        threshold = self._today_in_tz() - relativedelta(years=years)
        return self._gc_unlink_batch(
            Domain("active", "=", True) & Domain("date_deadline", "<", threshold)
        )

    @api.autovacuum
    def _gc_remove_old_done_activities(self) -> tuple[int, bool]:
        years = self._gc_retention_years("mail.activity.gc.delete_done_years")
        if not years:
            return 0, False
        threshold = self._today_in_tz() - relativedelta(years=years)
        return self._gc_unlink_batch(
            Domain("active", "=", False) & Domain("date_done", "<", threshold)
        )

    def _gc_unlink_batch(self, domain: Domain) -> tuple[int, bool]:
        collected = (
            self.sudo()
            .with_context(active_test=False)
            .search(domain, limit=self._GC_BATCH)
        )
        removed = len(collected)
        collected.unlink()
        _debug.lifecycle("gc_batch", removed=removed, more=removed == self._GC_BATCH)
        return removed, removed == self._GC_BATCH
