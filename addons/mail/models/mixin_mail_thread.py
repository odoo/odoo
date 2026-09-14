import base64
import datetime
import hashlib
import hmac
import json
import logging
import typing
from collections import defaultdict
from collections.abc import Collection, Iterable, Iterator, Sequence
from email.message import EmailMessage
from itertools import batched
from types import NotImplementedType
from typing import Any, Literal, Self
from urllib.parse import urlencode

from lxml import etree, html
from markupsafe import Markup, escape

from odoo import _, api, exceptions, fields, models, tools
from odoo.api import ValuesType
from odoo.exceptions import AccessError, MissingError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import (
    SQL,
    clean_context,
    html2plaintext,
    html_escape,
    is_html_empty,
    is_list_of,
    ormcache,
)
from odoo.tools.mail import (
    add_html_content,
    email_normalize,
    email_normalize_all,
    email_split_and_format_normalize,
    email_split_and_normalize,
    formataddr,
    generate_tracking_message_id,
)

from odoo.addons.mail.tools.discuss import Store, StoreFieldsInput, StoreFieldSpec
from odoo.addons.mail.tools.html_body import (
    iter_fragment_elements,
    parse_body_fragments,
    render_body_fragments,
)
from odoo.addons.mail.tools.recipients import prepare_recipient_data
from odoo.addons.mail.tools.web_push import (
    ENCRYPTION_BLOCK_OVERHEAD,
    ENCRYPTION_HEADER_SIZE,
    MAX_PAYLOAD_SIZE,
    DeviceUnreachableError,
    PushEndpointUnresolvableError,
    get_push_session,
    push_to_end_point,
)

if typing.TYPE_CHECKING:
    from .mail_followers import ExistingPolicy, MailFollowers
    from .mail_mail import MailMail
    from .mail_message import MailMessage
    from .mail_message_subtype import MailMessageSubtype
    from .mail_push_device import MailPushDevice
    from .mail_template import MailTemplate
    from .mail_tracking_value import MailTrackingValue
    from .res_company import ResCompany
    from .res_partner import ResPartner
    from odoo.addons.bus.models.ir_attachment import IrAttachment
    from odoo.addons.bus.models.res_users import ResUsers


MAX_DIRECT_PUSH = 5

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def _to_flush(model: models.BaseModel, *fnames: str) -> list[fields.Field]:
    return [model._fields[fname] for fname in fnames]


def _escape_body(body: str | Literal[False] | None) -> str:
    if body is None or body is False:
        return ""
    return escape(body)


_NOTIFY_TRANSPORT_PARAMETERS = frozenset(
    {"email_collector", "email_prefetch", "follower_data", "inbox_collector"}
)


