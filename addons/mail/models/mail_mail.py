import contextlib
import dataclasses
import datetime
import itertools
import json
import logging
import re
import smtplib
import typing
from collections import defaultdict
from collections.abc import Callable, Collection, Iterable, Iterator
from datetime import UTC, timedelta
from typing import Any, Literal, Self

import psycopg
from dateutil.parser import parse

from odoo import SUPERUSER_ID, _, api, fields, models, modules, tools
from odoo.api import ValuesType
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.modules.registry import Registry

from odoo.addons.mail.models.ir_mail_server import (
    MailDeliveryError,
    OutgoingEmailError,
)
from odoo.addons.mail.tools.failure_type import OUTGOING_FAILURE_TYPES

if typing.TYPE_CHECKING:
    from email.message import EmailMessage

    from .fetchmail import FetchmailServer
    from .ir_mail_server import IrMail_Server
    from .mail_alias_domain import MailAliasDomain
    from .mail_message import MailMessage
    from .mail_notification import MailNotification
    from .res_partner import ResPartner
    from odoo.addons.bus.models.ir_attachment import IrAttachment

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)
_PROGRESS_REPORT_EVERY = 50

_UNFOLLOW_LINK = "/mail/unfollow"
_UNFOLLOW_SPAN_ID = "mail_unfollow"
_UNFOLLOW_SPAN_OPEN_REGEX = re.compile(
    r'<span\b[^>]*\bid="mail_unfollow"[^>]*?(/?)>', re.IGNORECASE
)
_SPAN_TAG_REGEX = re.compile(r"<(/?)span\b[^>]*?(/?)>", re.IGNORECASE)
_UNFOLLOW_ANCHOR_REGEX = re.compile(
    r'<a\b[^>]*\bhref="[^"]*/mail/unfollow(?:[?#][^"]*)?"[^>]*>.*?</a>',
    re.DOTALL | re.IGNORECASE,
)


_ADDRESS_FAILURE_TYPES = frozenset({"mail_email_invalid", "mail_email_missing"})


@dataclasses.dataclass(slots=True)
class _DeliveryResult:
    msg: EmailMessage | None = None
    message_id: str | None = None
    failure_type: str | None = None
    failure_reason: str | None = None
    delivery_error: BaseException | None = None
    success_partner: ResPartner | None = None
    success_emails: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(slots=True)
class _SendOutcome:
    message_id: str | None = None
    failure_type: str | None = None
    failure_reason: str | None = None
    delivery_error: BaseException | None = None
    last_msg: EmailMessage | None = None
    success_partners: list[ResPartner] = dataclasses.field(default_factory=list)
    success_emails: list[str] = dataclasses.field(default_factory=list)

    def absorb(self, result: _DeliveryResult) -> None:
        self.last_msg = result.msg
        if result.message_id:
            self.message_id = result.message_id
        if result.failure_type and not (
            result.failure_type in _ADDRESS_FAILURE_TYPES
            and self.failure_type
            and self.failure_type not in _ADDRESS_FAILURE_TYPES
        ):
            self.failure_type = result.failure_type
            self.failure_reason = result.failure_reason
        if result.delivery_error is not None:
            self.delivery_error = result.delivery_error
        if result.success_partner:
            self.success_partners.append(result.success_partner)
        self.success_emails.extend(result.success_emails)


@dataclasses.dataclass(slots=True)
class _SendingMark:
    had_recipients: bool = False
    failure_type: str | None = None
    failure_reason: str | None = None
    previously_failing_ids: list[int] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(slots=True)
class _SendBatch:
    alias_domain: MailAliasDomain | None = None
    mail_server: IrMail_Server | Literal[False] = False
    smtp_session: smtplib.SMTP | None = None
    already_sent_pids: dict[int, set[int]] = dataclasses.field(default_factory=dict)
    doc_to_followers: dict[tuple[str, int], set[int]] = dataclasses.field(
        default_factory=dict
    )
    pending_notification_ids: dict[int, list[int]] = dataclasses.field(
        default_factory=dict
    )
    deferred_auto_delete: set[int] | None = None
    recipient_bearing_ids: frozenset[int] | None = None
    commits_per_mail: bool = False


