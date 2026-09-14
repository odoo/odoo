import contextlib
import logging
import re
import textwrap
import typing
from binascii import Error as binascii_error
from collections import defaultdict
from collections.abc import Collection, Sequence
from types import NotImplementedType
from typing import Any, Literal, Self

from lxml import html
from psycopg.errors import UniqueViolation

from odoo import _, api, fields, models, tools
from odoo.api import DomainType, ValuesType
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.fields import Command, Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, clean_context
from odoo.tools.misc import OrderedSet

from odoo.addons.mail.tools.discuss import Store

if typing.TYPE_CHECKING:
    from .discuss.mail_guest import MailGuest
    from .ir_mail_server import IrMail_Server
    from .mail_activity_type import MailActivityType
    from .mail_alias_domain import MailAliasDomain
    from .mail_mail import MailMail
    from .mail_message_link_preview import MessageMailLinkPreview
    from .mail_message_reaction import MailMessageReaction
    from .mail_message_subtype import MailMessageSubtype
    from .mail_notification import MailNotification
    from .mail_tracking_value import MailTrackingValue
    from .res_partner import ResPartner
    from odoo.addons.base.models.res_company import ResCompany
    from odoo.addons.bus.models.ir_attachment import IrAttachment

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)
_image_dataurl = re.compile(
    r'(data:image/[a-z]+?);base64,([a-z0-9+/\n]{3,}=*)\n*([\'"])(?: data-filename="([^"]*)")?',
    re.IGNORECASE,
)


PREVIEW_LENGTH = 190
PREVIEW_PLACEHOLDER = "[...]"
REACTION_CONTENT_MAX_LENGTH = 32