class MixinMailThread(models.AbstractModel):
    _name = "mixin.mail.thread"
    _inherit = ["mixin.mail.gateway"]
    _description = "Email Thread"
    _mail_flat_thread = True
    _mail_thread_customer = False
    _primary_email = "email"

    _CUSTOMER_HEADERS_LIMIT_COUNT = 50
    _FOLLOWER_PAGE_LIMIT = 100
    _EDITED_MARKER_CLASS = "o-mail-Message-edited"
    _ACTION_LINK_HMAC_SCOPE = "mail.action_link"
    _ACTION_LINK_SIGNED_PARAMS = (
        "model",
        "res_id",
        "action",
        "access_token",
        "auth_signup_token",
        "auth_login",
        "pid",
        "hash",
    )
    _ACTION_LINK_IMPLICIT_PARAMS = ("model", "res_id")

    _SOURCE_POST_FORBIDDEN_PARAMS = frozenset(
        {
            "body",
            "composition_mode",
            "incoming_email_cc",
            "incoming_email_to",
            "model",
            "res_id",
            "outgoing_email_to",
            "values",
        }
    )

    _BATCH_PER_RECORD_PARAMS = frozenset(
        {
            "attachment_ids",
            "attachments",
            "email_from",
            "parent_id",
            "partner_ids",
            "record_alias_domain_id",
            "record_company_id",
            "reply_to",
            "subject",
        }
    )

    _AUTHOR_SUBSCRIBE_EXEMPT_TYPES = (
        "notification",
        "user_notification",
        "auto_comment",
        "out_of_office",
    )

    message_is_follower = fields.Boolean(
        string="Is Follower",
        compute="_compute_message_is_follower",
        search="_search_message_is_follower",
    )
    message_follower_ids: MailFollowers = fields.One2many(
        comodel_name="mail.followers",
        inverse_name="res_id",
        string="Followers",
        groups="base.group_user",
    )
    message_partner_ids: ResPartner = fields.Many2many(
        comodel_name="res.partner",
        string="Followers (Partners)",
        compute="_compute_message_partner_ids",
        inverse="_inverse_message_partner_ids",
        search="_search_message_partner_ids",
        groups="base.group_user",
    )
    message_ids: MailMessage = fields.One2many(
        comodel_name="mail.message",
        inverse_name="res_id",
        string="Messages",
        domain=lambda self: [("message_type", "!=", "user_notification")],
        bypass_search_access=True,
    )
    has_message = fields.Boolean(
        compute="_compute_has_message",
        search="_search_has_message",
        store=False,
    )
    message_needaction = fields.Boolean(
        string="Action Needed",
        compute="_compute_message_needaction_stats",
        search="_search_message_needaction",
        help="If checked, new messages require your attention.",
    )
    message_needaction_counter = fields.Integer(
        string="Number of Actions",
        compute="_compute_message_needaction_stats",
        help="Number of messages requiring action",
    )
    message_has_error = fields.Boolean(
        string="Message Delivery error",
        compute="_compute_message_has_error_stats",
        search="_search_message_has_error",
        help="If checked, some messages have a delivery error.",
    )
    message_has_error_counter = fields.Integer(
        string="Number of errors",
        compute="_compute_message_has_error_stats",
        help="Number of messages with delivery error",
    )
    message_attachment_count = fields.Integer(
        string="Attachment Count",
        compute="_compute_message_attachment_count",
        groups="base.group_user",
    )

    @api.depends("message_follower_ids")
    def _compute_message_partner_ids(self) -> None:
        for thread in self:
            thread.message_partner_ids = thread.message_follower_ids.mapped(
                "partner_id"
            )

    def _inverse_message_partner_ids(self) -> None:
        to_subscribe, to_unsubscribe = defaultdict(list), defaultdict(list)
        for thread in self:
            wanted = thread.message_partner_ids
            current = thread.message_follower_ids.partner_id
            if added := (wanted - current):
                to_subscribe[tuple(added.ids)].append(thread.id)
            if removed := (current - wanted):
                to_unsubscribe[tuple(removed.ids)].append(thread.id)

        for partner_ids, thread_ids in to_subscribe.items():
            self.browse(thread_ids).message_subscribe(list(partner_ids))
        for partner_ids, thread_ids in to_unsubscribe.items():
            self.browse(thread_ids).message_unsubscribe(list(partner_ids))

    @api.model
    def _search_message_partner_ids(
        self, operator: str, operand: Any
    ) -> list | NotImplementedType:
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        if not (self.env.su or self.env.user._is_internal()):
            user_partner = self.env.user.partner_id
            allow_partner_ids = set(
                (user_partner | user_partner.commercial_partner_id).ids
            )
            operand_values = (
                operand
                if isinstance(operand, Iterable) and not isinstance(operand, str)
                else [operand]
            )
            if not allow_partner_ids.issuperset(operand_values):
                raise AccessError(
                    self.env._(
                        "Portal users can only filter threads by themselves as followers."
                    )
                )

        followers = (
            self.env["mail.followers"]
            .sudo()
            ._search(
                [
                    ("res_model", "=", self._name),
                    ("partner_id", operator, operand),
                ]
            )
        )
        return [("id", "in", followers.subselect("res_id"))]

    @api.depends("message_follower_ids")
    @api.depends_context("uid")
    def _compute_message_is_follower(self) -> None:
        followers = (
            self.env["mail.followers"]
            .sudo()
            .search_fetch(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "in", self.ids),
                    ("partner_id", "=", self.env.user.partner_id.id),
                ],
                ["res_id"],
            )
        )
        following_ids = set(followers.mapped("res_id"))
        for record in self:
            record.message_is_follower = record._origin.id in following_ids

    @api.model
    def _search_message_is_follower(
        self, operator: str, operand: Any
    ) -> list | NotImplementedType:
        if operator != "in":
            return NotImplemented
        followers = (
            self.env["mail.followers"]
            .sudo()
            ._search(
                [
                    ("res_model", "=", self._name),
                    ("partner_id", operator, self.env.user.partner_id.ids),
                ]
            )
        )
        return [("id", "in", followers.subselect("res_id"))]

    @api.depends("message_ids")
    def _compute_has_message(self) -> None:
        MailMessage = self.env["mail.message"]
        ids_with_message = {
            res_id
            for [res_id] in self.env.execute_query(
                SQL(
                    """
                    SELECT DISTINCT res_id
                      FROM mail_message
                     WHERE res_id = ANY(%s)
                       AND model = %s
                    """,
                    self.ids,
                    self._name,
                    to_flush=_to_flush(MailMessage, "model", "res_id"),
                )
            )
        }
        for record in self:
            record.has_message = record._origin.id in ids_with_message

    def _search_has_message(
        self, operator: str, value: Any
    ) -> list | NotImplementedType:
        if operator != "in":
            return NotImplemented
        return [
            (
                "id",
                "in",
                SQL(
                    "(SELECT res_id FROM mail_message WHERE model = %s)",
                    self._name,
                    to_flush=_to_flush(self.env["mail.message"], "model", "res_id"),
                ),
            )
        ]

    @api.depends_context("uid")
    def _compute_message_needaction_stats(self) -> None:
        res = dict.fromkeys(self.ids, 0)
        if self.ids:
            res.update(
                self.env.execute_query(
                    SQL(
                        """
                            SELECT msg.res_id, COUNT(*)
                              FROM mail_message msg
                        INNER JOIN mail_notification rel
                                ON rel.mail_message_id = msg.id
                             WHERE rel.res_partner_id = %s
                               AND COALESCE(rel.is_read, FALSE) = FALSE
                               AND msg.model = %s
                               AND msg.res_id = ANY(%s)
                               AND msg.message_type != 'user_notification'
                          GROUP BY msg.res_id
                        """,
                        self.env.user.partner_id.id,
                        self._name,
                        list(self.ids),
                        to_flush=(
                            _to_flush(
                                self.env["mail.message"],
                                "model",
                                "res_id",
                                "message_type",
                            )
                            + _to_flush(
                                self.env["mail.notification"],
                                "mail_message_id",
                                "res_partner_id",
                                "is_read",
                            )
                        ),
                    )
                )
            )

        for record in self:
            record.message_needaction_counter = res.get(record._origin.id, 0)
            record.message_needaction = bool(record.message_needaction_counter)

    @api.model
    def _search_message_needaction(
        self, operator: str, operand: Any
    ) -> list | NotImplementedType:
        if operator != "in":
            return NotImplemented
        return [("message_ids.needaction", operator, operand)]

    @api.depends_context("uid")
    def _compute_message_has_error_stats(self) -> None:
        res = {}
        if self.ids:
            res.update(
                self.env.execute_query(
                    SQL(
                        """
                            SELECT msg.res_id, COUNT(msg.res_id)
                              FROM mail_message msg
                        INNER JOIN mail_notification notif
                                ON notif.mail_message_id = msg.id
                             WHERE notif.notification_status IN ('exception', 'bounce')
                               AND notif.author_id = %s
                               AND msg.model = %s
                               AND msg.res_id = ANY(%s)
                               AND msg.message_type != 'user_notification'
                          GROUP BY msg.res_id
                        """,
                        self.env.user.partner_id.id,
                        self._name,
                        list(self.ids),
                        to_flush=(
                            _to_flush(
                                self.env["mail.message"],
                                "model",
                                "res_id",
                                "message_type",
                            )
                            + _to_flush(
                                self.env["mail.notification"],
                                "mail_message_id",
                                "author_id",
                                "notification_status",
                            )
                        ),
                    )
                )
            )

        for record in self:
            record.message_has_error_counter = res.get(record._origin.id, 0)
            record.message_has_error = bool(record.message_has_error_counter)

    @api.model
    def _search_message_has_error(
        self, operator: str, operand: Any
    ) -> list | NotImplementedType:
        if operator != "in":
            return NotImplemented
        message_domain = [
            ("has_error", "=", True),
            ("author_id", "=", self.env.user.partner_id.id),
        ]
        return [("message_ids", "any", message_domain)]

    def _compute_message_attachment_count(self) -> None:
        counts_per_res_id = dict(
            self.env["ir.attachment"]._read_group(
                [("res_id", "in", self._origin.ids), ("res_model", "=", self._name)],
                groupby=["res_id"],
                aggregates=["__count"],
            )
        )
        for record in self:
            record.message_attachment_count = counts_per_res_id.get(
                record._origin.id, 0
            )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        if (
            self.env.context.get("mail_create_nosubscribe")
            and "mail_post_autofollow_author_skip" not in self.env.context
        ):
            self = self.with_context(mail_post_autofollow_author_skip=True)

        if self.env.context.get("tracking_disable"):
            threads = super().create(vals_list)
            threads._track_discard()
            _debug.lifecycle(
                "create", model=self._name, count=len(threads), tracking="disabled"
            )
            return threads

        threads = super().create(vals_list)
        _debug.lifecycle(
            "create",
            model=self._name,
            count=len(threads),
            nosubscribe=bool(self.env.context.get("mail_create_nosubscribe")),
            nolog=bool(self.env.context.get("mail_create_nolog")),
            notrack=bool(self.env.context.get("mail_notrack")),
        )
        if (
            not self.env.context.get("mail_create_nosubscribe")
            and threads
            and self.env.user.active
            and not self.env.user.share
        ):
            _debug.logic(
                "author_subscribed_on_create", model=self._name, count=len(threads)
            )
            self.env["mail.followers"]._add_followers(
                threads._name,
                threads.ids,
                self.env.user.partner_id.ids,
                customer_ids=[],
                check_existing=False,
            )

        context_defaults = {
            key.removeprefix("default_"): val
            for key, val in self.env.context.items()
            if key.startswith("default_")
        }
        create_values_list = {
            thread.id: {**context_defaults, **values}
            for thread, values in zip(threads, vals_list, strict=True)
        }
        threads._message_auto_subscribe_batch(
            create_values_list, followers_existing_policy="update"
        )

        if not self.env.context.get("mail_create_nolog"):
            threads._message_post_creation()

        threads._track_discard()
        if not self.env.context.get("mail_notrack"):
            fnames = self._track_get_fields()
            for thread in threads:
                create_values = create_values_list[thread.id]
                changes = [fname for fname in fnames if create_values.get(fname)]
                if changes:
                    self.env.cr.precommit.add(thread._track_post_template_finalize)
                    self.env.cr.precommit.data.setdefault(
                        f"mail.tracking.create.{self._name}.{thread.id}", changes
                    )
        return threads

    def _message_post_creation(self) -> None:
        threads_no_subtype = self.env[self._name]
        threads_subtype = self.env[self._name]
        subtype_ids, bodies_subtype = {}, {}
        for thread in self:
            subtype = thread._creation_subtype()
            if not subtype:
                threads_no_subtype += thread
                continue
            threads_subtype += thread
            subtype_ids[thread.id] = subtype.id
            bodies_subtype[thread.id] = (
                Markup('<div summary="o_mail_notification"><p>%s</p></div>')
                % thread._creation_message()
            )
        _debug.pipeline(
            "creation_messages",
            model=self._name,
            posted=len(threads_subtype),
            logged=len(threads_no_subtype),
        )
        if threads_subtype:
            threads_subtype.sudo()._message_post_batch(
                bodies_subtype,
                subtype_ids=subtype_ids,
                author_id=self.env.user.partner_id.id,
            )
        if threads_no_subtype:
            bodies = {
                thread.id: thread._creation_message() for thread in threads_no_subtype
            }
            threads_no_subtype._message_log_batch(bodies=bodies)

    def write(self, vals: ValuesType) -> Literal[True]:
        if self.env.context.get("tracking_disable"):
            return super().write(vals)

        _debug.lifecycle(
            "write",
            model=self._name,
            count=len(self),
            fields=list(vals),
            notrack=bool(self.env.context.get("mail_notrack")),
        )
        if not self.env.context.get("mail_notrack"):
            self._track_prepare(self._fields)

        result = super().write(vals)

        stored = self.browse(self.ids)
        stored._message_auto_subscribe_batch(dict.fromkeys(stored.ids, vals))

        return result

    def unlink(self) -> Literal[True]:
        if not self:
            return True
        self._track_discard()
        messages = (
            self.env["mail.message"]
            .sudo()
            .search([("model", "=", self._name), ("res_id", "in", self.ids)])
        )
        followers = (
            self.env["mail.followers"]
            .sudo()
            .search([("res_model", "=", self._name), ("res_id", "in", self.ids)])
        )
        scheduled = (
            self.env["mail.scheduled.message"]
            .sudo()
            .search([("model", "=", self._name), ("res_id", "in", self.ids)])
        )
        _debug.lifecycle(
            "unlink",
            model=self._name,
            count=len(self),
            messages=len(messages),
            followers=len(followers),
            scheduled=len(scheduled),
        )
        messages.unlink()
        followers.unlink()
        scheduled.unlink()
        return super().unlink()

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        return super(MixinMailThread, self.with_context(mail_notrack=True)).copy_data(
            default=default
        )

    @api.model
    def get_empty_list_help(self, help_message: str) -> str:
        model = self.env.context.get("empty_list_help_model")
        res_id = self.env.context.get("empty_list_help_id")
        document_name = self.env.context.get(
            "empty_list_help_document_name", _("document")
        )
        nothing_here = is_html_empty(help_message)
        alias = None

        if model and res_id:
            record = self.env[model].sudo().browse(res_id).exists()
            if (
                record
                and "alias_id" in record
                and record.alias_id
                and record.alias_id.alias_name
                and record.alias_id.alias_domain
                and record.alias_id.alias_model_id.model == self._name
                and record.alias_id.alias_force_thread_id == 0
            ):
                alias = record.alias_id
        parent_model_id = self.env["ir.model"]._get_id(model) if model else None
        if not alias and parent_model_id and self.env.company.alias_domain_id:
            aliases = self.env["mail.alias"].search(
                [
                    ("alias_domain_id", "=", self.env.company.alias_domain_id.id),
                    ("alias_parent_model_id", "=", parent_model_id),
                    ("alias_name", "!=", False),
                    ("alias_force_thread_id", "=", False),
                    ("alias_parent_thread_id", "=", False),
                ],
                order="id ASC",
                limit=2,
            )
            if len(aliases) == 1:
                alias = aliases[0]

        if alias:
            email_link = Markup("<a href='mailto:%s'>%s</a>") % (
                alias.display_name,
                alias.display_name,
            )
            if nothing_here:
                dyn_help = _(
                    "Add a new %(document)s or send an email to %(email_link)s",
                    document=html_escape(document_name),
                    email_link=email_link,
                )
                return super().get_empty_list_help(
                    f"<p class='o_view_nocontent_smiling_face'>{dyn_help}</p>"
                )
            if "oe_view_nocontent_alias" not in help_message:
                dyn_help = _(
                    "Create new %(document)s by sending an email to %(email_link)s",
                    document=html_escape(document_name),
                    email_link=email_link,
                )
                return super().get_empty_list_help(
                    f"{help_message}<p class='oe_view_nocontent_alias'>{dyn_help}</p>"
                )

        if nothing_here:
            dyn_help = _("Create new %(document)s", document=html_escape(document_name))
            return super().get_empty_list_help(
                f"<p class='o_view_nocontent_smiling_face'>{dyn_help}</p>"
            )

        return super().get_empty_list_help(help_message)

    @api.model
    def get_views(
        self, views: list[list[int | str]], options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        res = super().get_views(views, options)
        if "form" in res["views"] and isinstance(
            self.env[self._name], self.env.registry["mixin.mail.activity"]
        ):
            res["models"][self._name]["has_activities"] = True
        return res

    def _compute_field_value(self, field: fields.Field, validate: bool = True) -> None:
        if not self.env.context.get("tracking_disable") and not self.env.context.get(
            "mail_notrack"
        ):
            self._track_prepare(
                f.name for f in self.pool.field_computed[field] if f.store
            )

        return super()._compute_field_value(field, validate=validate)

    def _mail_get_followers(self) -> dict[int, ResPartner]:
        records_su = self.sudo()
        follower_ids = set(records_su.message_partner_ids._ids)
        return {
            record.id: record.message_partner_ids.with_prefetch(follower_ids)
            for record in records_su
        }

    def _mail_get_thread_messages(self) -> dict[int, MailMessage]:
        messages_by_res_id = self.message_ids.grouped("res_id")
        return {
            record.id: messages_by_res_id.get(record.id, self.env["mail.message"])
            for record in self
        }

    def _creation_message(self) -> str:
        self.check_singleton()
        doc_name = self.env["ir.model"]._get(self._name).name
        return _("%s created", doc_name)

    def _is_valid_field_parameter(self, field: fields.Field, name: str) -> bool:
        return name == "tracking" or super()._is_valid_field_parameter(field, name)

    def _fallback_lang(self) -> Self:
        if not self.env.context.get("lang"):
            return self.with_context(lang=self.env.user.lang)
        return self

    def _check_can_update_message_content(self, messages: MailMessage) -> None:
        if messages.tracking_value_ids:
            raise exceptions.UserError(
                _("Messages with tracking values cannot be modified")
            )
        if any(message.message_type != "comment" for message in messages):
            raise exceptions.UserError(
                _("Only messages type comment can have their content updated")
            )

    def _track_prepare(self, fields_iter: Iterable[str]) -> None:
        fnames = self._track_get_fields().intersection(fields_iter)
        if not fnames:
            return
        _debug.pipeline(
            "track_prepare", model=self._name, count=len(self), fields=sorted(fnames)
        )
        self.env.cr.precommit.add(self._track_finalize)
        initial_values = self.env.cr.precommit.data.setdefault(
            f"mail.tracking.{self._name}", {}
        )
        writer_uids = self.env.cr.precommit.data.setdefault(
            f"mail.tracking.uid.{self._name}", {}
        )
        for record in self:
            if not record.id:
                continue
            writer_uids.setdefault(record.id, self.env.uid)
            values = initial_values.setdefault(record.id, {})
            if values is None:
                continue
            try:
                for fname in fnames:
                    value = (
                        field.convert_to_read(record[fname], record)
                        if (field := record._fields[fname]).type == "properties"
                        else record[fname]
                    )
                    values.setdefault(fname, value)
            except MissingError:
                initial_values.pop(record.id, None)
                writer_uids.pop(record.id, None)

    def _track_discard(self) -> None:
        if not self._track_get_fields():
            return
        self.env.cr.precommit.add(self._track_finalize)
        initial_values = self.env.cr.precommit.data.setdefault(
            f"mail.tracking.{self._name}", {}
        )
        for id_ in self.ids:
            initial_values[id_] = None

    def _track_filtered_for_display(
        self, tracking_values: MailTrackingValue
    ) -> MailTrackingValue:
        self.check_singleton()
        return tracking_values

    def _track_finalize(self) -> None:
        initial_values = self.env.cr.precommit.data.pop(
            f"mail.tracking.{self._name}", {}
        )
        writer_uids = self.env.cr.precommit.data.pop(
            f"mail.tracking.uid.{self._name}", {}
        )
        ids = [id_ for id_, vals in initial_values.items() if vals]
        if not ids:
            return
        fnames = self._track_get_fields()
        context = clean_context(self.env.context)
        ids_per_uid = defaultdict(list)
        for id_ in ids:
            ids_per_uid[writer_uids.get(id_, self.env.uid)].append(id_)
        _debug.pipeline(
            "track_finalize",
            model=self._name,
            records=len(ids),
            discarded=len(initial_values) - len(ids),
            writers=len(ids_per_uid),
        )
        overrides = {
            key: self.env.cr.precommit.data.pop(key)
            for key in (
                f"mail.tracking.message.{self._name}",
                f"mail.tracking.author.{self._name}",
            )
            if key in self.env.cr.precommit.data
        }
        for uid, uid_ids in ids_per_uid.items():
            self.env.cr.precommit.data.update(overrides)
            records = self.browse(uid_ids).with_user(uid).sudo()
            uid_context = context
            if uid != self.env.uid:
                uid_context = {k: v for k, v in context.items() if k != "lang"}
            tracking = records.with_context(uid_context)._message_track(
                fnames, initial_values
            )
            ids_per_changes = defaultdict(list)
            for record in records:
                changes, _tracking_value_ids = tracking.get(record.id, (None, None))
                if changes:
                    ids_per_changes[frozenset(changes)].append(record.id)
            _debug.pipeline(
                "track_finalize_uid",
                model=self._name,
                uid=uid,
                tracked=len(tracking),
                change_groups=len(ids_per_changes),
            )
            for changes, changed_ids in ids_per_changes.items():
                records.browse(changed_ids)._message_track_post_template(changes)

    def _track_set_author(self, author: ResPartner) -> None:
        if not self._track_get_fields():
            return
        authors = self.env.cr.precommit.data.setdefault(
            f"mail.tracking.author.{self._name}", {}
        )
        for id_ in self.ids:
            authors[id_] = author

    def _track_post_template_finalize(self) -> None:
        self._message_track_post_template(
            self.env.cr.precommit.data.pop(
                f"mail.tracking.create.{self._name}.{self.id}", []
            )
        )

    def _track_set_log_message(self, message: str) -> None:
        if not self._track_get_fields():
            return
        body_values = self.env.cr.precommit.data.setdefault(
            f"mail.tracking.message.{self._name}", {}
        )
        for id_ in self.ids:
            body_values[id_] = message

    def _track_get_default_log_message(self, tracked_fields: Collection[str]) -> str:
        return ""

    @ormcache("self.env.uid", "self.env.su")
    def _track_get_fields(self) -> frozenset[str]:
        model_fields = {
            name
            for name, field in self._fields.items()
            if getattr(field, "tracking", None)
        }
        model_fields |= {
            fname
            for fname, f in self._fields.items()
            if f.type == "properties"
            and f.definition_record in model_fields
            and getattr(f, "tracking", None) is not False
        }

        if not model_fields:
            return frozenset()
        _debug.perf.count(
            "track_fields_computed", model=self._name, fields=len(model_fields)
        )
        return frozenset(self.fields_get(model_fields, attributes=()))

    def _track_subtype(self, initial_values: dict) -> bool:
        self.check_singleton()
        return False

    def _message_track(
        self, fields_iter: Collection[str], initial_values_dict: dict
    ) -> dict:
        if not fields_iter:
            return {}

        tracked_fields = self.fields_get(
            fields_iter, attributes=("string", "type", "selection", "currency_field")
        )
        tracking = {}
        for record in self:
            try:
                tracking[record.id] = record._mail_track(
                    tracked_fields, initial_values_dict[record.id]
                )
            except MissingError:
                continue

        bodies = self.env.cr.precommit.data.pop(
            f"mail.tracking.message.{self._name}", {}
        )
        authors = self.env.cr.precommit.data.pop(
            f"mail.tracking.author.{self._name}", {}
        )
        log_bodies = {}
        log_authors = {}
        log_tracking_values = {}
        post_bodies = defaultdict(dict)
        post_authors = {}
        post_tracking_values = {}
        subtype_per_record = self._message_track_subtypes(tracking, initial_values_dict)
        for record in self:
            changes, tracking_value_ids = tracking.get(record.id, (None, None))
            if not changes:
                continue

            subtype = subtype_per_record[record.id]
            author_id = authors[record.id].id if record.id in authors else None
            body = (
                bodies[record.id]
                if record.id in bodies
                else record._track_get_default_log_message(changes)
            )
            if subtype:
                post_bodies[subtype.id][record.id] = body
                if author_id is not None:
                    post_authors[record.id] = author_id
                post_tracking_values[record.id] = tracking_value_ids
            elif tracking_value_ids:
                log_bodies[record.id] = body
                if author_id is not None:
                    log_authors[record.id] = author_id
                log_tracking_values[record.id] = tracking_value_ids

        _debug.pipeline(
            "message_track",
            model=self._name,
            count=len(self),
            tracked=len(tracking),
            posted=sum(len(bodies) for bodies in post_bodies.values()),
            logged=len(log_bodies),
        )
        self._message_track_post(post_bodies, post_authors, post_tracking_values)

        if log_bodies:
            self.browse(log_bodies)._message_log_batch(
                log_bodies,
                authors=log_authors or None,
                tracking_values=log_tracking_values,
            )

        return tracking

    def _message_track_subtypes(
        self, tracking: dict, initial_values_dict: dict
    ) -> dict[int, MailMessageSubtype]:
        subtype_per_record = {
            record.id: record._track_subtype(
                {
                    col_name: initial_values_dict[record.id][col_name]
                    for col_name in tracking[record.id][0]
                }
            )
            for record in self
            if tracking.get(record.id, (None, None))[0]
        }
        void = self.env["mail.message.subtype"]
        live_ids = set(
            void.union(*filter(None, subtype_per_record.values())).exists().ids
        )
        for res_id, subtype in subtype_per_record.items():
            if subtype and subtype.id not in live_ids:
                _debug.logic(
                    "track_subtype_missing",
                    model=self._name,
                    record=res_id,
                    subtype=subtype.id,
                )
                _logger.warning(
                    "mail.message.subtype %s no longer exists, logging %s "
                    "tracking without a subtype",
                    subtype.id,
                    self._name,
                )
                subtype_per_record[res_id] = void
        return subtype_per_record

    def _message_track_post(
        self,
        bodies_per_subtype: dict[int, dict[int, str]],
        authors: dict[int, int],
        tracking_values: dict[int, list],
    ) -> None:
        for subtype_id, subtype_bodies in bodies_per_subtype.items():
            self.browse(subtype_bodies)._message_post_batch(
                subtype_bodies,
                subtype_id=subtype_id,
                authors={
                    res_id: author
                    for res_id, author in authors.items()
                    if res_id in subtype_bodies
                },
                tracking_values={
                    res_id: values
                    for res_id, values in tracking_values.items()
                    if res_id in subtype_bodies
                },
            )

    def _message_track_post_template(self, changes: Collection[str] | None) -> bool:
        if not self or not changes:
            return True
        groups: dict[tuple, tuple[MailTemplate | str, dict, list[int]]] = {}
        for record in self:
            try:
                templates = record._track_template(changes)
            except MissingError:
                if not record.exists():
                    continue
                raise
            for template, post_kwargs in templates.values():
                if not template:
                    continue
                key = (
                    template
                    if isinstance(template, str)
                    else (template._name, template.id),
                    repr(sorted(post_kwargs.items())),
                )
                groups.setdefault(key, (template, post_kwargs, []))[2].append(record.id)

        cleaned_self = self.with_context(
            clean_context(self.env.context)
        )._fallback_lang()
        _debug.pipeline(
            "track_post_template",
            model=self._name,
            count=len(self),
            changes=sorted(changes),
            groups=len(groups),
        )
        for template, post_kwargs, res_ids in groups.values():
            post_kwargs = dict(post_kwargs)
            composition_mode = post_kwargs.pop("composition_mode", "comment")
            post_kwargs.setdefault("message_type", "auto_comment")
            post_kwargs.setdefault("notify_author_mention", True)
            records = cleaned_self.browse(res_ids)
            _debug.logic(
                "track_template_group",
                model=self._name,
                template=template if isinstance(template, str) else template.id,
                mode=composition_mode,
                records=len(res_ids),
            )
            if composition_mode == "mass_mail":
                records.message_mail_with_source(template, **post_kwargs)
            else:
                records.message_post_with_source(template, **post_kwargs)
        return True

    def _track_template(self, changes: Collection[str]) -> dict:
        return {}

    @api.model
    def message_new(self, msg_dict: dict, custom_values: dict | None = None) -> Self:
        data = {}
        if isinstance(custom_values, dict):
            data = custom_values.copy()
        name_field = self._rec_name or "name"
        if name_field in self._fields and not data.get(name_field):
            data[name_field] = msg_dict.get("subject", "")

        primary_email = self._mail_get_primary_email_field()
        if primary_email and msg_dict.get("email_from"):
            data[primary_email] = msg_dict["email_from"]

        _debug.lifecycle(
            "message_new",
            model=self._name,
            message_id=msg_dict.get("message_id"),
            fields=list(data),
        )
        return self.create(data)

    def message_update(
        self, msg_dict: dict, update_vals: ValuesType | None = None
    ) -> bool:
        if update_vals:
            _debug.lifecycle(
                "message_update",
                model=self._name,
                records=self.ids,
                message_id=msg_dict.get("message_id"),
                fields=list(update_vals),
            )
            self.write(update_vals)
        return True

    @api.model
    def _mail_get_or_create_partner_from_emails(
        self,
        emails: list[str],
        records: models.BaseModel | None = None,
        force_create: bool = False,
    ) -> list:
        if records and self._mail_is_thread(records):
            per_record = records._partner_get_or_create_from_emails(
                dict.fromkeys(records, emails),
                avoid_alias=True,
                no_create=not force_create,
            )
            all_partners = self.env["res.partner"].browse(
                {
                    partner.id
                    for partners in per_record.values()
                    for partner in partners
                    if partner.id
                }
            )
        else:
            all_partners = self.env[
                "mixin.mail.thread"
            ]._partner_get_or_create_from_emails_single(
                emails,
                avoid_alias=True,
                no_create=not force_create,
            )
        void = self.env["res.partner"]
        partner_by_email = {}
        for partner in all_partners:
            for email_key in (partner.email_normalized, partner.email):
                if email_key:
                    partner_by_email.setdefault(email_key, partner)
        _debug.logic(
            "partners_from_emails",
            model=self._name,
            emails=len(emails),
            found=len(all_partners),
            force_create=force_create,
            per_record=bool(records and self._mail_is_thread(records)),
        )
        return [
            partner_by_email.get(
                email_normalize(email_input) or email_input or None, void
            )
            for email_input in emails
        ]

    def _message_post_check_parameters(
        self,
        kwargs: dict,
        message_type: str,
        attachments: list[tuple | list] | None,
        attachment_ids: list[int] | None,
        partner_ids: list[int] | None,
    ) -> None:
        self._check_supported_parameters(
            set(kwargs.keys()), forbidden_names={"model", "res_id", "subtype"}
        )
        if self._name == "mixin.mail.thread" or not self.id:
            raise ValueError(
                "Posting a message should be done on a business document. "
                "Use message_notify to send a notification to an user."
            )
        if message_type == "user_notification":
            raise ValueError("Use message_notify to send a notification to an user.")
        self._check_attachments_format(attachments)
        if attachment_ids and not is_list_of(attachment_ids, int):
            raise ValueError(
                "Posting a message should receive attachments records as a list "
                f"of IDs (received {attachment_ids!r})"
            )
        if partner_ids and not is_list_of(partner_ids, int):
            raise ValueError(
                "Posting a message should receive partners as a list of IDs "
                f"(received {partner_ids!r})"
            )

    def _check_attachments_format(self, attachments: list[tuple | list] | None) -> None:
        if attachments and not all(
            isinstance(attachment, (list, tuple)) and len(attachment) in (2, 3)
            for attachment in attachments
        ):
            raise ValueError(
                "Attachments should be given as a list of lists or tuples of two "
                f"or three elements (received {attachments!r})"
            )

    def _message_split_kwargs(self, kwargs: dict) -> tuple[dict, dict]:
        message_fields = self.env["mail.message"]._fields
        msg_kwargs = {key: val for key, val in kwargs.items() if key in message_fields}
        notif_kwargs = {
            key: val for key, val in kwargs.items() if key not in message_fields
        }
        return msg_kwargs, notif_kwargs

    def message_post(
        self,
        *,
        body: str = "",
        subject: str | None = None,
        message_type: str = "notification",
        email_from: str | None = None,
        author_id: int | None = None,
        parent_id: int | Literal[False] = False,
        subtype_xmlid: str | None = None,
        subtype_id: int | Literal[False] = False,
        partner_ids: list[int] | None = None,
        outgoing_email_to: str | Literal[False] = False,
        incoming_email_to: str | Literal[False] = False,
        incoming_email_cc: str | Literal[False] = False,
        attachments: list[tuple | list] | None = None,
        attachment_ids: list[int] | None = None,
        body_is_html: bool = False,
        **kwargs,
    ) -> MailMessage:
        self.check_singleton()

        self._message_post_check_parameters(
            kwargs, message_type, attachments, attachment_ids, partner_ids
        )
        attachment_ids = list(attachment_ids or [])
        partner_ids = list(partner_ids or [])
        msg_kwargs, notif_kwargs = self._message_split_kwargs(kwargs)

        self = self._fallback_lang()

        guest = self.env["mail.guest"]._get_guest_from_context()
        if not author_id and self.env.user._is_public() and guest:
            author_guest_id = guest.id
            author_id, email_from = False, False
        else:
            author_guest_id = False
            author_id, email_from = self._message_compute_author(author_id, email_from)

        if subtype_xmlid:
            subtype_id = self.env["ir.model.data"]._xmlid_to_res_id(subtype_xmlid)
        if not subtype_id:
            subtype_id = self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_note")

        _debug.pipeline(
            "message_post",
            model=self._name,
            record=self.id,
            message_type=message_type,
            subtype=subtype_id,
            author=author_id,
            guest=author_guest_id,
            parent=parent_id,
            partners=len(partner_ids),
            attachments=len(attachments or ()) + len(attachment_ids),
            notif_kwargs=sorted(notif_kwargs),
        )
        self._message_post_subscribe_recipients(partner_ids)
        msg_values = self._message_post_values(
            body,
            msg_kwargs,
            message_type=message_type,
            subject=subject,
            subtype_id=subtype_id,
            author_id=author_id,
            author_guest_id=author_guest_id,
            email_from=email_from,
            parent_id=parent_id,
            partner_ids=partner_ids,
            outgoing_email_to=outgoing_email_to,
            incoming_email_to=incoming_email_to,
            incoming_email_cc=incoming_email_cc,
            attachments=attachments,
            attachment_ids=attachment_ids,
            body_is_html=body_is_html,
        )
        new_message = self._message_create([msg_values])

        self._message_post_subscribe_author([msg_values])

        self._message_post_after_hook(new_message, msg_values)
        with _debug.perf(
            "message_post_notify",
            cr=self.env.cr,
            model=self._name,
            record=self.id,
            message=new_message.id,
        ):
            self._notify_thread(new_message, msg_values, **notif_kwargs)
        return new_message

    def _message_post_subscribe_recipients(self, partner_ids: list[int]) -> None:
        if not partner_ids:
            return
        if self.env.context.get("mail_post_autofollow"):
            _debug.logic(
                "post_autofollow",
                model=self._name,
                record=self.id,
                partners=len(partner_ids),
                by="context",
            )
            self.message_subscribe(partner_ids=list(partner_ids))
        elif (
            self.env.context.get("mail_post_autofollow") is not False
            and self._mail_thread_customer
        ):
            customer = self._mail_get_customer()
            if customer.id in partner_ids:
                _debug.logic(
                    "post_autofollow",
                    model=self._name,
                    record=self.id,
                    partners=1,
                    by="customer",
                )
                self.message_subscribe(partner_ids=customer.ids)

    def _message_post_values(
        self,
        body: str,
        msg_kwargs: dict,
        *,
        message_type: str,
        subject: str | None,
        subtype_id: int | Literal[False],
        author_id: int | None,
        author_guest_id: int | Literal[False],
        email_from: str | None,
        parent_id: int | Literal[False],
        partner_ids: list[int],
        outgoing_email_to: str | Literal[False],
        incoming_email_to: str | Literal[False],
        incoming_email_cc: str | Literal[False],
        attachments: list[tuple | list] | None,
        attachment_ids: list[int],
        body_is_html: bool = False,
    ) -> dict:
        self.check_singleton()
        if body_is_html:
            _debug.logic(
                "body_is_html",
                model=self._name,
                record=self.id,
                message_type=message_type,
            )
            if self.env.user._is_internal():
                _logger.warning(
                    "Posting HTML message using body_is_html=True, use a Markup object instead (user: %s)",
                    self.env.user.id,
                )
            body = Markup(body)
        msg_values = self._message_post_values_common(
            body,
            msg_kwargs,
            message_type=message_type,
            subject=subject,
            subtype_id=subtype_id,
            author_id=author_id,
            author_guest_id=author_guest_id,
            email_from=email_from,
            parent_id=self._message_compute_parent_id(parent_id),
            partner_ids=partner_ids,
            attachment_ids=attachment_ids,
            outgoing_email_to=outgoing_email_to,
            incoming_email_to=incoming_email_to,
            incoming_email_cc=incoming_email_cc,
        )
        if "record_alias_domain_id" not in msg_values:
            msg_values["record_alias_domain_id"] = (
                self.sudo()
                ._mail_get_alias_domains(default_company=self.env.company)[self.id]
                .id
            )
        if "record_company_id" not in msg_values:
            msg_values["record_company_id"] = self._mail_get_companies(
                default=self.env.company
            )[self.id].id
        if "reply_to" not in msg_values:
            msg_values["reply_to"] = self._notify_get_reply_to(
                default=email_from, author_id=author_id
            )[self.id]
        msg_values.update(
            self._process_attachments_for_post(attachments, attachment_ids, msg_values)
        )
        return msg_values

    def _message_post_values_common(
        self,
        body: str,
        msg_kwargs: dict,
        *,
        message_type: str,
        subject: str | Literal[False] | None,
        subtype_id: int | Literal[False],
        author_id: int | Literal[False] | None,
        author_guest_id: int | Literal[False],
        email_from: str | Literal[False] | None,
        parent_id: int | Literal[False],
        partner_ids: Collection[int] = (),
        attachment_ids: Collection[int] = (),
        outgoing_email_to: str | Literal[False] = False,
        incoming_email_to: str | Literal[False] = False,
        incoming_email_cc: str | Literal[False] = False,
    ) -> dict:
        self.check_singleton()
        msg_values = dict(msg_kwargs)
        msg_values.setdefault("email_add_signature", True)
        msg_values.setdefault("tracking_value_ids", False)
        msg_values.update(
            {
                "attachment_ids": list(attachment_ids),
                "author_guest_id": author_guest_id,
                "author_id": author_id,
                "body": _escape_body(body),
                "email_from": email_from,
                "incoming_email_cc": incoming_email_cc,
                "incoming_email_to": incoming_email_to,
                "message_type": message_type,
                "model": self._name,
                "outgoing_email_to": outgoing_email_to,
                "parent_id": parent_id,
                "partner_ids": list(partner_ids),
                "res_id": self.id,
                "subject": subject or False,
                "subtype_id": subtype_id,
            }
        )
        return msg_values

    def _message_post_batch(
        self,
        bodies: dict[int, str],
        *,
        subtype_ids: dict[int, int] | None = None,
        subtype_id: int | Literal[False] = False,
        message_type: str = "notification",
        author_id: int | None = None,
        authors: dict[int, int] | None = None,
        email_from: str | None = None,
        subject: str | Literal[False] = False,
        tracking_values: dict[int, list] | None = None,
        values_per_record: dict[int, dict] | None = None,
        notify_per_record: dict[int, dict] | None = None,
        **kwargs,
    ) -> MailMessage:
        if not self:
            return self.env["mail.message"]
        msg_kwargs, notif_kwargs = self._message_post_batch_check_parameters(
            kwargs, message_type
        )
        values_per_record = self._message_post_batch_check_per_record(
            values_per_record, notify_per_record
        )

        records = self._fallback_lang()
        if not subtype_id:
            subtype_id = self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_note")
        subtype_ids = subtype_ids or {}
        authors = authors or {}
        tracking_values = tracking_values or {}
        _debug.pipeline(
            "message_post_batch",
            model=self._name,
            count=len(records),
            message_type=message_type,
            subtype=subtype_id,
        )

        values_list = records._message_post_batch_values(
            bodies,
            msg_kwargs,
            message_type=message_type,
            subject=subject,
            subtype_id=subtype_id,
            subtype_ids=subtype_ids,
            author_id=author_id,
            authors=authors,
            email_from=email_from,
            tracking_values=tracking_values,
            values_per_record=values_per_record,
        )
        records._message_post_subscribe_author(values_list)
        messages = records._message_create(values_list)
        follower_data = notif_kwargs.pop(
            "follower_data", None
        ) or records._message_post_batch_follower_data(
            message_type,
            values_list,
            include_followers=not notif_kwargs.get("notify_skip_followers"),
        )
        records._message_post_batch_notify(
            messages,
            values_list,
            follower_data,
            notif_kwargs,
            notify_per_record=notify_per_record or {},
        )
        return messages

    def _message_post_values_all(self, post_values_all: dict[int, dict]) -> MailMessage:
        if not post_values_all:
            return self.env["mail.message"]
        if len(post_values_all) == 1:
            res_id, post_values = next(iter(post_values_all.items()))
            return self.browse(res_id).message_post(**post_values)
        common = None
        bodies, values_per_record, notify_per_record = {}, {}, {}
        per_record_keys = self._BATCH_PER_RECORD_PARAMS | (
            self._get_message_create_valid_field_names()
            - {"author_id", "body", "message_type", "model", "res_id", "subtype_id"}
        )
        for res_id, post_values in post_values_all.items():
            rest = dict(post_values)
            bodies[res_id] = rest.pop("body", "")
            if "force_email_lang" in rest:
                notify_per_record[res_id] = {
                    "force_email_lang": rest.pop("force_email_lang")
                }
            values_per_record[res_id] = {
                key: rest.pop(key) for key in list(rest) if key in per_record_keys
            }
            if common is None:
                common = rest
            elif rest != common:
                common = False
                break
        if common is False or common.get("body_is_html"):
            _debug.logic(
                "post_values_all",
                model=self._name,
                records=len(post_values_all),
                by="loop",
                reason="uncommon_values" if common is False else "body_is_html",
            )
            return self._message_post_values_all_loop(post_values_all)
        common = dict(common)
        if subtype_xmlid := common.pop("subtype_xmlid", None):
            common["subtype_id"] = self.env["ir.model.data"]._xmlid_to_res_id(
                subtype_xmlid
            )
        _debug.logic(
            "post_values_all",
            model=self._name,
            records=len(post_values_all),
            by="batch",
        )
        return self.browse(list(post_values_all))._message_post_batch(
            bodies,
            values_per_record=values_per_record,
            notify_per_record=notify_per_record,
            **common,
        )

    def _message_post_values_all_loop(
        self, post_values_all: dict[int, dict]
    ) -> MailMessage:
        messages = self.env["mail.message"]
        for res_id, post_values in post_values_all.items():
            messages += self.browse(res_id).message_post(**post_values)
        return messages

    def _message_post_batch_check_per_record(
        self,
        values_per_record: dict[int, dict] | None,
        notify_per_record: dict[int, dict] | None,
    ) -> dict[int, dict]:
        values_per_record = values_per_record or {}
        allowed = self._BATCH_PER_RECORD_PARAMS | (
            self._get_message_create_valid_field_names()
            - {"body", "message_type", "model", "res_id", "subtype_id"}
        )
        for res_id, values in values_per_record.items():
            self._check_supported_parameters(set(values), restricting_names=allowed)
            self._check_attachments_format(values.get("attachments"))
            for key in ("attachment_ids", "partner_ids"):
                if values.get(key) and not is_list_of(values[key], int):
                    raise ValueError(
                        f"Batch post should receive {key} as a list of IDs "
                        f"(received {values[key]!r} for record {res_id})"
                    )
        valid_notify = self._get_notify_valid_parameters()
        for values in (notify_per_record or {}).values():
            self._check_supported_parameters(
                set(values), restricting_names=valid_notify
            )
        return values_per_record

    def _message_post_batch_notify(
        self,
        messages: MailMessage,
        values_list: list[dict],
        follower_data: dict,
        notif_kwargs: dict,
        notify_per_record: dict[int, dict] | None = None,
    ) -> None:
        notify_per_record = notify_per_record or {}
        email_collector: list[dict] = []
        inbox_collector: list[dict] = []
        email_prefetch = (
            self._notify_by_email_prefetch(messages)
            if not self._is_notification_scheduled(notif_kwargs.get("scheduled_date"))
            and self._notify_batch_wants_email_prefetch(follower_data, values_list)
            else {}
        )
        with _debug.perf(
            "message_post_batch_notify",
            cr=self.env.cr,
            model=self._name,
            messages=len(messages),
            prefetched=len(email_prefetch),
        ) as span:
            for record, message, values in zip(
                self, messages, values_list, strict=True
            ):
                record._message_post_after_hook(message, values)
                record._notify_thread(
                    message,
                    values,
                    follower_data={
                        record.id: self._message_post_batch_record_followers(
                            follower_data.get(record.id, {}), values
                        )
                    },
                    email_collector=email_collector,
                    email_prefetch=email_prefetch.get(message.id),
                    inbox_collector=inbox_collector,
                    **{**notif_kwargs, **notify_per_record.get(record.id, {})},
                )
            span.set(collected=len(email_collector), inbox=len(inbox_collector))
        self._notify_by_inbox_flush(inbox_collector)
        self._notify_by_email_flush(
            email_collector,
            force_send=notif_kwargs.get("force_send", True),
            send_after_commit=notif_kwargs.get("send_after_commit", True),
        )

    def _message_post_batch_check_parameters(
        self, kwargs: dict, message_type: str
    ) -> tuple[dict, dict]:
        if message_type == "user_notification":
            raise ValueError("Use message_notify to send a notification to an user.")
        self._check_supported_parameters(
            set(kwargs.keys()),
            forbidden_names={
                "attachment_ids",
                "attachments",
                "body",
                "model",
                "parent_id",
                "partner_ids",
                "res_id",
                "subtype",
                "subtype_xmlid",
            },
        )
        return self._message_split_kwargs(kwargs)

    def _message_post_batch_values(
        self,
        bodies: dict[int, str],
        msg_kwargs: dict,
        *,
        message_type: str,
        subject: str | Literal[False],
        subtype_id: int | Literal[False],
        subtype_ids: dict[int, int],
        author_id: int | None,
        authors: dict[int, int],
        email_from: str | None,
        tracking_values: dict[int, list],
        values_per_record: dict[int, dict] | None = None,
    ) -> list[dict]:
        values_per_record = values_per_record or {}
        emails_from = {
            res_id: values["email_from"]
            for res_id, values in values_per_record.items()
            if "email_from" in values
        }
        author_per_override, reply_tos_per_author = self._message_post_batch_authors(
            author_id, email_from, authors, emails_from
        )
        alias_domains = self.sudo()._mail_get_alias_domains(
            default_company=self.env.company
        )
        companies = self._mail_get_companies(default=self.env.company)
        parent_ids = self._message_compute_parent_ids()
        parent_ids.update(self._message_post_batch_parent_ids(values_per_record))

        values_list = []
        for record in self:
            record_author_id, record_email_from = author_per_override[
                (authors.get(record.id), emails_from.get(record.id))
            ]
            extra = dict(values_per_record.get(record.id, {}))
            partner_ids = extra.pop("partner_ids", None) or []
            attachments = extra.pop("attachments", None)
            attachment_ids = extra.pop("attachment_ids", None) or []
            extra.pop("parent_id", None)
            extra.pop("email_from", None)
            record._message_post_subscribe_recipients(partner_ids)
            values = record._message_post_values_common(
                bodies.get(record.id),
                msg_kwargs,
                message_type=message_type,
                subject=extra.pop("subject", subject),
                subtype_id=subtype_ids.get(record.id, subtype_id),
                author_id=record_author_id,
                author_guest_id=False,
                email_from=record_email_from,
                parent_id=parent_ids.get(record.id, False),
                partner_ids=partner_ids,
            )
            values.update(extra)
            if record.id in tracking_values:
                values["tracking_value_ids"] = tracking_values[record.id]
            values.setdefault("record_alias_domain_id", alias_domains[record.id].id)
            values.setdefault("record_company_id", companies[record.id].id)
            values.setdefault(
                "reply_to",
                reply_tos_per_author[(record_author_id, record_email_from)][record.id],
            )
            if attachments or attachment_ids:
                values.update(
                    record._process_attachments_for_post(
                        attachments, attachment_ids, values
                    )
                )
            values_list.append(values)
        return values_list

    def _message_post_batch_parent_ids(
        self, values_per_record: dict[int, dict]
    ) -> dict[int, int]:
        asked = {
            res_id: values["parent_id"]
            for res_id, values in values_per_record.items()
            if values.get("parent_id")
        }
        if not asked:
            return {}
        on_thread = {
            (message.res_id, message.id)
            for message in self.env["mail.message"]
            .sudo()
            .search(
                [
                    ("id", "in", list(set(asked.values()))),
                    ("model", "=", self._name),
                    ("res_id", "in", list(asked)),
                ]
            )
        }
        kept = {
            res_id: parent_id
            for res_id, parent_id in asked.items()
            if (res_id, parent_id) in on_thread
        }
        _debug.logic(
            "batch_parents",
            model=self._name,
            asked=len(asked),
            kept=len(kept),
        )
        return kept

    def _message_post_batch_authors(
        self,
        author_id: int | None,
        email_from: str | None,
        authors: dict[int, int],
        emails_from: dict[int, str] | None = None,
    ) -> tuple[dict, dict]:
        emails_from = emails_from or {}
        overrides = {
            (authors.get(record.id), emails_from.get(record.id)) for record in self
        }
        self._mail_warm_author_emails({author for author, _email in overrides})
        _debug.perf.count(
            "batch_authors_resolved", model=self._name, overrides=len(overrides)
        )
        author_per_override = {}
        for override in overrides:
            author_override, email_override = override
            author_per_override[override] = self._message_compute_batch_author(
                author_id if author_override is None else author_override,
                email_override
                if email_override is not None
                else email_from
                if author_override is None
                else None,
            )
        reply_tos_per_author = self._notify_get_reply_to_per_author(
            set(author_per_override.values())
        )
        return author_per_override, reply_tos_per_author

    def _message_post_subscribe_author(self, values_list: list[dict]) -> None:
        if self.env.context.get("mail_post_autofollow_author_skip"):
            return
        comment_subtype_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "mail.mt_comment"
        )
        res_ids_per_author = defaultdict(list)
        for values in values_list:
            if (
                values["message_type"] not in self._AUTHOR_SUBSCRIBE_EXEMPT_TYPES
                and values["subtype_id"] == comment_subtype_id
            ):
                res_ids_per_author[values["author_id"]].append(values["res_id"])
        for author_id, res_ids in res_ids_per_author.items():
            real_author = self._message_compute_real_author(author_id)
            _debug.logic(
                "author_subscribe",
                model=self._name,
                author=author_id,
                records=len(res_ids),
                subscribed=bool(real_author and not real_author.partner_share),
            )
            if real_author and not real_author.partner_share:
                self.browse(res_ids)._message_subscribe(
                    partner_ids=[real_author.id], customer_ids=[]
                )

    def _notify_batch_wants_email_prefetch(
        self, follower_data: dict, values_list: list[dict]
    ) -> bool:
        if any(
            pdata["notif"] == "email"
            for record_data in follower_data.values()
            for pdata in record_data.values()
        ):
            return True
        return any(values.get("outgoing_email_to") for values in values_list)

    def _notify_by_email_prefetch(self, messages: MailMessage) -> dict:
        ancestors = self._notify_by_email_get_ancestors(messages)
        TrackingValue = self.env["mail.tracking.value"].sudo()
        tracking_values = TrackingValue.search_fetch(
            [("mail_message_id", "in", messages.ids)], ["mail_message_id"]
        )
        tracking_ids_by_message = defaultdict(list)
        for tracking_value in tracking_values:
            tracking_ids_by_message[tracking_value.mail_message_id.id].append(
                tracking_value.id
            )
        _debug.perf.count(
            "email_prefetch",
            model=self._name,
            messages=len(messages),
            tracking_values=len(tracking_values),
        )
        return {
            message.id: {
                "ancestors": ancestors[message.id],
                "tracking_values": TrackingValue.browse(
                    tracking_ids_by_message[message.id]
                ),
            }
            for message in messages
        }

    def _message_post_batch_follower_data(
        self, message_type: str, values_list: list[dict], include_followers: bool = True
    ) -> dict:
        by_subtype = defaultdict(list)
        pids_by_subtype = defaultdict(set)
        for record, values in zip(self, values_list, strict=True):
            by_subtype[values["subtype_id"]].append(record.id)
            pids_by_subtype[values["subtype_id"]].update(
                values.get("partner_ids") or ()
            )
        follower_data = {}
        for subtype_id, res_ids in by_subtype.items():
            follower_data.update(
                self.env["mail.followers"]._get_recipient_data(
                    self.browse(res_ids),
                    message_type,
                    subtype_id,
                    sorted(pids_by_subtype[subtype_id]),
                    include_followers=include_followers,
                )
            )
        _debug.perf.count(
            "batch_follower_data",
            model=self._name,
            subtypes=len(by_subtype),
            records=len(follower_data),
            include_followers=include_followers,
        )
        return follower_data

    @api.model
    def _message_post_batch_record_followers(
        self, record_data: dict, values: dict
    ) -> dict:
        record_pids = set(values.get("partner_ids") or ())
        if not record_pids:
            return {
                pid: data for pid, data in record_data.items() if data["is_follower"]
            }
        return {
            pid: data
            for pid, data in record_data.items()
            if data["is_follower"] or pid in record_pids
        }

    def _message_post_after_hook(self, message: MailMessage, msg_values: dict) -> None:
        return

    def _message_mail_after_hook(self, mails: MailMail) -> None:
        return

    def _process_existing_attachments_for_post(
        self, attachment_ids: list[int], model: str, res_id: int
    ) -> list[tuple]:
        filtered_attachment_ids = (
            self.env["ir.attachment"]
            .sudo()
            .browse(attachment_ids)
            .filtered(
                lambda a: (
                    a.res_model in ("mail.compose.message", "mail.scheduled.message")
                    and a.create_uid.id == self.env.uid
                )
            )
        )
        if filtered_attachment_ids:
            filtered_attachment_ids.write({"res_model": model, "res_id": res_id})
        if not self.env.user._is_internal():
            attachment_ids = filtered_attachment_ids.ids
        _debug.logic(
            "existing_attachments_for_post",
            model=model,
            record=res_id,
            requested=len(attachment_ids),
            relinked=len(filtered_attachment_ids),
            internal=self.env.user._is_internal(),
        )
        return [(4, att_id) for att_id in attachment_ids]

    def _get_body_attachment_markers(self, fragments: list) -> tuple[set, set]:
        body_cids, body_filenames = set(), set()
        for node in iter_fragment_elements(fragments, "img"):
            if node.get("src", "").startswith("cid:"):
                body_cids.add(node.get("src").split("cid:")[1])
            elif node.get("data-filename"):
                body_filenames.add(node.get("data-filename"))
        return body_cids, body_filenames

    def _prepare_new_attachments_for_post(
        self,
        attachments: list[tuple | list],
        model: str,
        res_id: int,
        body_cids: set,
        body_filenames: set,
    ) -> tuple[list[dict], list[tuple]]:
        values_list, extra_list = [], []
        for attachment in attachments:
            if len(attachment) == 2:
                name, content = attachment
                cid = False
                info = {}
            elif len(attachment) == 3:
                name, content, info = attachment
                cid = info and info.get("cid")
            else:
                continue

            if isinstance(content, str):
                encoding = info and info.get("encoding")
                try:
                    content = content.encode(encoding or "utf-8")
                except UnicodeEncodeError:
                    content = content.encode("utf-8")
            elif isinstance(content, EmailMessage):
                content = content.as_bytes()
            elif content is None:
                continue

            attachment_values = {
                "name": name,
                "datas": base64.b64encode(content),
                "type": "binary",
                "description": name,
                "res_model": model,
                "res_id": res_id,
            }
            token = False
            if (cid and cid in body_cids) or (name and name in body_filenames):
                token = self.env["ir.attachment"]._prepare_access_token()
                attachment_values["access_token"] = token
            values_list.append(attachment_values)
            extra_list.append((cid, name, token, info))
        return values_list, extra_list

    def _update_body_attachment_urls(
        self, fragments: list, attach_cid_mapping: dict, attach_name_mapping: dict
    ) -> bool:
        postprocessed = False
        for node in iter_fragment_elements(fragments, "img"):
            att_id, token = False, False
            if node.get("src", "").startswith("cid:"):
                cid = node.get("src").split("cid:")[1]
                att_id, token = attach_cid_mapping.get(cid, (False, False))
            if (not att_id or not token) and node.get("data-filename"):
                att_id, token = attach_name_mapping.get(
                    node.get("data-filename"), (False, False)
                )
            if att_id and token:
                node.set("src", f"/web/image/{att_id}?access_token={token}")
                postprocessed = True
        return postprocessed

    def _process_attachments_for_post(
        self,
        attachments: list[tuple | list] | None,
        attachment_ids: list[int],
        message_values: dict,
    ) -> dict:
        if "res_id" in message_values:
            model, res_id = message_values["model"], message_values["res_id"]
        else:
            self.check_singleton()
            model, res_id = self._name, self.id
        body = ""
        if message_values.get("body"):
            body = (
                escape(message_values["body"])
                if not is_html_empty(message_values["body"])
                else ""
            )

        m2m_attachment_ids = []
        if attachment_ids:
            m2m_attachment_ids += self._process_existing_attachments_for_post(
                attachment_ids, model, res_id
            )

        return_values = {}
        if attachments:
            fragments, body_cids, body_filenames = None, set(), set()
            if body:
                fragments = parse_body_fragments(body)
                body_cids, body_filenames = self._get_body_attachment_markers(fragments)

            attachment_values_list, attachment_extra_list = (
                self._prepare_new_attachments_for_post(
                    attachments, model, res_id, body_cids, body_filenames
                )
            )
            new_attachments = self._create_attachments_for_post(
                attachment_values_list, attachment_extra_list
            )
            attach_cid_mapping, attach_name_mapping = {}, {}
            for attachment, (cid, name, token, _info) in zip(
                new_attachments, attachment_extra_list, strict=True
            ):
                if cid:
                    attach_cid_mapping[cid] = (attachment.id, token)
                if name:
                    attach_name_mapping[name] = (attachment.id, token)
                m2m_attachment_ids.append((4, attachment.id))

            _debug.pipeline(
                "attachments_for_post",
                model=model,
                record=res_id,
                created=len(new_attachments),
                cids=len(body_cids),
                filenames=len(body_filenames),
            )
            if (body_cids or body_filenames) and body:
                if self._update_body_attachment_urls(
                    fragments, attach_cid_mapping, attach_name_mapping
                ):
                    _debug.logic(
                        "body_attachment_urls_rewritten", model=model, record=res_id
                    )
                    return_values["body"] = render_body_fragments(fragments)
        return_values["attachment_ids"] = m2m_attachment_ids
        return return_values

    def _create_attachments_for_post(
        self, values_list: list[dict], extra_list: list[tuple]
    ) -> IrAttachment:
        return self.env["ir.attachment"].sudo().create(values_list)

    def _process_attachments_for_template_post(
        self, mail_template: MailTemplate
    ) -> dict:
        return {}

    def _get_source_with_bodies(
        self,
        source_ref: models.BaseModel | str,
        kwargs: dict,
        render_values: dict | None,
        render_values_per_record: dict[int, dict] | None = None,
    ) -> tuple:
        template, view = self._get_source_from_ref(source_ref)
        self._check_supported_parameters(
            set(kwargs.keys()),
            forbidden_names=set(self._SOURCE_POST_FORBIDDEN_PARAMS),
        )
        _debug.logic(
            "source_resolved",
            model=self._name,
            count=len(self),
            template=template.id if template else None,
            view=view.id if view else None,
        )
        bodies = (
            self.env["mixin.mail.render"]._render_template_qweb_view(
                view,
                self._name,
                self.ids,
                add_context=render_values,
                add_context_per_record=render_values_per_record,
            )
            if view
            else {}
        )
        return template, bodies

    def message_mail_with_source(
        self,
        source_ref: models.BaseModel | str,
        *,
        render_values: dict | None = None,
        message_type: str = "notification",
        auto_commit: bool = False,
        **kwargs,
    ) -> MailMail:
        template, bodies = self._get_source_with_bodies(
            source_ref, kwargs, render_values
        )

        composer_values = {
            "composition_mode": "mass_mail",
            "message_type": message_type,
            "subtype_id": kwargs.pop("subtype_id", False)
            or self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_note"),
            **kwargs,
        }
        composer_ctx = {
            "default_composition_mode": "mass_mail",
            "default_model": self._name,
            "default_template_id": template.id if template else False,
        }

        mails_su = self.env["mail.mail"].sudo()
        for subset in [self] if template else self:
            composer_ctx["default_res_ids"] = subset.ids
            if not template:
                composer_values["body"] = bodies[subset.id]

            composer = (
                self.env["mail.compose.message"]
                .with_context(**composer_ctx)
                .create(composer_values)
            )
            mails_as_sudo, _messages = composer._action_send_mail(
                auto_commit=auto_commit
            )
            mails_su += mails_as_sudo
        _debug.pipeline(
            "message_mail_with_source",
            model=self._name,
            count=len(self),
            template=template.id if template else None,
            mails=len(mails_su),
            auto_commit=auto_commit,
        )
        return mails_su

    def activity_send_mail(self, template_id: int) -> bool:
        template = self.env["mail.template"].browse(template_id).exists()
        if not template or template.model != self._name:
            _debug.logic(
                "activity_send_mail_refused",
                model=self._name,
                template=template_id,
                reason="missing" if not template else "model_mismatch",
            )
            if template:
                _logger.warning(
                    "Refused to send template %s (model %s) on %s",
                    template.id,
                    template.model,
                    self._name,
                )
            return False
        self.message_post_with_source(template, subtype_xmlid="mail.mt_comment")
        return True

    def message_post_with_source(
        self,
        source_ref: models.BaseModel | str,
        *,
        render_values: dict | None = None,
        render_values_per_record: dict[int, dict] | None = None,
        message_type: str = "notification",
        subtype_xmlid: str | Literal[False] = False,
        subtype_id: int | Literal[False] = False,
        **kwargs,
    ) -> MailMessage:
        template, bodies = self._get_source_with_bodies(
            source_ref, kwargs, render_values, render_values_per_record
        )

        if subtype_xmlid:
            subtype_id = self.env["ir.model.data"]._xmlid_to_res_id(subtype_xmlid)
        if not subtype_id:
            subtype_id = self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_note")

        if template:
            post_values_all = {}
            target = self
            for record in self:
                composer = (
                    self.env["mail.compose.message"]
                    .with_context(
                        default_composition_mode="comment",
                        default_model=self._name,
                        default_res_ids=record.ids,
                        default_template_id=template.id,
                    )
                    .create(
                        {
                            "message_type": message_type,
                            "subtype_id": subtype_id,
                            **kwargs,
                        }
                    )
                )
                post_values_all.update(composer._prepare_post_values(record.ids))
                target = composer._get_comment_target_model()
            messages_all = target._message_post_values_all(post_values_all)
        else:
            messages_all = self._message_post_values_all(
                {
                    record.id: {
                        "body": bodies[record.id],
                        "message_type": message_type,
                        "subtype_id": subtype_id,
                        **kwargs,
                    }
                    for record in self
                }
            )
        _debug.pipeline(
            "message_post_with_source",
            model=self._name,
            count=len(self),
            template=template.id if template else None,
            messages=len(messages_all),
        )
        return messages_all

    def _message_post_origin_links(
        self,
        origins: Iterable[tuple[int, models.BaseModel]],
        *,
        subtype_xmlid: str | Literal[False] = "mail.mt_note",
        subtype_id: int | Literal[False] = False,
    ) -> MailMessage:
        rounds: list[dict[int, models.BaseModel]] = []
        for res_id, origin in origins:
            if not origin:
                continue
            for pairs in rounds:
                if res_id not in pairs:
                    pairs[res_id] = origin
                    break
            else:
                rounds.append({res_id: origin})
        messages = self.env["mail.message"]
        for pairs in rounds:
            records = self.browse(list(pairs))
            messages += records.message_post_with_source(
                "mail.message_origin_link",
                render_values_per_record={
                    record.id: {"self": record, "origin": pairs[record.id]}
                    for record in records
                },
                subtype_xmlid=subtype_xmlid,
                subtype_id=subtype_id,
            )
        return messages

    def message_notify(
        self,
        *,
        body: str = "",
        subject: str | Literal[False] = False,
        author_id: int | None = None,
        email_from: str | None = None,
        model: str | Literal[False] = False,
        res_id: int | Literal[False] = False,
        subtype_xmlid: str | None = None,
        subtype_id: int | Literal[False] = False,
        partner_ids: list[int] | Literal[False] = False,
        attachments: list[tuple | list] | None = None,
        attachment_ids: list[int] | None = None,
        **kwargs,
    ) -> MailMessage:
        if self:
            self.check_singleton()
        key = self.id if self else False
        return self._message_notify_batch(
            {key: body},
            subjects={key: subject},
            author_id=author_id,
            email_from=email_from,
            model=model,
            res_id=res_id,
            subtype_xmlid=subtype_xmlid,
            subtype_id=subtype_id,
            partner_ids=partner_ids,
            attachments=attachments,
            attachment_ids=attachment_ids,
            **kwargs,
        )

    def _message_notify_check_parameters(
        self,
        kwargs: dict,
        *,
        bodies: dict,
        partner_ids: list[int] | Literal[False],
        partner_ids_per_record: dict[int, list[int]] | None,
        attachments: list[tuple | list] | None,
        attachment_ids: list[int] | None,
    ) -> tuple[dict, dict]:
        if len(bodies) > 1 and (attachments or attachment_ids):
            raise ValueError(
                "Batch notification cannot support attachments on more than 1 document"
            )
        self._check_supported_parameters(
            set(kwargs.keys()),
            forbidden_names={
                "incoming_email_cc",
                "incoming_email_to",
                "message_id",
                "message_type",
                "outgoing_email_to",
                "parent_id",
            },
        )
        self._check_attachments_format(attachments)
        if attachment_ids and not is_list_of(attachment_ids, int):
            raise ValueError(
                "Notification should receive attachments records as a list of "
                f"IDs (received {attachment_ids!r})"
            )
        if not is_list_of(partner_ids, int):
            raise ValueError(
                "Notification should receive partners given as a list of IDs "
                f"(received {partner_ids!r})"
            )
        for record_id, record_pids in (partner_ids_per_record or {}).items():
            if not is_list_of(record_pids, int):
                raise ValueError(
                    "Notification should receive partners given as a list of IDs "
                    f"(received {record_pids!r} for record {record_id})"
                )

        msg_kwargs, notif_kwargs = self._message_split_kwargs(kwargs)
        if len(bodies) > 1 and (
            flattened := {"record_alias_domain_id", "record_company_id", "reply_to"}
            & set(msg_kwargs)
        ):
            raise ValueError(
                f"Batch notification derives {', '.join(sorted(flattened))} from "
                "each document and cannot take them per call"
            )
        notif_kwargs["notify_author_mention"] = notif_kwargs.get(
            "notify_author_mention", True
        )
        return msg_kwargs, notif_kwargs

    def _message_notify_batch_values(
        self,
        bodies: dict,
        msg_kwargs: dict,
        *,
        subjects: dict,
        model: str | Literal[False],
        res_id: int | Literal[False],
        subtype_id: int | Literal[False],
        author_id: int | None,
        email_from: str | None,
        partner_ids: list[int],
        partner_ids_per_record: dict[int, list[int]],
        attachments: list[tuple | list] | None,
        attachment_ids: list[int] | None,
    ) -> tuple[list[dict], list[models.BaseModel]]:
        alias_domains = (
            self._mail_get_alias_domains(default_company=self.env.company)
            if self and "record_alias_domain_id" not in msg_kwargs
            else {}
        )
        companies = (
            self._mail_get_companies(default=self.env.company)
            if self and "record_company_id" not in msg_kwargs
            else {}
        )
        reply_tos = (
            self._notify_get_reply_to(default=email_from, author_id=author_id)
            if "reply_to" not in msg_kwargs
            else {}
        )

        values_list = []
        notified_records = []
        for record_id, body in bodies.items():
            notified_records.append(
                self.browse(record_id) if record_id else self.browse()
            )
            msg_values = {
                "author_id": author_id,
                "email_from": email_from,
                "model": self._name if record_id else model,
                "res_id": record_id or res_id,
                "body": _escape_body(body),
                "is_internal": True,
                "message_type": "user_notification",
                "subject": subjects.get(record_id, False),
                "subtype_id": subtype_id,
                "message_id": generate_tracking_message_id("message-notify"),
                "partner_ids": partner_ids_per_record.get(record_id, partner_ids),
                "email_add_signature": True,
            }
            msg_values.update(msg_kwargs)
            if record_id:
                if "record_alias_domain_id" not in msg_values:
                    msg_values["record_alias_domain_id"] = alias_domains[record_id].id
                if "record_company_id" not in msg_values:
                    msg_values["record_company_id"] = companies[record_id].id
            if "reply_to" not in msg_values:
                msg_values["reply_to"] = reply_tos[record_id]
            if attachments or attachment_ids:
                msg_values.update(
                    self._process_attachments_for_post(
                        attachments, attachment_ids, msg_values
                    )
                )
            values_list.append(msg_values)
        return values_list, notified_records

    def _message_notify_batch_dispatch(
        self,
        messages: MailMessage,
        values_list: list[dict],
        notified_records: list[models.BaseModel],
        subtype_id: int | Literal[False],
        partner_ids: list[int],
        per_record_pids: dict[int, list[int]],
        notif_kwargs: dict,
    ) -> None:
        all_pids = sorted(
            {*partner_ids, *(pid for pids in per_record_pids.values() for pid in pids)}
        )
        follower_data = notif_kwargs.pop("follower_data", None) or self.env[
            "mail.followers"
        ]._get_recipient_data(self, "user_notification", subtype_id, all_pids)
        email_collector: list[dict] = []
        inbox_collector: list[dict] = []
        email_prefetch = (
            self._notify_by_email_prefetch(messages)
            if self._notify_batch_wants_email_prefetch(follower_data, values_list)
            else {}
        )
        _debug.pipeline(
            "message_notify_dispatch",
            model=self._name,
            messages=len(messages),
            partners=len(all_pids),
            prefetched=len(email_prefetch),
        )
        for message, msg_values, notified in zip(
            messages, values_list, notified_records, strict=True
        ):
            record_data = follower_data.get(notified.id if notified else 0, {})
            if per_record_pids:
                record_pids = set(msg_values["partner_ids"])
                record_data = {
                    pid: data for pid, data in record_data.items() if pid in record_pids
                }
            notified._fallback_lang()._notify_thread(
                message,
                msg_values,
                follower_data={notified.id: record_data},
                email_collector=email_collector,
                email_prefetch=email_prefetch.get(message.id),
                inbox_collector=inbox_collector,
                **notif_kwargs,
            )
        self._notify_by_inbox_flush(inbox_collector)
        self._notify_by_email_flush(
            email_collector,
            force_send=notif_kwargs.get("force_send", True),
            send_after_commit=notif_kwargs.get("send_after_commit", True),
        )

    def _message_notify_batch(
        self,
        bodies: dict,
        *,
        subjects: dict | None = None,
        author_id: int | None = None,
        email_from: str | None = None,
        model: str | Literal[False] = False,
        res_id: int | Literal[False] = False,
        subtype_xmlid: str | None = None,
        subtype_id: int | Literal[False] = False,
        partner_ids: list[int] | Literal[False] = False,
        partner_ids_per_record: dict[int, list[int]] | None = None,
        attachments: list[tuple | list] | None = None,
        attachment_ids: list[int] | None = None,
        **kwargs,
    ) -> MailMessage:
        partner_ids_per_record = partner_ids_per_record or {}
        if not partner_ids and not any(partner_ids_per_record.values()):
            _debug.logic(
                "message_notify_skipped", model=self._name, reason="no_recipients"
            )
            _logger.warning("Message notify called without recipient_ids, skipping")
            return self.env["mail.message"]
        partner_ids = list(partner_ids or [])
        msg_kwargs, notif_kwargs = self._message_notify_check_parameters(
            kwargs,
            bodies=bodies,
            partner_ids=partner_ids,
            partner_ids_per_record=partner_ids_per_record,
            attachments=attachments,
            attachment_ids=attachment_ids,
        )

        author_id, email_from = self._message_compute_batch_author(
            author_id, email_from
        )

        if not model or not res_id:
            model, res_id = False, False

        if subtype_xmlid:
            subtype_id = self.env["ir.model.data"]._xmlid_to_res_id(subtype_xmlid)
        if not subtype_id:
            subtype_id = self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_note")

        _debug.pipeline(
            "message_notify_batch",
            model=self._name,
            bodies=len(bodies),
            target_model=model or None,
            target=res_id or None,
            author=author_id,
            partners=len(partner_ids),
            per_record=len(partner_ids_per_record),
        )
        values_list, notified_records = self._message_notify_batch_values(
            bodies,
            msg_kwargs,
            subjects=subjects or {},
            model=model,
            res_id=res_id,
            subtype_id=subtype_id,
            author_id=author_id,
            email_from=email_from,
            partner_ids=partner_ids,
            partner_ids_per_record=partner_ids_per_record,
            attachments=attachments,
            attachment_ids=attachment_ids,
        )

        messages = self._message_create(values_list)
        self._message_notify_batch_dispatch(
            messages,
            values_list,
            notified_records,
            subtype_id,
            partner_ids,
            partner_ids_per_record,
            notif_kwargs,
        )
        return messages

    def _message_log_with_view(
        self,
        view_ref: models.BaseModel | str | int,
        render_values: dict | None = None,
        message_type: str = "notification",
        **kwargs,
    ) -> MailMessage:
        self._check_supported_parameters(
            set(kwargs.keys()),
            forbidden_names={
                "body",
                "bodies",
                "incoming_email_cc",
                "incoming_email_to",
                "outgoing_email_to",
            },
        )

        with _debug.perf(
            "log_view_rendered",
            cr=self.env.cr,
            model=self._name,
            count=len(self),
            view=view_ref if isinstance(view_ref, (str, int)) else view_ref.id,
        ):
            bodies = self.env["mixin.mail.render"]._render_template_qweb_view(
                view_ref,
                self._name,
                self.ids,
                add_context=render_values,
            )

        return self._message_log_batch(
            bodies=bodies, message_type=message_type, **kwargs
        )

    def _message_log(
        self,
        *,
        body: str = "",
        subject: str | Literal[False] = False,
        author_id: int | None = None,
        email_from: str | None = None,
        message_type: str = "notification",
        partner_ids: list[int] | Literal[False] = False,
        attachment_ids: list[int] | Literal[False] = False,
        tracking_value_ids: list | Literal[False] = False,
    ) -> MailMessage:
        self.check_singleton()

        return self._message_log_batch(
            {self.id: body},
            subject=subject,
            author_id=author_id,
            email_from=email_from,
            message_type=message_type,
            partner_ids=partner_ids,
            attachment_ids=attachment_ids,
            tracking_values={self.id: tracking_value_ids}
            if tracking_value_ids
            else None,
        )

    def _message_log_batch(
        self,
        bodies: dict,
        subject: str | Literal[False] = False,
        author_id: int | None = None,
        email_from: str | None = None,
        message_type: str = "notification",
        partner_ids: list[int] | Literal[False] = False,
        attachment_ids: list[int] | Literal[False] = False,
        authors: dict[int, int] | None = None,
        tracking_values: dict[int, list] | None = None,
    ) -> MailMessage:
        if len(self) > 1 and attachment_ids:
            raise ValueError(
                "Batch log cannot support attachments on more than 1 document"
            )

        self._mail_warm_author_emails((authors or {}).values())
        default_author = self._message_compute_batch_author(author_id, email_from)
        author_per_id = {None: default_author}

        def _author_values(record_id: int) -> tuple:
            override = (authors or {}).get(record_id)
            if override not in author_per_id:
                author_per_id[override] = self._message_compute_batch_author(
                    override, None
                )
            return author_per_id[override]

        for record in self:
            _author_values(record.id)
        reply_to_per_author = {
            pair: per_record[False]
            for pair, per_record in self.env["mixin.mail.thread"]
            ._notify_get_reply_to_per_author(set(author_per_id.values()))
            .items()
        }

        base_message_values = {
            "model": self._name,
            "record_alias_domain_id": False,
            "record_company_id": False,
            "attachment_ids": attachment_ids,
            "message_type": message_type,
            "is_internal": True,
            "subject": subject,
            "subtype_id": self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_note"),
            "email_add_signature": False,
            "partner_ids": partner_ids,
        }

        values_list = []
        for record in self:
            record_author_id, record_email_from = _author_values(record.id)
            values_list.append(
                dict(
                    base_message_values,
                    author_id=record_author_id,
                    email_from=record_email_from,
                    reply_to=reply_to_per_author[(record_author_id, record_email_from)],
                    res_id=record.id,
                    body=_escape_body(bodies.get(record.id)),
                    message_id=generate_tracking_message_id("message-notify"),
                    tracking_value_ids=(tracking_values or {}).get(record.id, False),
                )
            )
        _debug.pipeline(
            "message_log_batch",
            model=self._name,
            count=len(self),
            message_type=message_type,
            authors=len(author_per_id),
            tracked=len(tracking_values or {}),
        )
        return self.sudo()._message_create(values_list)

    def _mail_warm_author_emails(self, author_ids: Collection[int | None]) -> None:
        ids = {author_id for author_id in author_ids if author_id}
        if len(ids) > 1:
            self.env["res.partner"].browse(ids).mapped("email_formatted")

    def _message_compute_author(
        self,
        author_id: int | Literal[False] | None = None,
        email_from: str | None = None,
    ) -> tuple:
        by = "given"
        if author_id is None:
            if email_from:
                author = self._partner_get_or_create_from_emails_single(
                    [email_from], no_create=True
                )
                by = "email_from"
            else:
                author = self.env.user.partner_id
                email_from = author.email_formatted
                by = "user"
            author_id = author.id

        if email_from is None:
            if author_id:
                author = self.env["res.partner"].browse(author_id)
                email_from = author.email_formatted

        _debug.logic("author_computed", model=self._name, author=author_id, by=by)
        return author_id, email_from

    def _message_compute_batch_author(
        self,
        author_id: int | Literal[False] | None = None,
        email_from: str | None = None,
    ) -> tuple:
        author_source = self if len(self) == 1 else self.browse()
        return author_source._message_compute_author(author_id, email_from)

    def _message_compute_real_author(self, author_id: int) -> ResPartner:
        real_author = self.env["res.partner"]
        if self.env.user.active:
            real_author = self.env.user.partner_id
        elif author_id:
            author = self.env["res.partner"].browse(author_id)
            if author.active and author != self.env.ref("base.partner_root"):
                real_author = author
        return real_author

    def _message_compute_parent_id(
        self, parent_id: int | Literal[False]
    ) -> int | Literal[False]:
        messages_sudo = self.env["mail.message"].sudo()
        current_ancestor = messages_sudo
        if parent_id:
            current_ancestor = messages_sudo.search(
                [
                    ("id", "=", parent_id),
                    ("model", "=", self._name),
                    ("res_id", "=", self.id),
                ],
            )
        if current_ancestor:
            return current_ancestor.id
        if _debug.logic.enabled and parent_id:
            _debug.logic(
                "parent_not_on_thread",
                model=self._name,
                record=self.id,
                parent=parent_id,
            )
        return self._message_compute_parent_ids().get(self.id, False)

    def _message_compute_parent_ids(self) -> dict[int, int | Literal[False]]:
        parents = dict.fromkeys(self.ids, False)
        if not self._mail_flat_thread or not self.ids:
            return parents
        _debug.perf.count("parent_ids_queried", model=self._name, count=len(self.ids))
        parents.update(
            self.env.execute_query(
                SQL(
                    """
                    SELECT DISTINCT ON (res_id) res_id, id
                      FROM mail_message
                     WHERE model = %s
                       AND res_id = ANY(%s)
                       AND message_type != 'user_notification'
                     ORDER BY res_id,
                              (message_type IN ('comment', 'email')) DESC,
                              COALESCE(date, create_date) DESC,
                              id DESC
                    """,
                    self._name,
                    list(self.ids),
                    to_flush=_to_flush(
                        self.env["mail.message"],
                        "model",
                        "res_id",
                        "message_type",
                        "date",
                        "create_date",
                    ),
                )
            )
        )
        return parents

    def _message_compute_subject(self) -> str:
        self.check_singleton()
        return self.display_name

    def _message_create(self, values_list: list[dict]) -> MailMessage:
        ignored_names = self._get_message_create_ignore_field_names()
        values_list = [
            {key: val for key, val in values.items() if key not in ignored_names}
            for values in values_list
        ]
        create_values_list = []

        self._check_supported_parameters(
            {key for values in values_list for key in values},
            restricting_names=self._get_message_create_valid_field_names(),
        )

        for values in values_list:
            create_values = dict(values)
            create_values["partner_ids"] = [
                (4, pid) for pid in (create_values.get("partner_ids") or [])
            ]
            create_values_list.append(create_values)

        with _debug.perf(
            "message_create",
            cr=self.env.cr,
            model=self._name,
            count=len(create_values_list),
        ):
            return (
                self.env["mail.message"]
                .with_context(clean_context(self.env.context))
                .create(create_values_list)
            )

    def _get_message_create_valid_field_names(self) -> set:
        return {
            "attachment_ids",
            "author_guest_id",
            "author_id",
            "body",
            "create_date",
            "date",
            "email_add_signature",
            "email_from",
            "email_layout_xmlid",
            "incoming_email_cc",
            "incoming_email_to",
            "is_internal",
            "mail_activity_type_id",
            "mail_server_id",
            "message_id",
            "message_type",
            "model",
            "outgoing_email_to",
            "parent_id",
            "partner_ids",
            "record_alias_domain_id",
            "record_company_id",
            "reply_to",
            "reply_to_force_new",
            "res_id",
            "subject",
            "subtype_id",
            "tracking_value_ids",
        }

    def _get_message_create_ignore_field_names(self) -> set:
        return set()

    def _get_source_from_ref(self, source_ref: models.BaseModel | str) -> tuple:
        template, view = False, False
        if isinstance(source_ref, models.BaseModel):
            if source_ref._name == "mail.template":
                template = source_ref
            elif source_ref._name == "ir.ui.view":
                view = source_ref
            else:
                raise ValueError(
                    f"Invalid template or view source record {source_ref}, is "
                    f"{source_ref._name} instead"
                )
            if not template and not view:
                source_type = "template" if template is not False else "view"
                raise ValueError(
                    "Mailing or posting with a source should not be called with "
                    f"an empty {source_type}"
                )
        elif isinstance(source_ref, str):
            try:
                res_model, res_id = self.env[
                    "ir.model.data"
                ]._xmlid_to_res_model_res_id(source_ref, raise_if_not_found=True)
            except ValueError as e:
                raise ValueError(
                    f"Invalid template or view source Xml ID {source_ref} does "
                    "not exist anymore"
                ) from e
            if res_model == "mail.template":
                template = self.env["mail.template"].browse(res_id)
            elif res_model == "ir.ui.view":
                view = self.env["ir.ui.view"].browse(res_id)
            else:
                raise ValueError(
                    f"Invalid template or view source reference {source_ref}, is "
                    f"{res_model} instead"
                )
        else:
            raise ValueError(
                f"Invalid template or view source {source_ref} (type "
                f"{type(source_ref)}), should be a record or an XMLID"
            )
        return template, view

    def _get_notify_valid_parameters(self) -> set:
        valid = {
            "email_collector",
            "email_prefetch",
            "follower_data",
            "force_email_company",
            "force_email_lang",
            "force_record_name",
            "force_send",
            "inbox_collector",
            "mail_auto_delete",
            "model_description",
            "notify_author",
            "notify_author_mention",
            "notify_skip_followers",
            "scheduled_date",
            "send_after_commit",
            "skip_existing",
            "subtitles",
        }
        if not self.env.user.share or self.env.su:
            valid |= {"mail_headers"}
        return valid

    def _notify_get_flag(self, kwargs: dict, param_name: str, context_key: str) -> bool:
        value = kwargs.get(param_name)
        if value is None:
            return bool(self.env.context.get(context_key))
        return bool(value)

    @api.model
    def _is_notification_scheduled(
        self, notify_scheduled_date: str | datetime.datetime | None
    ) -> datetime.datetime | Literal[False]:
        if notify_scheduled_date:
            parsed_datetime = self.env["mail.mail"]._parse_scheduled_datetime(
                notify_scheduled_date
            )
            notify_scheduled_date = (
                parsed_datetime.replace(tzinfo=None) if parsed_datetime else False
            )
        now = self.env.cr.now()
        if now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        return (
            notify_scheduled_date
            if notify_scheduled_date and notify_scheduled_date > now
            else False
        )

    def _check_supported_parameters(
        self,
        parameter_names: set[str],
        forbidden_names: set[str] | None = None,
        restricting_names: set[str] | None = None,
    ) -> None:
        conflicting_names = set()
        if forbidden_names:
            conflicting_names = parameter_names & forbidden_names
        elif restricting_names:
            conflicting_names = parameter_names - restricting_names
        if conflicting_names:
            raise ValueError(
                "Those values are not supported when posting or notifying: "
                f"{', '.join(conflicting_names)}"
            )

    def _notify_cancel_by_type_generic(self, notification_type: str) -> bool:
        records = self.env.execute_query(
            SQL(
                """
                SELECT notif.id, msg.id
                  FROM mail_notification notif
                  JOIN mail_message msg ON notif.mail_message_id = msg.id
                 WHERE notif.notification_type = %s
                   AND notif.author_id = %s
                   AND notif.notification_status IN ('bounce', 'exception')
                   AND msg.model = %s
                """,
                notification_type,
                self.env.user.partner_id.id,
                self._name,
                to_flush=(
                    _to_flush(self.env["mail.message"], "model")
                    + _to_flush(
                        self.env["mail.notification"],
                        "author_id",
                        "mail_message_id",
                        "notification_status",
                        "notification_type",
                    )
                ),
            )
        )
        _debug.lifecycle(
            "notifications_canceled",
            model=self._name,
            notification_type=notification_type,
            count=len(records),
        )
        if records:
            notif_ids, msg_ids = zip(*records, strict=True)
            self.env["mail.notification"].browse(notif_ids).sudo().write(
                {"notification_status": "canceled"}
            )
            self.env["mail.message"].browse(
                set(msg_ids)
            )._notify_message_notification_update()
        return True

    @api.model
    def notify_cancel_by_type(self, notification_type: str) -> bool:
        if not self.env.user._is_internal():
            raise exceptions.AccessError(_("Access Denied"))
        self.browse().check_access("read")

        if notification_type == "email":
            self._notify_cancel_by_type_generic("email")
        return True

    def _notify_thread(
        self, message: MailMessage, msg_vals: dict | Literal[False] = False, **kwargs
    ) -> list[dict]:
        self = self._fallback_lang()
        self._check_supported_parameters(
            set(kwargs.keys()), restricting_names=self._get_notify_valid_parameters()
        )

        recipients_data = self._notify_get_recipients(
            message, msg_vals=msg_vals, **kwargs
        )
        uid2pid = {r["uid"]: r["id"] for r in recipients_data if r["id"] and r["uid"]}
        users = self.env["res.users"].browse(uid2pid)
        users._fields["partner_id"]._insert_cache(users, uid2pid.values())

        scheduled_date = self._is_notification_scheduled(
            kwargs.pop("scheduled_date", None)
        )
        _debug.pipeline(
            "notify_thread",
            model=self._name,
            record=self.id,
            message=message.id,
            recipients=len(recipients_data),
            inbox=sum(1 for r in recipients_data if r["notif"] == "inbox"),
            email=sum(1 for r in recipients_data if r["notif"] == "email"),
            scheduled=scheduled_date or None,
        )

        if not scheduled_date:
            self._notify_thread_with_out_of_office(
                message, recipients_data, msg_vals=msg_vals, **kwargs
            )

        if not recipients_data:
            return recipients_data

        if scheduled_date:
            _debug.logic(
                "notification_scheduled",
                model=self._name,
                message=message.id,
                scheduled=scheduled_date,
            )
            replayable = {
                key: value
                for key, value in kwargs.items()
                if key not in _NOTIFY_TRANSPORT_PARAMETERS
            }
            self.env["mail.message.schedule"].sudo().create(
                {
                    "scheduled_datetime": scheduled_date,
                    "mail_message_id": message.id,
                    "notification_parameters": self.env[
                        "mail.message.schedule"
                    ]._serialize_notification_parameters(replayable),
                }
            )
        else:
            self._notify_thread_by_inbox(
                message, recipients_data, msg_vals=msg_vals, **kwargs
            )
            self._notify_thread_by_email(
                message, recipients_data, msg_vals=msg_vals, **kwargs
            )
            self._notify_thread_by_web_push(
                message, recipients_data, msg_vals=msg_vals, **kwargs
            )

        return recipients_data

    def _notify_thread_by_inbox(
        self,
        message: MailMessage,
        recipients_data: list[dict],
        msg_vals: dict | Literal[False] = False,
        inbox_collector: list[dict] | None = None,
        **kwargs,
    ) -> None:
        inbox_pids_uids = sorted(
            [
                (r["id"], r["uid"])
                for r in recipients_data
                if r["id"] and r["notif"] == "inbox"
            ]
        )
        if not inbox_pids_uids:
            return
        entry = {
            "message": message,
            "msg_vals": msg_vals,
            "pids_uids": inbox_pids_uids,
        }
        if inbox_collector is not None:
            _debug.logic(
                "inbox_collected",
                model=self._name,
                message=message.id,
                partners=len(inbox_pids_uids),
            )
            inbox_collector.append(entry)
            return
        self._notify_by_inbox_flush([entry])

    def _notify_by_inbox_flush(self, collected: list[dict]) -> None:
        if not collected:
            return
        messages_sudo = (
            self.env["mail.message"]
            .sudo()
            .browse([entry["message"].id for entry in collected])
        )
        entries_by_message_id = {entry["message"].id: entry for entry in collected}
        with _debug.perf(
            "inbox_flush",
            cr=self.env.cr,
            model=self._name,
            messages=len(collected),
        ) as span:
            self.env["mail.notification"].sudo().create(
                [
                    {
                        "author_id": message.author_id.id,
                        "mail_message_id": message.id,
                        "notification_status": "sent",
                        "notification_type": "inbox",
                        "res_partner_id": pid,
                    }
                    for message in messages_sudo
                    for pid, _uid in entries_by_message_id[message.id]["pids_uids"]
                ]
            )
            entries_by_uid: dict[int, list[tuple[dict, int]]] = defaultdict(list)
            for entry in collected:
                for pid, uid in entry["pids_uids"]:
                    if uid:
                        entries_by_uid[uid].append((entry, pid))
            followers_by_thread = self._notify_inbox_get_followers(
                messages_sudo, entries_by_uid
            )
            starred_pids_by_message = {
                message.id: frozenset(message.starred_partner_ids.ids)
                for message in messages_sudo
            }
            span.set(
                notifications=sum(len(e["pids_uids"]) for e in collected),
                users=len(entries_by_uid),
            )

        shared_main_user_by_author: dict[int, int | None] = {}
        for uid, user_entries in entries_by_uid.items():
            self._notify_by_inbox_push(
                self.env["res.users"].browse(uid),
                user_entries,
                starred_pids_by_message,
                followers_by_thread,
                shared_main_user_by_author,
            )

    def _notify_by_inbox_push(
        self,
        user: ResUsers,
        user_entries: list[tuple[dict, int]],
        starred_pids_by_message: dict[int, frozenset[int]],
        followers_by_thread: dict[tuple[str, int], MailFollowers],
        shared_main_user_by_author: dict[int, int | None],
    ) -> None:
        main_user_field = self.env["res.partner"]._fields["main_user_id"]
        starred_field = self.env["mail.message"]._fields["starred"]
        messages_for_user = (
            self.env["mail.message"]
            .browse([entry["message"].id for entry, _pid in user_entries])
            .with_user(user)
            .with_context(allowed_company_ids=[], mail_notify_inbox=True)
        )
        starred_field._insert_cache(
            messages_for_user,
            [
                pid in starred_pids_by_message[entry["message"].id]
                for entry, pid in user_entries
            ],
        )
        for message_for_user, (entry, pid) in zip(
            messages_for_user, user_entries, strict=True
        ):
            author_sudo = message_for_user.sudo().author_id
            if author_sudo and author_sudo.id != pid:
                if author_sudo.id in shared_main_user_by_author:
                    main_user_field._insert_cache(
                        author_sudo, [shared_main_user_by_author[author_sudo.id]]
                    )
                else:
                    shared_main_user_by_author[author_sudo.id] = (
                        author_sudo.main_user_id.id or None
                    )
            message_sudo = message_for_user.sudo()
            store = Store(bus_channel=user).add(
                message_for_user,
                msg_vals=entry["msg_vals"],
                add_followers=True,
                followers=followers_by_thread.get(
                    (message_sudo.model, message_sudo.res_id),
                    self.env["mail.followers"].sudo(),
                ),
            )
            user._bus_send(
                "mail.message/inbox",
                {
                    "message_id": message_for_user.id,
                    "store_data": store.get_result(),
                },
            )

    def _notify_inbox_get_followers(
        self,
        messages_sudo: MailMessage,
        entries_by_uid: dict[int, list[tuple[dict, int]]],
    ) -> dict[tuple[str, int], MailFollowers]:
        void = self.env["mail.followers"].sudo()
        if not entries_by_uid:
            return {}
        partner_ids = self.env["res.users"].browse(list(entries_by_uid)).partner_id.ids
        res_ids_by_model = defaultdict(set)
        for message in messages_sudo:
            if message.model and message.res_id:
                res_ids_by_model[message.model].add(message.res_id)
        if not res_ids_by_model:
            return {}
        domain = Domain.OR(
            Domain("res_model", "=", model) & Domain("res_id", "in", list(res_ids))
            for model, res_ids in res_ids_by_model.items()
        ) & Domain("partner_id", "in", partner_ids)
        followers_by_thread = defaultdict(lambda: void)
        for follower in void.search_fetch(
            domain, ["res_model", "res_id", "partner_id"]
        ):
            followers_by_thread[(follower.res_model, follower.res_id)] |= follower
        return followers_by_thread

    def _notify_thread_by_email(
        self,
        message: MailMessage,
        recipients_data: list[dict],
        *,
        msg_vals: dict | Literal[False] = False,
        mail_auto_delete: bool = True,
        model_description: str | Literal[False] = False,
        force_email_company: ResCompany | Literal[False] = False,
        force_email_lang: str | Literal[False] = False,
        force_record_name: str | Literal[False] = False,
        subtitles: list[str] | None = None,
        force_send: bool = True,
        send_after_commit: bool = True,
        email_collector: list[dict] | None = None,
        email_prefetch: dict | None = None,
        **kwargs,
    ) -> bool:
        prepared = self._notify_by_email_prepare(
            message,
            recipients_data,
            msg_vals=msg_vals,
            mail_auto_delete=mail_auto_delete,
            model_description=model_description,
            force_email_company=force_email_company,
            force_email_lang=force_email_lang,
            force_record_name=force_record_name,
            subtitles=subtitles,
            email_prefetch=email_prefetch,
            **kwargs,
        )
        if email_collector is not None:
            _debug.logic(
                "email_collected",
                model=self._name,
                message=message.id,
                mails=len(prepared),
            )
            email_collector.extend(prepared)
            return True
        self._notify_by_email_flush(
            prepared, force_send=force_send, send_after_commit=send_after_commit
        )
        return True

    def _notify_by_email_split_group(
        self,
        recipients_group: dict,
        base_mail_values: dict,
        mail_body: Markup,
        batch_size: int,
    ) -> Iterator[tuple[dict, tuple]]:
        for recipient_ids_chunk in batched(
            recipients_group["recipients_ids"], batch_size, strict=False
        ):
            yield (
                self._notify_by_email_get_final_mail_values(
                    recipient_ids_chunk,
                    base_mail_values,
                    additional_values={"body_html": mail_body},
                ),
                ("res_partner_id", recipient_ids_chunk),
            )
        if recipients_emails := recipients_group["recipients_emails"]:
            mail_values = self._notify_by_email_get_final_mail_values(
                [], base_mail_values, additional_values={"body_html": mail_body}
            )
            mail_values["email_to"] = ",".join(recipients_emails)
            yield mail_values, ("mail_email_address", recipients_emails)

    def _notify_by_email_prepare(
        self,
        message: MailMessage,
        recipients_data: list[dict],
        *,
        msg_vals: dict | Literal[False] = False,
        mail_auto_delete: bool = True,
        model_description: str | Literal[False] = False,
        force_email_company: ResCompany | Literal[False] = False,
        force_email_lang: str | Literal[False] = False,
        force_record_name: str | Literal[False] = False,
        subtitles: list[str] | None = None,
        email_prefetch: dict | None = None,
        **kwargs,
    ) -> list[dict]:
        partners_data = [r for r in recipients_data if r["notif"] == "email"]
        if not partners_data:
            return []

        additional_values = {"auto_delete": mail_auto_delete}
        if kwargs.get("mail_headers"):
            additional_values["headers"] = kwargs["mail_headers"]
        email_prefetch = email_prefetch or {}
        base_mail_values = self._notify_by_email_get_base_mail_values(
            message,
            partners_data,
            additional_values=additional_values,
            ancestors=email_prefetch.get("ancestors"),
        )
        base_notification_values = self._notify_by_email_get_base_notification_values(
            message
        )

        gen_batch_size = (
            self.env["ir.config_parameter"]._get_int_param("mail.batch_size", 50) or 50
        )
        mail_values_list = []
        notif_targets = []
        groups = 0  # debuglog
        for (
            _lang,
            render_values,
            recipients_group,
        ) in self._notify_get_classified_recipients_iterator(
            message,
            partners_data,
            msg_vals=msg_vals,
            model_description=model_description,
            force_email_company=force_email_company,
            force_email_lang=force_email_lang,
            force_record_name=force_record_name,
            subtitles=subtitles,
            tracking_values=email_prefetch.get("tracking_values"),
        ):
            mail_body = self._notify_by_email_render_layout(
                message,
                recipients_group,
                msg_vals=msg_vals,
                render_values=render_values,
            )
            for mail_values, target in self._notify_by_email_split_group(
                recipients_group, base_mail_values, mail_body, gen_batch_size
            ):
                mail_values_list.append(mail_values)
                notif_targets.append(target)
            groups += 1  # debuglog

        _debug.pipeline(
            "email_prepared",
            model=self._name,
            message=message.id,
            recipients=len(partners_data),
            groups=groups,
            mails=len(mail_values_list),
            batch_size=gen_batch_size,
            prefetched=bool(email_prefetch),
        )
        return [
            {
                "mail_values": mail_values,
                "target_field": target_field,
                "targets": targets,
                "notification_values": base_notification_values,
            }
            for mail_values, (target_field, targets) in zip(
                mail_values_list, notif_targets, strict=True
            )
        ]

    def _notify_by_email_flush(
        self,
        prepared: list[dict],
        *,
        force_send: bool = True,
        send_after_commit: bool = True,
    ) -> MailMail:
        if not prepared:
            return self.env["mail.mail"]

        clean_env_context = clean_context(self.env.context)
        SafeMail = self.env["mail.mail"].sudo().with_context(clean_env_context)
        SafeNotification = (
            self.env["mail.notification"].sudo().with_context(clean_env_context)
        )

        with _debug.perf(
            "email_flush_create", cr=self.env.cr, model=self._name, mails=len(prepared)
        ) as span:
            emails = SafeMail.create([entry["mail_values"] for entry in prepared])
            notif_create_values = [
                {
                    "mail_mail_id": mail.id,
                    entry["target_field"]: target,
                    **entry["notification_values"],
                }
                for mail, entry in zip(emails, prepared, strict=True)
                for target in entry["targets"]
            ]
            if notif_create_values:
                SafeNotification.create(notif_create_values)
            span.set(notifications=len(notif_create_values))

        if force_send := self.env.context.get("mail_notify_force_send", force_send):
            force_send_limit = self.env["ir.config_parameter"]._get_int_param(
                "mail.mail.force.send.limit", 100
            )
            force_send = len(emails) < force_send_limit
        _debug.logic(
            "email_flush_send",
            model=self._name,
            mails=len(emails),
            force_send=bool(force_send),
            after_commit=send_after_commit,
        )
        if force_send:
            if send_after_commit:
                emails.send_after_commit()
            else:
                emails.send()
        return emails

    def _notify_get_classified_recipients_iterator(
        self,
        message: MailMessage,
        recipients_data: list[dict],
        msg_vals: dict | Literal[False] = False,
        model_description: str | Literal[False] = False,
        force_email_company: ResCompany | Literal[False] = False,
        force_email_lang: str | Literal[False] = False,
        force_record_name: str | Literal[False] = False,
        subtitles: list[str] | None = None,
        tracking_values: MailTrackingValue | None = None,
    ) -> Iterator[tuple]:
        lang_to_recipients = {}
        for data in recipients_data:
            if lang_code := data.get("lang"):
                lang_code = (
                    bool(self.env["res.lang"]._get_lang_cached(lang_code)) and lang_code
                )
            lang_to_recipients.setdefault(
                lang_code or force_email_lang or self.env.lang,
                [],
            ).append(data)
        _debug.logic(
            "recipients_by_lang",
            model=self._name,
            message=message.id,
            langs=sorted(lang or "" for lang in lang_to_recipients),
            recipients=len(recipients_data),
        )

        for lang, lang_recipients_data in lang_to_recipients.items():
            record_wlang = self.with_context(lang=lang)
            lang_model_description = model_description
            if not lang_model_description:
                lang_model_description = record_wlang._get_model_description(
                    (msg_vals and msg_vals.get("model")) or message.model
                )
            recipients_groups_list = record_wlang._notify_get_recipients_classify(
                message,
                lang_recipients_data,
                lang_model_description,
                msg_vals=msg_vals,
            )
            render_values = record_wlang._notify_by_email_prepare_rendering_context(
                message,
                msg_vals=msg_vals,
                model_description=lang_model_description,
                force_email_company=force_email_company,
                force_email_lang=lang,
                force_record_name=force_record_name,
                tracking_values=tracking_values,
            )
            if subtitles:
                render_values["subtitles"] = subtitles

            _debug.pipeline(
                "recipients_classified",
                model=self._name,
                message=message.id,
                lang=lang,
                recipients=len(lang_recipients_data),
                groups=len(recipients_groups_list),
            )
            for recipients_group in recipients_groups_list:
                group_render_values = render_values
                if not render_values["show_unfollow"] and any(
                    r["is_follower"]
                    for r in recipients_group["recipients_data"]
                    if r["id"] and r["uid"] and not r["ushare"]
                ):
                    group_render_values = {**render_values, "show_unfollow": True}
                yield (lang, group_render_values, recipients_group)

    def _notify_by_email_get_signature(
        self, message: MailMessage, msg_vals: dict
    ) -> tuple[ResUsers, str, bool]:
        author = (
            message.env["res.partner"].browse(msg_vals.get("author_id"))
            if "author_id" in msg_vals
            else message.author_id
        )
        author_user = author.main_user_id
        if not author_user:
            return author_user, "", False
        email_add_signature = msg_vals.get(
            "email_add_signature", message.email_add_signature
        )
        signature = (
            Markup("<div>-- <br/>%s</div>") % author_user.signature
            if email_add_signature
            else ""
        )
        return author_user, signature, email_add_signature

    def _notify_by_email_get_company(
        self,
        record_wlang: Self,
        force_email_company: ResCompany | Literal[False],
    ) -> tuple[ResCompany, str | Literal[False]]:
        if force_email_company:
            company = force_email_company
        else:
            company = (
                record_wlang.company_id.sudo()
                if (
                    record_wlang
                    and "company_id" in record_wlang
                    and record_wlang.company_id
                )
                else record_wlang.env.company
            )
        website_url = False
        if company.website:
            website_url = (
                company.website
                if company.website.lower().startswith(("http:", "https:"))
                else "http://%s" % company.website
            )
        return company, website_url

    def _notify_by_email_layout_flags(self) -> dict:
        context = self.env.context
        return {
            "email_notification_force_header": context.get(
                "email_notification_force_header", False
            ),
            "email_notification_force_footer": context.get(
                "email_notification_force_footer", False
            ),
            "email_notification_allow_header": context.get(
                "email_notification_allow_header", True
            ),
            "email_notification_allow_footer": context.get(
                "email_notification_allow_footer", False
            ),
        }

    def _notify_by_email_prepare_rendering_context(
        self,
        message: MailMessage,
        msg_vals: dict | Literal[False] = False,
        model_description: str | Literal[False] = False,
        force_email_company: ResCompany | Literal[False] = False,
        force_email_lang: str | Literal[False] = False,
        force_record_name: str | Literal[False] = False,
        tracking_values: MailTrackingValue | None = None,
    ) -> dict:
        msg_vals = msg_vals or {}

        lang = force_email_lang or self.env.lang
        record_wlang = self.with_context(lang=lang)

        author_user, signature, email_add_signature = (
            self._notify_by_email_get_signature(message, msg_vals)
        )
        company, website_url = self._notify_by_email_get_company(
            record_wlang, force_email_company
        )

        if not model_description:
            model_description = record_wlang._get_model_description(
                msg_vals.get("model", message.model)
            )
        record_name = force_record_name or message.with_context(lang=lang).record_name

        check_tracking = (
            msg_vals.get("tracking_value_ids", True) if msg_vals else bool(self)
        )
        tracking = []
        if check_tracking:
            if tracking_values is None:
                _debug.perf.count(
                    "tracking_values_searched", model=self._name, message=message.id
                )
                tracking_values = (
                    self.env["mail.tracking.value"]
                    .sudo()
                    .search([("mail_message_id", "in", message.ids)])
                )
            tracking_values = tracking_values._filtered_has_field_access(self.env)
            if tracking_values:
                tracking_values = record_wlang._track_filtered_for_display(
                    tracking_values
                )
            tracking = [
                (
                    fmt_vals["fieldInfo"]["changedField"],
                    fmt_vals["oldValue"],
                    fmt_vals["newValue"],
                )
                for fmt_vals in tracking_values._tracking_value_format()
            ]

        subtype_id = msg_vals.get("subtype_id", message.subtype_id.id)
        is_discussion = subtype_id == self.env["ir.model.data"]._xmlid_to_res_id(
            "mail.mt_comment"
        )

        return {
            "is_discussion": is_discussion,
            "message": message,
            "subtype": message.subtype_id,
            "tracking_values": tracking,
            "model_description": model_description,
            "record": record_wlang,
            "record_name": record_name,
            "subtitles": [record_name],
            "author_user": author_user,
            "company": company,
            "email_add_signature": email_add_signature,
            "lang": lang,
            "show_unfollow": self._partner_unfollow_enabled,
            "signature": signature,
            "website_url": website_url,
            "is_html_empty": is_html_empty,
            **self._notify_by_email_layout_flags(),
        }

    def _notify_by_email_render_layout(
        self,
        message: MailMessage,
        recipients_group: dict,
        msg_vals: dict | Literal[False] = False,
        render_values: dict | None = None,
    ) -> Markup:
        if render_values is None:
            render_values = {}
        msg_vals = msg_vals or {}

        email_layout_xmlid = msg_vals.get(
            "email_layout_xmlid", message.email_layout_xmlid
        )
        template_xmlid = email_layout_xmlid or "mail.mail_notification_layout"

        render_values = {**render_values, **recipients_group}
        with _debug.perf(
            "email_layout_rendered",
            cr=self.env.cr,
            model=self._name,
            message=message.id,
            layout=template_xmlid,
            lang=render_values.get("lang", self.env.lang),
        ):
            mail_body = self.env["ir.qweb"]._render(
                template_xmlid,
                render_values,
                minimal_qcontext=True,
                raise_if_not_found=False,
                lang=render_values.get("lang", self.env.lang),
            )
        if not mail_body:
            _debug.logic(
                "email_layout_missing", model=self._name, layout=template_xmlid
            )
            _logger.warning(
                "QWeb template %s not found or is empty when sending notification emails. Sending without layouting.",
                template_xmlid,
            )
            mail_body = message.body
        return mail_body

    _REFERENCES_ANCESTORS_LIMIT = 32

    def _notify_by_email_get_ancestors(
        self, messages: MailMessage
    ) -> dict[int, MailMessage]:
        by_model_res_id = defaultdict(list)
        for message in messages:
            by_model_res_id[message.model].append(message.res_id)
        ancestors_by_res_id = {}
        MailMessageSudo = self.env["mail.message"].sudo()
        ancestor_fields = _to_flush(
            MailMessageSudo, "model", "res_id", "subtype_id", "message_id"
        )
        for model, res_ids in by_model_res_id.items():
            if not model:
                continue
            rows = self.env.execute_query(
                SQL(
                    """
                    SELECT res_id, id
                      FROM (SELECT res_id,
                                   id,
                                   ROW_NUMBER() OVER (PARTITION BY res_id
                                                          ORDER BY id DESC) AS rank
                              FROM mail_message
                             WHERE model = %s
                               AND res_id = ANY(%s)
                               AND subtype_id IS NOT NULL
                               AND COALESCE(message_id, '') != ''
                           ) ranked
                     WHERE rank <= %s
                     ORDER BY res_id, id DESC
                    """,
                    model,
                    list(set(res_ids)),
                    self._REFERENCES_ANCESTORS_LIMIT + 1,
                    to_flush=ancestor_fields,
                )
            )
            for res_id, message_id in rows:
                ancestors_by_res_id.setdefault((model, res_id), []).append(message_id)

        MailMessageSudo.browse(
            {mid for ids in ancestors_by_res_id.values() for mid in ids}
        ).fetch(["message_id", "is_internal", "message_type", "subtype_id"])
        _debug.perf.count(
            "email_ancestors_loaded",
            model=self._name,
            messages=len(messages),
            models=len(by_model_res_id),
            threads=len(ancestors_by_res_id),
        )
        return {
            message.id: MailMessageSudo.browse(
                [
                    mid
                    for mid in ancestors_by_res_id.get(
                        (message.model, message.res_id), ()
                    )
                    if mid != message.id
                ][: self._REFERENCES_ANCESTORS_LIMIT]
            )
            for message in messages
        }

    _REFERENCES_OUTGOING_TYPES = (
        "comment",
        "auto_comment",
        "email",
        "email_outgoing",
    )

    def _notify_by_email_references(
        self, message_sudo: MailMessage, ancestors: MailMessage | None
    ) -> str:
        if ancestors is None:
            ancestors = self._notify_by_email_get_ancestors(message_sudo)[
                message_sudo.id
            ]
        preferred = ancestors.sorted(
            lambda m: (
                not m.is_internal and not m.subtype_id.internal,
                m.message_type in self._REFERENCES_OUTGOING_TYPES,
                m.message_type not in ("user_notification", "out_of_office"),
            ),
            reverse=True,
        )
        chosen = preferred[:3].sorted("id")
        return " ".join(m.message_id for m in (chosen + message_sudo))

    def _notify_by_email_get_base_mail_values(
        self,
        message: MailMessage,
        recipients_data: list[dict],
        additional_values: dict | None = None,
        ancestors: MailMessage | None = None,
    ) -> dict:
        mail_subject = message.subject
        if not mail_subject and self:
            mail_subject = self._message_compute_subject()
        if not mail_subject:
            mail_subject = message.record_name
        if mail_subject:
            mail_subject = " ".join(mail_subject.splitlines())

        message_sudo = message.sudo()
        references = self._notify_by_email_references(message_sudo, ancestors)
        base_mail_values = {
            "mail_message_id": message.id,
            "references": references,
        }
        if mail_subject != message.subject:
            base_mail_values["subject"] = mail_subject
        if additional_values:
            base_mail_values.update(additional_values)

        headers = dict(base_mail_values.get("headers") or {})
        external = [
            r
            for r in recipients_data
            if r["active"] and r["email_normalized"] and r["share"]
        ]
        external_emails = [
            formataddr((r["name"], r["email_normalized"])) for r in external
        ]
        external_emails_normalized = [r["email_normalized"] for r in external]
        external_emails += list(
            dict.fromkeys(
                email
                for email in email_split_and_format_normalize(
                    f"{message_sudo.incoming_email_to or ''},{message_sudo.incoming_email_cc or ''}"
                )
                if email_normalize(email) not in external_emails_normalized
            )
        )
        if external_emails:
            if len(external_emails) < self._CUSTOMER_HEADERS_LIMIT_COUNT:
                headers["X-Msg-To-Add"] = ",".join(external_emails)
            else:
                _logger.info(
                    "Message %s has %s external recipients, over the %s header "
                    "limit: sending without X-Msg-To-Add",
                    message.id,
                    len(external_emails),
                    self._CUSTOMER_HEADERS_LIMIT_COUNT,
                )
        if message_sudo.record_alias_domain_id.bounce_email:
            headers["Return-Path"] = message_sudo.record_alias_domain_id.bounce_email
        headers = self._notify_by_email_get_headers(headers=headers)
        if headers:
            base_mail_values["headers"] = headers
        return base_mail_values

    def _notify_by_email_get_final_mail_values(
        self,
        recipient_ids: Sequence[int],
        mail_values: dict,
        additional_values: dict | None = None,
    ) -> dict:
        final_mail_values = dict(mail_values)
        final_mail_values["recipient_ids"] = [(4, pid) for pid in recipient_ids]
        if additional_values:
            final_mail_values.update(additional_values)
        return final_mail_values

    def _notify_by_email_get_base_notification_values(
        self, message: MailMessage
    ) -> dict:
        return {
            "author_id": message.author_id.id,
            "is_read": True,
            "mail_message_id": message.id,
            "notification_status": "ready",
            "notification_type": "email",
        }

    def _notify_thread_by_web_push(
        self,
        message: MailMessage,
        recipients_data: list[dict],
        msg_vals: dict | Literal[False] = False,
        **kwargs,
    ) -> None:
        partner_ids = self._notify_get_recipients_for_extra_notifications(
            message, recipients_data, msg_vals=msg_vals
        )
        devices, private_key, public_key = self._web_push_get_partners_parameters(
            partner_ids
        )
        _debug.logic(
            "web_push_targets",
            model=self._name,
            message=message.id,
            partners=len(partner_ids),
            devices=len(devices),
            vapid=bool(private_key),
        )
        if not devices:
            return
        payload_by_lang = {}
        for render_lang in {
            lang or self.env.lang for lang in devices.partner_id.mapped("lang")
        }:
            if render_lang == self.env.lang:
                record_wlang, message_wlang = self, message
            else:
                record_wlang = self.with_context(lang=render_lang)
                message_wlang = message.with_context(lang=render_lang)
            payload_by_lang[render_lang] = record_wlang._web_push_truncate_payload(
                record_wlang._notify_by_web_push_prepare_payload(
                    message_wlang,
                    msg_vals=msg_vals,
                    force_record_name=kwargs.get("force_record_name"),
                )
            )
        self._web_push_send_notification(
            devices,
            private_key,
            public_key,
            payload_by_lang=payload_by_lang,
            payload=next(iter(payload_by_lang.values())),
        )

    def _web_push_get_partners_parameters(self, partner_ids: list[int]) -> tuple:
        devices_su = self.env["mail.push.device"].sudo()
        if not partner_ids:
            return devices_su, None, None
        vapid_private_key = self.env["credential.credential"]._get_system_secret(
            "mail.web_push_vapid_private_key"
        )
        vapid_public_key = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("mail.web_push_vapid_public_key")
        )
        if not vapid_private_key or not vapid_public_key:
            return devices_su, None, None
        return (
            devices_su.search([("partner_id", "in", partner_ids)]),
            vapid_private_key,
            vapid_public_key,
        )

    def _web_push_send_notification(
        self,
        devices: MailPushDevice,
        private_key: str | None,
        public_key: str | None,
        payload_by_lang: dict | None = None,
        payload: dict | None = None,
    ) -> None:
        if len(devices) < MAX_DIRECT_PUSH:
            session = get_push_session(self.env)
            devices_to_unlink = set()
            for device in devices:
                try:
                    push_to_end_point(
                        base_url=self.get_base_url(),
                        device={
                            "id": device.id,
                            "endpoint": device.endpoint,
                            "keys": device.keys,
                        },
                        payload=json.dumps(
                            (
                                payload_by_lang
                                and payload_by_lang.get(
                                    device.partner_id.lang or self.env.lang
                                )
                            )
                            or payload
                        ),
                        vapid_private_key=private_key,
                        vapid_public_key=public_key,
                        session=session,
                    )
                except DeviceUnreachableError:
                    devices_to_unlink.add(device.id)
                except PushEndpointUnresolvableError:
                    _logger.info(
                        "Push endpoint temporarily unresolvable, keeping device %s",
                        device.id,
                    )
                except Exception as e:  # pylint: disable=broad-except
                    _logger.error(
                        "An error occurred while contacting the endpoint: %s", e
                    )

            _debug.pipeline(
                "web_push_direct",
                model=self._name,
                devices=len(devices),
                unreachable=len(devices_to_unlink),
            )
            if devices_to_unlink:
                devices_list = list(devices_to_unlink)
                self.env["mail.push.device"].sudo().browse(devices_list).unlink()

        else:
            _debug.pipeline("web_push_queued", model=self._name, devices=len(devices))
            self.env["mail.push"].sudo().create(
                [
                    {
                        "mail_push_device_id": device.id,
                        "payload": json.dumps(
                            (
                                payload_by_lang
                                and payload_by_lang.get(
                                    device.partner_id.lang or self.env.lang
                                )
                            )
                            or payload
                        ),
                    }
                    for device in devices
                ]
            )
            self.env.ref("mail.ir_cron_web_push_notification")._trigger()

    def _notify_by_web_push_prepare_payload(
        self,
        message: MailMessage,
        msg_vals: dict | Literal[False] = False,
        force_record_name: str | Literal[False] = False,
    ) -> dict:
        msg_vals = msg_vals or {}
        author_id = msg_vals.get("author_id", message.author_id.id)
        model = msg_vals.get("model", message.model)
        title = force_record_name or message.record_name
        res_id = msg_vals.get("res_id", message.res_id)
        body = msg_vals.get("body", message.body)

        if author_id:
            author_name = self.env["res.partner"].browse(author_id).name
            title = "%s: %s" % (author_name, title)
            icon = "/web/image/res.partner/%d/avatar_128" % author_id
        else:
            icon = "/web/static/img/odoo-icon-192x192.png"

        if tools.is_html_empty(body) and message.attachment_ids:
            total_attachments = len(message.attachment_ids)
            attachments = message.attachment_ids.sudo()

            def get_attachment_label(attachment: IrAttachment) -> str:
                return (
                    self.env._("Voice Message")
                    if attachment.voice_ids
                    else attachment.name
                )

            if total_attachments == 1:
                body = get_attachment_label(attachments[0])
            elif total_attachments == 2:
                body = self.env._(
                    "%(file1)s and %(file2)s",
                    file1=get_attachment_label(attachments[0]),
                    file2=get_attachment_label(attachments[1]),
                )
            else:
                body = self.env._(
                    "%(file1)s and %(count)d other attachments",
                    file1=get_attachment_label(attachments[0]),
                    count=total_attachments - 1,
                )

        return {
            "title": title,
            "options": {
                "body": html2plaintext(body, include_references=False)
                + self._generate_tracking_message(message),
                "icon": icon,
                "data": {
                    "model": model or "",
                    "res_id": res_id or "",
                },
            },
        }

    def _notify_get_recipients(
        self, message: MailMessage, msg_vals: dict | Literal[False] = False, **kwargs
    ) -> list[dict]:
        msg_vals = msg_vals or {}
        msg_sudo = message.sudo()

        pids = msg_vals.get("partner_ids", msg_sudo.partner_ids.ids)
        message_type = msg_vals.get("message_type", msg_sudo.message_type)
        subtype_id = msg_vals.get("subtype_id", msg_sudo.subtype_id.id)

        recipients_data = []
        follower_data = kwargs.get("follower_data")
        if follower_data is None:
            follower_data = self.env["mail.followers"]._get_recipient_data(
                self,
                message_type,
                subtype_id,
                pids,
                include_followers=not kwargs.get("notify_skip_followers"),
            )
        res = follower_data[self.id if self else 0]
        outgoing_email_to_lst = email_split_and_normalize(
            msg_vals.get("outgoing_email_to", msg_sudo.outgoing_email_to)
        )
        if not res and not outgoing_email_to_lst:
            _debug.logic(
                "no_recipients", model=self._name, record=self.id, message=message.id
            )
            return recipients_data

        skip_author_id = self._notify_get_skip_author(message, msg_vals, pids, kwargs)

        emailed_normalized = set(
            email_normalize_all(
                f"{msg_vals.get('incoming_email_to', msg_sudo.incoming_email_to) or ''}, "
                f"{msg_vals.get('incoming_email_cc', msg_sudo.incoming_email_cc) or ''}"
            )
        )
        emailed_normalized_covered = set(emailed_normalized)

        for pid, pdata in res.items():
            if pid and pid == skip_author_id:
                continue
            if pdata["active"] is False:
                continue
            if (
                pdata["notif"] == "email"
                and pdata["email_normalized"] in emailed_normalized
            ):
                continue
            recipients_data.append(pdata)
            if pdata["notif"] == "email" and pdata["email_normalized"]:
                emailed_normalized_covered.add(pdata["email_normalized"])

        for name, email_address in outgoing_email_to_lst:
            if not email_address or email_address in emailed_normalized_covered:
                continue
            emailed_normalized_covered.add(email_address)
            recipients_data.append(
                prepare_recipient_data(
                    email_normalized=email_address,
                    name=name or email_address,
                )
            )

        if kwargs.get("skip_existing"):
            recipients_data = self._notify_get_recipients_not_yet_notified(
                message, recipients_data
            )
        _debug.logic(
            "recipients_computed",
            model=self._name,
            record=self.id,
            message=message.id,
            candidates=len(res),
            skip_author=skip_author_id or None,
            already_emailed=len(emailed_normalized),
            outgoing_to=len(outgoing_email_to_lst),
            recipients=len(recipients_data),
        )
        return recipients_data

    def _notify_get_skip_author(
        self,
        message: MailMessage,
        msg_vals: dict,
        pids: list[int],
        kwargs: dict,
    ) -> int | Literal[False]:
        if self._notify_get_flag(kwargs, "notify_author", "mail_notify_author"):
            return False
        author_id = msg_vals.get("author_id") or message.author_id.id
        skip_author_id = self._message_compute_real_author(author_id).id
        if (
            self._notify_get_flag(
                kwargs, "notify_author_mention", "mail_notify_author_mention"
            )
            and skip_author_id in pids
        ):
            return False
        return skip_author_id

    def _notify_get_recipients_not_yet_notified(
        self, message: MailMessage, recipients_data: list[dict]
    ) -> list[dict]:
        pids = [r["id"] for r in recipients_data if r["id"]]
        emails = [
            r["email_normalized"]
            for r in recipients_data
            if not r["id"] and r["email_normalized"]
        ]
        if not pids and not emails:
            return recipients_data
        existing = (
            self.env["mail.notification"]
            .sudo()
            .search(
                [
                    ("mail_message_id", "in", message.ids),
                    "|",
                    ("res_partner_id", "in", pids),
                    ("mail_email_address", "in", emails),
                ]
            )
        )
        existing_pids = set(existing.res_partner_id.ids)
        existing_emails = set(existing.mapped("mail_email_address"))
        _debug.logic(
            "recipients_already_notified",
            model=self._name,
            message=message.id,
            partners=len(existing_pids),
            emails=len(existing_emails),
        )
        return [
            r
            for r in recipients_data
            if (
                r["id"] not in existing_pids
                if r["id"]
                else r["email_normalized"] not in existing_emails
            )
        ]

    def _notify_get_recipients_groups(
        self,
        message: MailMessage,
        model_description: str,
        msg_vals: dict | Literal[False] = False,
    ) -> list:
        return [
            [
                "user",
                lambda pdata: pdata["type"] == "user",
                {
                    "active": True,
                    "has_button_access": self.env["mail.message"]._is_thread_message(
                        vals=msg_vals, thread=self
                    ),
                },
            ],
            [
                "portal",
                lambda pdata: pdata["type"] == "portal",
                {
                    "active": False,
                    "has_button_access": False,
                },
            ],
            [
                "follower",
                lambda pdata: pdata["is_follower"],
                {
                    "active": False,
                    "has_button_access": False,
                },
            ],
            [
                "customer",
                lambda pdata: True,
                {
                    "active": True,
                    "has_button_access": False,
                },
            ],
        ]

    def _notify_get_recipients_groups_fillup(
        self,
        groups: list,
        model_description: str,
        msg_vals: dict | Literal[False] = False,
    ) -> list:
        access_link = self._notify_get_action_link("view", **(msg_vals or {}))

        if model_description:
            view_title = _("View %s", model_description)
        else:
            view_title = _("View")

        is_thread_message = self.env["mail.message"]._is_thread_message(
            vals=msg_vals, thread=self
        )

        for group_name, _group_func, group_data in groups:
            group_data.setdefault("active", True)
            group_data.setdefault("has_button_access", is_thread_message)
            group_data.setdefault("notification_group_name", group_name)
            group_data.setdefault("recipients_data", [])
            group_data.setdefault("recipients_emails", [])
            group_data.setdefault("recipients_ids", [])
            group_button_access = group_data.setdefault("button_access", {})
            group_button_access.setdefault("url", access_link)
            group_button_access.setdefault("title", view_title)

        return groups

    def _notify_get_recipients_classify(
        self,
        message: MailMessage,
        recipients_data: list[dict],
        model_description: str,
        msg_vals: dict | Literal[False] = False,
    ) -> list:
        local_msg_vals = dict(msg_vals) if msg_vals else {}
        groups = self._notify_get_recipients_groups_fillup(
            self._notify_get_recipients_groups(
                message, model_description, msg_vals=local_msg_vals
            ),
            model_description,
            msg_vals=local_msg_vals,
        )
        for _group_name, _group_func, group_data in groups:
            if "actions" in group_data:
                _logger.warning("Invalid usage of actions in notification groups")

        for recipient_data in recipients_data:
            for _group_name, group_func, group_data in groups:
                if group_data["active"] and group_func(recipient_data):
                    group_data["recipients_data"].append(recipient_data)
                    if recipient_data["id"]:
                        group_data["recipients_ids"].append(recipient_data["id"])
                    elif recipient_data["email_normalized"]:
                        group_data["recipients_emails"].append(
                            recipient_data["email_normalized"]
                        )
                    break

        return [
            group_data
            for _group_name, _group_func, group_data in groups
            if group_data["recipients_data"]
        ]

    def _notify_get_recipients_for_extra_notifications(
        self,
        message: MailMessage,
        recipients_data: list[dict],
        msg_vals: dict | Literal[False] = False,
    ) -> set[int]:
        msg_vals = msg_vals or {}
        msg_sudo = message.sudo()
        emailed_normalized = set(
            email_normalize_all(
                f"{msg_vals.get('incoming_email_to', msg_sudo.incoming_email_to) or ''}, "
                f"{msg_vals.get('incoming_email_cc', msg_sudo.incoming_email_cc) or ''}"
            )
        )
        notif_pids = []
        notif_pids_notinbox = []
        for recipient in (r for r in recipients_data if r["active"] and r["id"]):
            if (
                emailed_normalized
                and recipient["email_normalized"] in emailed_normalized
            ):
                continue
            notif_pids.append(recipient["id"])
            if recipient["notif"] != "inbox":
                notif_pids_notinbox.append(recipient["id"])
        if not notif_pids:
            return set()

        msg_type = msg_vals.get("message_type") or msg_sudo.message_type
        _debug.logic(
            "extra_notification_recipients",
            model=self._name,
            message=message.id,
            message_type=msg_type,
            partners=len(notif_pids),
            not_inbox=len(notif_pids_notinbox),
        )
        if msg_type in self._web_push_all_recipients_message_types():
            return set(notif_pids)
        if msg_type in self._web_push_inbox_recipients_message_types():
            return set(notif_pids) - set(notif_pids_notinbox)
        return set()

    @api.model
    def _web_push_all_recipients_message_types(self) -> frozenset[str]:
        return frozenset({"comment"})

    @api.model
    def _web_push_inbox_recipients_message_types(self) -> frozenset[str]:
        return frozenset({"notification", "user_notification", "email"})

    def _notify_get_action_link(self, link_type: str, **kwargs) -> str:
        params = self._get_action_link_params(link_type, **kwargs)

        if link_type in ["view", "unfollow"]:
            base_link = "/mail/%s" % link_type
        elif link_type == "controller":
            controller = kwargs.get("controller")
            base_link = "%s" % controller
        else:
            raise NotImplementedError(f"Invalid notification link type {link_type}")

        if link_type != "view":
            token = self._encode_link(base_link, params)
            params["token"] = token

        link = "%s?%s" % (base_link, urlencode(sorted(params.items())))
        if self:
            link = self[0].get_base_url() + link

        return link

    def _notify_thread_with_out_of_office(
        self,
        message: MailMessage,
        recipients_data: list[dict],
        msg_vals: dict | Literal[False] = False,
        **kwargs,
    ) -> MailMessage:
        ooo_messages = self.env["mail.message"]
        if not self or self._transient:
            return ooo_messages
        if not self.env["res.users"]._has_out_of_office_configured():
            return ooo_messages
        msg_vals = msg_vals or {}
        if msg_vals.get("message_type", message.message_type) not in (
            "comment",
            "email",
        ):
            return ooo_messages

        trigger_is_internal = bool(msg_vals.get("is_internal", message.is_internal))
        recipient = self._message_compute_real_author(
            msg_vals.get("author_id") or message.author_id.id
        ).sudo()
        email_to = (
            (msg_vals.get("email_from") or message.email_from)
            if not recipient
            else False
        )
        if not recipient and not email_to:
            return ooo_messages

        ooo_users = self._notify_thread_with_out_of_office_get_users(
            message, recipients_data, recipient, msg_vals=msg_vals
        )
        if not ooo_users:
            return ooo_messages

        already_mailed = self._notify_thread_with_out_of_office_get_already_replied(
            ooo_users, recipient, email_to
        )
        _debug.logic(
            "out_of_office",
            model=self._name,
            record=self.id,
            message=message.id,
            users=len(ooo_users),
            already_replied=len(already_mailed),
            recipient=recipient.id or None,
        )
        original_subject = msg_vals.get("subject", message.subject)
        for user in ooo_users.filtered(lambda u: u.partner_id not in already_mailed):
            body = self.env["ir.qweb"]._render(
                "mail.message_notification_out_of_office",
                {
                    "out_of_office_message": user.out_of_office_message,
                    "replied_body": msg_vals.get("body", message.body),
                    "signature": user.signature,
                    "is_html_empty": is_html_empty,
                },
                minimal_qcontext=True,
                raise_if_not_found=False,
            )
            ooo_messages += self.sudo().message_post(
                author_id=user.partner_id.id,
                body=body,
                email_from=user.email_formatted,
                mail_headers={
                    "Auto-Submitted": "auto-replied",
                    "X-Auto-Response-Suppress": "All",
                },
                message_type="out_of_office",
                notify_author=True,
                notify_skip_followers=True,
                outgoing_email_to=email_to,
                partner_ids=recipient.ids,
                is_internal=trigger_is_internal,
                subject=_(
                    "Auto: %(subject)s", subject=(original_subject or self.display_name)
                ),
                subtype_id=self.env.ref(
                    "mail.mt_note" if trigger_is_internal else "mail.mt_comment"
                ).id,
            )
        return ooo_messages

    def _notify_thread_with_out_of_office_get_users(
        self,
        message: MailMessage,
        recipients_data: list[dict],
        recipient: ResPartner,
        msg_vals: dict | Literal[False] = False,
    ) -> ResUsers:
        msg_vals = msg_vals or {}
        pids = msg_vals.get("partner_ids", message.partner_ids.ids)
        internal_uids = [
            r["uid"]
            for r in recipients_data
            if (
                r["active"]
                and r["id"]
                and r["id"] in pids
                and r["id"] not in recipient.ids
                and r["uid"]
                and not r["share"]
            )
        ]
        users_to_check = self.env["res.users"].sudo().browse(
            internal_uids
        ) | self._notify_thread_with_out_of_office_get_additional_users(
            message, recipients_data, recipient, msg_vals=msg_vals
        )
        if not users_to_check:
            return self.env["res.users"].sudo()
        users_to_check.fetch(["is_out_of_office", "out_of_office_message"])
        return users_to_check.filtered(
            lambda u: u.is_out_of_office and not is_html_empty(u.out_of_office_message)
        )

    def _notify_thread_with_out_of_office_get_already_replied(
        self,
        ooo_users: ResUsers,
        recipient: ResPartner,
        email_to: str | Literal[False],
    ) -> ResPartner:
        exchange_domain = Domain.OR(
            ([Domain("partner_ids", "in", recipient.ids)] if recipient else [])
            + ([Domain("outgoing_email_to", "=", email_to)] if email_to else [])
        )
        sent_su = (
            self.env["mail.message"]
            .sudo()
            .search(
                Domain(
                    [
                        ("author_id", "in", ooo_users.partner_id.ids),
                        ("message_type", "=", "out_of_office"),
                        ("date", ">=", "-4d"),
                    ]
                )
                & exchange_domain
            )
        )
        return sent_su.author_id

    def _notify_thread_with_out_of_office_get_additional_users(
        self,
        message: MailMessage,
        recipients_data: list[dict],
        ooo_author: ResPartner,
        msg_vals: dict | Literal[False] = False,
    ) -> ResUsers:
        pids = [r["id"] for r in recipients_data if r["id"]]
        additional_users_su = self.env["res.users"].sudo()
        if self and "user_id" in self:
            additional_users_su += self.user_id.sudo().filtered(
                lambda u: u.partner_id != ooo_author
            )

        parent_msg = self.env["mail.message"].sudo()
        if (msg_vals or {}).get("parent_id"):
            parent_msg = self.env["mail.message"].sudo().browse(msg_vals["parent_id"])
        elif "parent_id" not in (msg_vals or {}):
            parent_msg = message.parent_id
        parent_author = (
            parent_msg.author_id
            if parent_msg.author_id.active
            else self.env["res.partner"]
        )
        if (
            parent_author
            and parent_author.id not in pids
            and parent_author != ooo_author
            and not parent_msg.author_id.partner_share
        ):
            additional_users_su |= parent_msg.author_id.main_user_id
        return additional_users_su

    @api.model
    def _encode_link(self, base_link: str, params: dict) -> str:
        return tools.hmac(
            self.env(su=True),
            self._ACTION_LINK_HMAC_SCOPE,
            (base_link, sorted((key, str(value)) for key, value in params.items())),
        )

    @api.model
    def _encode_link_legacy_sha1(self, base_link: str, params: dict) -> str:
        secret = self.env["ir.config_parameter"].sudo().get_param("database.secret")
        token = "%s?%s" % (
            base_link,
            " ".join("%s=%s" % (key, params[key]) for key in sorted(params)),
        )
        return hmac.new(
            secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha1
        ).hexdigest()

    def _get_action_link_params(self, link_type: str, **kwargs) -> dict:
        params = {
            "model": kwargs.get("model", self._name),
            "res_id": kwargs.get("res_id", self.ids[0] if self else False),
        }
        forwarded = (
            set(self._ACTION_LINK_SIGNED_PARAMS)
            - set(self._ACTION_LINK_IMPLICIT_PARAMS)
        ) | {"token"}
        params.update(
            {
                key: value
                for key, value in kwargs.items()
                if value is not None and key in forwarded
            }
        )
        if link_type == "controller":
            params.pop("model")
        return params

    @api.model
    def _generate_tracking_message(
        self, message: MailMessage, return_line: str = "\n"
    ) -> str:
        tracking_message = ""
        if message.subtype_id and message.subtype_id.description:
            tracking_message = (
                return_line + message.subtype_id.description + return_line
            )

        def _fmt(value: Any, is_bool: bool) -> str:
            if is_bool:
                return str(bool(value))
            return "" if value is None or value is False else str(value)

        trackings = message.sudo().tracking_value_ids._filtered_free_field_access()
        for formatted in trackings._tracking_value_format():
            is_bool = formatted["fieldInfo"]["fieldType"] == "boolean"
            old_value = _fmt(formatted["oldValue"], is_bool)
            new_value = _fmt(formatted["newValue"], is_bool)
            tracking_message += (
                formatted["fieldInfo"]["changedField"] + ": " + old_value
            )
            if old_value != new_value:
                tracking_message += " → " + new_value
            tracking_message += return_line

        return tracking_message

    @api.model
    def _get_model_description(self, model_name: str) -> str | Literal[False]:
        if not model_name:
            return False
        if "lang" not in self.env.context:
            raise ValueError("At this point lang should be correctly set")
        return self.env["ir.model"]._get(model_name).display_name

    @api.model
    def _web_push_truncate_json_string(self, value: str, max_chars: int) -> str:
        escaped = json.dumps(value)[1:-1]
        if len(escaped) <= max_chars:
            return value
        try:
            truncated = json.loads(f'"{escaped[:max_chars].rstrip(chr(92))}"')
        except json.decoder.JSONDecodeError as json_error:
            truncated = json.loads(f'"{escaped[: json_error.pos - 2]}"')
        while truncated and "\ud800" <= truncated[-1] <= "\udfff":
            truncated = truncated[:-1]
        return truncated

    @api.model
    def _web_push_truncate_payload(self, payload: dict) -> dict:
        max_length = self._truncate_payload_get_max_payload_length()
        overflow = len(json.dumps(payload).encode()) - max_length
        if overflow <= 0:
            return payload

        for key, holder in sorted(
            (("body", payload["options"]), ("title", payload)),
            key=lambda field: len(json.dumps(field[1][field[0]])),
            reverse=True,
        ):
            escaped_length = len(json.dumps(holder[key])[1:-1])
            holder[key] = self._web_push_truncate_json_string(
                holder[key], max(0, escaped_length - overflow)
            )
            overflow = len(json.dumps(payload).encode()) - max_length
            if overflow <= 0:
                return payload

        _logger.warning(
            "Web push payload is %s bytes over its %s budget with an empty "
            "title and body; sending it anyway.",
            overflow,
            max_length,
        )
        return payload

    @staticmethod
    def _truncate_payload_get_max_payload_length() -> int:
        return MAX_PAYLOAD_SIZE - ENCRYPTION_HEADER_SIZE - ENCRYPTION_BLOCK_OVERHEAD

    def message_subscribe(
        self, partner_ids: list[int] | None = None, subtype_ids: list[int] | None = None
    ) -> bool:
        if not self or not partner_ids:
            return True

        adding_current = set(partner_ids) == {self.env.user.partner_id.id}

        if adding_current:
            try:
                self.check_access("read")
            except exceptions.AccessError:
                _debug.logic(
                    "subscribe_refused",
                    model=self._name,
                    records=self.ids,
                    reason="no_read_access",
                )
                return False
            customer_ids = self.env.user.partner_id.ids if self.env.user.share else []
        else:
            self.check_access("write")
            partners = (
                self.env["res.partner"]
                .sudo()
                .search_fetch(
                    [("id", "in", partner_ids), ("active", "=", True)],
                    ["partner_share"],
                    order="id",
                )
            )
            partner_ids = partners.ids
            customer_ids = partners.filtered("partner_share").ids

        return self._message_subscribe(
            partner_ids, subtype_ids, customer_ids=customer_ids
        )

    def _message_subscribe(
        self,
        partner_ids: list[int] | None = None,
        subtype_ids: list[int] | None = None,
        customer_ids: list[int] | None = None,
    ) -> bool:
        if not self:
            return True

        _debug.lifecycle(
            "subscribe",
            model=self._name,
            count=len(self),
            partners=len(partner_ids or ()),
            subtypes=len(subtype_ids or ()),
            customers=len(customer_ids or ()),
        )
        if not subtype_ids:
            self.env["mail.followers"]._add_followers(
                self._name,
                self.ids,
                partner_ids,
                customer_ids=customer_ids,
                check_existing=True,
                existing_policy="skip",
            )
        else:
            self.env["mail.followers"]._add_followers_multi(
                self._name,
                dict.fromkeys(self.ids, dict.fromkeys(partner_ids, subtype_ids)),
                check_existing=True,
                existing_policy="replace",
            )

        return True

    def message_unsubscribe(self, partner_ids: list[int] | None = None) -> bool:
        if not partner_ids:
            return True
        if set(partner_ids) != {self.env.user.partner_id.id}:
            self.check_access("write")
        elif not self.env.user._is_internal():
            self.check_access("read")
        followers = (
            self.env["mail.followers"]
            .sudo()
            .search(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "in", self.ids),
                    ("partner_id", "in", partner_ids),
                ]
            )
        )
        _debug.lifecycle(
            "unsubscribe",
            model=self._name,
            count=len(self),
            partners=len(partner_ids),
            removed=len(followers),
        )
        followers.unlink()
        return True

    def _message_auto_subscribe_followers(
        self, updated_values: dict, default_subtype_ids: list[int]
    ) -> list:
        field = self._fields.get("user_id")
        user_id = updated_values.get("user_id")
        if (
            field
            and user_id
            and field.comodel_name == "res.users"
            and getattr(field, "tracking", False)
        ):
            user = self.env["res.users"].sudo().browse(user_id)
            try:
                if user.active:
                    return [
                        (
                            user.partner_id.id,
                            default_subtype_ids,
                            "mail.message_user_assigned"
                            if user != self.env.user
                            else False,
                        )
                    ]
            except MissingError, AccessError:
                pass
        return []

    def _message_auto_subscribe_notify(
        self,
        partner_ids: list[int],
        template: str,
        partner_ids_per_record: dict[int, list[int]] | None = None,
    ) -> None:
        if not self or self.env.context.get("mail_auto_subscribe_no_notify"):
            return
        if not self.env.registry.ready:
            return
        if self.env.context.get("install_demo"):
            return

        _debug.pipeline(
            "auto_subscribe_notify",
            model=self._name,
            count=len(self),
            template=template,
            partners=len(partner_ids),
            per_record=len(partner_ids_per_record or {}),
        )
        model_description = self.env["ir.model"]._get(self._name).display_name
        has_company = "company_id" in self
        IrQweb = self.env["ir.qweb"]
        RenderMixin = self.env["mixin.mail.render"]
        bodies, subjects = {}, {}
        for record in self:
            company = record.company_id.sudo() if has_company else self.env.company
            values = {
                "access_link": record._notify_get_action_link("view"),
                "company": company,
                "model_description": model_description,
                "object": record,
            }
            assignation_msg = IrQweb._render(template, values, minimal_qcontext=True)
            bodies[record.id] = RenderMixin._replace_local_links(assignation_msg)
            subjects[record.id] = _("You have been assigned to %s", record.display_name)
        self._message_notify_batch(
            bodies,
            subjects=subjects,
            partner_ids=partner_ids,
            partner_ids_per_record=partner_ids_per_record,
            email_layout_xmlid="mail.mail_notification_layout",
            model_description=model_description,
        )

    def _auto_subscribe_apply_parent_subtypes(
        self,
        subscriptions: list[tuple],
        subtype_maps: tuple,
        new_partner_subtypes: dict,
    ) -> None:
        child_ids, all_int_ids, parent = subtype_maps
        for partner_id, subtype_ids, pshare, active in subscriptions:
            if not (partner_id and active):
                continue
            sids = [parent[sid] for sid in subtype_ids if parent.get(sid)]
            sids += [
                sid for sid in subtype_ids if sid not in parent and sid in child_ids
            ]
            new_partner_subtypes[partner_id] = (
                set(sids) - set(all_int_ids) if pshare else set(sids)
            )

    def _auto_subscribe_apply_default_followers(
        self, updated_values: dict, def_ids: list[int], new_partner_subtypes: dict
    ) -> dict:
        notify_data = {}
        for partner_id, sids, template in self._message_auto_subscribe_followers(
            updated_values, def_ids
        ):
            new_partner_subtypes.setdefault(partner_id, sids)
            if template:
                lang = self.env["res.partner"].browse(partner_id).lang
                notify_data.setdefault((template, lang), []).append(partner_id)
        return notify_data

    def _mail_warm_auto_subscribe_users(self, vals_per_record: dict) -> None:
        field = self._fields.get("user_id")
        if not field or field.comodel_name != "res.users":
            return
        user_ids = {
            user_id
            for values in vals_per_record.values()
            if (user_id := values.get("user_id"))
        }
        if len(user_ids) > 1:
            users = self.env["res.users"].sudo().browse(user_ids).exists()
            users.fetch(["active", "partner_id"])
            users.partner_id.fetch(["lang"])

    def _message_auto_subscribe_parents(
        self, vals_per_record: dict, relation: dict
    ) -> tuple[dict, dict]:
        all_parent_ids_by_model = {}
        records_with_relations = {}
        for record_id, updated_values in vals_per_record.items():
            updated_relation = {}
            for res_model, fnames in relation.items():
                for fname in fnames:
                    if updated_values.get(fname):
                        updated_relation.setdefault(res_model, set()).add(fname)
                        all_parent_ids_by_model.setdefault(res_model, set()).add(
                            updated_values[fname]
                        )
            if updated_relation:
                records_with_relations[record_id] = (updated_values, updated_relation)

        parent_subscription_data = {}
        if all_parent_ids_by_model:
            for row in self.env["mail.followers"]._get_subscription_data(
                [
                    (model, list(pids))
                    for model, pids in all_parent_ids_by_model.items()
                ],
                None,
            ):
                parent_subscription_data.setdefault(
                    (row.res_model, row.res_id), []
                ).append(
                    (
                        row.partner_id,
                        row.subtype_ids,
                        row.partner_share,
                        row.partner_active,
                    )
                )
        return records_with_relations, parent_subscription_data

    def _message_auto_subscribe_batch(
        self, vals_per_record: dict, followers_existing_policy: ExistingPolicy = "skip"
    ) -> bool:
        if not self:
            return True

        child_ids, def_ids, all_int_ids, parent, relation = self.env[
            "mail.message.subtype"
        ]._get_auto_subscription_subtypes(self._name)
        subtype_maps = (child_ids, all_int_ids, parent)

        self._mail_warm_auto_subscribe_users(vals_per_record)
        records_with_relations, parent_subscription_data = (
            self._message_auto_subscribe_parents(vals_per_record, relation)
        )

        all_new_partner_subtypes = {}
        all_notify_data = {}

        for record in self:
            record_id = record.id
            updated_values = vals_per_record[record_id]
            new_partner_subtypes = {}

            if record_id in records_with_relations:
                _vals, rec_updated_relation = records_with_relations[record_id]
                for res_model, fnames in rec_updated_relation.items():
                    for fname in fnames:
                        parent_doc_id = updated_values[fname]
                        record._auto_subscribe_apply_parent_subtypes(
                            parent_subscription_data.get(
                                (res_model, parent_doc_id), []
                            ),
                            subtype_maps,
                            new_partner_subtypes,
                        )

            notify_data = record._auto_subscribe_apply_default_followers(
                updated_values, def_ids, new_partner_subtypes
            )

            if new_partner_subtypes:
                all_new_partner_subtypes[record_id] = new_partner_subtypes
            if notify_data:
                all_notify_data[record_id] = notify_data

        _debug.pipeline(
            "auto_subscribe_batch",
            model=self._name,
            count=len(self),
            with_relations=len(records_with_relations),
            parents=len(parent_subscription_data),
            subscribed=len(all_new_partner_subtypes),
            notified=len(all_notify_data),
            policy=followers_existing_policy,
        )
        if all_new_partner_subtypes:
            self.env["mail.followers"]._add_followers_multi(
                self._name,
                all_new_partner_subtypes,
                check_existing=True,
                existing_policy=followers_existing_policy,
            )

        self._message_auto_subscribe_notify_batch(all_notify_data)

        return True

    def _message_auto_subscribe_notify_batch(
        self, notify_data_per_record: dict
    ) -> None:
        notify_groups = defaultdict(dict)
        for record_id, notify_data in notify_data_per_record.items():
            for (template, lang), partner_ids in notify_data.items():
                notify_groups[(template, lang)][record_id] = list(partner_ids)
        for (template, lang), pids_per_record in notify_groups.items():
            self.browse(pids_per_record).with_context(
                lang=lang
            )._message_auto_subscribe_notify(
                [], template, partner_ids_per_record=pids_per_record
            )

    @api.readonly
    def message_get_followers(
        self,
        after: int | None = None,
        limit: int | None = None,
        filter_recipients: bool = False,
    ) -> dict:
        self.check_singleton()
        store = Store()
        self._message_followers_to_store(
            store, after, limit or self._FOLLOWER_PAGE_LIMIT, filter_recipients
        )
        return store.get_result()

    def _message_followers_domain(self, filter_recipients: bool = False) -> Domain:
        domain = Domain(
            [
                ("res_id", "in", self.ids),
                ("res_model", "=", self._name),
                ("partner_id", "!=", self.env.user.partner_id.id),
            ]
        )
        if filter_recipients:
            domain &= Domain(
                [
                    (
                        "subtype_ids",
                        "=",
                        self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_comment"),
                    ),
                    ("partner_id.active", "=", True),
                ]
            )
        return domain

    def _message_followers_to_store_batch(
        self,
        store: Store,
        after: int | None = None,
        limit: int | None = None,
        filter_recipients: bool = False,
    ) -> dict[int, MailFollowers]:
        self.check_access("read")
        limit = self._FOLLOWER_PAGE_LIMIT if limit is None else limit
        void = self.env["mail.followers"]
        if not self:
            return {}

        Followers = void.sudo()
        domain = self._message_followers_domain(filter_recipients)
        if after:
            domain &= Domain("id", ">", after)
        query = Followers._search(domain, order="id ASC")
        rows = self.env.execute_query(
            SQL(
                """
                SELECT id, res_id
                  FROM (SELECT id, res_id,
                               ROW_NUMBER() OVER (PARTITION BY res_id
                                                      ORDER BY id) AS rank
                          FROM (%s) matched
                       ) ranked
                 WHERE rank <= %s
                 ORDER BY res_id, id
                """,
                query.select(
                    SQL.identifier(query.table, "id"),
                    SQL.identifier(query.table, "res_id"),
                ),
                limit,
            )
        )
        ids_by_res_id = defaultdict(list)
        for follower_id, res_id in rows:
            ids_by_res_id[res_id].append(follower_id)

        all_ids = tuple(
            follower_id for ids in ids_by_res_id.values() for follower_id in ids
        )
        key = "recipients" if filter_recipients else "followers"
        mode = "ADD" if after else "REPLACE"
        res = {}
        for thread in self:
            followers = (
                Followers.browse(ids_by_res_id.get(thread.id, ()))
                .with_env(self.env)
                .with_prefetch(all_ids)
            )
            res[thread.id] = followers
            store.add(
                thread,
                {key: Store.Many(followers, mode=mode)},
                as_thread=True,
            )
        return res

    def _message_followers_count(
        self,
        page_by_res_id: dict[int, MailFollowers],
        limit: int | None = None,
        filter_recipients: bool = False,
    ) -> dict[int, int]:
        limit = self._FOLLOWER_PAGE_LIMIT if limit is None else limit
        full = self.browse(
            [res_id for res_id, page in page_by_res_id.items() if len(page) >= limit]
        )
        if not full:
            return {}
        return dict(
            self.env["mail.followers"]
            .sudo()
            ._read_group(
                full._message_followers_domain(filter_recipients),
                groupby=["res_id"],
                aggregates=["__count"],
            )
        )

    def _message_followers_to_store(
        self,
        store: Store,
        after: int | None = None,
        limit: int | None = None,
        filter_recipients: bool = False,
    ) -> MailFollowers:
        self.check_singleton()
        return self._message_followers_to_store_batch(
            store, after=after, limit=limit, filter_recipients=filter_recipients
        )[self.id]

    def message_change_thread(
        self,
        new_thread: models.BaseModel,
        new_parent_message: MailMessage | Literal[False] = False,
    ) -> bool:
        self.check_singleton()
        self.check_access("write")
        new_thread.check_access("read")
        MailMessage = self.env["mail.message"]
        messages = MailMessage.search(
            [
                ("model", "=", self._name),
                ("res_id", "=", self.id),
                ("message_type", "!=", "user_notification"),
            ]
        )
        non_generic_messages = messages.filtered(lambda m: m.subtype_id.res_model)
        generic_messages = messages - non_generic_messages

        msg_vals = {"res_id": new_thread.id, "model": new_thread._name}
        if new_parent_message:
            msg_vals["parent_id"] = new_parent_message.id
        generic_messages.sudo().write(msg_vals)

        messages_with_description = MailMessage

        if self._name != new_thread._name:
            msg_vals["subtype_id"] = None

            messages_with_description = non_generic_messages.filtered(
                lambda msg: msg.subtype_id.description
            )
            for message in messages_with_description:
                body = add_html_content(
                    message.subtype_id.description,
                    message.body,
                )
                message.sudo().write({**msg_vals, "body": body})

        (non_generic_messages - messages_with_description).sudo().write(msg_vals)
        _debug.lifecycle(
            "thread_changed",
            model=self._name,
            record=self.id,
            new_model=new_thread._name,
            new_record=new_thread.id,
            messages=len(messages),
            generic=len(generic_messages),
            described=len(messages_with_description),
        )
        return True

    def _message_update_body(self, message: MailMessage, body: str) -> str:
        if not body and message._filtered_empty():
            return ""
        tree = html.fragment_fromstring(_escape_body(body), create_parent="div")
        children = list(tree)
        if not children:
            return _escape_body(body) + Markup(
                f'<span class="{self._EDITED_MARKER_CLASS}"/>'
            )
        for marker in tree.find_class(self._EDITED_MARKER_CLASS):
            parent = marker.getparent()
            if marker.tail:
                previous = marker.getprevious()
                if previous is None:
                    parent.text = (parent.text or "") + marker.tail
                else:
                    previous.tail = (previous.tail or "") + marker.tail
            parent.remove(marker)
        children = list(tree)
        last_block = (
            children[-1] if children and children[-1].tag in ("div", "p") else tree
        )
        if last_block.text and not last_block.text[-1].isspace():
            last_block.text += " "
        etree.SubElement(
            last_block, "span", attrib={"class": self._EDITED_MARKER_CLASS}
        )
        return (tree.text or "") + Markup(
            "".join(etree.tostring(child, encoding="unicode") for child in tree)
        )

    def _message_update_content(
        self,
        message: MailMessage,
        /,
        *,
        body: str,
        attachment_ids: list[int] | None = None,
        partner_ids: list[int] | None = None,
        strict: bool = True,
        **kwargs,
    ) -> None:
        self.check_singleton()
        if strict:
            self._check_can_update_message_content(message.sudo())

        msg_values = {}
        if body is False:
            body = ""
        if body is not None:
            msg_values["body"] = self._message_update_body(message, body)
        if attachment_ids:
            msg_values.update(
                self._process_attachments_for_post(
                    [],
                    attachment_ids,
                    {
                        "body": body,
                        "model": self._name,
                        "res_id": self.id,
                    },
                )
            )
        elif attachment_ids is not None:
            message.attachment_ids._remove_and_notify()
        if partner_ids is not None:
            msg_values.update(
                {"partner_ids": [int(pid) for pid in partner_ids] or False}
            )
        if "subject" in kwargs:
            msg_values["subject"] = kwargs["subject"]
        _debug.lifecycle(
            "message_content_updated",
            model=self._name,
            record=self.id,
            message=message.id,
            fields=list(msg_values),
            attachments=len(attachment_ids or ()),
            strict=strict,
        )
        if msg_values:
            message.write(msg_values)
        if message._filtered_empty():
            self._clean_empty_message(message)

        if "scheduled_date" in kwargs:
            if kwargs["scheduled_date"]:
                self.env[
                    "mail.message.schedule"
                ].sudo()._update_message_scheduled_datetime(
                    message, kwargs["scheduled_date"]
                )
            else:
                self.env["mail.message.schedule"].sudo()._send_message_notifications(
                    message
                )

        res = [
            Store.Many("attachment_ids", sort="id"),
            "body",
            Store.Many("partner_ids", ["avatar_128", "name"]),
            "pinned_at",
            "write_date",
            *message._get_fields_store_linked_messages(),
            *self._get_fields_store_message_update_extra(),
        ]
        if "subject" in kwargs:
            res.append("subject")
        if body is not None:
            self.env["mail.message.translation"].sudo().search(
                [("message_id", "=", message.id)]
            ).unlink()
            res.append({"translationValue": False})
        Store(bus_channel=message._bus_channel()).add(message, res).bus_send()

    def _clean_empty_message(self, message: MailMessage) -> None:
        message.message_link_preview_ids._unlink_and_notify()

    def _get_fields_store_message_update_extra(self) -> list[StoreFieldSpec]:
        return []

    def _thread_to_store_batch_data(
        self, store: Store, request_list: list[str]
    ) -> dict:
        res = {
            "self_follower": {},
            "followers": {},
            "recipients": {},
            "followers_total": {},
            "recipients_total": {},
            "attachments": {},
            "scheduled": defaultdict(lambda: self.env["mail.scheduled.message"]),
            "suggested_recipients": {},
        }
        if "followers" in request_list:
            for follower in self.env["mail.followers"].search_fetch(
                [
                    ("res_id", "in", self.ids),
                    ("res_model", "=", self._name),
                    ("partner_id", "=", self.env.user.partner_id.id),
                ],
                ["res_id"],
            ):
                res["self_follower"][follower.res_id] = follower
            res["followers"] = self._message_followers_to_store_batch(store)
            res["recipients"] = self._message_followers_to_store_batch(
                store, filter_recipients=True
            )
            res["followers_total"] = self._message_followers_count(res["followers"])
            res["recipients_total"] = self._message_followers_count(
                res["recipients"], filter_recipients=True
            )
        if "attachments" in request_list:
            res["attachments"] = self._get_mail_thread_data_attachments()
        if "scheduledMessages" in request_list:
            for scheduled in self.env["mail.scheduled.message"].search_fetch(
                [("model", "=", self._name), ("res_id", "in", self.ids)], ["res_id"]
            ):
                res["scheduled"][scheduled.res_id] |= scheduled
        if "suggestedRecipients" in request_list:
            res["suggested_recipients"] = self._message_get_suggested_recipients_batch(
                reply_discussion=True, no_create=True
            )
        return res

    def _thread_to_store(
        self,
        store: Store,
        fields: StoreFieldsInput,
        *,
        request_list: list[str] | None = None,
    ) -> None:
        is_request = request_list is not None
        request_list = request_list or []
        store.add_records_fields(self, fields, as_thread=True)
        is_own_target = is_request and store.target.is_current_user(self.env)
        post_operations = (
            self._mail_get_operation_for_mail_message_operation("create")
            if is_own_target
            else {}
        )
        is_activity_mixin = isinstance(
            self.env[self._name], self.env.registry["mixin.mail.activity"]
        )
        readable_ids = writable_ids = frozenset()
        if is_own_target:
            readable_ids = frozenset(self.sudo(False)._filtered_access("read")._ids)
            writable_ids = frozenset(self.sudo(False)._filtered_access("write")._ids)
        with _debug.perf(
            "thread_to_store_batch_data",
            cr=self.env.cr,
            model=self._name,
            count=len(self),
            requests=request_list,
        ):
            batch = self._thread_to_store_batch_data(store, request_list)
        self_follower_by_res_id = batch["self_follower"]
        followers_by_res_id = batch["followers"]
        recipients_by_res_id = batch["recipients"]
        followers_total = batch["followers_total"]
        recipients_total = batch["recipients_total"]
        attachments_by_res_id = batch["attachments"]
        scheduled_by_res_id = batch["scheduled"]
        suggested_by_res_id = batch["suggested_recipients"]
        for thread in self:
            res = {}
            if is_own_target:
                res["hasReadAccess"] = thread.id in readable_ids
                res["hasWriteAccess"] = thread.id in writable_ids
                res["canPostOnReadonly"] = post_operations.get(thread) == "read"
            if "activities" in request_list and is_activity_mixin:
                res["activities"] = Store.Many(
                    thread.with_context(active_test=True).activity_ids
                )
            if "attachments" in request_list:
                res["attachments"] = Store.Many(
                    attachments_by_res_id.get(thread.id, self.env["ir.attachment"])
                )
                res["areAttachmentsLoaded"] = True
                res["isLoadingAttachments"] = False
            if "contact_fields" in request_list:
                res["primary_email_field"] = (
                    thread._mail_get_primary_email_field() or False
                )
                res["partner_fields"] = thread._mail_get_partner_fields()
            if "followers" in request_list:
                res.update(
                    thread._thread_to_store_followers(
                        self_follower_by_res_id.get(
                            thread.id, self.env["mail.followers"]
                        ),
                        followers_by_res_id,
                        recipients_by_res_id,
                        followers_total,
                        recipients_total,
                    )
                )
            if "display_name" in request_list:
                res["display_name"] = thread.display_name
            if "scheduledMessages" in request_list:
                res["scheduledMessages"] = Store.Many(scheduled_by_res_id[thread.id])
            if "suggestedRecipients" in request_list:
                res["suggestedRecipients"] = suggested_by_res_id.get(thread.id, [])
            if res:
                store.add(thread, res, as_thread=True)

    def _thread_to_store_followers(
        self,
        self_follower: MailFollowers,
        followers_by_res_id: dict,
        recipients_by_res_id: dict,
        followers_total: dict,
        recipients_total: dict,
    ) -> dict:
        self.check_singleton()
        void = self.env["mail.followers"]
        followers = followers_by_res_id.get(self.id, void)
        recipients = recipients_by_res_id.get(self.id, void)
        return {
            "selfFollower": Store.One(self_follower),
            "followersCount": followers_total.get(self.id, len(followers))
            + (1 if self_follower else 0),
            "recipientsCount": recipients_total.get(self.id, len(recipients)),
        }

    def _get_mail_thread_data_attachments(self) -> dict[int, IrAttachment]:
        Attachment = self.env["ir.attachment"]
        ids_by_res_id = defaultdict(list)
        for attachment in Attachment.search(
            [("res_id", "in", self.ids), ("res_model", "=", self._name)],
            order="id desc",
        ):
            ids_by_res_id[attachment.res_id].append(attachment.id)

        supersedes = "original_id" in Attachment._fields
        res = {}
        for record in self:
            attachments = Attachment.browse(ids_by_res_id.get(record.id, ()))
            res[record.id] = (
                self._filtered_unsuperseded_attachments(attachments)
                if supersedes
                else attachments
            )
        return res

    def _filtered_unsuperseded_attachments(
        self, attachments: IrAttachment
    ) -> IrAttachment:
        svg_ids = attachments.filtered(
            lambda attachment: attachment.mimetype == "image/svg+xml"
        )
        non_svg_id_set = set((attachments - svg_ids)._ids)
        svg_id_set = set(svg_ids._ids)
        original_id_set = set(attachments.mapped("original_id")._ids)
        return attachments.filtered(
            lambda attachment: (
                (attachment.id in svg_id_set and attachment.id not in original_id_set)
                or (
                    attachment.id in non_svg_id_set
                    and attachment.original_id.id not in non_svg_id_set
                )
            )
        )

    def _get_allowed_message_params(self) -> set:
        return {"email_add_signature", "message_type", "subject", "subtype_xmlid"}

    @api.model
    def _get_allowed_access_params(self) -> set:
        return set()

    @api.model
    def _get_thread_with_access(
        self, thread_id: int, *, mode: str = "read", **kwargs
    ) -> Self:
        allowed_params = self._get_allowed_access_params()
        if invalid := (set((kwargs or {}).keys()) - allowed_params):
            _logger.warning(
                "Invalid access parameters to _get_thread_with_access: %s", invalid
            )

        thread = self.browse(thread_id)
        if thread.exists() and thread.sudo(False).with_context(
            allowed_company_ids=[]
        ).has_access(mode):
            return thread
        _debug.logic(
            "thread_access_refused", model=self._name, record=thread_id, mode=mode
        )
        return self.browse()