class MailMail(models.Model):
    _name = "mail.mail"
    _description = "Outgoing Mails"
    _inherits = {"mail.message": "mail_message_id"}
    _order = "id desc"
    _rec_name = "subject"

    _mail_partner_fields = ()

    _FATAL_MEMORY_ERRORS = (MemoryError,)
    _FATAL_SESSION_ERRORS = (psycopg.Error, smtplib.SMTPServerDisconnected)
    _FATAL_SEND_ERRORS = _FATAL_MEMORY_ERRORS + _FATAL_SESSION_ERRORS

    _FAILING_NOTIFICATION_STATUS = ("bounce", "exception")

    _AUTO_DELETE_FAILURE_TYPES = _ADDRESS_FAILURE_TYPES

    _NOTIFICATION_STATUS_PER_STATE = {
        "outgoing": "ready",
        "sent": "sent",
        "exception": "exception",
        "cancel": "canceled",
    }

    _state_outgoing_id_idx = models.Index("(id) WHERE state = 'outgoing'")

    @api.model
    def default_get(self, fields: list[str]) -> ValuesType:
        return super(
            MailMail, self.with_context(default_message_type="email_outgoing")
        ).default_get(fields)

    mail_message_id: MailMessage = fields.Many2one(
        comodel_name="mail.message",
        string="Message",
        index=True,
        required=True,
        ondelete="cascade",
        bypass_search_access=True,
    )
    mail_message_id_int = fields.Integer(
        compute="_compute_mail_message_id_int",
        compute_sudo=True,
    )
    message_type = fields.Selection(
        related="mail_message_id.message_type",
        inherited=True,
        default="email_outgoing",
    )
    body_html = fields.Text(
        string="Text Contents",
        help="Rich-text/HTML message",
    )
    body_content = fields.Html(
        string="Rich-text Contents",
        sanitize=True,
        compute="_compute_body_content",
        search="_search_body_content",
    )
    references = fields.Text(
        readonly=True,
        help="Message references, such as identifiers of previous messages",
    )
    headers = fields.Json(
        copy=False,
        help="Extra SMTP headers to stamp on the outgoing message, as a mapping "
        "of header name to value.",
    )
    restricted_attachment_count = fields.Integer(
        string="Restricted attachments",
        compute="_compute_restricted_attachments",
    )
    unrestricted_attachment_ids: IrAttachment = fields.Many2many(
        comodel_name="ir.attachment",
        string="Unrestricted Attachments",
        compute="_compute_restricted_attachments",
        inverse="_inverse_unrestricted_attachment_ids",
    )
    is_notification = fields.Boolean(
        string="Notification Email",
        help="Mail has been created to notify people of an existing mail.message",
    )
    email_to = fields.Text(
        string="To",
        help="Message recipients (emails)",
    )
    email_cc = fields.Char(
        string="Cc",
        help="Carbon copy message recipients",
    )
    recipient_ids: ResPartner = fields.Many2many(
        comodel_name="res.partner",
        string="To (Partners)",
        context={"active_test": False},
    )
    state = fields.Selection(
        selection=[
            ("outgoing", "Outgoing"),
            ("sent", "Sent"),
            ("exception", "Delivery Failed"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="outgoing",
        copy=False,
        readonly=True,
    )
    failure_type = fields.Selection(
        selection=OUTGOING_FAILURE_TYPES,
        string="Failure type",
    )
    failure_reason = fields.Text(
        copy=False,
        readonly=True,
        help="Failure reason. This is usually the exception thrown by the email server, stored to ease the debugging of mailing issues.",
    )
    auto_delete = fields.Boolean(
        help="This option permanently removes any track of email after it's been sent, including from the Technical menu in the Settings, in order to preserve storage space of your Odoo database."
    )
    scheduled_date = fields.Datetime(
        string="Scheduled Send Date",
        help="If set, the queue manager will send the email after the date. If not set, the email will be send as soon as possible. Unless a timezone is specified, it is considered as being in UTC timezone.",
    )
    fetchmail_server_id: FetchmailServer = fields.Many2one(
        comodel_name="fetchmail.server",
        string="Inbound Mail Server",
        index="btree_not_null",
        readonly=True,
    )

    @api.constrains("mail_message_id", "mail_server_id")
    def _check_mail_server_id(self) -> None:
        for mail in self:
            if mail.mail_server_id and not mail._filtered_mail_mail_servers(
                mail.mail_server_id
            ):
                _debug.logic(
                    "mail_server_refused", mail=mail.id, server=mail.mail_server_id.id
                )
                raise ValidationError(
                    _("You may not create a message using another user's mail server.")
                )

    @api.depends("body_html")
    def _compute_body_content(self) -> None:
        for mail in self:
            mail.body_content = mail.body_html

    @api.depends("mail_message_id")
    def _compute_mail_message_id_int(self) -> None:
        for mail in self:
            mail.mail_message_id_int = mail.mail_message_id.id

    @api.depends("attachment_ids")
    def _compute_restricted_attachments(self) -> None:
        for mail_sudo, mail in zip(self.sudo(), self, strict=True):
            mail.unrestricted_attachment_ids = mail_sudo.attachment_ids.sudo(
                False
            )._filtered_access("read")
            mail.restricted_attachment_count = len(mail_sudo.attachment_ids) - len(
                mail.unrestricted_attachment_ids
            )

    def _inverse_unrestricted_attachment_ids(self) -> None:
        for mail_sudo, mail in zip(self.sudo(), self, strict=True):
            restricted_attachments = (
                mail_sudo.attachment_ids
                - mail_sudo.attachment_ids.sudo(False)._filtered_access("read")
            )
            mail_sudo.attachment_ids = (
                restricted_attachments | mail.unrestricted_attachment_ids
            )

    def _search_body_content(self, operator: str, value: Any) -> list:
        return [("body_html", operator, value)]

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        for values in vals_list:
            if "is_notification" not in values and values.get("mail_message_id"):
                values["is_notification"] = True
            if "scheduled_date" in values:
                values["scheduled_date"] = self._normalize_scheduled_date(
                    values["scheduled_date"]
                )
        new_mails = super().create(vals_list)

        ids_w_attach = [
            mail.id
            for mail, values in zip(new_mails, vals_list, strict=True)
            if values.get("attachment_ids")
        ]
        if ids_w_attach:
            self.browse(ids_w_attach).attachment_ids.check_access("read")

        _debug.lifecycle(
            "create",
            count=len(new_mails),
            notifications=sum(1 for v in vals_list if v.get("is_notification")),
            scheduled=sum(1 for v in vals_list if v.get("scheduled_date")),
            with_attachments=len(ids_w_attach),
        )
        return new_mails

    def write(self, vals: ValuesType) -> Literal[True]:
        if "scheduled_date" in vals:
            vals["scheduled_date"] = self._normalize_scheduled_date(
                vals["scheduled_date"]
            )
        res = super().write(vals)
        if vals.get("attachment_ids"):
            self.attachment_ids.check_access("read")
        if _debug.lifecycle.enabled and "state" in vals:
            _debug.lifecycle(
                "state", mails=self.ids, state=vals["state"], fields=list(vals)
            )
        return res

    def unlink(self) -> Literal[True]:
        mail_msg_cascade_ids = {
            mail.mail_message_id.id for mail in self if not mail.is_notification
        }
        res = super().unlink()
        if mail_msg_cascade_ids:
            still_referenced = set(
                self.sudo()
                .search([("mail_message_id", "in", list(mail_msg_cascade_ids))])
                .mapped("mail_message_id.id")
            )
            orphan_ids = mail_msg_cascade_ids - still_referenced
            _debug.lifecycle(
                "unlink",
                count=len(mail_msg_cascade_ids),
                orphan_messages=len(orphan_ids),
            )
            if orphan_ids:
                self.env["mail.message"].browse(orphan_ids).unlink()
        return res

    def action_retry(self) -> None:
        self.filtered(lambda mail: mail.state == "exception").mark_outgoing()

    def action_view_document(self) -> dict:
        self.check_singleton()
        return {
            "res_id": self.res_id,
            "res_model": self.model,
            "target": "current",
            "type": "ir.actions.act_window",
            "view_mode": "form",
        }

    def mark_outgoing(self) -> Literal[True]:
        _debug.lifecycle("mark_outgoing", mails=self.ids)
        res = self.write(
            {"failure_reason": False, "failure_type": False, "state": "outgoing"}
        )
        self._sync_email_notification_status()
        return res

    def cancel(self) -> Literal[True]:
        _debug.lifecycle("cancel", mails=self.ids)
        res = self.write({"state": "cancel"})
        self._sync_email_notification_status()
        return res

    def _sync_email_notification_status(self) -> None:
        notifications = (
            self.env["mail.notification"]
            .sudo()
            .search(
                [
                    ("notification_type", "=", "email"),
                    ("mail_mail_id", "in", self.ids),
                    ("notification_status", "!=", "sent"),
                ]
            )
        )
        if not notifications:
            return
        was_failing = notifications.filtered(
            lambda notif: notif.notification_status in self._FAILING_NOTIFICATION_STATUS
        )
        status_per_mail = {mail.id: mail._get_notification_status() for mail in self}
        _debug.pipeline(
            "notification_status_synced",
            mails=len(self),
            notifications=len(notifications),
            was_failing=len(was_failing),
        )
        per_status = defaultdict(list)
        for notification in notifications:
            per_status[status_per_mail[notification.mail_mail_id.id]].append(
                notification.id
            )
        for status, notification_ids in per_status.items():
            values = {"notification_status": status}
            if status == "ready":
                values |= {"failure_reason": False, "failure_type": False}
            notifications.browse(notification_ids).write(values)
        self._notify_notification_status_change(was_failing)

    def _notify_notification_status_change(
        self, notifications: MailNotification
    ) -> None:
        messages = notifications.mail_message_id.filtered(
            lambda message: message._is_thread_message()
        )
        if messages:
            messages._notify_message_notification_update()

    @api.model
    def process_email_queue(
        self, email_ids: Collection[int] = (), batch_size: int = 1000
    ) -> None:
        domain = [
            "&",
            ("state", "=", "outgoing"),
            "|",
            ("scheduled_date", "=", False),
            ("scheduled_date", "<=", fields.Datetime.now()),
        ]
        if email_ids:
            domain = [("id", "in", list(email_ids)), *domain]
        batch_size = self.env["ir.config_parameter"]._get_positive_int_param(
            "mail.mail.queue.batch.size", batch_size
        )
        send_limit = None if email_ids else batch_size
        send_ids = self.search(domain, limit=send_limit, order="id").ids
        _debug.pipeline(
            "queue_pass",
            forced=len(email_ids),
            batch_size=batch_size,
            selected=len(send_ids),
        )
        _logger.info(
            "Processing email queue with send limit of '%s'%s",
            send_limit,
            " (with forced 'email_ids')" if email_ids else "",
        )
        if not email_ids:
            ids_done = set()
            total = (
                len(send_ids)
                if len(send_ids) < batch_size
                else self.search_count(domain)
            )

            unreported = [0]

            def post_send_callback(ids: list[int], final: bool = False) -> bool:
                processed = set(ids) - ids_done
                ids_done.update(processed)
                unreported[0] += len(processed)
                if not self.env.context.get("ir_cron_progress_id"):
                    return False
                if not final and unreported[0] < _PROGRESS_REPORT_EVERY:
                    return False
                self.env["ir.cron"]._commit_progress(
                    unreported[0], remaining=total - len(ids_done)
                )
                unreported[0] = 0
                return True
        else:
            post_send_callback = None

        try:
            auto_commit = not modules.module.current_test
            with _debug.perf(
                "queue_send",
                cr=self.env.cr,
                mails=len(send_ids),
                auto_commit=auto_commit,
            ):
                self.browse(send_ids).send(
                    auto_commit=auto_commit, post_send_callback=post_send_callback
                )
        except self._FATAL_SEND_ERRORS:
            raise
        except Exception:
            _logger.exception("Failed processing mail queue")

    @api.model
    def _get_domain_pending_email_notifications(
        self, mail_ids: list[int]
    ) -> list[tuple]:
        return [
            ("notification_type", "=", "email"),
            ("mail_mail_id", "in", mail_ids),
            ("notification_status", "not in", ("sent", "canceled")),
        ]

    def _postprocess_sent_message(
        self,
        success_partners: list[ResPartner],
        success_emails: list[str],
        failure_reason: str | Literal[False] | None = False,
        failure_type: str | None = None,
        pending_notification_ids: list[int] | None = None,
        defer_auto_delete: set[int] | None = None,
        previously_failing_ids: Collection[int] | None = None,
    ) -> None:
        notif_mails_ids = self.ids
        if notif_mails_ids:
            notifications = (
                self.env["mail.notification"].browse(pending_notification_ids)
                if pending_notification_ids is not None
                else self.env["mail.notification"].search(
                    self._get_domain_pending_email_notifications(notif_mails_ids)
                )
            )
            if notifications:
                self._settle_notifications(
                    notifications,
                    success_partners,
                    success_emails,
                    failure_reason=failure_reason,
                    failure_type=failure_type,
                    previously_failing_ids=previously_failing_ids,
                )
        if not failure_type or failure_type in self._AUTO_DELETE_FAILURE_TYPES:
            to_delete = self.sudo().filtered(lambda mail: mail.auto_delete)
            _debug.lifecycle(
                "auto_delete",
                mails=self.ids,
                deleted=len(to_delete),
                deferred=defer_auto_delete is not None,
                failure_type=failure_type,
            )
            if defer_auto_delete is None:
                to_delete.unlink()
            else:
                defer_auto_delete.update(to_delete.ids)

    def _settle_notifications(
        self,
        notifications: MailNotification,
        success_partners: list[ResPartner],
        success_emails: list[str],
        failure_reason: str | Literal[False] | None = False,
        failure_type: str | None = None,
        previously_failing_ids: Collection[int] | None = None,
    ) -> None:
        was_failing = (
            notifications.browse(set(previously_failing_ids) & set(notifications.ids))
            if previously_failing_ids is not None
            else notifications.filtered(
                lambda notif: (
                    notif.notification_status in self._FAILING_NOTIFICATION_STATUS
                )
            )
        )
        reached_pids = {partner.id for partner in success_partners}
        reached_emails = set(success_emails)
        unreached = notifications.filtered(
            lambda notif: (
                notif.res_partner_id.id not in reached_pids
                and tools.mail.email_normalize(
                    notif.mail_email_address or "", strict=False
                )
                not in reached_emails
            )
        )
        failed = unreached if failure_type else self.env["mail.notification"]
        _debug.pipeline(
            "notifications_settled",
            mails=self.ids,
            notifications=len(notifications),
            sent=len(notifications) - len(unreached),
            failed=len(failed),
            unreached=len(unreached) - len(failed),
            was_failing=len(was_failing),
            failure_type=failure_type,
        )
        (notifications - unreached).sudo().write(
            {"notification_status": "sent", "failure_type": "", "failure_reason": ""}
        )
        if failed:
            failed.sudo().write(
                {
                    "notification_status": "exception",
                    "failure_type": failure_type,
                    "failure_reason": failure_reason,
                }
            )
        elif unreached:
            self._record_unreached_notifications(unreached)
        self._notify_notification_status_change(failed | was_failing)

    def _record_unreached_notifications(self, unreached: MailNotification) -> None:
        by_address = unreached.filtered(lambda notif: not notif.res_partner_id)
        _debug.logic(
            "unreached_notifications",
            mails=self.ids,
            by_address=len(by_address),
            orphaned=len(unreached) - len(by_address),
        )
        if by_address:
            by_address.sudo().write(
                {
                    "notification_status": "exception",
                    "failure_type": "mail_email_invalid",
                    "failure_reason": _(
                        "This address could not be used as a recipient and was "
                        "left out of the message that was sent."
                    ),
                }
            )
        if orphaned := unreached - by_address:
            _logger.warning(
                "Mail (mail.mail) %s was delivered without carrying %s of its "
                "notifications: partners %s are not among its recipients",
                self.ids,
                len(orphaned),
                orphaned.res_partner_id.ids,
            )
            orphaned.sudo().write(
                {
                    "notification_status": "exception",
                    "failure_type": "unknown",
                    "failure_reason": _(
                        "This recipient is not listed on the message that was "
                        "sent, so nothing was delivered to them."
                    ),
                }
            )

    @api.model
    def _get_send_batch_size(self, default: int = 50) -> int:
        return self.env["ir.config_parameter"]._get_positive_int_param(
            "mail.batch_size", default
        )

    @api.model
    def _normalize_scheduled_date(
        self, scheduled_date: datetime.datetime | datetime.date | str | None
    ) -> datetime.datetime | Literal[False]:
        if not scheduled_date:
            return False
        parsed_datetime = self._parse_scheduled_datetime(scheduled_date)
        return parsed_datetime.replace(tzinfo=None) if parsed_datetime else False

    def _parse_scheduled_datetime(
        self, scheduled_datetime: datetime.datetime | datetime.date | str
    ) -> datetime.datetime | Literal[False]:
        if isinstance(scheduled_datetime, datetime.datetime):
            parsed_datetime = scheduled_datetime
        elif isinstance(scheduled_datetime, datetime.date):
            parsed_datetime = datetime.datetime.combine(
                scheduled_datetime, datetime.time.min
            )
        else:
            try:
                parsed_datetime = parse(scheduled_datetime, yearfirst=True)
            except ValueError, TypeError:
                parsed_datetime = False
        if parsed_datetime:
            parsed_datetime = parsed_datetime.replace(microsecond=0)
            if not parsed_datetime.tzinfo:
                parsed_datetime = parsed_datetime.replace(tzinfo=UTC)
            else:
                try:
                    parsed_datetime = parsed_datetime.astimezone(UTC)
                except ValueError, OverflowError, OSError:
                    _debug.logic("scheduled_date_rejected", reason="utc_conversion")
                    _logger.warning(
                        "Could not convert scheduled date %r to UTC; ignoring it.",
                        scheduled_datetime,
                    )
                    parsed_datetime = False
        return parsed_datetime

    @api.model
    def _estimate_email_size(
        self, headers: dict | None, body: str, attachments_size: Iterable[int]
    ) -> int:
        return int(
            len(json.dumps(headers or {}, ensure_ascii=False).encode(errors="ignore"))
            + len((body or "").encode(errors="ignore"))
            + sum(attachments_size) * 4 / 3
            + 10 * 1024
        )

    def _filtered_mail_mail_servers(self, mail_servers: IrMail_Server) -> IrMail_Server:
        if self.env["ir.config_parameter"]._get_bool_param(
            "mail.disable_personal_mail_servers"
        ):
            _debug.logic("personal_servers_disabled", mails=self.ids)
            return mail_servers.filtered(lambda server: not server.owner_user_id)
        authors = self.mail_message_id.create_uid
        return mail_servers.filtered(
            lambda server: server.owner_user_id in [self.env["res.users"], authors]
        )

    def _get_envelope_email_from(self) -> str:
        self.check_singleton()
        emails_from = tools.mail.email_split_and_format_normalize(self.email_from)
        return emails_from[0] if emails_from else self.email_from

    def _prepare_outgoing_body(self) -> str:
        self.check_singleton()
        if tools.is_html_empty(self.body_html):
            return ""
        return self.env["mixin.mail.render"]._replace_local_links(self.body_html)

    @api.model
    def _has_unfollow_block(self, body: str | Literal[False]) -> bool:
        return bool(body) and _UNFOLLOW_LINK in body and _UNFOLLOW_SPAN_ID in body

    @api.model
    def _resolve_unfollow_span(self, body: str) -> tuple[int, int] | None:
        opening = _UNFOLLOW_SPAN_OPEN_REGEX.search(body)
        if not opening:
            return None
        if opening.group(1):
            return opening.start(), opening.end()
        depth = 1
        for tag in _SPAN_TAG_REGEX.finditer(body, opening.end()):
            if tag.group(2):
                continue
            depth += -1 if tag.group(1) else 1
            if depth == 0:
                return opening.start(), tag.end()
        return opening.start(), len(body)

    @api.model
    def _resolve_unfollow_block(self, body: str) -> tuple[int, int] | None:
        if not self._has_unfollow_block(body):
            return None
        return self._resolve_unfollow_span(body)

    def _is_unfollow_link_required(
        self,
        partner: ResPartner | Literal[False],
        doc_to_followers: dict | None = None,
    ) -> bool:
        self.check_singleton()
        return bool(
            partner
            and self.model
            and self.id
            and (
                getattr(self.env.get(self.model), "_partner_unfollow_enabled", False)
                or not partner.partner_share
            )
            and partner.id
            in (doc_to_followers or {}).get((self.model, self.res_id), ())
        )

    def _apply_unfollow_block(
        self,
        body: str,
        block: tuple[int, int] | None,
        partner: ResPartner | Literal[False] = False,
        doc_to_followers: dict | None = None,
    ) -> str:
        self.check_singleton()
        if block is None:
            return self._strip_unfollow_block(body)
        start, end = block
        if self._is_unfollow_link_required(partner, doc_to_followers):
            unfollow_url = self.env["mixin.mail.thread"]._notify_get_action_link(
                "unfollow", model=self.model, res_id=self.res_id, pid=partner.id
            )
            return (
                body[:start]
                + body[start:end].replace(_UNFOLLOW_LINK, unfollow_url)
                + body[end:]
            )
        return body[:start] + self._strip_unfollow_block(body[start:end]) + body[end:]

    @api.model
    def _strip_unfollow_block(self, body: str | Literal[False]) -> str | Literal[False]:
        if not body:
            return body
        if block := self._resolve_unfollow_span(body):
            start, end = block
            body = body[:start] + body[end:]
        if _UNFOLLOW_LINK in body:
            body = re.sub(_UNFOLLOW_ANCHOR_REGEX, "", body)
        return body

    def _get_already_sent_pids(
        self, already_sent_pids: dict[int, set[int]] | None = None
    ) -> set[int]:
        self.check_singleton()
        if already_sent_pids is not None:
            return already_sent_pids.get(self.id) or set()
        return self._get_already_sent_pids_batch(self.ids)[self.id]

    @api.model
    def _get_already_sent_pids_batch(
        self, mail_ids: Collection[int]
    ) -> dict[int, set[int]]:
        return self._get_email_notifications_batch(mail_ids)[0]

    @api.model
    def _get_email_notifications_batch(
        self, mail_ids: Collection[int]
    ) -> tuple[dict[int, set[int]], dict[int, list[int]]]:
        already_sent_pids = defaultdict(set)
        pending_ids = defaultdict(list)
        if not mail_ids:
            return already_sent_pids, pending_ids
        notifications = (
            self.env["mail.notification"]
            .sudo()
            .search_fetch(
                [
                    ("mail_mail_id", "in", list(mail_ids)),
                    ("notification_type", "=", "email"),
                ],
                [
                    "mail_mail_id",
                    "mail_message_id",
                    "res_partner_id",
                    "notification_status",
                ],
            )
        )
        for notification in notifications:
            mail_id = notification.mail_mail_id.id
            status = notification.notification_status
            if status == "sent":
                already_sent_pids[mail_id].add(notification.res_partner_id.id)
            elif status and status != "canceled":
                pending_ids[mail_id].append(notification.id)
        _debug.perf.count(
            "email_notifications_loaded",
            mails=len(mail_ids),
            notifications=len(notifications),
            already_sent=sum(len(pids) for pids in already_sent_pids.values()),
            pending=sum(len(ids) for ids in pending_ids.values()),
        )
        return already_sent_pids, pending_ids

    def _prepare_outgoing_attachments(
        self,
        body: str,
        headers: dict,
        mail_server: IrMail_Server | Literal[False] = False,
        smtp_session: smtplib.SMTP | None = None,
    ) -> tuple[str, list[tuple]]:
        self.check_singleton()
        attachments = self.sudo().attachment_ids
        if body and attachments:
            link_ids = {
                int(link)
                for link in re.findall(r"/web/(?:content|image)/([0-9]+)", body)
            }
            if link_ids:
                attachments -= self.env["ir.attachment"].sudo().browse(list(link_ids))

        url_attachments = attachments.filtered(
            lambda attachment: (
                attachment.url
                and not attachment.file_size
                and attachment.url.startswith(("http://", "https://", "ftp://"))
            )
        )
        if url_attachments:
            _debug.logic(
                "attachments_linked",
                mail=self.id,
                reason="url",
                count=len(url_attachments),
            )
            body = self._link_instead_of_attach(body, url_attachments)
            attachments -= url_attachments

        if record_owned_attachments := attachments.filtered(
            lambda attachment: (
                attachment.res_model
                and attachment.res_id
                and attachment.res_model != "mail.message"
            )
        ):
            estimated_email_size_bytes = self._estimate_email_size(
                headers,
                body,
                [attachment.file_size for attachment in attachments],
            )
            max_email_size_bytes = (
                (mail_server or self.env["ir.mail_server"])
                .sudo()
                ._get_max_email_size(smtp_session)
                * 1024
                * 1024
            )
            if estimated_email_size_bytes > max_email_size_bytes:
                _debug.logic(
                    "attachments_linked",
                    mail=self.id,
                    reason="size",
                    count=len(record_owned_attachments),
                    estimated=estimated_email_size_bytes,
                    max=max_email_size_bytes,
                )
                body = self._link_instead_of_attach(body, record_owned_attachments)
                attachments -= record_owned_attachments
        read_attachments = attachments.sorted("id").read(["name", "raw", "mimetype"])
        email_attachments = [
            (a["name"], a["raw"], a["mimetype"])
            for a in read_attachments
            if a["raw"] is not False
        ]
        if len(email_attachments) != len(read_attachments):
            _debug.logic(
                "attachments_without_content",
                mail=self.id,
                count=len(read_attachments) - len(email_attachments),
            )
            _logger.warning(
                "Mail (mail.mail) with ID %r sent without %s attachment(s) that "
                "hold no content: %s",
                self.id,
                len(read_attachments) - len(email_attachments),
                [a["name"] for a in read_attachments if a["raw"] is False],
            )
        attachments.invalidate_recordset(["raw", "datas"])

        return body, email_attachments

    def _link_instead_of_attach(self, body: str, attachments: IrAttachment) -> str:
        attachments.generate_access_token()
        return tools.mail.add_html_content(
            body,
            self.env["ir.qweb"]._render(
                "mail.mail_attachment_links", {"attachments": attachments}
            ),
            plaintext=False,
        )

    def _prepare_recipient_groups(
        self, already_sent_pids: dict | None = None
    ) -> list[dict]:
        self.check_singleton()
        email_list = []
        raw_group, covered = self._prepare_raw_recipient_group()
        if covered:
            _logger.info(
                "Mail (mail.mail) with ID %r: %s also name a recipient partner, "
                "sent to the partner only",
                self.id,
                covered,
            )
        if raw_group:
            email_list.append(raw_group)
        recipients = self.recipient_ids
        if self.is_notification and recipients:
            sent_pids = self._get_already_sent_pids(already_sent_pids=already_sent_pids)
            if sent_pids:
                _debug.logic(
                    "recipients_already_sent",
                    mail=self.id,
                    skipped=len(recipients.filtered(lambda p: p.id in sent_pids)),
                )
                recipients = recipients.filtered(
                    lambda partner: partner.id not in sent_pids
                )
        for partner in recipients:
            email_to_normalized = tools.mail.email_normalize_all(partner.email)
            raw_email = (partner.email or "").strip()
            if email_to_normalized:
                email_to = [
                    tools.formataddr((partner.name or "", email))
                    for email in email_to_normalized
                ]
            else:
                email_to = [raw_email] if raw_email else []
            email_list.append(
                {
                    "email_cc": [],
                    "email_to": email_to,
                    "email_to_normalized": email_to_normalized,
                    "partner": partner,
                }
            )

        _debug.logic(
            "recipient_groups",
            mail=self.id,
            raw=raw_group is not None,
            covered=len(covered),
            partners=len(recipients),
            groups=len(email_list),
        )
        return email_list

    def _prepare_raw_recipient_group(self) -> tuple[dict | None, list[str]]:
        self.check_singleton()
        partner_emails = {
            email
            for partner in self.recipient_ids
            for email in tools.mail.email_normalize_all(partner.email)
        }
        email_to, email_cc, covered = [], [], []
        for fname, addresses in (("email_to", email_to), ("email_cc", email_cc)):
            for address in tools.mail.email_split_and_format_normalize(
                self[fname] or ""
            ):
                if tools.email_normalize(address) in partner_emails:
                    covered.append(address)
                else:
                    addresses.append(address)
        has_raw_addresses = bool(
            (self.email_to or "").strip() or (self.email_cc or "").strip()
        )
        if not (email_to or email_cc) and (covered or not has_raw_addresses):
            return None, covered
        return {
            "email_cc": email_cc,
            "email_to": email_to,
            "email_to_normalized": [
                tools.email_normalize(address) for address in email_to + email_cc
            ],
            "partner": self.env["res.partner"],
        }, covered

    def _prepare_outgoing_list(
        self,
        mail_server: IrMail_Server | Literal[False] = False,
        doc_to_followers: dict | None = None,
        smtp_session: smtplib.SMTP | None = None,
        already_sent_pids: dict | None = None,
    ) -> list[dict]:
        self.check_singleton()
        body = self._prepare_outgoing_body()

        headers = {}
        if self.headers:
            if isinstance(self.headers, dict):
                headers = dict(self.headers)
            else:
                _debug.logic(
                    "headers_rejected", mail=self.id, type=type(self.headers).__name__
                )
                _logger.warning(
                    "Mail headers must be a mapping (received %r)", self.headers
                )
        if bounce_email := (
            self.record_alias_domain_id.bounce_email or self.env.company.bounce_email
        ):
            headers.setdefault("Return-Path", bounce_email)

        email_list = self._prepare_recipient_groups(already_sent_pids=already_sent_pids)

        body, email_attachments = self._prepare_outgoing_attachments(
            body, headers, mail_server=mail_server, smtp_session=smtp_session
        )
        email_from = self._get_envelope_email_from()

        results = []
        plaintext_per_body = {}
        unfollow_block = self._resolve_unfollow_block(body)
        body_without_unfollow_link = None
        for email_values in email_list:
            partner = email_values["partner"]
            if unfollow_block is not None and self._is_unfollow_link_required(
                partner, doc_to_followers
            ):
                body_personalized = self._apply_unfollow_block(
                    body, unfollow_block, partner, doc_to_followers
                )
            else:
                if body_without_unfollow_link is None:
                    body_without_unfollow_link = self._apply_unfollow_block(
                        body, unfollow_block
                    )
                body_personalized = body_without_unfollow_link
            if body_personalized not in plaintext_per_body:
                plaintext_per_body[body_personalized] = tools.html2plaintext(
                    body_personalized
                )
            results.append(
                {
                    "attachments": email_attachments,
                    "body": body_personalized,
                    "body_alternative": plaintext_per_body[body_personalized],
                    "email_cc": email_values["email_cc"],
                    "email_from": email_from,
                    "email_to": email_values["email_to"],
                    "email_to_normalized": email_values["email_to_normalized"],
                    "headers": dict(headers),
                    "message_id": self.message_id,
                    "object_id": f"{self.res_id}-{self.model}" if self.res_id else "",
                    "partner": partner,
                    "references": self.references,
                    "reply_to": self.reply_to,
                    "subject": self.subject,
                }
            )

        _debug.pipeline(
            "outgoing_list",
            mail=self.id,
            emails=len(results),
            attachments=len(email_attachments),
            bodies=len(plaintext_per_body),
            unfollow=unfollow_block is not None,
        )
        return results

    def _split_by_mail_configuration(self) -> Iterator[tuple]:
        fields_to_group = ["email_from", "mail_server_id", "record_alias_domain_id"]
        self.fetch(fields_to_group)
        all_mail_servers = (
            self.env["ir.mail_server"].sudo().search([], order="sequence, id")
        )

        group_per_email_from = defaultdict(list)
        for mail in self:
            key = (
                mail.mail_server_id.id,
                mail.record_alias_domain_id.id,
                mail._get_envelope_email_from(),
                mail._filtered_mail_mail_servers(all_mail_servers),
            )
            group_per_email_from[key].append(mail.id)

        group_per_smtp_from = defaultdict(list)
        for (
            mail_server_id,
            alias_domain_id,
            email_from,
            allowed_mail_servers,
        ), mail_ids in group_per_email_from.items():
            if not mail_server_id:
                mail_server = self.env["ir.mail_server"]
                if alias_domain_id:
                    alias_domain = (
                        self.env["mail.alias.domain"].sudo().browse(alias_domain_id)
                    )
                    mail_server = mail_server.with_context(
                        domain_notifications_email=alias_domain.default_from_email,
                        domain_bounce_address=alias_domain.bounce_email,
                    )
                mail_server, smtp_from = mail_server._get_mail_server(
                    email_from, allowed_mail_servers
                )
                mail_server_id = mail_server.id if mail_server else False
            else:
                smtp_from = email_from

            group_per_smtp_from[(mail_server_id, alias_domain_id, smtp_from)].extend(
                mail_ids
            )

        batch_size = self.env["ir.config_parameter"]._get_positive_int_param(
            "mail.session.batch.size", 1000
        )
        _debug.pipeline(
            "split_by_configuration",
            mails=len(self),
            servers=len(all_mail_servers),
            from_groups=len(group_per_email_from),
            smtp_groups=len(group_per_smtp_from),
            batch_size=batch_size,
        )
        for (
            mail_server_id,
            alias_domain_id,
            smtp_from,
        ), record_ids in group_per_smtp_from.items():
            for batch_ids in itertools.batched(record_ids, batch_size, strict=False):
                yield mail_server_id, alias_domain_id, smtp_from, batch_ids

    def _filtered_ready_to_send(self) -> Self:
        now = fields.Datetime.now()
        return self.filtered(
            lambda mail: (
                mail.state == "outgoing"
                and (not mail.scheduled_date or mail.scheduled_date <= now)
            )
        )

    def _has_any_recipient(self) -> bool:
        self.check_singleton()
        return bool(
            (self.email_to or "").strip()
            or self.recipient_ids
            or (self.email_cc or "").strip()
        )

    def _raw_address_message_count(self) -> int:
        self.check_singleton()
        return int(self._prepare_raw_recipient_group()[0] is not None)

    def _personal_server_cost(self) -> int:
        return sum(
            (len(mail.recipient_ids) + mail._raw_address_message_count()) or 1
            for mail in self
        )

    @api.model
    def _rotate_quota_minute(self, mail_server: IrMail_Server) -> datetime.datetime:
        current_minute = self.env.cr.now().replace(second=0, microsecond=0)
        server_limit_minute = (
            mail_server.owner_limit_time or current_minute - timedelta(minutes=1)
        )
        if server_limit_minute > current_minute:
            _debug.logic(
                "quota_minute_in_future",
                server=mail_server.id,
                limit_minute=server_limit_minute,
                current=current_minute,
            )
            _logger.error(
                "Mail: invalid owner_limit_time %s > %s for %s",
                server_limit_minute,
                current_minute,
                mail_server.name,
            )
        if server_limit_minute != current_minute:
            mail_server.owner_limit_time = current_minute
            mail_server.owner_limit_count = 0
            server_limit_minute = current_minute
        return server_limit_minute

    def _schedule_delayed_batch(
        self,
        mail_server: IrMail_Server,
        server_limit_minute: datetime.datetime,
        max_send: int,
    ) -> None:
        owner_limit_count = mail_server.owner_limit_count
        scheduled_per_mail = {}
        for mail in self:
            cost = mail._personal_server_cost()
            if owner_limit_count < max_send:
                owner_limit_count += cost
            else:
                owner_limit_count = cost
                server_limit_minute += timedelta(minutes=1)
            scheduled_per_mail[mail.id] = server_limit_minute

        for scheduled_date, mail_ids in itertools.groupby(
            sorted(scheduled_per_mail, key=scheduled_per_mail.get),
            key=scheduled_per_mail.get,
        ):
            self.browse(list(mail_ids)).scheduled_date = scheduled_date

        _debug.lifecycle(
            "delayed_batch_scheduled",
            server=mail_server.id,
            mails=len(self),
            max_send=max_send,
            first=min(scheduled_per_mail.values()),
            last=max(scheduled_per_mail.values()),
        )
        self.env.ref("mail.ir_cron_mail_scheduler_action")._trigger(
            min(scheduled_per_mail.values()) + timedelta(seconds=59)
        )

    def _split_by_delayed_batch(self, mail_server: IrMail_Server) -> Self:
        if not mail_server or not mail_server.owner_user_id:
            return self

        mail_server.lock_for_update()
        mail_server.invalidate_recordset(["owner_limit_count", "owner_limit_time"])

        MAX_SEND = mail_server._get_personal_mail_servers_limit()
        server_limit_minute = self._rotate_quota_minute(mail_server)

        to_send_ids = []
        to_delay_ids = []
        notifs = (
            self.env["mail.notification"]
            .sudo()
            .search(self._get_domain_pending_email_notifications(self.ids))
        )
        for mail in self.sorted(lambda k: (k.create_date, k.id)):
            room = MAX_SEND - mail_server.owner_limit_count
            cost = mail._personal_server_cost()
            if room <= 0:
                to_delay_ids.append(mail.id)
                continue
            if cost <= room:
                to_send_ids.append(mail.id)
                mail_server.owner_limit_count += cost
                continue
            raw_cost = mail._raw_address_message_count()
            to_keep = room - raw_cost
            if to_keep <= 0:
                to_delay_ids.append(mail.id)
                continue
            new_mail = mail._split_off_sendable_copy(notifs, to_keep, raw_cost)
            mail_server.owner_limit_count += to_keep + raw_cost
            to_send_ids.append(new_mail.id)
            to_delay_ids.append(mail.id)

        to_send = self.browse(to_send_ids)
        to_delay = self.browse(to_delay_ids)
        if to_delay:
            to_delay._schedule_delayed_batch(mail_server, server_limit_minute, MAX_SEND)

        _debug.logic(
            "personal_server_quota",
            server=mail_server.id,
            max_send=MAX_SEND,
            used=mail_server.owner_limit_count,
            to_send=len(to_send),
            delayed=len(to_delay),
        )
        _logger.info(
            "Mail: personal server %s: %s emails about to be sent / %s emails delayed",
            mail_server.name,
            len(to_send),
            len(to_delay),
        )
        return to_send

    def _split_off_sendable_copy(
        self, notifs: MailNotification, to_keep: int, raw_cost: int
    ) -> Self:
        self.check_singleton()
        recipient_ids = self.recipient_ids
        moved_partners = recipient_ids[:to_keep]
        new_mail = (
            self.with_user(self.create_uid)
            .sudo()
            .copy(
                {
                    "headers": self.headers,
                    "mail_message_id": self.mail_message_id.id,
                    "recipient_ids": moved_partners.ids,
                }
            )
        )
        self.write(
            {
                "recipient_ids": recipient_ids[to_keep:],
                "email_cc": False,
                "email_to": False,
            }
        )
        notifs.filtered(
            lambda notif: (
                notif.mail_mail_id == self
                and (
                    notif.res_partner_id in moved_partners
                    or (not notif.res_partner_id and raw_cost)
                )
            )
        ).mail_mail_id = new_mail
        _debug.lifecycle(
            "sendable_copy_split",
            mail=self.id,
            new_mail=new_mail.id,
            moved=len(moved_partners),
            raw=raw_cost,
        )
        return new_mail

    def send_after_commit(self) -> None:
        if modules.module.current_test:
            self.exists().send()
            return

        email_ids = self.ids
        dbname = self.env.cr.dbname
        _context = self.env.context
        _debug.logic("send_after_commit", mails=len(email_ids))

        @self.env.cr.postcommit.add
        def send_emails_with_new_cursor() -> None:
            db_registry = Registry(dbname)
            with db_registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, _context)
                env["mail.mail"].browse(email_ids).exists().send()

    def send(
        self,
        auto_commit: bool = False,
        raise_exception: bool = False,
        post_send_callback: Callable[..., bool] | None = None,
    ) -> None:
        outgoing = self._filtered_ready_to_send()
        for (
            mail_server_id,
            alias_domain_id,
            smtp_from,
            batch_ids,
        ) in outgoing._split_by_mail_configuration():
            mail_server = self.env["ir.mail_server"].browse(mail_server_id)

            quota_charged = 0
            if mail_server and mail_server.owner_user_id:
                to_send = self.browse(batch_ids)._split_by_delayed_batch(mail_server)
                quota_charged = to_send._personal_server_cost()
                batch_ids = to_send.ids
                if not batch_ids:
                    continue

            _debug.pipeline(
                "send_batch",
                mails=len(batch_ids),
                server=mail_server_id,
                alias_domain=alias_domain_id,
                smtp_from=smtp_from,
                quota_charged=quota_charged,
            )
            smtp_session = None
            try:
                smtp_session = self.env["ir.mail_server"]._connect__(
                    mail_server_id=mail_server_id,
                    smtp_from=smtp_from,
                    resolve_server=False,
                )
            except Exception as exc:
                _debug.logic(
                    "smtp_connect_failed",
                    server=mail_server_id,
                    error=type(exc).__name__,
                    raised=raise_exception,
                )
                if raise_exception:
                    raise MailDeliveryError(
                        _("Unable to connect to SMTP Server"), exc
                    ) from exc
                self.browse(batch_ids)._record_connect_failure(
                    exc, mail_server, quota_charged
                )
            else:
                with _debug.perf(
                    "send_batch",
                    cr=self.env.cr,
                    mails=len(batch_ids),
                    server=mail_server_id,
                ):
                    self.browse(batch_ids)._send(
                        auto_commit=auto_commit,
                        raise_exception=raise_exception,
                        smtp_session=smtp_session,
                        alias_domain_id=alias_domain_id,
                        mail_server=mail_server,
                        post_send_callback=post_send_callback,
                    )
                if not modules.module.current_test:
                    _logger.info(
                        "Processed batch of %s mail.mail records via mail server ID #%s",
                        len(batch_ids),
                        mail_server_id,
                    )
            finally:
                self._close_smtp_session(smtp_session)

    @api.model
    def _close_smtp_session(self, smtp_session: smtplib.SMTP | None) -> None:
        if not smtp_session:
            return
        try:
            smtp_session.quit()
        except smtplib.SMTPServerDisconnected:
            _debug.logic("smtp_quit_failed", error="SMTPServerDisconnected")
            _logger.info(
                "Ignoring SMTPServerDisconnected while trying to quit non open session"
            )
        except Exception as error:
            _debug.logic("smtp_quit_failed", error=type(error).__name__)
            _logger.info("Ignoring error while closing SMTP session", exc_info=True)
            with contextlib.suppress(Exception):
                smtp_session.close()

    def _record_connect_failure(
        self,
        exception: BaseException,
        mail_server: IrMail_Server,
        quota_charged: int = 0,
    ) -> None:
        if quota_charged:
            mail_server.owner_limit_count = max(
                0, mail_server.owner_limit_count - quota_charged
            )
        failure_reason = (
            "\n".join(str(arg) for arg in exception.args)
            if exception.args
            else str(exception)
        )
        outgoing = self.filtered(lambda mail: mail.state == "outgoing")
        _debug.lifecycle(
            "connect_failure_recorded",
            mails=outgoing.ids,
            server=mail_server.id or None,
            quota_refunded=quota_charged,
        )
        outgoing.write(
            {
                "state": "exception",
                "failure_reason": failure_reason,
                "failure_type": "mail_smtp",
            }
        )
        outgoing._postprocess_sent_message(
            success_partners=[],
            success_emails=[],
            failure_reason=failure_reason,
            failure_type="mail_smtp",
        )

    def action_send_and_close(self) -> dict:
        self.filtered("scheduled_date").write({"scheduled_date": False})
        self.send()
        return {
            "name": _("Emails"),
            "res_model": "mail.mail",
            "view_mode": "list",
            "views": [[False, "list"], [False, "form"]],
            "target": "main",
            "type": "ir.actions.act_window",
        }

    def _send(
        self,
        auto_commit: bool = False,
        raise_exception: bool = False,
        smtp_session: smtplib.SMTP | None = None,
        alias_domain_id: int | Literal[False] = False,
        mail_server: IrMail_Server | Literal[False] = False,
        post_send_callback: Callable[..., bool] | None = None,
    ) -> bool:
        if self.env["ir.mail_server"]._disable_send():
            _debug.logic("send_disabled", mails=len(self))
            return True

        to_send = self
        if mail_server:
            unauthorized = self.filtered(
                lambda mail: not mail._filtered_mail_mail_servers(mail_server)
            )
            if unauthorized:
                _debug.logic(
                    "unauthorized_server",
                    server=mail_server.id,
                    mails=unauthorized.ids,
                    raised=raise_exception,
                )
                if raise_exception:
                    raise UserError(
                        _("Unauthorized server for some of the sending mails.")
                    )
                to_send = self - unauthorized
                unauthorized._record_unauthorized_server(mail_server)

        batch = to_send._prepare_send_batch(
            alias_domain_id, mail_server, smtp_session, auto_commit=auto_commit
        )

        ids = to_send._ids
        for index, mail_id in enumerate(ids):
            mail = self.browse(mail_id)
            if not auto_commit:
                mail = mail.with_prefetch(ids[index:])
            if mail.state != "outgoing":
                continue
            mail._send_one(batch, raise_exception=raise_exception)
            if auto_commit is True:
                if not (post_send_callback and post_send_callback([mail_id])):
                    self.env.cr.commit()
        if batch.deferred_auto_delete:
            _debug.lifecycle(
                "deferred_auto_delete", count=len(batch.deferred_auto_delete)
            )
            self.browse(batch.deferred_auto_delete).sudo().unlink()
        if post_send_callback:
            post_send_callback(self.ids, final=True)
        return True

    def _record_unauthorized_server(self, mail_server: IrMail_Server) -> None:
        failure_reason = _(
            "The outgoing mail server %(server)s is not available to this email.",
            server=mail_server.sudo().display_name,
        )
        _logger.warning(
            "Mail: %s not usable by mail.mail %s; recorded as a delivery failure",
            mail_server.sudo().display_name,
            self.ids,
        )
        outgoing = self.filtered(lambda mail: mail.state == "outgoing")
        outgoing.write(
            {
                "failure_reason": failure_reason,
                "failure_type": "mail_server_unauthorized",
                "state": "exception",
            }
        )
        outgoing._postprocess_sent_message(
            success_partners=[],
            success_emails=[],
            failure_reason=failure_reason,
            failure_type="mail_server_unauthorized",
        )

    def _prepare_send_batch(
        self,
        alias_domain_id: int | Literal[False],
        mail_server: IrMail_Server | Literal[False],
        smtp_session: smtplib.SMTP | None,
        auto_commit: bool = False,
    ) -> _SendBatch:
        cache_survives_loop = not auto_commit
        if cache_survives_loop:
            mails_with_unfollow_link = self.filtered(
                lambda mail: self._has_unfollow_block(mail.body_html)
            )
        else:
            mails_with_unfollow_link = (
                self.sudo()
                .search([("id", "in", self.ids), ("body_html", "like", _UNFOLLOW_LINK)])
                .filtered(lambda mail: self._has_unfollow_block(mail.body_html))
            )
        already_sent_pids, pending_notification_ids = (
            self._get_email_notifications_batch(self.ids)
        )
        _debug.perf.count(
            "send_batch_prepared",
            mails=len(self),
            unfollow=len(mails_with_unfollow_link),
            already_sent=len(already_sent_pids),
            pending=len(pending_notification_ids),
            cache_survives=cache_survives_loop,
        )
        return _SendBatch(
            commits_per_mail=auto_commit,
            deferred_auto_delete=set() if cache_survives_loop else None,
            alias_domain=self.env["mail.alias.domain"].sudo().browse(alias_domain_id),
            mail_server=mail_server,
            smtp_session=smtp_session,
            already_sent_pids=already_sent_pids,
            doc_to_followers=self.env["mail.followers"]._get_mail_doc_to_followers(
                mails_with_unfollow_link.ids
            ),
            pending_notification_ids=pending_notification_ids,
            recipient_bearing_ids=frozenset(
                self.sudo().filtered(lambda mail: mail._has_any_recipient()).ids
            ),
        )

    def _send_one(self, batch: _SendBatch, raise_exception: bool = False) -> None:
        self.check_singleton()
        IrMailServer = self.env["ir.mail_server"]
        outcome = _SendOutcome()
        email_list = []

        pending_notification_ids = batch.pending_notification_ids.get(self.id, [])
        mark = _SendingMark()
        try:
            mark = self._begin_sending(outcome, batch, pending_notification_ids)
            email_list = self._deliver_all(outcome, batch)
            if (
                not outcome.message_id
                and raise_exception
                and outcome.delivery_error is not None
            ):
                raise outcome.delivery_error
        except self._FATAL_MEMORY_ERRORS:
            _debug.logic("send_fatal", mail=self.id, kind="memory")
            _logger.exception(
                "MemoryError while processing mail with ID %r and Msg-Id %r. "
                "Consider raising the --limit-memory-hard startup option",
                self.id,
                self.message_id,
            )
            raise
        except self._FATAL_SESSION_ERRORS:
            _debug.logic("send_fatal", mail=self.id, kind="session")
            _logger.exception(
                "Exception while processing mail with ID %r and Msg-Id %r.",
                self.id,
                self.message_id,
            )
            raise
        except Exception as e:
            self._record_send_failure(
                e,
                outcome,
                batch,
                mark,
                pending_notification_ids=pending_notification_ids,
            )
            if raise_exception:
                self._reraise_send_error(e)
        else:
            self._record_send_success(
                outcome,
                email_list,
                batch,
                mark,
                pending_notification_ids=pending_notification_ids,
            )
            if not outcome.message_id and raise_exception and outcome.failure_type:
                raise MailDeliveryError(
                    outcome.failure_reason
                    or IrMailServer._get_outgoing_email_message(
                        IrMailServer.NO_VALID_RECIPIENT
                    )
                )
            if outcome.message_id:
                try:
                    self._log_sent(outcome, email_list)
                except Exception:
                    _logger.exception(
                        "Mail (mail.mail) %r was sent; logging it was not", self.id
                    )

    def _begin_sending(
        self,
        outcome: _SendOutcome,
        batch: _SendBatch,
        pending_notification_ids: list[int],
    ) -> _SendingMark:
        self.check_singleton()
        mark = self._mark_sending(
            pending_notification_ids=pending_notification_ids,
            recipient_bearing_ids=batch.recipient_bearing_ids,
        )
        if mark.failure_type:
            outcome.failure_type = mark.failure_type
            outcome.failure_reason = mark.failure_reason
        if batch.commits_per_mail:
            self.env.cr.commit()
        return mark

    @api.model
    def _reraise_send_error(self, exception: Exception) -> typing.NoReturn:
        if isinstance(exception, UnicodeEncodeError):
            raise MailDeliveryError(f"Invalid text: {exception.object}") from exception
        if isinstance(exception, AssertionError):
            raise MailDeliveryError(". ".join(exception.args)) from exception
        raise exception

    def _deliver_all(self, outcome: _SendOutcome, batch: _SendBatch) -> list[dict]:
        self.check_singleton()
        email_list = self._prepare_outgoing_list(
            mail_server=batch.mail_server or self.mail_server_id,
            doc_to_followers=batch.doc_to_followers,
            smtp_session=batch.smtp_session,
            already_sent_pids=batch.already_sent_pids,
        )
        with _debug.perf(
            "deliver", cr=self.env.cr, mail=self.id, emails=len(email_list)
        ) as span:
            for email in email_list:
                outcome.absorb(self._deliver_one(email, batch, outcome.failure_type))
            span.set(
                delivered=len(outcome.success_partners) + len(outcome.success_emails),
                failure_type=outcome.failure_type,
            )
        return email_list

    def _record_send_success(
        self,
        outcome: _SendOutcome,
        email_list: list[dict],
        batch: _SendBatch,
        mark: _SendingMark,
        pending_notification_ids: list[int] | None = None,
    ) -> None:
        self.check_singleton()
        nothing_left_to_deliver = (
            mark.had_recipients
            and not email_list
            and bool(batch.already_sent_pids.get(self.id))
        )
        _debug.lifecycle(
            "send_success",
            mail=self.id,
            message_id=outcome.message_id or None,
            partners=len(outcome.success_partners),
            emails=len(outcome.success_emails),
            failure_type=outcome.failure_type,
            nothing_left=nothing_left_to_deliver,
        )
        self._record_send_outcome(
            outcome,
            email_list,
            nothing_left_to_deliver=nothing_left_to_deliver,
        )
        try:
            self._postprocess_sent_message(
                success_partners=outcome.success_partners,
                success_emails=outcome.success_emails,
                failure_type=outcome.failure_type,
                failure_reason=outcome.failure_reason,
                pending_notification_ids=pending_notification_ids,
                defer_auto_delete=batch.deferred_auto_delete,
                previously_failing_ids=mark.previously_failing_ids,
            )
        except Exception:
            _logger.exception(
                "Mail (mail.mail) %r was delivered; settling its notifications was not",
                self.id,
            )

    def _record_send_failure(
        self,
        exception: BaseException,
        outcome: _SendOutcome,
        batch: _SendBatch,
        mark: _SendingMark,
        pending_notification_ids: list[int] | None = None,
    ) -> None:
        self.check_singleton()
        outcome.failure_type, outcome.failure_reason = self._classify_send_error(
            exception,
            failure_type=outcome.failure_type,
            failure_reason=outcome.failure_reason,
        )
        _debug.lifecycle(
            "send_failure",
            mail=self.id,
            error=type(exception).__name__,
            failure_type=outcome.failure_type,
            partners=len(outcome.success_partners),
            emails=len(outcome.success_emails),
        )
        _logger.error(
            "failed sending mail (id: %s) due to %s",
            self.id,
            outcome.failure_reason,
            exc_info=exception,
        )
        self.write(
            {
                "failure_reason": outcome.failure_reason,
                "failure_type": outcome.failure_type,
                "state": "exception",
            }
        )
        self._postprocess_sent_message(
            success_partners=outcome.success_partners,
            success_emails=outcome.success_emails,
            failure_reason=outcome.failure_reason,
            failure_type=outcome.failure_type,
            pending_notification_ids=pending_notification_ids,
            defer_auto_delete=batch.deferred_auto_delete,
            previously_failing_ids=mark.previously_failing_ids,
        )

    def _mark_sending(
        self,
        pending_notification_ids: list[int] | None = None,
        recipient_bearing_ids: frozenset[int] | None = None,
    ) -> _SendingMark:
        self.check_singleton()
        no_recipients = (
            self.id not in recipient_bearing_ids
            if recipient_bearing_ids is not None
            else not self._has_any_recipient()
        )
        mark = _SendingMark(had_recipients=not no_recipients)
        _debug.logic(
            "mark_sending",
            mail=self.id,
            no_recipients=no_recipients,
            pending=len(pending_notification_ids or ()),
        )
        placeholder = _(
            "Placeholder recorded before sending. Still present means the send "
            "was interrupted before it could record an outcome; see the server log."
        )
        if no_recipients:
            mark.failure_type = "mail_email_missing"
            mark.failure_reason = self.env[
                "ir.mail_server"
            ]._get_outgoing_email_message(self.env["ir.mail_server"].NO_VALID_RECIPIENT)
        self.write(
            {
                "state": "exception",
                "failure_reason": mark.failure_reason or placeholder,
                "failure_type": "mail_email_missing" if no_recipients else "unknown",
            }
        )
        notifs = (
            self.env["mail.notification"].browse(pending_notification_ids)
            if pending_notification_ids is not None
            else self.env["mail.notification"].search(
                self._get_domain_pending_email_notifications(self.ids)
            )
        )
        if notifs:
            mark.previously_failing_ids = notifs.filtered(
                lambda notif: (
                    notif.notification_status in self._FAILING_NOTIFICATION_STATUS
                )
            ).ids
            notifs.sudo().write(
                {
                    "notification_status": "exception",
                    "failure_type": "unknown",
                    "failure_reason": placeholder,
                }
            )
            notifs.flush_recordset(
                ["notification_status", "failure_type", "failure_reason"]
            )
        return mark

    def _deliver_one(
        self,
        email: dict,
        batch: _SendBatch,
        previous_failure_type: str | None = None,
    ) -> _DeliveryResult:
        self.check_singleton()
        IrMailServer = self.env["ir.mail_server"]
        email_to_normalized = email.get("email_to_normalized") or []
        send_context = {"send_validated_to": email_to_normalized}
        if batch.alias_domain:
            send_context.update(
                domain_notifications_email=batch.alias_domain.default_from_email,
                domain_bounce_address=email["headers"].get("Return-Path")
                or batch.alias_domain.bounce_email,
            )
        SendIrMailServer = IrMailServer.with_context(**send_context)
        msg = SendIrMailServer._prepare_email__(
            email_from=email["email_from"],
            email_to=email["email_to"],
            subject=email["subject"],
            body=email["body"],
            body_alternative=email["body_alternative"],
            email_cc=email["email_cc"],
            reply_to=email["reply_to"],
            attachments=email["attachments"],
            message_id=email["message_id"],
            references=email["references"],
            object_id=email["object_id"],
            subtype="html",
            subtype_alternative="plain",
            headers=email["headers"],
        )
        result = _DeliveryResult(msg=msg)
        recipient_partner = email.get("partner")
        try:
            result.message_id = SendIrMailServer.send_email(
                msg,
                mail_server_id=(batch.mail_server and batch.mail_server.id)
                or self.mail_server_id.id,
                smtp_session=batch.smtp_session,
            )
            if recipient_partner:
                result.success_partner = recipient_partner
            else:
                result.success_emails = list(email_to_normalized)
        except OutgoingEmailError as error:
            if error.code != IrMailServer.NO_VALID_RECIPIENT:
                raise
            if (
                not email.get("email_to")
                and previous_failure_type != "mail_email_invalid"
            ):
                result.failure_type = "mail_email_missing"
            else:
                result.failure_type = "mail_email_invalid"
            result.failure_reason = str(error)
            _debug.logic(
                "recipient_invalid", mail=self.id, failure_type=result.failure_type
            )
            _logger.info(
                "Ignoring invalid recipients for mail.mail %s: %s",
                self.message_id,
                email.get("email_to"),
            )
        except MailDeliveryError as error:
            if "OutboundSpamException" in str(error):
                result.failure_type = "mail_spam"
            else:
                result.failure_type = "unknown"
            result.failure_reason = str(error)
            _debug.logic(
                "delivery_failed", mail=self.id, failure_type=result.failure_type
            )
            _logger.warning(
                "Delivery failed for one recipient of mail.mail %s: %s",
                self.message_id,
                error,
            )
            result.delivery_error = error
        return result

    def _record_send_outcome(
        self,
        outcome: _SendOutcome,
        email_list: list[dict],
        nothing_left_to_deliver: bool = False,
    ) -> None:
        self.check_singleton()
        if not outcome.message_id:
            mail_vals = {}
            if outcome.failure_reason:
                mail_vals["failure_reason"] = outcome.failure_reason
            if outcome.failure_type:
                mail_vals["failure_type"] = outcome.failure_type
            if not mail_vals and nothing_left_to_deliver:
                mail_vals = {
                    "state": "sent",
                    "failure_type": False,
                    "failure_reason": False,
                }
            if mail_vals:
                self.write(mail_vals)
            return
        partial_failure = bool(outcome.delivery_error)
        self.write(
            {
                "state": "sent",
                "failure_type": outcome.failure_type if partial_failure else False,
                "failure_reason": outcome.failure_reason if partial_failure else False,
            }
        )
        if outcome.message_id != self.message_id:
            _debug.logic(
                "message_id_rewritten",
                mail=self.id,
                old=self.message_id,
                new=outcome.message_id,
            )
            try:
                self.mail_message_id.message_id = outcome.message_id
            except AccessError:
                _logger.warning(
                    "Mail (mail.mail) %r was delivered under Message-Id %r; its "
                    "message keeps %r, which this user may not write",
                    self.id,
                    outcome.message_id,
                    self.message_id,
                )

    def _log_sent(self, outcome: _SendOutcome, email_list: list[dict]) -> None:
        if not _logger.isEnabledFor(logging.INFO):
            return
        _logger.info(
            "Mail (mail.mail) with ID %r and Message-Id %r from %r to (redacted) %s "
            "successfully sent over %s SMTP attempt(s)",
            self.id,
            outcome.message_id,
            tools.email_normalize(outcome.last_msg["from"])
            if outcome.last_msg
            else None,
            ", ".join(
                repr(tools.mail.email_anonymize(addr))
                for email in email_list
                for addr in filter(
                    None,
                    map(
                        tools.email_normalize,
                        email["email_to"]
                        if isinstance(email["email_to"], (list, tuple))
                        else [email["email_to"]],
                    ),
                )
            ),
            len(email_list),
        )

    def _classify_send_error(
        self,
        exception: BaseException,
        failure_type: str | None = None,
        failure_reason: str | None = None,
    ) -> tuple[str, str]:
        IrMailServer = self.env["ir.mail_server"]
        if isinstance(exception, OutgoingEmailError):
            failure_reason = str(exception)
            if exception.code == IrMailServer.NO_VALID_FROM:
                failure_type = "mail_from_invalid"
            elif exception.code in (
                IrMailServer.NO_FOUND_FROM,
                IrMailServer.NO_FOUND_SMTP_FROM,
            ):
                failure_type = "mail_from_missing"
        if isinstance(exception, MailDeliveryError) and (
            "OutboundSpamException" in str(exception)
        ):
            failure_type = "mail_spam"
        if not failure_reason:
            failure_reason = str(exception)
        if not failure_type:
            failure_type = "unknown"
        _debug.logic(
            "send_error_classified",
            error=type(exception).__name__,
            failure_type=failure_type,
        )
        return failure_type, failure_reason

    def _get_notification_values(self) -> list[dict]:
        return [
            {
                "author_id": mail.author_id.id,
                "is_read": True,
                "mail_mail_id": mail.id,
                "mail_message_id": mail.mail_message_id.id,
                "notification_type": "email",
                "notification_status": mail._get_notification_status(),
                "failure_type": mail.failure_type,
            }
            for mail in self
        ]

    def _get_notification_status(self) -> str:
        self.check_singleton()
        return self._NOTIFICATION_STATUS_PER_STATE.get(self.state, "ready")