class MailMessage(models.Model):
    _name = "mail.message"
    _inherit = ["mixin.bus.listener"]
    _description = "Message"
    _order = "id desc"
    _rec_name = "subject"

    _mail_partner_fields = ()

    _AUTHOR_FIELD_NAMES = ("author_id", "email_from")
    _ENVELOPE_FIELD_NAMES = (
        *_AUTHOR_FIELD_NAMES,
        "author_guest_id",
        "date",
        "is_internal",
        "message_type",
        "pinned_at",
        "subtype_id",
    )

    @api.model
    def default_get(self, fields: list[str]) -> ValuesType:
        res = super().default_get(fields)
        self._update_author(
            res,
            author="author_id" in fields,
            email_from="email_from" in fields,
        )
        return res

    @api.model
    def _update_author(
        self, values: ValuesType, *, author: bool = True, email_from: bool = True
    ) -> None:
        wants_author = author and "author_id" not in values
        wants_email_from = email_from and "email_from" not in values
        if not (wants_author or wants_email_from):
            return
        author_id, computed_email_from = self.env[
            "mixin.mail.thread"
        ]._message_compute_author(values.get("author_id"), values.get("email_from"))
        if wants_email_from:
            values["email_from"] = computed_email_from
        if wants_author:
            values["author_id"] = author_id

    subject = fields.Char()
    date = fields.Datetime(default=fields.Datetime.now)
    body = fields.Html(
        string="Contents",
        sanitize_style=True,
        default="",
    )
    preview = fields.Char(
        compute="_compute_preview",
        help="The text-only beginning of the body used as email preview.",
    )
    message_link_preview_ids: MessageMailLinkPreview = fields.One2many(
        comodel_name="mail.message.link.preview",
        inverse_name="message_id",
        groups="base.group_erp_manager",
    )
    reaction_ids: MailMessageReaction = fields.One2many(
        comodel_name="mail.message.reaction",
        inverse_name="message_id",
        string="Reactions",
        groups="base.group_system",
    )
    attachment_ids: IrAttachment = fields.Many2many(
        comodel_name="ir.attachment",
        relation="message_attachment_rel",
        column1="message_id",
        column2="attachment_id",
        string="Attachments",
        bypass_search_access=True,
    )
    parent_id: MailMessage = fields.Many2one(
        comodel_name="mail.message",
        string="Parent Message",
        index="btree_not_null",
        ondelete="set null",
    )
    child_ids: MailMessage = fields.One2many(
        comodel_name="mail.message",
        inverse_name="parent_id",
        string="Child Messages",
    )
    model = fields.Char(string="Related Document Model")
    res_id = fields.Many2oneReference(
        model_field="model",
        string="Related Document ID",
    )
    record_name = fields.Char(
        string="Message Record Name",
        compute="_compute_record_name",
        store=False,
    )
    record_alias_domain_id: MailAliasDomain = fields.Many2one(
        comodel_name="mail.alias.domain",
        string="Alias Domain",
        ondelete="set null",
    )
    record_company_id: ResCompany = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        ondelete="set null",
    )
    message_type = fields.Selection(
        selection=[
            ("email", "Incoming Email"),
            ("comment", "Comment"),
            ("email_outgoing", "Outgoing Email"),
            ("notification", "System notification"),
            ("auto_comment", "Automated Targeted Notification"),
            ("out_of_office", "Out-of-office Message"),
            ("user_notification", "User Specific Notification"),
        ],
        string="Type",
        default="comment",
        required=True,
        help="Used to categorize message generator"
        "\n'email': generated by an incoming email e.g. mailgateway"
        "\n'comment': generated by user input e.g. through discuss or composer"
        "\n'email_outgoing': generated by a mailing"
        "\n'notification': generated by system e.g. tracking messages"
        "\n'auto_comment': generated by automated notification mechanism e.g. acknowledgment"
        "\n'user_notification': generated for a specific recipient",
    )
    subtype_id: MailMessageSubtype = fields.Many2one(
        comodel_name="mail.message.subtype",
        index=True,
        ondelete="set null",
    )
    mail_activity_type_id: MailActivityType = fields.Many2one(
        comodel_name="mail.activity.type",
        index="btree_not_null",
        ondelete="set null",
    )
    is_internal = fields.Boolean(
        string="Employee Only",
        help="Hide to public / portal users, independently from subtype configuration.",
    )
    email_from = fields.Char(
        string="From",
        help="Email address of the sender. This field is set when no matching partner is found and replaces the author_id field in the chatter.",
    )
    author_id: ResPartner = fields.Many2one(
        comodel_name="res.partner",
        index=True,
        ondelete="set null",
        help="Author of the message. If not set, email_from may hold an email address that did not match any partner.",
    )
    author_avatar = fields.Binary(
        related="author_id.avatar_128",
        string="Author's avatar",
        depends=["author_id"],
        readonly=False,
    )
    author_guest_id: MailGuest = fields.Many2one(
        comodel_name="mail.guest",
        string="Guest",
    )
    is_current_user_or_guest_author = fields.Boolean(
        compute="_compute_is_current_user_or_guest_author"
    )
    partner_ids: ResPartner = fields.Many2many(
        comodel_name="res.partner",
        string="Recipients",
        context={"active_test": False},
    )
    incoming_email_to = fields.Text(string="Emails To")
    incoming_email_cc = fields.Char(string="Emails Cc")
    outgoing_email_to = fields.Char(string="Outgoing Emails To")
    notified_partner_ids: ResPartner = fields.Many2many(
        comodel_name="res.partner",
        relation="mail_notification",
        string="Partners with Need Action",
        depends=["notification_ids"],
        copy=False,
        context={"active_test": False},
    )
    needaction = fields.Boolean(
        string="Need Action",
        compute="_compute_needaction",
        search="_search_needaction",
    )
    has_error = fields.Boolean(
        string="Has error",
        compute="_compute_has_error",
        search="_search_has_error",
    )
    notification_ids: MailNotification = fields.One2many(
        comodel_name="mail.notification",
        inverse_name="mail_message_id",
        string="Notifications",
        depends=["notified_partner_ids"],
        copy=False,
        bypass_search_access=True,
    )
    starred_partner_ids: ResPartner = fields.Many2many(
        comodel_name="res.partner",
        relation="mail_message_res_partner_starred_rel",
        string="Favorited By",
    )
    pinned_at = fields.Datetime(
        string="Pinned",
        help="Datetime at which the message has been pinned",
    )
    starred = fields.Boolean(
        compute="_compute_starred",
        search="_search_starred",
        compute_sudo=False,
        help="Current user has a starred notification linked to this message",
    )
    tracking_value_ids: MailTrackingValue = fields.One2many(
        comodel_name="mail.tracking.value",
        inverse_name="mail_message_id",
        string="Tracking values",
        groups="base.group_system",
        help="Tracked values are stored in a separate model. This field allow to reconstruct "
        "the tracking and to generate statistics on the model.",
    )
    reply_to_force_new = fields.Boolean(
        string="No threading for answers",
        help="If true, answers do not go in the original document discussion thread. Instead, it will check for the reply_to in tracking message-id and redirected accordingly. This has an impact on the generated message-id.",
    )
    message_id = fields.Char(
        string="Message-Id",
        index="btree",
        copy=False,
        readonly=True,
        help="Message unique identifier",
    )
    reply_to = fields.Char(
        string="Reply-To",
        help="Reply email address. Setting the reply_to bypasses the automatic thread creation.",
    )
    mail_server_id: IrMail_Server = fields.Many2one(
        comodel_name="ir.mail_server",
        string="Outgoing mail server",
    )
    email_layout_xmlid = fields.Char(
        string="Layout",
        copy=False,
    )
    email_add_signature = fields.Boolean(default=True)
    mail_ids: MailMail = fields.One2many(
        comodel_name="mail.mail",
        inverse_name="mail_message_id",
        string="Mails",
        groups="base.group_system",
    )

    _model_res_id_id_idx = models.Index("(model, res_id, id)")

    @api.depends("body")
    def _compute_preview(self) -> None:
        for message in self:
            plaintext_ct = tools.mail.html_to_inner_content(message.body)
            message.preview = self._shorten_preview(plaintext_ct)

    @api.model
    def _shorten_preview(self, text: str) -> str:
        collapsed = " ".join(text.split())
        if len(collapsed) <= PREVIEW_LENGTH:
            return collapsed
        shortened = textwrap.shorten(collapsed, PREVIEW_LENGTH)
        if shortened != PREVIEW_PLACEHOLDER:
            return shortened
        return (
            collapsed[: PREVIEW_LENGTH - len(PREVIEW_PLACEHOLDER)] + PREVIEW_PLACEHOLDER
        )

    def _get_linked_message_ids(self) -> dict[int, list[int]]:
        ids_by_message = defaultdict(list)
        for message in self:
            if not message.body or "o_message_redirect" not in message.body:
                continue
            str_ids = html.fromstring(message.body).xpath(
                "//a[contains(@class, 'o_message_redirect') and @data-oe-model='mail.message']/@data-oe-id",
            )
            for str_id in str_ids:
                with contextlib.suppress(ValueError, TypeError):
                    ids_by_message[message.id].append(int(str_id))
        return ids_by_message

    def _get_linked_messages(self) -> tuple[dict[int, Self], Self]:
        ids_by_message = self._get_linked_message_ids()
        mids = {mid for mids in ids_by_message.values() for mid in mids}
        if not mids:
            return {}, self.browse()
        linked_messages = self.sudo(False).search(Domain("id", "in", list(mids)))
        readable = set(linked_messages.ids)
        by_message = {}
        for message_id, linked_ids in ids_by_message.items():
            allowed = [mid for mid in linked_ids if mid in readable]
            if allowed:
                by_message[message_id] = linked_messages.browse(allowed)
        return by_message, linked_messages

    @api.depends("model", "res_id")
    def _compute_record_name(self) -> None:
        free = self.filtered(
            lambda m: not m.model or not m.res_id or m.model not in self.env
        )
        free.record_name = False
        for message, record in (self - free)._record_by_message().items():
            try:
                message.record_name = record.sudo().display_name
            except MissingError:
                message.record_name = False

    @api.depends("author_id", "author_guest_id")
    @api.depends_context("guest", "uid")
    def _compute_is_current_user_or_guest_author(self) -> None:
        user = self.env.user
        guest = self.env["mail.guest"]._get_guest_from_context()
        for message in self:
            if (
                not user._is_public()
                and (message.author_id and message.author_id == user.partner_id)
            ) or (message.author_guest_id and message.author_guest_id == guest):
                message.is_current_user_or_guest_author = True
            else:
                message.is_current_user_or_guest_author = False

    @api.depends("notification_ids")
    @api.depends_context("uid")
    def _compute_needaction(self) -> None:
        partner = self.env.user.partner_id
        for message in self:
            message.needaction = any(
                notification.res_partner_id == partner and not notification.is_read
                for notification in message.sudo().notification_ids
            )

    def _get_message_ids_with_notification(self, domain: DomainType) -> set[int]:
        return set(
            self.env["mail.notification"]
            .sudo()
            .search_fetch(
                [("mail_message_id", "in", self.ids), *domain],
                ["mail_message_id"],
            )
            .mail_message_id.ids
        )

    @api.model
    def _search_needaction(
        self, operator: str, operand: Any
    ) -> list | NotImplementedType:
        if operator != "in":
            return NotImplemented
        notification_ids = (
            self.env["mail.notification"]
            .sudo()
            ._search(
                [
                    ("res_partner_id", "=", self.env.user.partner_id.id),
                    ("is_read", "=", False),
                ]
            )
        )
        return [("notification_ids", "in", notification_ids)]

    @api.depends("notification_ids.notification_status")
    def _compute_has_error(self) -> None:
        failed = self._get_message_ids_with_notification(
            [("notification_status", "in", ("bounce", "exception"))]
        )
        for message in self:
            message.has_error = message.id in failed

    @api.model
    def _search_has_error(
        self, operator: str, operand: Any
    ) -> list | NotImplementedType:
        if operator != "in":
            return NotImplemented
        return [("notification_ids.notification_status", "in", ("bounce", "exception"))]

    @api.depends("starred_partner_ids")
    @api.depends_context("uid")
    def _compute_starred(self) -> None:
        partner = self.env.user.partner_id
        field = self._fields["starred_partner_ids"]
        cached = self.filtered(lambda message: self.env.cache.contains(message, field))
        for message in cached:
            message.starred = partner in message.sudo().starred_partner_ids
        if uncached := self - cached:
            rows = self.env.execute_query(
                SQL(
                    """ SELECT mail_message_id
                        FROM mail_message_res_partner_starred_rel
                        WHERE mail_message_id = ANY(%s) AND res_partner_id = %s """,
                    uncached.ids,
                    partner.id,
                )
            )
            starred_ids = {mid for [mid] in rows}
            for message in uncached:
                message.starred = message.id in starred_ids

    @api.model
    def _search_starred(self, operator: str, operand: Any) -> list | NotImplementedType:
        if operator != "in":
            return NotImplemented
        return [("starred_partner_ids", "in", self.env.user.partner_id.ids)]

    def _is_thread_model(self) -> bool:
        self.check_singleton()
        return self._is_thread_model_name(self.sudo().model)

    @api.model
    def _is_thread_model_name(self, model_name: str) -> bool:
        return bool(model_name) and isinstance(
            self.env.get(model_name), self.pool["mixin.mail.thread"]
        )

    def _get_thread_model(self) -> models.Model:
        self.check_singleton()
        return self.env[
            self.sudo().model if self._is_thread_model() else "mixin.mail.thread"
        ]

    @api.model
    def _get_with_access(self, message_id: int, mode: str = "read", **kwargs) -> Self:
        message = self.browse(message_id).exists()
        if not message:
            return message

        allowed_params = message._get_thread_model()._get_allowed_access_params()
        if invalid := (set(kwargs) - allowed_params):
            _logger.debug("Ignoring parameters to _get_with_access: %s", invalid)
            kwargs = {
                key: value for key, value in kwargs.items() if key in allowed_params
            }

        if (
            self.env.user._is_public()
            and self.env["mail.guest"]._get_guest_from_context()
        ):
            if not message.sudo(False)._get_forbidden_access(mode):
                _debug.logic("access", message=message_id, mode=mode, by="guest")
                return message
        elif message.sudo(False).has_access(mode):
            return message

        if (
            mode == "read"
            and not self.env.user._is_internal()
            and message.sudo(False)._get_forbidden_internal(mode)
        ):
            _debug.logic("access_refused", message=message_id, mode=mode, by="internal")
            return self.browse()

        if message.res_id and message._is_thread_model():
            thread_su = self.env[message.model].browse(message.res_id).sudo()
            access_mode = thread_su._mail_get_operation_for_mail_message_operation(
                mode
            ).get(thread_su)
            if access_mode and self.env[message.model]._get_thread_with_access(
                message.res_id, mode=access_mode, **kwargs
            ):
                _debug.logic(
                    "access",
                    message=message_id,
                    mode=mode,
                    by="thread",
                    thread_mode=access_mode,
                )
                return message

        _debug.logic("access_refused", message=message_id, mode=mode, by="thread")
        return self.browse()

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        vals_list = [dict(values) for values in vals_list]
        if not (self.env.su or self.env.user.has_group("base.group_user")):
            _debug.logic(
                "author_fields_stripped", count=len(vals_list), uid=self.env.uid
            )
            for values in vals_list:
                for field_name in self._AUTHOR_FIELD_NAMES:
                    values.pop(field_name, None)
            self = self.with_context(
                {
                    k: v
                    for k, v in self.env.context.items()
                    if k not in ["default_author_id", "default_email_from"]
                }
            )

        self._update_email_from(vals_list)

        reply_tos = self._get_reply_to_batch(vals_list)
        tracking_values_list = []
        for index, values in enumerate(vals_list):
            if not values.get("message_id"):
                values["message_id"] = self._get_message_id(values)
            if "reply_to" not in values:
                values["reply_to"] = reply_tos[index]
            if not values.get("attachment_ids", True):
                del values["attachment_ids"]
            if "body" in values:
                values["body"], inline_commands = self._extract_body_attachments(
                    values, *self._get_thread_target(values)
                )
                if inline_commands:
                    values["attachment_ids"] = [
                        *values.get("attachment_ids", ()),
                        *inline_commands,
                    ]
            tracking_values_list.append(values.pop("tracking_value_ids", False))

        visible = [
            (values["model"], values["res_id"])
            for values in vals_list
            if self._is_thread_message_visible(vals=values)
        ]
        self._invalidate_documents(visible)
        messages = super().create(vals_list)

        self._check_created_attachments_access(messages, vals_list)

        commands_per_message = {
            message: tracking_values_cmd
            for message, tracking_values_cmd in zip(
                messages, tracking_values_list, strict=True
            )
            if tracking_values_cmd
        }
        if commands_per_message:
            self._create_tracking_values(commands_per_message)

        _debug.lifecycle(
            "create",
            count=len(messages),
            visible=len(visible),
            tracked=len(commands_per_message),
            types=sorted({values.get("message_type") or "" for values in vals_list}),
        )
        return messages

    def _update_email_from(self, vals_list: list[ValuesType]) -> None:
        pending = [values for values in vals_list if "email_from" not in values]
        if not pending:
            return
        self._prefetch_authors(pending, "email_formatted")
        for values in pending:
            self._update_author(values, author=False)

    def _prefetch_authors(self, vals_list: list[ValuesType], *field_names: str) -> None:
        authors = OrderedSet(
            values["author_id"] for values in vals_list if values.get("author_id")
        )
        if authors:
            self.env["res.partner"].sudo().browse(authors).fetch(list(field_names))

    @api.model
    def _get_thread_target(
        self, values: dict
    ) -> tuple[str | None, int | Literal[False]]:
        model = values.get("model", self.env.context.get("default_model"))
        res_id = values.get("res_id", self.env.context.get("default_res_id")) or False
        if model and model not in self.env:
            _logger.warning(
                "mail.message created with a model that is not in the registry: %s",
                model,
            )
            model, res_id = None, False
        if not self._is_thread_message(vals={"model": model, "res_id": res_id}):
            res_id = False
        return model, res_id

    def _get_reply_to_batch(self, vals_list: list[ValuesType]) -> list:
        out: list = [None] * len(vals_list)
        by_group = defaultdict(list)
        for index, values in enumerate(vals_list):
            if "reply_to" in values:
                continue
            model, res_id = self._get_thread_target(values)
            by_group[(model, bool(res_id))].append((index, res_id, values))

        self._prefetch_authors(
            [values for items in by_group.values() for _i, _r, values in items], "name"
        )

        for (model, is_thread), items in by_group.items():
            if is_thread:
                records = self.env[model].browse(
                    {res_id for _index, res_id, _values in items}
                )
            else:
                records = self.env[model] if model else self.env["mixin.mail.thread"]
            records_su = records.sudo()
            addresses = records_su._notify_get_reply_to_addresses()
            for index, res_id, values in items:
                address = addresses.get(res_id)
                out[index] = (
                    records_su._notify_get_reply_to_formatted_email(
                        address, author_id=values.get("author_id")
                    )
                    if address
                    else values.get("email_from")
                )
        return out

    def _extract_body_attachments(
        self,
        values: ValuesType,
        model: str | None = None,
        res_id: int | Literal[False] = False,
    ) -> tuple[str, list[tuple[int, int]]]:
        Attachments = self.env["ir.attachment"].with_context(
            clean_context(self.env.context)
        )
        commands: list[tuple[int, int]] = []
        data_to_url = {}

        def base64_to_boundary(match: re.Match) -> str:
            key = match.group(2)
            if not data_to_url.get(key):
                name = match.group(4) or "image%s" % len(data_to_url)
                try:
                    attachment = Attachments.create(
                        {
                            "name": name,
                            "datas": match.group(2),
                            "res_model": model,
                            "res_id": res_id,
                        }
                    )
                except binascii_error:
                    _debug.logic("inline_image_rejected", model=model, record=res_id)
                    _logger.warning(
                        "Impossible to create an attachment out of badly formated base64 embedded image. Image has been removed."
                    )
                    return match.group(3)
                else:
                    attachment.generate_access_token()
                    commands.append((4, attachment.id))
                    data_to_url[key] = [
                        "/web/image/%s?access_token=%s"
                        % (attachment.id, attachment.access_token),
                        name,
                        attachment.id,
                    ]
            return f'{data_to_url[key][0]}{match.group(3)} alt="{data_to_url[key][1]}" data-attachment-id="{data_to_url[key][2]}"'

        body = _image_dataurl.sub(base64_to_boundary, values["body"] or "")
        if _debug.pipeline.enabled and commands:
            _debug.pipeline(
                "inline_images_extracted",
                model=model,
                record=res_id,
                attachments=len(commands),
            )
        return body, commands

    def _check_created_attachments_access(
        self, messages: Self, vals_list: list[ValuesType]
    ) -> None:
        doc_to_attachment_ids = defaultdict(set)
        opaque_messages = self.browse()
        for message, values in zip(messages, vals_list, strict=True):
            commands = values.get("attachment_ids", ())
            if not all(
                isinstance(command, int) or command[0] in (4, 6) for command in commands
            ):
                opaque_messages |= message
                continue
            message_attachment_ids = set()
            for command in commands:
                if isinstance(command, int):
                    message_attachment_ids.add(command)
                elif command[0] == 6:
                    message_attachment_ids |= set(command[2])
                else:
                    message_attachment_ids.add(command[1])
            if message_attachment_ids:
                key = (values.get("model"), values.get("res_id"))
                doc_to_attachment_ids[key] |= message_attachment_ids

        if opaque_messages.attachment_ids:
            opaque_messages.attachment_ids.check_access("read")
        if not doc_to_attachment_ids:
            return

        attachment_ids_all = {
            attachment_id
            for doc_attachment_ids in doc_to_attachment_ids.values()
            for attachment_id in doc_attachment_ids
        }
        AttachmentSudo = (
            self.env["ir.attachment"].sudo().with_prefetch(list(attachment_ids_all))
        )
        foreign_ids = OrderedSet()
        for (model, res_id), doc_attachment_ids in doc_to_attachment_ids.items():
            foreign_ids.update(
                AttachmentSudo.browse(doc_attachment_ids)
                .filtered(
                    lambda att, model=model, res_id=res_id: (
                        att.res_model != model or att.res_id != res_id
                    )
                )
                ._ids
            )
        _debug.logic(
            "created_attachments_checked",
            messages=len(messages),
            opaque=len(opaque_messages),
            attachments=len(attachment_ids_all),
            foreign=len(foreign_ids),
        )
        if foreign_ids:
            self.env["ir.attachment"].browse(foreign_ids).check_access("read")

    @api.model
    def _create_tracking_values(self, commands_per_message: dict) -> None:
        vals_list = []
        for message, tracking_values_cmd in commands_per_message.items():
            vals_list += [
                dict(cmd[2], mail_message_id=message.id)
                for cmd in tracking_values_cmd
                if len(cmd) == 3 and cmd[0] == 0
            ]
            other_cmd = [
                cmd for cmd in tracking_values_cmd if len(cmd) != 3 or cmd[0] != 0
            ]
            if other_cmd:
                message.sudo().write({"tracking_value_ids": other_cmd})
        _debug.lifecycle(
            "tracking_values_created",
            messages=len(commands_per_message),
            values=len(vals_list),
        )
        if vals_list:
            self.env["mail.tracking.value"].sudo().create(vals_list)

    def read(
        self, fields: Sequence[str] | None = None, load: str = "_classic_read"
    ) -> list[dict]:
        self.check_access("read")
        return super().read(fields=fields, load=load)

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        self.check_access("read")
        return super().copy_data(default=default)

    @api.constrains("partner_ids")
    def _check_thread_allows_partner_ids(self) -> None:
        empty = self.browse()
        messages_by_model = defaultdict(lambda: empty)
        for message in self:
            if message.model and message.res_id:
                messages_by_model[message.model] += message
        for model_name, messages in messages_by_model.items():
            model = self.env.get(model_name)
            check = getattr(model, "_check_thread_message_partner_ids", None)
            if check is not None:
                check(messages)

    def fetch(self, field_names: Collection[str] | None = None) -> None:
        if not self.env.su and self.env.user.share:
            if forbidden := self._get_forbidden_access("read"):
                raise AccessError(
                    _(
                        "You cannot read the following messages: %(ids)s",
                        ids=", ".join(str(mid) for mid in forbidden.ids),
                    )
                )
        return super(MailMessage, self.sudo()).fetch(field_names)

    def write(self, vals: ValuesType) -> Literal[True]:
        if not (self.env.su or self.env.user.has_group("base.group_user")):
            vals = {
                key: value
                for key, value in vals.items()
                if key not in self._ENVELOPE_FIELD_NAMES
            }
        record_changed = "model" in vals or "res_id" in vals
        if record_changed and not self.env.is_system():
            _debug.logic("write_refused", messages=self.ids, reason="record_change")
            raise AccessError(
                _("Only administrators can modify 'model' and 'res_id' fields.")
            )
        if vals.get("parent_id") and not self.env.is_system():
            self._check_parent_on_same_document(vals["parent_id"])
        _debug.lifecycle(
            "write", count=len(self), fields=list(vals), record_changed=record_changed
        )
        if record_changed or "message_type" in vals:
            self._invalidate_documents()
        res = super().write(vals)
        if vals.get("attachment_ids"):
            self.attachment_ids.check_access("read")
        if "notification_ids" in vals or record_changed:
            self._invalidate_documents()
        return res

    def _check_parent_on_same_document(self, parent_id: int) -> None:
        parent = self.sudo().browse(parent_id)
        for message in self.sudo():
            if (parent.model, parent.res_id) != (message.model, message.res_id):
                raise AccessError(
                    _("A message can only reply to a message of the same document.")
                )

    def unlink(self) -> Literal[True]:
        if not self:
            return True
        self.check_access("unlink")
        own_ids = set(self._ids)
        self.mapped("attachment_ids").filtered(
            lambda attach: (
                attach.res_model == self._name
                and (attach.res_id in own_ids or attach.res_id == 0)
            )
        ).unlink()
        message_ids_by_partner = defaultdict(OrderedSet)
        partners_with_user = self.partner_ids.filtered("user_ids")
        for elem in self:
            for partner in (
                elem.partner_ids & partners_with_user | elem.notification_ids.author_id
            ):
                message_ids_by_partner[partner].add(elem.id)
        for partner, message_ids in message_ids_by_partner.items():
            partner._bus_send("mail.message/delete", {"message_ids": list(message_ids)})
        _debug.lifecycle(
            "unlink", count=len(self), notified_partners=len(message_ids_by_partner)
        )
        return super(MailMessage, self.sudo()).unlink()

    def export_data(self, fields_to_export: list[str]) -> dict:
        if not self.env.is_admin():
            raise AccessError(
                _("Only administrators are allowed to export mail message")
            )

        return super().export_data(fields_to_export)

    def action_view_document(self) -> dict:
        self.check_singleton()
        if not self._is_thread_message() or self.sudo().model not in self.env:
            raise UserError(self.env._("This message is not attached to a document."))
        return {
            "res_id": self.res_id,
            "res_model": self.model,
            "target": "current",
            "type": "ir.actions.act_window",
            "view_mode": "form",
        }

    @api.model
    def mark_all_as_read(self, domain: DomainType | None = None) -> list[int]:
        notification_domain = [("res_partner_id", "=", self.env.user.partner_id.id)]
        if domain:
            notification_domain.append(
                (
                    "mail_message_id",
                    "in",
                    self._search(Domain(domain), bypass_access=True),
                )
            )
        return self.browse()._mark_notifications_read(notification_domain)

    def set_message_done(self) -> list[int]:
        return self._mark_notifications_read(
            [
                ("mail_message_id", "in", self.ids),
                ("res_partner_id", "=", self.env.user.partner_id.id),
            ]
        )

    def _mark_notifications_read(self, domain) -> list[int]:
        notifications = (
            self.env["mail.notification"]
            .sudo()
            .search_fetch([*domain, ("is_read", "=", False)], ["mail_message_id"])
        )
        if not notifications:
            return []
        notifications.write({"is_read": True})
        message_ids = notifications.mail_message_id.ids
        _debug.lifecycle(
            "notifications_read",
            partner=self.env.user.partner_id.id,
            notifications=len(notifications),
            messages=len(message_ids),
        )
        self.env.user._bus_send(
            "mail.message/mark_as_read",
            {
                "message_ids": message_ids,
                "needaction_inbox_counter": self.env.user.partner_id._get_needaction_count(),
            },
        )
        return message_ids

    @api.model
    def unstar_all(self) -> None:
        starred_messages = self.sudo().search(
            [("starred_partner_ids", "in", self.env.user.partner_id.id)]
        )
        starred_messages.starred_partner_ids = [
            Command.unlink(self.env.user.partner_id.id)
        ]
        _debug.lifecycle(
            "unstar_all",
            partner=self.env.user.partner_id.id,
            count=len(starred_messages),
        )
        self.env.user._bus_send(
            "mail.message/toggle_star",
            {"message_ids": starred_messages.ids, "starred": False},
        )

    def toggle_message_starred(self) -> dict:
        self.check_singleton()
        self.check_access("read")
        starred = not self.starred
        _debug.lifecycle("star_toggled", message=self.id, starred=starred)
        if starred:
            self.sudo().starred_partner_ids = [
                Command.link(self.env.user.partner_id.id)
            ]
        else:
            self.sudo().starred_partner_ids = [
                Command.unlink(self.env.user.partner_id.id)
            ]
        Store(bus_channel=self.env.user).add(self).bus_send()
        self.env.user._bus_send(
            "mail.message/toggle_star", {"message_ids": [self.id], "starred": starred}
        )
        return Store().add(self, {"starred": starred}).get_result()

    def _message_reaction(
        self,
        content: str,
        action: str,
        partner: ResPartner,
        guest: MailGuest,
        store: Store | None = None,
    ) -> None:
        self.check_singleton()
        if action not in ("add", "remove"):
            raise ValueError(f"Wrong reaction action ({action})")
        if (
            not content
            or not content.strip()
            or len(content) > REACTION_CONTENT_MAX_LENGTH
        ):
            raise ValueError("Wrong reaction content")
        group = self._reaction_group(content)
        own = group.filtered(
            lambda reaction: (
                reaction.partner_id == partner and reaction.guest_id == guest
            )
        )
        if action == "add" and not own:
            create_values = {
                "message_id": self.id,
                "content": content,
                "partner_id": partner.id,
                "guest_id": guest.id,
            }
            try:
                with self.env.cr.savepoint():
                    group |= self.env["mail.message.reaction"].create(create_values)
            except UniqueViolation:
                _debug.logic("reaction_duplicate", message=self.id, content=content)
                group = self._reaction_group(content)
        if action == "remove" and own:
            own.unlink()
            group -= own
        _debug.lifecycle(
            "reaction",
            message=self.id,
            action=action,
            content=content,
            partner=partner.id or None,
            guest=guest.id or None,
            group=len(group),
        )
        if store:
            self._reaction_group_to_store(store, content, group)
        self._bus_send_reaction_group(content, group)

    def _reaction_group(self, content: str) -> MailMessageReaction:
        return (
            self.env["mail.message.reaction"]
            .search_fetch(
                [("message_id", "=", self.id), ("content", "=", content)],
                ["partner_id", "guest_id"],
            )
            .sorted("id", reverse=True)
        )

    def _bus_send_reaction_group(
        self, content: str, group: MailMessageReaction | None = None
    ) -> None:
        store = Store(bus_channel=self._bus_channel())
        self._reaction_group_to_store(store, content, group)
        store.bus_send()

    def _reaction_group_to_store(
        self, store: Store, content: str, group: MailMessageReaction | None = None
    ) -> None:
        reactions = self._reaction_group(content) if group is None else group
        reaction_group = (
            Store.Many(reactions, mode="ADD")
            if reactions
            else [("DELETE", {"message": self.id, "content": content})]
        )
        store.add(self, {"reactions": reaction_group})

    def _bus_channel(self) -> models.Model:
        self.check_singleton()
        return self.env.user

    def _filtered_empty(self) -> Self:
        return self.filtered(lambda message: message._is_empty())

    def _is_empty(self) -> bool:
        self.check_singleton()
        return (
            (not self.body or tools.is_html_empty(self.body))
            and (not self.subtype_id or not self.subtype_id.description)
            and not self.attachment_ids
            and not (
                self._has_field_access(self._fields["tracking_value_ids"], "read")
                and self.tracking_value_ids
            )
        )

    @api.model
    def _get_reply_to(self, values: dict) -> str:
        if "reply_to" in values:
            return values["reply_to"]
        return self._get_reply_to_batch([values])[0]

    @api.model
    def _get_message_id(self, values: dict) -> str:
        if values.get("reply_to_force_new"):
            return tools.mail.generate_tracking_message_id("reply_to")
        model, res_id = self._get_thread_target(values)
        if res_id:
            return tools.mail.generate_tracking_message_id(f"{res_id}-{model}")
        return tools.mail.generate_tracking_message_id("private")

    def _is_thread_message(
        self, vals: ValuesType | None = None, thread: models.Model | None = None
    ) -> bool:
        vals = vals or {}
        if "model" in vals:
            res_model = vals["model"]
        elif thread:
            res_model = thread._name
        else:
            res_model = self.model
        if "res_id" in vals:
            res_id = vals["res_id"]
        elif thread and thread.ids:
            res_id = thread.ids[0]
        else:
            res_id = self.res_id
        return (
            bool(res_id) if (res_model and res_model != "mixin.mail.thread") else False
        )

    def _is_thread_message_visible(
        self, vals: ValuesType | None = None, thread: models.Model | None = None
    ) -> bool:
        if not self._is_thread_message(vals=vals, thread=thread):
            return False
        if vals and "message_type" in vals:
            message_type = vals["message_type"]
        else:
            message_type = self.message_type
        return message_type != "user_notification"

    _NOTIFICATION_STATE_FIELD_NAMES = (
        "message_needaction",
        "message_needaction_counter",
        "message_has_error",
        "message_has_error_counter",
    )

    def _invalidate_notification_state(self) -> None:
        for model_name in set(self.mapped("model")):
            if self._is_thread_model_name(model_name):
                self.env[model_name].invalidate_model(
                    self._NOTIFICATION_STATE_FIELD_NAMES
                )

    def _invalidate_documents(
        self, documents: list[tuple[str, int]] | None = None
    ) -> None:
        fnames = ["message_ids", *self._NOTIFICATION_STATE_FIELD_NAMES]
        if documents is None:
            self.flush_recordset(["model", "res_id"])
            documents = [(record.model, record.res_id) for record in self]
        ids_by_model = defaultdict(OrderedSet)
        for model_name, res_id in documents:
            if res_id and self._is_thread_model_name(model_name):
                ids_by_model[model_name].add(res_id)
        _debug.perf.count(
            "documents_invalidated",
            messages=len(self),
            models=len(ids_by_model),
            records=sum(len(ids) for ids in ids_by_model.values()),
        )
        for rec_model, rec_ids in ids_by_model.items():
            self.env[rec_model].browse(rec_ids).invalidate_recordset(fnames)

    def _thread_pointers(self) -> list[tuple[Self, str, int]]:
        return [
            (message, message.model, message.res_id)
            for message in self
            if message.model in self.env and message.res_id
        ]

    def _prefetch_thread_pointers(self) -> list[tuple[str, int]]:
        own_ids = set(self._ids)
        peers = self.browse([mid for mid in self._prefetch_ids if mid not in own_ids])
        if not peers:
            return []
        try:
            return [(model, res_id) for _msg, model, res_id in peers._thread_pointers()]
        except MissingError:
            return [
                (model, res_id)
                for _msg, model, res_id in peers.exists()._thread_pointers()
            ]

    def _records_by_model_name(self) -> dict:
        ids_by_model = defaultdict(OrderedSet)
        prefetch_ids_by_model = defaultdict(OrderedSet)
        for _message, model, res_id in self._thread_pointers():
            ids_by_model[model].add(res_id)
        for model, res_id in self._prefetch_thread_pointers():
            prefetch_ids_by_model[model].add(res_id)
        return {
            model_name: self.env[model_name]
            .browse(ids)
            .with_prefetch(tuple(ids | prefetch_ids_by_model[model_name]))
            for model_name, ids in ids_by_model.items()
        }

    def _record_by_message(self) -> dict:
        records_by_model_name = self._records_by_model_name()
        return {
            message: self.env[model]
            .browse(res_id)
            .with_prefetch(records_by_model_name[model]._prefetch_ids)
            for message, model, res_id in self._thread_pointers()
        }
