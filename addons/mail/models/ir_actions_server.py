import typing
from collections import defaultdict
from collections.abc import Callable
from typing import Literal, Self

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools.date_utils import get_timedelta, time_unit_selection

FOLLOWER_STATES = frozenset({"followers", "remove_followers"})
MAIL_STATES = frozenset({"mail_post", "next_activity"}) | FOLLOWER_STATES

STATE_MODEL_FLAG = {
    "next_activity": "is_mail_activity",
    "followers": "is_mail_thread",
    "remove_followers": "is_mail_thread",
}
POST_SUBTYPE_XMLIDS = {"comment": "mail.mt_comment", "note": "mail.mt_note"}

if typing.TYPE_CHECKING:
    from .mail_activity_type import MailActivityType
    from .mail_template import MailTemplate
    from .res_partner import ResPartner
    from odoo.addons.base.models.ir_model import IrModel
    from odoo.addons.base.models.ir_model_fields import IrModelFields
    from odoo.addons.bus.models.res_users import ResUsers

_debug = DebugLog(__name__)


class IrActionsServer(models.Model):
    _name = "ir.actions.server"
    _description = "Server Action"
    _inherit = ["ir.actions.server", "mixin.mail.thread", "mixin.mail.activity"]

    name = fields.Char(tracking=True)
    model_id: IrModel = fields.Many2one(tracking=True)
    crud_model_id: IrModel = fields.Many2one(tracking=True)
    link_field_id: IrModelFields = fields.Many2one(tracking=True)
    update_path = fields.Char(tracking=True)
    value = fields.Text(tracking=True)
    evaluation_type = fields.Selection(tracking=True)
    webhook_url = fields.Char(tracking=True)

    state = fields.Selection(
        selection_add=[
            ("next_activity", "Create Activity"),
            ("mail_post", "Send Email"),
            ("followers", "Add Followers"),
            ("remove_followers", "Remove Followers"),
            ("code",),
        ],
        ondelete={
            "mail_post": "cascade",
            "followers": "cascade",
            "remove_followers": "cascade",
            "next_activity": "cascade",
        },
        tracking=True,
    )
    followers_type = fields.Selection(
        selection=[
            ("specific", "Specific Followers"),
            ("generic", "Dynamic Followers"),
        ],
        compute="_compute_followers_type",
        store=True,
        readonly=False,
        help="""
            - Specific Followers: select specific contacts to add/remove from record's followers.
            - Dynamic Followers: all contacts of the chosen record's field will be added/removed from followers.
        """,
    )
    followers_partner_field_name = fields.Char(
        string="Followers Field",
        compute="_compute_followers_info",
        store=True,
        readonly=False,
    )
    partner_ids: ResPartner = fields.Many2many(
        comodel_name="res.partner",
        compute="_compute_followers_info",
        store=True,
        readonly=False,
    )

    template_id: MailTemplate = fields.Many2one(
        comodel_name="mail.template",
        string="Email Template",
        compute="_compute_template_id",
        store=True,
        readonly=False,
        domain="[('model_id', '=', model_id)]",
        ondelete="set null",
    )
    mail_post_autofollow = fields.Boolean(
        string="Subscribe Recipients",
        default=True,
    )
    mail_post_method = fields.Selection(
        selection=[("email", "Email"), ("comment", "Message"), ("note", "Note")],
        string="Send Email As",
        compute="_compute_mail_post_method",
        store=True,
        readonly=False,
    )

    activity_type_id: MailActivityType = fields.Many2one(
        comodel_name="mail.activity.type",
        string="Activity Type",
        compute="_compute_activity_info",
        store=True,
        readonly=False,
        domain="['|', ('res_model', '=', False), ('res_model', '=', model_name)]",
        ondelete="restrict",
    )
    activity_summary = fields.Char(
        string="Title",
        compute="_compute_activity_summaries",
        store=True,
        readonly=False,
    )
    automated_activity_summary = fields.Char(
        compute="_compute_activity_summaries",
        store=True,
    )
    activity_note = fields.Html(
        string="Note",
        compute="_compute_activity_info",
        store=True,
        readonly=False,
    )
    activity_date_deadline_range = fields.Integer(
        string="Due Date In",
        compute="_compute_activity_info",
        store=True,
        readonly=False,
    )
    activity_date_deadline_range_type = fields.Selection(
        selection=time_unit_selection("day", "week", "month"),
        string="Due type",
        compute="_compute_activity_info",
        store=True,
        readonly=False,
    )
    activity_user_type = fields.Selection(
        selection=[
            ("specific", "Specific User"),
            ("generic", "Dynamic User (based on record)"),
        ],
        string="User Type",
        compute="_compute_activity_info",
        store=True,
        readonly=False,
        help="Use 'Specific User' to always assign the same user on the next activity. Use 'Dynamic User' to specify the field name of the user to choose on the record.",
    )
    activity_user_id: ResUsers = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        compute="_compute_activity_user_info",
        store=True,
        readonly=False,
    )
    activity_user_field_name = fields.Char(
        string="User Field",
        compute="_compute_activity_user_info",
        store=True,
        readonly=False,
    )

    @api.model
    def _get_fields_name_depends(self) -> list[str]:
        return [
            *super()._get_fields_name_depends(),
            "template_id.name",
            "activity_type_id.name",
        ]

    def _prepare_automated_name(self) -> str:
        self.check_singleton()
        if self.state == "mail_post" and self.template_id:
            return _("Send %(template_name)s", template_name=self.template_id.name)
        if self.state == "next_activity" and self.activity_type_id:
            return _(
                "Create %(activity_name)s", activity_name=self.activity_type_id.name
            )
        return super()._prepare_automated_name()

    @api.model
    def _get_states_needing_a_live_record(self) -> frozenset[str]:
        return super()._get_states_needing_a_live_record() | MAIL_STATES

    def _is_batchable(self) -> bool:
        self.check_singleton()
        return self.state in MAIL_STATES or super()._is_batchable()

    def _get_mail_model_flag(self) -> str | Literal[False]:
        self.check_singleton()
        if self.state == "mail_post":
            return "is_mail_thread" if self.mail_post_method != "email" else False
        return STATE_MODEL_FLAG.get(self.state, False)

    @api.depends("state", "mail_post_method")
    def _compute_available_model_ids(self) -> None:
        super()._compute_available_model_ids()
        mail_based = self.filtered(lambda action: action.state in MAIL_STATES)
        if not mail_based:
            return
        supported = {}

        def supported_ids(flag):
            if flag not in supported:
                domain = [("transient", "=", False)]
                if flag:
                    domain.append((flag, "=", True))
                supported[flag] = set(self.env["ir.model"].search(domain)._ids)
            return supported[flag]

        for action in mail_based:
            allowed = supported_ids(action._get_mail_model_flag())
            action.available_model_ids = [
                model_id
                for model_id in action.available_model_ids._ids
                if model_id in allowed
            ]

    @api.depends(
        "model_id.is_mail_activity", "model_id.is_mail_thread", "model_id.transient"
    )
    def _compute_allowed_states(self) -> None:
        super()._compute_allowed_states()
        for action in self:
            model = action.model_id
            unsupported = (
                MAIL_STATES
                if model.transient
                else {
                    state for state, flag in STATE_MODEL_FLAG.items() if not model[flag]
                }
            )
            if unsupported:
                action.allowed_states = [
                    state for state in action.allowed_states if state not in unsupported
                ]

    @api.depends("model_id", "state")
    def _compute_template_id(self) -> None:
        to_reset = self.filtered(
            lambda act: (
                act.state != "mail_post" or (act.model_id != act.template_id.model_id)
            )
        )
        if to_reset:
            to_reset.template_id = False

    @api.depends("state")
    def _compute_mail_post_method(self) -> None:
        for action in self:
            if action.state != "mail_post":
                action.mail_post_method = False
            elif not action.mail_post_method:
                action.mail_post_method = "comment"

    @api.depends("model_id", "state")
    def _compute_followers_type(self) -> None:
        to_reset = self.filtered(
            lambda act: not act.model_id or act.state not in FOLLOWER_STATES
        )
        to_reset.followers_type = False
        to_default = (self - to_reset).filtered(lambda act: not act.followers_type)
        to_default.followers_type = "specific"

    @api.depends("model_id", "followers_type")
    def _compute_followers_info(self) -> None:
        for action in self:
            if action.followers_type != "specific":
                action.partner_ids = False
            if action.followers_type != "generic":
                action.followers_partner_field_name = False
            elif not action._path_leads_to(
                "followers_partner_field_name", "res.partner"
            ):
                action.followers_partner_field_name = (
                    action._get_partner_field_name()
                )

    def _get_partner_field_name(self) -> str | Literal[False]:
        self.check_singleton()
        model = self._get_target_model()
        if model is None:
            return False
        fnames = model._mail_get_partner_fields()
        return fnames[0] if fnames else False

    @api.depends("model_id", "state")
    def _compute_activity_info(self) -> None:
        to_reset = self.filtered(
            lambda act: not act.model_id or act.state != "next_activity"
        )
        if to_reset:
            to_reset.activity_type_id = False
            to_reset.activity_note = False
            to_reset.activity_date_deadline_range = False
            to_reset.activity_date_deadline_range_type = False
            to_reset.activity_user_type = False
        for action in self - to_reset:
            if (
                action.activity_type_id.res_model
                and action.model_id.model != action.activity_type_id.res_model
            ):
                action.activity_type_id = False
            if not action.activity_date_deadline_range_type:
                action.activity_date_deadline_range_type = "day"
            if not action.activity_user_type:
                action.activity_user_type = "specific"

    @api.depends("model_id", "state", "activity_type_id")
    def _compute_activity_summaries(self) -> None:
        for action in self:
            if not action.model_id or action.state != "next_activity":
                action.automated_activity_summary = False
                action.activity_summary = False
                continue
            was_automated = action.activity_summary == action.automated_activity_summary
            action.automated_activity_summary = action.activity_type_id.summary
            if was_automated or not action.activity_summary:
                action.activity_summary = action.automated_activity_summary

    @api.depends("model_id", "activity_user_type")
    def _compute_activity_user_info(self) -> None:
        for action in self:
            if action.activity_user_type != "specific":
                action.activity_user_id = False
            if action.activity_user_type != "generic":
                action.activity_user_field_name = False
            elif not action._path_leads_to("activity_user_field_name", "res.users"):
                action.activity_user_field_name = action._get_user_field_name()

    def _get_user_field_name(self) -> str | Literal[False]:
        self.check_singleton()
        model = self._get_target_model()
        if model is None:
            return False
        field = model._fields.get("user_id")
        if field and field.type == "many2one" and field.comodel_name == "res.users":
            return "user_id"
        return False

    def _get_target_model(self) -> models.BaseModel | None:
        self.check_singleton()
        model_name = self.model_id.model
        if not model_name or model_name not in self.env.registry:
            return None
        return self.env[model_name]

    def _path_leads_to(self, field_name: str, comodel: str) -> bool:
        self.check_singleton()
        if self._get_target_model() is None:
            return False
        field_chain = self._get_relation_chain(field_name)
        return bool(field_chain) and field_chain[-1].comodel_name == comodel

    @api.model
    def _get_fields_warning_depends(self) -> list[str]:
        return super()._get_fields_warning_depends() + [
            "activity_type_id",
            "activity_user_field_name",
            "activity_user_type",
            "followers_partner_field_name",
            "followers_type",
            "partner_ids",
            "mail_post_method",
            "model_id.is_mail_activity",
            "model_id.is_mail_thread",
            "model_id.transient",
            "template_id",
            "template_id.model_id",
        ]

    def _get_warning_messages(self) -> list[str]:
        self.check_singleton()
        warnings = super()._get_warning_messages()

        if self.state == "mail_post" and not self.template_id:
            warnings.append(_("Select the email template to send."))

        if self.state == "next_activity" and not self.activity_type_id:
            warnings.append(_("Select the type of activity to schedule."))

        if (
            self.state == "mail_post"
            and self.template_id
            and self.template_id.model_id != self.model_id
        ):
            warnings.append(
                _(
                    "Mail template model of %(action_name)s does not match action model.",
                    action_name=self.name,
                )
            )

        if self.state in MAIL_STATES and self.model_id.transient:
            warnings.append(_("This action cannot be done on transient models."))

        flag = self._get_mail_model_flag()
        if flag and not self.model_id[flag]:
            if flag == "is_mail_activity":
                warnings.append(
                    _(
                        "A next activity can only be planned on models that use activities."
                    )
                )
            else:
                warnings.append(
                    _("This action can only be done on a mail thread models")
                )

        if (
            self.state in FOLLOWER_STATES
            and self.followers_type == "specific"
            and not self.partner_ids
        ):
            warnings.append(_("Select the contacts to add or remove."))

        if self.state in FOLLOWER_STATES and self.followers_type == "generic":
            warnings += self._get_path_warnings(
                "followers_partner_field_name",
                "res.partner",
                lambda: _("Select the field holding the contacts to follow."),
                lambda path: _(
                    "The field '%(field_chain_str)s' is not a partner field.",
                    field_chain_str=path,
                ),
            )

        if self.state == "next_activity" and self.activity_user_type == "generic":
            warnings += self._get_path_warnings(
                "activity_user_field_name",
                "res.users",
                lambda: _("Select the field holding the user to assign."),
                lambda path: _(
                    "The field '%(field_chain_str)s' is not a user field.",
                    field_chain_str=path,
                ),
            )

        return warnings

    def _get_path_warnings(
        self,
        field_name: str,
        comodel: str,
        unset_message: Callable[[], str],
        wrong_comodel_message: Callable[[str], str],
    ) -> list[str]:
        self.check_singleton()
        if not self[field_name]:
            return [unset_message()]
        field_chain = self._get_relation_chain(field_name)
        if not field_chain:
            return [
                _(
                    "The field '%(path)s' does not exist on %(model)s.",
                    path=self[field_name],
                    model=self.model_id.display_name,
                )
            ]
        if field_chain[-1].comodel_name != comodel:
            return [wrong_comodel_message(self._get_relation_chain_label(field_chain))]
        return []

    @api.constrains(
        "model_id",
        "state",
        "followers_type",
        "followers_partner_field_name",
        "activity_user_type",
        "activity_user_field_name",
    )
    def _check_relation_paths(self) -> None:
        for action in self:
            if action.state in FOLLOWER_STATES and action.followers_type == "generic":
                action._get_relation_chain(
                    "followers_partner_field_name", raise_on_error=True
                )
            if (
                action.state == "next_activity"
                and action.activity_user_type == "generic"
            ):
                action._get_relation_chain(
                    "activity_user_field_name", raise_on_error=True
                )

    def _run_action_followers_multi(self, eval_context: dict | None = None) -> bool:
        self._subscribe_followers(subscribe=True)
        return False

    def _run_action_remove_followers_multi(
        self, eval_context: dict | None = None
    ) -> bool:
        self._subscribe_followers(subscribe=False)
        return False

    def _subscribe_followers(self, subscribe: bool) -> None:
        records = self._get_records_targeted().with_context(self._get_run_context())
        if not records:
            return
        batches = self._get_follower_batches(records)
        _debug.pipeline(
            "followers_action",
            action=self.id,
            subscribe=subscribe,
            records=len(records),
            batches=len(batches),
            by=self.followers_type,
        )
        for partner_ids, batch in batches.items():
            if subscribe:
                batch.message_subscribe(partner_ids=list(partner_ids))
            else:
                batch.message_unsubscribe(partner_ids=list(partner_ids))

    def _get_follower_batches(
        self, records: models.BaseModel
    ) -> dict[tuple[int, ...], models.BaseModel]:
        if self.followers_type == "specific":
            return {tuple(self.partner_ids.ids): records} if self.partner_ids else {}
        path = self.followers_partner_field_name
        if not path:
            return {}
        prefetched = records
        for segment in path.split("."):
            prefetched = prefetched.mapped(segment)
        per_partners = defaultdict(records.browse)
        for record in records:
            partners = record.mapped(path)
            if partners:
                per_partners[tuple(sorted(partners.ids))] |= record
        return per_partners

    def _get_recompute_pending(self, records: models.BaseModel) -> models.BaseModel:
        old_values = self.env.context.get("old_values")
        if not old_values or not records:
            return records.browse()
        domain_post = self.env.context.get("domain_post") or []
        post_filtered = {
            leaf[0] for leaf in domain_post if isinstance(leaf, (tuple, list))
        }
        field_names = {
            field_name
            for values in old_values.values()
            for field_name in values
            if field_name not in post_filtered and field_name in records._fields
        }
        pending = records.browse()
        for field_name in field_names:
            pending |= records & self.env.get_records_to_compute(
                records._fields[field_name]
            )
        if _debug.logic.enabled and pending:
            _debug.logic(
                "recompute_pending",
                action=self.id,
                records=len(records),
                pending=len(pending),
                fields=sorted(field_names),
            )
        return pending

    def _is_recompute(self) -> bool:
        return bool(self._get_recompute_pending(self._get_records_targeted()))

    def _get_run_context(self) -> dict:
        return {
            key: value
            for key, value in self.env.context.items()
            if not key.startswith("default_")
        }

    def _prepare_mail_post_context(self) -> dict:
        context = self._get_run_context()
        context["mail_post_autofollow_author_skip"] = True
        context["mail_post_autofollow"] = self.mail_post_autofollow
        return context

    def _run_action_mail_post_multi(self, eval_context: dict | None = None) -> bool:
        records = self._get_records_targeted()
        records -= self._get_recompute_pending(records)
        if not self.template_id or not records:
            return False

        context = self._prepare_mail_post_context()
        _debug.pipeline(
            "mail_post_action",
            action=self.id,
            template=self.template_id.id,
            records=len(records),
            method=self.mail_post_method,
        )
        if subtype_xmlid := POST_SUBTYPE_XMLIDS.get(self.mail_post_method):
            self._post_template_on(
                records.with_context(context),
                self.env["ir.model.data"]._xmlid_to_res_id(subtype_xmlid),
            )
        else:
            self.template_id.with_context(context).send_mail_batch(
                records.ids, force_send=False
            )
        return False

    def _post_template_on(self, records, subtype_id: int) -> None:
        if len(records) == 1:
            records.message_post_with_source(
                self.template_id,
                message_type="auto_comment",
                subtype_id=subtype_id,
            )
            return
        records.env["mail.compose.message"].with_context(
            default_composition_mode="comment",
            default_model=records._name,
            default_res_ids=records.ids,
            default_template_id=self.template_id.id,
        ).create(
            {"message_type": "auto_comment", "subtype_id": subtype_id}
        )._action_send_mail()

    def _run_action_next_activity_multi(self, eval_context: dict | None = None) -> bool:
        records = self._get_records_targeted()
        records -= self._get_recompute_pending(records)
        if not self.activity_type_id or not records:
            return False
        records = records.with_context(self._get_run_context())

        vals = {
            "activity_type_id": self.activity_type_id.id,
            "summary": self.activity_summary or "",
            "note": self.activity_note or "",
        }
        assignees = self._get_activity_assignees(records)
        _debug.pipeline(
            "next_activity_action",
            action=self.id,
            activity_type=self.activity_type_id.id,
            records=len(records),
            assignee_batches=len(assignees),
            by=self.activity_user_type,
        )
        for user, batch in assignees:
            batch_vals = dict(vals)
            if user:
                batch_vals["user_id"] = user.id
            if self.activity_date_deadline_range:
                assignee = user or self.activity_type_id.default_user_id
                batch_vals["date_deadline"] = (
                    self.env["mail.activity"]._today_for(assignee)
                    + self._get_activity_deadline_delta()
                )
            batch.activity_schedule(**batch_vals)
        return False

    def _get_activity_deadline_delta(self) -> relativedelta:
        self.check_singleton()
        unit = self.activity_date_deadline_range_type or "day"
        return get_timedelta(self.activity_date_deadline_range, unit)

    def _get_activity_assignees(
        self, records: models.BaseModel
    ) -> list[tuple[ResUsers, models.BaseModel]]:
        if self.activity_user_type == "specific":
            return [(self.activity_user_id, records)]
        if self.activity_user_type != "generic" or not self.activity_user_field_name:
            return [(self.env["res.users"], records)]
        by_user_id = defaultdict(records.browse)
        for record in records:
            users = record.mapped(self.activity_user_field_name)
            by_user_id[users.ids[0] if users else False] |= record
        return [
            (self.env["res.users"].browse(user_id or ()), batch)
            for user_id, batch in by_user_id.items()
        ]

    def _prepare_eval_context(self, action: Self) -> dict:
        return super(
            IrActionsServer, self.with_context(mail_notify_force_send=False)
        )._prepare_eval_context(action=action)
