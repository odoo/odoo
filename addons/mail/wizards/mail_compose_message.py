import ast
import base64
import itertools
import json
import typing
from collections.abc import Collection
from typing import Any, Literal

from odoo import Command, _, api, fields, models, tools
from odoo.api import ValuesType
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools.mail import (
    email_normalize,
    email_normalize_all,
    email_split_and_format,
    is_html_empty,
)
from odoo.tools.misc import clean_context

from ..models.mail_template import (
    ATTACHMENT_FIELD_NAMES,
    DYNAMIC_FIELD_NAMES,
    RECIPIENT_FIELD_NAMES,
)
from odoo.addons.mail.tools.parser import parse_res_ids
from odoo.addons.mail.tools.recipients import prepare_recipient_data

if typing.TYPE_CHECKING:
    from ..models.ir_mail_server import IrMail_Server
    from ..models.mail_activity_type import MailActivityType
    from ..models.mail_alias_domain import MailAliasDomain
    from ..models.mail_mail import MailMail
    from ..models.mail_message import MailMessage
    from ..models.mail_message_subtype import MailMessageSubtype
    from ..models.mail_scheduled_message import MailScheduledMessage
    from ..models.mail_template import MailTemplate
    from ..models.res_partner import ResPartner
    from odoo.addons.base.models.res_company import ResCompany
    from odoo.addons.bus.models.ir_attachment import IrAttachment
    from odoo.addons.bus.models.res_users import ResUsers

_debug = DebugLog(__name__)

COMPOSER_FIELD_TO_TEMPLATE_FIELD = {
    "attachments": "report_template_ids",
    "body": "body_html",
    "partner_ids": "partner_to",
}

TEMPLATE_FIELD_TO_COMPOSER_FIELD = {"body_html": "body"}

TEMPLATE_RENDER_FIELDS = DYNAMIC_FIELD_NAMES - RECIPIENT_FIELD_NAMES

SENT_EMAILS_MAPPING_CONTEXT_KEY = "mail_composer_sent_emails_mapping"


def _reopen(self, res_id: int, model: str, context: dict | None = None) -> dict:
    context = dict(context or {}, default_model=model)
    return {
        "name": _("Compose Email"),
        "type": "ir.actions.act_window",
        "view_mode": "form",
        "res_id": res_id,
        "res_model": self._name,
        "target": "new",
        "context": context,
    }


class MailComposeMessage(models.TransientModel):
    _name = "mail.compose.message"
    _inherit = ["mixin.mail.composer"]
    _description = "Email composition wizard"
    _log_access = True
    _batch_size = 50

    @api.model
    def default_get(self, fields: list[str]) -> ValuesType:
        composer = self
        if self.env.context.get("default_subtype_xmlid"):
            composer = composer.with_context(
                default_subtype_id=self.env["ir.model.data"]._xmlid_to_res_id(
                    self.env.context["default_subtype_xmlid"]
                )
            )
        if "default_res_id" in self.env.context:
            raise ValueError(
                "Deprecated usage of 'default_res_id', should use 'default_res_ids'."
            )
        if (
            "body" in fields
            and self.env.context.get("default_body")
            and self.env.context.get("body_contains_signature_only")
            and super().default_get(["template_id"]).get("template_id")
        ):
            ctx = dict(composer.env.context)
            ctx.pop("default_body", None)
            composer = composer.with_context(ctx)

        result = super(MailComposeMessage, composer).default_get(fields)

        if "create_uid" in fields and "create_uid" not in result:
            result["create_uid"] = self.env.uid

        return {fname: result[fname] for fname in result if fname in fields}

    subject = fields.Char(
        compute="_compute_subject",
        store=True,
        readonly=False,
    )
    body = fields.Html(
        string="Contents",
        sanitize_style=True,
        compute="_compute_body",
        store=True,
        readonly=False,
        render_engine="qweb",
        render_options={"post_process": True},
    )
    parent_id: MailMessage = fields.Many2one(
        comodel_name="mail.message",
        string="Parent Message",
        ondelete="set null",
    )
    template_id: MailTemplate = fields.Many2one(
        comodel_name="mail.template",
        string="Use template",
        domain="[('model', '=', model), '|', ('user_id','=', False), ('user_id', '=', uid)]",
    )
    template_render_values = fields.Json(compute="_compute_template_render_values")
    template_render_attachments = fields.Json(
        compute="_compute_template_render_attachments"
    )
    lang = fields.Char(precompute=False)
    attachment_ids: IrAttachment = fields.Many2many(
        comodel_name="ir.attachment",
        relation="mail_compose_message_ir_attachments_rel",
        column1="wizard_id",
        column2="attachment_id",
        string="Attachments",
        compute="_compute_attachment_ids",
        store=True,
        readonly=False,
        bypass_search_access=True,
    )
    email_layout_xmlid = fields.Char(
        string="Email Notification Layout",
        compute="_compute_email_layout_xmlid",
        compute_sudo=False,
        store=True,
        copy=False,
        readonly=False,
    )
    email_add_signature = fields.Boolean(
        string="Add signature",
        compute="_compute_email_add_signature",
        store=True,
        readonly=False,
    )
    email_from = fields.Char(
        string="From",
        compute="_compute_authorship",
        compute_sudo=False,
        store=True,
        readonly=False,
        help="Email address of the sender. This field is set when no matching partner is found and replaces the author_id field in the chatter.",
    )
    author_id: ResPartner = fields.Many2one(
        comodel_name="res.partner",
        compute="_compute_authorship",
        compute_sudo=False,
        store=True,
        readonly=False,
        help="Author of the message. If not set, email_from may hold an email address that did not match any partner.",
    )
    composition_mode = fields.Selection(
        selection=[
            ("comment", "Post on a document"),
            ("mass_mail", "Email Mass Mailing"),
        ],
        string="Composition mode",
        default="comment",
    )
    composition_batch = fields.Boolean(
        string="Batch composition",
        compute="_compute_composition_batch",
    )
    composition_comment_option = fields.Selection(
        selection=[("reply_all", "Reply-All"), ("forward", "Forward")],
        string="Comment Options",
    )
    model = fields.Char(
        string="Related Document Model",
        compute="_compute_model",
        store=True,
        readonly=False,
    )
    model_is_thread = fields.Boolean(
        string="Thread-Enabled",
        compute="_compute_model_is_thread",
    )
    res_ids = fields.Text(
        string="Related Document IDs",
        compute="_compute_res_ids",
        store=True,
        readonly=False,
    )
    res_domain = fields.Text(string="Active domain")
    res_domain_user_id: ResUsers = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        help="Used as context used to evaluate composer domain",
    )
    record_alias_domain_id: MailAliasDomain = fields.Many2one(
        comodel_name="mail.alias.domain",
        string="Alias Domain",
        compute="_compute_record_environment",
        store=True,
        readonly=False,
    )
    record_company_id: ResCompany = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        compute="_compute_record_environment",
        store=True,
        readonly=False,
    )
    message_type = fields.Selection(
        selection=[
            ("auto_comment", "Automated Targeted Notification"),
            ("comment", "Comment"),
            ("notification", "System notification"),
        ],
        string="Type",
        default="comment",
        required=True,
        help="Message type: email for email message, notification for system "
        "message, comment for other messages such as user replies",
    )
    subtype_id: MailMessageSubtype = fields.Many2one(
        comodel_name="mail.message.subtype",
        compute="_compute_subtype_id",
        store=True,
        readonly=False,
        ondelete="set null",
    )
    subtype_is_log = fields.Boolean(
        string="Is a log",
        compute="_compute_subtype_is_log",
    )
    mail_activity_type_id: MailActivityType = fields.Many2one(
        comodel_name="mail.activity.type",
        ondelete="set null",
    )
    reply_to = fields.Char(
        compute="_compute_reply_to",
        compute_sudo=False,
        store=True,
        readonly=False,
        help="Reply email address. Setting the reply_to bypasses the automatic thread creation.",
    )
    reply_to_force_new = fields.Boolean(
        string="Considers answers as new thread",
        compute="_compute_reply_to_force_new",
        store=True,
        readonly=False,
        help="Manage answers as new incoming emails instead of replies going to the same thread.",
    )
    reply_to_mode = fields.Selection(
        selection=[
            ("update", "Store email and replies in the chatter of each record"),
            ("new", "Collect replies on a specific email address"),
        ],
        string="Replies",
        compute="_compute_reply_to_mode",
        inverse="_inverse_reply_to_mode",
        help="Original Discussion: Answers go in the original document discussion thread. \n Another Email Address: Answers go to the email address mentioned in the tracking message-id instead of original document discussion thread. \n This has an impact on the generated message-id.",
    )
    partner_ids: ResPartner = fields.Many2many(
        comodel_name="res.partner",
        relation="mail_compose_message_res_partner_rel",
        column1="wizard_id",
        column2="partner_id",
        string="Additional Contacts",
        compute="_compute_partner_ids",
        store=True,
        readonly=False,
    )
    partner_ids_all_have_email = fields.Boolean(
        compute="_compute_partner_ids_all_have_email"
    )
    notified_bcc_contains_share = fields.Boolean(
        string="Is an external partner follower of the document?",
        compute="_compute_notified_bcc_contains_share",
    )
    auto_delete = fields.Boolean(
        string="Delete Emails",
        compute="_compute_auto_delete",
        compute_sudo=False,
        store=True,
        readonly=False,
        help="This option permanently removes any track of email after it's been sent, including from the Technical menu in the Settings, in order to preserve storage space of your Odoo database.",
    )
    auto_delete_keep_log = fields.Boolean(
        string="Keep Message Copy",
        compute="_compute_auto_delete_keep_log",
        store=True,
        readonly=False,
        help="Keep a copy of the email content if emails are removed (mass mailing only)",
    )
    force_send = fields.Boolean(
        string="Send mailing or notifications directly",
        compute="_compute_force_send",
        store=True,
        readonly=False,
    )
    mail_server_id: IrMail_Server = fields.Many2one(
        comodel_name="ir.mail_server",
        string="Outgoing mail server",
        compute="_compute_mail_server_id",
        compute_sudo=False,
        store=True,
        readonly=False,
    )
    notify_author = fields.Boolean(
        compute="_compute_notify_author",
        store=True,
        readonly=False,
    )
    notify_author_mention = fields.Boolean(
        compute="_compute_notify_author_mention",
        store=True,
        readonly=False,
    )
    notify_skip_followers = fields.Boolean(
        compute="_compute_notify_skip_followers",
        store=True,
        readonly=False,
    )
    scheduled_date = fields.Char(
        compute="_compute_scheduled_date",
        compute_sudo=False,
        store=True,
        readonly=False,
        help="In comment mode: if set, postpone notifications sending. "
        "In mass mail mode: if sent, send emails after that date. "
        "This date is considered as being in UTC timezone.",
    )
    use_exclusion_list = fields.Boolean(
        default=True,
        copy=False,
        help="Prevent sending messages to blacklisted contacts. Disable only when absolutely necessary.",
    )
    template_name = fields.Char()

    @api.constrains("res_ids")
    def _check_res_ids(self) -> None:
        for composer in self:
            composer._evaluate_res_ids()

    @api.constrains("res_domain")
    def _check_res_domain(self) -> None:
        for composer in self:
            composer._evaluate_res_domain()

    @api.depends(
        "composition_mode", "model", "parent_id", "res_domain", "res_ids", "template_id"
    )
    def _compute_subject(self) -> None:
        for composer in self:
            if composer.template_id:
                composer._update_value_from_template("subject")
            if not composer.template_id or not composer.subject:
                subject = composer.parent_id.subject
                if (
                    not subject
                    and composer.model
                    and composer.composition_mode == "comment"
                    and not composer.composition_batch
                ):
                    res_ids = composer._evaluate_res_ids()
                    if res_ids and composer.model_is_thread:
                        subject = (
                            self.env[composer.model]
                            .browse(res_ids)
                            ._message_compute_subject()
                        )
                    elif res_ids:
                        subject = self.env[composer.model].browse(res_ids).display_name
                composer.subject = subject

    @api.depends("composition_mode", "model", "res_domain", "res_ids", "template_id")
    def _compute_body(self) -> None:
        for composer in self:
            if composer.template_id:
                composer._update_value_from_template("body_html", "body")
            if not composer.template_id:
                composer.body = False

    @api.depends("composition_mode", "model", "res_domain", "res_ids", "template_id")
    def _compute_template_render_values(self) -> None:
        for composer in self:
            values = composer._render_template_fields(TEMPLATE_RENDER_FIELDS)
            if values and (scheduled_date := values.get("scheduled_date")):
                values["scheduled_date"] = fields.Datetime.to_string(scheduled_date)
            composer.template_render_values = values

    @api.depends("composition_mode", "model", "res_domain", "res_ids", "template_id")
    def _compute_template_render_attachments(self) -> None:
        for composer in self:
            values = composer._render_template_fields(ATTACHMENT_FIELD_NAMES)
            if values and (attachments := values.get("attachments")):
                values["attachments"] = [
                    [name, datas.decode()] for name, datas in attachments
                ]
            composer.template_render_attachments = values

    def _render_template_fields(self, fnames) -> dict | Literal[False]:
        """Render the template's `fnames` for the composer's one record.

        Attachments render apart from the text fields: a report renders its page,
        and building that page's assets flushes, which recomputes the composer's
        other fields while the render that asked for it is still running.
        """
        self.check_singleton()
        if (
            not self.template_id
            or self.composition_mode != "comment"
            or self.composition_batch
        ):
            return False
        res_ids = self._evaluate_res_ids() or [0]
        return self.template_id._prepare_mail_vals(res_ids, fnames)[res_ids[0]]

    @api.depends("composition_mode", "model", "res_domain", "res_ids", "template_id")
    def _compute_attachment_ids(self) -> None:
        for composer in self:
            if composer.template_id.attachment_ids and (
                composer.composition_mode == "mass_mail" or composer.composition_batch
            ):
                composer.attachment_ids = composer.template_id.attachment_ids
            elif rendered_values := composer.template_render_attachments:
                attachment_ids = list(rendered_values.get("attachment_ids") or [])
                if attachments := rendered_values.get("attachments"):
                    attachment_ids += (
                        self.env["ir.attachment"]
                        .create(
                            [
                                {
                                    "name": attach_fname,
                                    "datas": attach_datas,
                                    "res_model": "mail.compose.message",
                                    "res_id": 0,
                                    "type": "binary",
                                }
                                for attach_fname, attach_datas in attachments
                            ]
                        )
                        .ids
                    )
                if attachment_ids:
                    composer.attachment_ids = attachment_ids
            elif not composer.template_id:
                composer.attachment_ids = False

    @api.depends("composition_mode", "template_id")
    def _compute_email_add_signature(self) -> None:
        for composer in self:
            if composer.composition_mode == "mass_mail":
                composer.email_add_signature = False
            else:
                composer.email_add_signature = not bool(composer.template_id)

    @api.depends("template_id")
    def _compute_email_layout_xmlid(self) -> None:
        for composer in self:
            if composer.template_id.email_layout_xmlid:
                composer.email_layout_xmlid = composer.template_id.email_layout_xmlid
            if not composer.template_id:
                composer.email_layout_xmlid = False

    @api.depends(
        "composition_mode",
        "email_from",
        "model",
        "res_domain",
        "res_ids",
        "template_id",
    )
    @api.depends_context("uid")
    def _compute_authorship(self) -> None:
        Thread = self.env["mixin.mail.thread"].with_context(active_test=False)
        for composer in self:
            rendering_mode = (
                composer.composition_mode == "comment"
                and not composer.composition_batch
            )
            updated_author_id = None

            if composer.template_id.email_from:
                composer._update_value_from_template("email_from")
            elif composer.template_id:
                composer.email_from = self.env.user.email_formatted
            elif not composer.template_id or not composer.email_from:
                if self.env.context.get("default_email_from"):
                    composer.email_from = self.env.context["default_email_from"]
                else:
                    composer.email_from = self.env.user.email_formatted
                    updated_author_id = self.env.user.partner_id.id

            if composer.email_from and rendering_mode and not updated_author_id:
                updated_author_id, _ = Thread._message_compute_author(
                    None,
                    composer.email_from,
                )
                if not updated_author_id:
                    updated_author_id = self.env.user.partner_id.id
            if not rendering_mode or not composer.template_id:
                updated_author_id = self.env.user.partner_id.id

            if updated_author_id:
                composer.author_id = updated_author_id

    @api.depends("res_domain", "res_ids")
    def _compute_composition_batch(self) -> None:
        for composer in self:
            if composer.res_domain:
                composer.composition_batch = True
                continue
            res_ids = composer._evaluate_res_ids()
            composer.composition_batch = len(res_ids) > 1 if res_ids else False

    @api.depends("composition_mode", "parent_id")
    def _compute_model(self) -> None:
        for composer in self:
            if composer.parent_id and composer.composition_mode == "comment":
                composer.model = composer.parent_id.model
            elif not composer.model:
                composer.model = self.env.context.get("active_model")

    @api.depends("model")
    def _compute_model_is_thread(self) -> None:
        thread = self.pool["mixin.mail.thread"]
        for composer in self:
            composer.model_is_thread = bool(
                composer.model
                and composer.model in self.env
                and isinstance(self.env[composer.model], thread)
            )

    @api.depends("composition_mode", "parent_id")
    def _compute_res_ids(self) -> None:
        for composer in self.filtered(lambda composer: not composer.res_ids):
            if composer.parent_id and composer.composition_mode == "comment":
                composer.res_ids = f"{[composer.parent_id.res_id]}"
            else:
                active_res_ids = parse_res_ids(
                    self.env.context.get("active_ids"), self.env
                )
                if active_res_ids and len(active_res_ids) <= 500:
                    composer.res_ids = f"{self.env.context['active_ids']}"
                elif not active_res_ids and self.env.context.get("active_id"):
                    composer.res_ids = f"{[self.env.context['active_id']]}"

    @api.depends("composition_mode", "model", "res_domain", "res_ids")
    def _compute_record_environment(self) -> None:
        toreset = self.filtered(
            lambda comp: (
                (comp.record_company_id or comp.record_alias_domain_id)
                and comp.composition_batch
            )
        )
        if toreset:
            toreset.record_alias_domain_id = False
            toreset.record_company_id = False

        toupdate = self.filtered(lambda comp: not comp.composition_batch)
        for composer in toupdate:
            res_ids = composer._evaluate_res_ids()
            if composer.model in self.env and len(res_ids) == 1:
                record = self.env[composer.model].browse(res_ids)
                composer.record_company_id = record._mail_get_companies(
                    default=self.env.company
                )[record.id]
                composer.record_alias_domain_id = record._mail_get_alias_domains(
                    default_company=self.env.company
                )[record.id]

    @api.depends("composition_mode")
    def _compute_subtype_id(self) -> None:
        comment_composers = self.filtered(
            lambda comp: comp.composition_mode == "comment"
        )
        if comment_composers:
            comment_composers.subtype_id = self.env["ir.model.data"]._xmlid_to_res_id(
                "mail.mt_comment"
            )
        (self - comment_composers).subtype_id = False

    @api.depends("subtype_id")
    def _compute_subtype_is_log(self) -> None:
        note_id = self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_note")
        self.subtype_is_log = False
        for composer in self.filtered("subtype_id"):
            composer.subtype_is_log = composer.subtype_id.id == note_id

    @api.depends("composition_mode", "model", "res_domain", "res_ids", "template_id")
    def _compute_reply_to(self) -> None:
        for composer in self:
            if composer.template_id:
                composer._update_value_from_template("reply_to")
            else:
                composer.reply_to = False

    @api.depends("model", "reply_to")
    def _compute_reply_to_force_new(self) -> None:
        non_thread = self.filtered(
            lambda composer: not composer.model or not composer.model_is_thread
        )
        non_thread.reply_to_force_new = True
        for composer in self - non_thread:
            composer.reply_to_force_new = bool(composer.reply_to)

    @api.depends("reply_to_force_new")
    def _compute_reply_to_mode(self) -> None:
        for composer in self:
            composer.reply_to_mode = "new" if composer.reply_to_force_new else "update"

    def _inverse_reply_to_mode(self) -> None:
        for composer in self:
            composer.reply_to_force_new = composer.reply_to_mode == "new"
            if composer.reply_to_mode != "new":
                composer.reply_to = False

    @api.depends(
        "composition_mode",
        "message_type",
        "model",
        "parent_id",
        "res_domain",
        "res_ids",
        "subtype_id",
        "template_id",
    )
    def _compute_partner_ids(self) -> None:
        for composer in self:
            template = composer.template_id
            if (
                template
                and composer.composition_mode == "comment"
                and not composer.composition_batch
                and (not template.use_default_to or not composer.partner_ids)
            ):
                res_ids = composer._evaluate_res_ids() or [0]
                rendered_values = composer._prepare_template_vals(
                    res_ids,
                    {"email_cc", "email_to", "partner_ids"},
                    allow_suggested=composer.message_type == "comment"
                    and not composer.subtype_is_log,
                    find_or_create_partners=True,
                )[res_ids[0]]
                if rendered_values.get("partner_ids"):
                    composer.partner_ids = rendered_values["partner_ids"]
            elif composer.parent_id and composer.composition_mode == "comment":
                composer.partner_ids = composer.parent_id.partner_ids
            elif not composer.template_id:
                composer.partner_ids = False

    @api.depends("partner_ids")
    def _compute_partner_ids_all_have_email(self) -> None:
        for record in self:
            record.partner_ids_all_have_email = all(record.partner_ids.mapped("email"))

    @api.depends(
        "composition_batch",
        "composition_mode",
        "message_type",
        "model",
        "res_ids",
        "subtype_id",
    )
    @api.depends_context("uid")
    def _compute_notified_bcc_contains_share(self) -> None:
        post_composers = self.filtered(
            lambda comp: (
                comp.model
                and comp.composition_mode == "comment"
                and not comp.composition_batch
            )
        )
        (self - post_composers).notified_bcc_contains_share = False
        for composer in post_composers:
            record = self.env[composer.model].browse(composer._evaluate_res_ids()[:1])
            recipients_data = self.env["mail.followers"]._get_recipient_data(
                record, composer.message_type, composer.subtype_id.id
            )[record.id]
            composer.notified_bcc_contains_share = any(
                pdata["share"]
                for pid, pdata in recipients_data.items()
                if (pid and pdata["active"] and pid != self.env.user.partner_id.id)
            )

    @api.depends("composition_mode", "template_id")
    def _compute_auto_delete(self) -> None:
        for composer in self:
            if composer.template_id:
                composer.auto_delete = composer.template_id.auto_delete
            else:
                composer.auto_delete = composer.composition_mode == "comment"

    @api.depends("composition_mode", "auto_delete")
    def _compute_auto_delete_keep_log(self) -> None:
        toreset = self.filtered(
            lambda comp: comp.composition_mode != "mass_mail" or not comp.auto_delete
        )
        toreset.auto_delete_keep_log = False
        (self - toreset).auto_delete_keep_log = True

    @api.depends("composition_mode", "model", "res_domain", "res_ids")
    def _compute_force_send(self) -> None:
        for composer in self:
            if not composer.composition_batch:
                composer.force_send = True
            elif composer.composition_mode == "comment" or composer.res_domain:
                composer.force_send = False
            else:
                force_send_limit = self.env["ir.config_parameter"]._get_int_param(
                    "mail.mail.force.send.limit", 100
                )
                res_ids = composer._evaluate_res_ids()
                composer.force_send = len(res_ids) <= force_send_limit

    @api.depends("template_id")
    def _compute_mail_server_id(self) -> None:
        for composer in self:
            if composer.template_id.mail_server_id:
                composer.mail_server_id = composer.template_id.mail_server_id
            if not composer.template_id:
                composer.mail_server_id = False

    @api.depends("composition_mode")
    def _compute_notify_author(self) -> None:
        self.filtered(lambda c: c.composition_mode != "comment").notify_author = False

    @api.depends("composition_mode")
    def _compute_notify_author_mention(self) -> None:
        self.filtered(
            lambda c: c.composition_mode != "comment"
        ).notify_author_mention = False

    @api.depends("composition_mode", "composition_comment_option")
    def _compute_notify_skip_followers(self) -> None:
        self.filtered(
            lambda c: c.composition_mode != "comment"
        ).notify_skip_followers = False
        self.filtered(
            lambda c: (
                c.composition_mode == "comment"
                and c.composition_comment_option == "forward"
            )
        ).notify_skip_followers = True

    @api.depends("composition_mode", "model", "res_domain", "res_ids", "template_id")
    def _compute_scheduled_date(self) -> None:
        for composer in self:
            if composer.template_id:
                composer._update_value_from_template("scheduled_date")
            if not composer.template_id:
                composer.scheduled_date = False

    @api.depends("composition_mode", "model", "res_domain", "res_ids", "template_id")
    def _compute_lang(self) -> None:
        for composer in self:
            if composer.template_id:
                composer._update_value_from_template("lang")
            if not composer.template_id:
                composer.lang = False

    @api.depends("model")
    def _compute_render_model(self) -> None:
        for composer in self:
            composer.render_model = composer.model

    def _compute_can_edit_body(self) -> None:
        non_mass_mail = self.filtered(lambda m: m.composition_mode != "mass_mail")
        non_mass_mail.can_edit_body = True
        super(MailComposeMessage, self - non_mass_mail)._compute_can_edit_body()

    def _compute_field_value(self, field: fields.Field, validate: bool = True) -> None:
        if field.compute_sudo:
            return super(
                MailComposeMessage, self.with_context(prefetch_fields=False)
            )._compute_field_value(field, validate=validate)
        return super()._compute_field_value(field, validate=validate)

    @api.autovacuum
    def _gc_lost_attachments(self) -> None:
        limit_date = fields.Datetime.subtract(fields.Datetime.now(), days=1)
        lost = self.env["ir.attachment"].search(
            [
                ("res_model", "=", self._name),
                ("res_id", "=", 0),
                ("create_date", "<", limit_date),
                ("write_date", "<", limit_date),
            ]
        )
        _debug.lifecycle("gc_lost_attachments", removed=len(lost))
        lost.unlink()

    def action_schedule_message(self) -> dict:
        self._action_schedule_message()
        return {"type": "ir.actions.act_window_close"}

    def _prepare_schedule_message_post_values(self, post_values: dict) -> dict:
        self.check_singleton()
        return {
            "attachment_ids": post_values.pop("attachment_ids"),
            "author_id": post_values.pop("author_id"),
            "body": post_values.pop("body"),
            "composition_comment_option": self.composition_comment_option,
            "is_note": self.subtype_is_log,
            "model": self.model,
            "partner_ids": post_values.pop("partner_ids"),
            "res_id": self._evaluate_res_ids()[0],
            "scheduled_date": post_values.pop("scheduled_date"),
            "send_context": clean_context(self.env.context),
            "subject": post_values.pop("subject"),
            "notification_parameters": json.dumps(post_values),
        }

    def _action_schedule_message(self) -> MailScheduledMessage:
        if any(
            wizard.composition_mode != "comment" or wizard.composition_batch
            for wizard in self
        ):
            raise UserError(_("A message can only be scheduled in monocomment mode"))
        create_values = []
        for wizard in self:
            wizard = wizard.with_context(clean_context(wizard.env.context))
            res_ids = wizard._evaluate_res_ids()
            if not res_ids:
                raise UserError(_("A scheduled message needs a target record."))
            res_id = res_ids[0]
            post_values = wizard._manage_mail_values(
                wizard._prepare_mail_values([res_id])
            ).get(res_id)
            if not post_values:
                continue
            if not post_values["scheduled_date"]:
                raise UserError(_("A scheduled date is needed to schedule a message"))
            create_values.append(
                wizard._prepare_schedule_message_post_values(post_values)
            )
        _debug.lifecycle(
            "messages_scheduled", wizards=self.ids, scheduled=len(create_values)
        )
        return self.env["mail.scheduled.message"].create(create_values)

    def action_send_mail(self) -> dict:
        self._action_send_mail(auto_commit=False)
        res_ids = self._evaluate_res_ids()
        record_name = False
        if self.model and len(res_ids) == 1 and self.composition_mode == "comment":
            record_name = self.env[self.model].browse(res_ids[0]).display_name
        return {
            "type": "ir.actions.client",
            "tag": "action_send_mail_callback",
            "params": {
                "record_name": record_name,
            },
        }

    def _action_send_mail(self, auto_commit: bool = False) -> tuple:
        result_mails_su, result_messages = (
            self.env["mail.mail"].sudo(),
            self.env["mail.message"],
        )

        for wizard in self:
            if wizard.res_domain:
                search_domain = wizard._evaluate_res_domain()
                res_ids = self.env[wizard.model].search(search_domain).ids  # noqa: E8507  model and domain both vary per wizard, so no one query spans them
            else:
                res_ids = wizard._evaluate_res_ids()
            if not res_ids and wizard.composition_mode == "comment":
                raise ValueError(
                    f"Mail composer in comment mode should run on at least one "
                    f"record. No records found (model {wizard.model})."
                )

            with _debug.perf(
                "send_mail",
                cr=self.env.cr,
                wizard=wizard.id,
                model=wizard.model or None,
                mode=wizard.composition_mode,
                records=len(res_ids),
                template=wizard.template_id.id or None,
                by_domain=bool(wizard.res_domain),
                auto_commit=auto_commit,
            ):
                if wizard.composition_mode == "mass_mail":
                    result_mails_su += wizard._action_send_mail_mass_mail(
                        res_ids, auto_commit=auto_commit
                    )
                else:
                    result_messages += wizard._action_send_mail_comment(res_ids)

        return result_mails_su, result_messages

    def _action_send_mail_comment(self, res_ids: list[int]) -> MailMessage:
        self.check_singleton()
        post_values_all = self._prepare_post_values(res_ids)
        ActiveModel = self._get_comment_target_model()
        _debug.pipeline(
            "send_comment",
            wizard=self.id,
            model=ActiveModel._name,
            records=len(post_values_all),
            batch=self.composition_batch,
            by="notify" if ActiveModel._name == "mixin.mail.thread" else "post",
        )
        if ActiveModel._name == "mixin.mail.thread":
            messages = self.env["mail.message"]
            for res_id, post_values in post_values_all.items():
                post_values.pop("message_type")
                post_values.pop("parent_id", False)
                if self.model:
                    post_values["model"] = self.model
                    post_values["res_id"] = res_id
                message = ActiveModel.message_notify(**post_values)
                if not message:
                    raise UserError(_("No recipient found."))
                messages += message
            return messages
        return ActiveModel._message_post_values_all(post_values_all)

    def _get_comment_target_model(self) -> models.Model:
        self.check_singleton()
        ActiveModel = (
            self.env[self.model]
            if self.model and hasattr(self.env[self.model], "message_post")
            else self.env["mixin.mail.thread"]
        )
        if self.composition_batch:
            ActiveModel = ActiveModel.with_context(
                mail_post_autofollow_author_skip=True,
            )
        return ActiveModel

    def _prepare_post_values(self, res_ids: list[int]) -> dict[int, dict]:
        self.check_singleton()
        return self._manage_mail_values(self._prepare_mail_values(res_ids))

    def _action_send_mail_mass_mail(
        self, res_ids: list[int], auto_commit: bool = False
    ) -> MailMail:
        mails_sudo = self.env["mail.mail"].sudo()

        batch_size = self.env["mail.mail"]._get_send_batch_size(self._batch_size or 50)
        counter_mails_done = 0
        composer = self.with_context(**{SENT_EMAILS_MAPPING_CONTEXT_KEY: {}})
        for res_ids_iter in itertools.batched(res_ids, batch_size, strict=False):
            prepared_mail_values_filtered = composer._manage_mail_values(
                composer._prepare_mail_values(res_ids_iter)
            )
            iter_mails_sudo = (
                self.env["mail.mail"]
                .sudo()
                .create(list(prepared_mail_values_filtered.values()))
            )
            self.env["mail.notification"].sudo().create(
                self._generate_mail_notification_values(iter_mails_sudo)
            )
            mails_sudo += iter_mails_sudo

            records = (
                self.env[self.model].browse(prepared_mail_values_filtered.keys())
                if self.model and hasattr(self.env[self.model], "message_post")
                else False
            )
            if records:
                records._message_mail_after_hook(iter_mails_sudo)

            sent_in_batch = False
            if self.force_send:
                iter_mails_sudo_tosend = iter_mails_sudo._filtered_ready_to_send()
                if iter_mails_sudo_tosend:
                    iter_mails_sudo_tosend.send(auto_commit=auto_commit)
                    sent_in_batch = True
            if auto_commit is True:
                batch_done = len(prepared_mail_values_filtered)
                counter_mails_done += batch_done
                self.env["ir.cron"]._commit_progress(
                    batch_done, remaining=len(res_ids) - counter_mails_done
                )
            _debug.pipeline(
                "mass_mail_batch",
                wizard=self.id,
                batch=len(res_ids_iter),
                prepared=len(prepared_mail_values_filtered),
                mails=len(iter_mails_sudo),
                sent=sent_in_batch,
                done=counter_mails_done,
                total=len(res_ids),
            )
            if not (sent_in_batch and auto_commit):
                self.env.invalidate_all()

        return mails_sudo

    def _generate_mail_notification_values(self, mails: MailMail) -> list:
        if self.auto_delete and not self.auto_delete_keep_log:
            _debug.logic(
                "mail_notifications_skipped", wizard=self.id, reason="auto_delete"
            )
            return []

        create_vals_all = []
        for mail, notif_base_values in zip(
            mails, mails._get_notification_values(), strict=False
        ):
            emails = set(
                tools.mail.email_split_and_format_normalize(
                    f"{mail.email_to or ''}, {mail.email_cc or ''}"
                )
            )
            emails = emails or ([mail.email_to] if mail.email_to else "")

            if not mail.recipient_ids and not emails:
                create_vals_all.append(notif_base_values)
            else:
                create_vals_all.extend(
                    notif_base_values | {"res_partner_id": partner.id}
                    for partner in mail.recipient_ids
                )
                create_vals_all.extend(
                    notif_base_values | {"mail_email_address": email}
                    for email in emails
                )
        return create_vals_all

    def open_template_creation_wizard(self) -> dict:
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "view_id": self.env.ref(
                "mail.mail_compose_message_view_form_template_save"
            ).id,
            "name": _("Create a Mail Template"),
            "res_model": "mail.compose.message",
            "context": {"dialog_size": "medium"},
            "target": "new",
            "res_id": self.id,
        }

    def create_mail_template(self) -> dict:
        self.check_singleton()
        if not self.model or self.model not in self.env:
            raise UserError(
                _("Template creation from composer requires a valid model.")
            )
        model_id = self.env["ir.model"]._get_id(self.model)
        values = {
            "name": self.template_name,
            "body_html": self.body,
            "model_id": model_id,
            "use_default_to": True,
            "user_id": self.env.uid,
        }
        template = self.env["mail.template"].create(values)
        _debug.lifecycle(
            "template_created_from_composer",
            wizard=self.id,
            template=template.id,
            model=self.model,
        )

        if self.attachment_ids:
            attachments = (
                self.env["ir.attachment"]
                .sudo()
                .browse(self.attachment_ids.ids)
                .filtered(
                    lambda a: (
                        a.res_model == "mail.compose.message"
                        and a.create_uid.id == self.env.uid
                    )
                )
            )
            if attachments:
                attachments.write({"res_model": template._name, "res_id": template.id})
                template.attachment_ids = self.attachment_ids

        self.write({"template_id": template.id})
        return _reopen(
            self,
            self.id,
            self.model,
            context={**self.env.context, "dialog_size": "large"},
        )

    def cancel_save_template(self) -> dict:
        self.check_singleton()
        return _reopen(
            self,
            self.id,
            self.model,
            context={**self.env.context, "dialog_size": "large"},
        )

    def _invalid_email_state(self) -> str:
        return (
            "cancel"
            if self.auto_delete and not self.auto_delete_keep_log
            else "exception"
        )

    def _prepare_mail_values(self, res_ids: list[int]) -> dict:
        self.check_singleton()
        email_mode = self.composition_mode == "mass_mail"
        rendering_mode = email_mode or self.composition_batch

        base_values = self._prepare_mail_values_static()

        additional_values_all = {}
        _debug.logic(
            "mail_values_by",
            wizard=self.id,
            records=len(res_ids),
            by="dynamic"
            if rendering_mode and self.model
            else "rendered"
            if not rendering_mode
            else "static",
            email_mode=email_mode,
        )
        if rendering_mode and self.model:
            additional_values_all = self._prepare_mail_values_dynamic(res_ids)
        elif not rendering_mode:
            additional_values_all = self._prepare_mail_values_rendered(res_ids)

        mail_values_all = {
            res_id: dict(base_values, **additional_values_all.get(res_id, {}))
            for res_id in res_ids
        }

        if email_mode:
            mail_values_all = self._process_mail_values_state(mail_values_all)
            for mail_values in mail_values_all.values():
                message_id = self.env["mail.message"]._get_message_id(mail_values)
                mail_values["message_id"] = message_id
                mail_values["references"] = message_id
        return mail_values_all

    def _manage_mail_values(self, mail_values_all: dict) -> dict:
        return mail_values_all

    def _prepare_mail_values_static(self) -> dict:
        self.check_singleton()
        email_mode = self.composition_mode == "mass_mail"

        if email_mode:
            subtype_id = False
        elif self.subtype_id:
            subtype_id = self.subtype_id.id
        else:
            subtype_id = self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_comment")

        values = {
            "author_id": self.author_id.id,
            "mail_activity_type_id": self.mail_activity_type_id.id,
            "mail_server_id": self.mail_server_id.id,
            "message_type": "email_outgoing" if email_mode else self.message_type,
            "parent_id": self.parent_id.id,
            "reply_to_force_new": self.reply_to_force_new and bool(self.reply_to),
            "subtype_id": subtype_id,
        }
        if email_mode:
            values.update(
                auto_delete=self.auto_delete,
                is_notification=not self.auto_delete or self.auto_delete_keep_log,
                model=self.model,
            )
        else:
            model_description = self.env.context.get("model_description")
            values.update(
                email_add_signature=self.email_add_signature,
                email_layout_xmlid=self.email_layout_xmlid,
                force_send=self.force_send,
                mail_auto_delete=self.auto_delete,
                model_description=model_description,
                record_alias_domain_id=self.record_alias_domain_id.id,
                record_company_id=self.record_company_id.id,
            )
            if self.notify_author:
                values["notify_author"] = self.notify_author
            if self.notify_author_mention:
                values["notify_author_mention"] = self.notify_author_mention
            if self.notify_skip_followers:
                values["notify_skip_followers"] = self.notify_skip_followers
        return values

    def _prepare_mail_values_dynamic(self, res_ids: list[int]) -> dict:
        self.check_singleton()
        RecordsModel = self.env[self.model].with_prefetch(res_ids)
        email_mode = self.composition_mode == "mass_mail"
        records = RecordsModel.browse(res_ids)

        langs = self._render_lang(res_ids)
        emails_from = self._render_field("email_from", res_ids)
        mail_values_all = self._prepare_mail_values_per_record(
            records, res_ids, langs, emails_from, email_mode
        )
        _debug.pipeline(
            "dynamic_mail_values",
            wizard=self.id,
            records=len(res_ids),
            langs=len(set(langs.values())),
            template=self.template_id.id or None,
            reply_to_force_new=self.reply_to_force_new,
            layout=self.email_layout_xmlid or None,
        )

        if self.template_id:
            self._update_mail_values_from_template(mail_values_all, res_ids, langs)
        elif not self.partner_ids and email_mode:
            default_recipients = records._message_get_default_recipients()
            for res_id in res_ids:
                mail_values_all[res_id].update(default_recipients.get(res_id, {}))
        if not email_mode and self.partner_ids:
            for mail_values in mail_values_all.values():
                mail_values["partner_ids"] = list(
                    dict.fromkeys(
                        [*mail_values.get("partner_ids", []), *self.partner_ids.ids]
                    )
                )

        if self.reply_to_force_new:
            reply_to_values = self._render_field("reply_to", res_ids)
        else:
            reply_to_values = records._notify_get_reply_to_batch(
                defaults=emails_from,
                author_ids=dict.fromkeys(res_ids, self.author_id.id),
            )

        for res_id, mail_values in mail_values_all.items():
            record = RecordsModel.browse(res_id)
            self._update_mail_values_attachments(mail_values, record, email_mode)

            if email_mode:
                mail_values["headers"] = record._notify_by_email_get_headers()
                recipient_ids_all = set(mail_values.pop("partner_ids", [])) | set(
                    self.partner_ids.ids
                )
                mail_values["recipient_ids"] = [(4, pid) for pid in recipient_ids_all]

            reply_to = reply_to_values.get(res_id)
            if not reply_to and email_mode:
                reply_to = mail_values.get("email_from", False)
            if reply_to:
                mail_values["reply_to"] = reply_to

            if email_mode and self.email_layout_xmlid and mail_values["recipient_ids"]:
                self._update_mail_values_layout_body(
                    mail_values, record, res_id, langs[res_id]
                )

        return mail_values_all

    def _prepare_mail_values_per_record(
        self,
        records: models.Model,
        res_ids: list[int],
        langs: dict,
        emails_from: dict,
        email_mode: bool,
    ) -> dict:
        companies = records._mail_get_companies(default=self.env.company)
        alias_domains = records._mail_get_alias_domains(
            default_company=self.env.company
        )
        subjects = self._render_field(
            "subject", res_ids, compute_lang=True, res_ids_lang=langs
        )
        bodies = self._render_field(
            "body",
            res_ids,
            compute_lang=True,
            res_ids_lang=langs,
            options={"preserve_comments": email_mode},
        )

        return {
            res_id: {
                "body": bodies[res_id],
                "email_from": emails_from[res_id],
                "scheduled_date": False,
                "subject": subjects[res_id],
                "record_alias_domain_id": alias_domains[res_id].id,
                "record_company_id": companies[res_id].id,
                **(
                    {
                        "body_html": bodies[res_id],
                        "res_id": res_id,
                    }
                    if email_mode
                    else {}
                ),
                **(
                    {
                        "force_email_lang": langs[res_id],
                    }
                    if not email_mode
                    else {}
                ),
            }
            for res_id in res_ids
        }

    def _update_mail_values_from_template(
        self,
        mail_values_all: dict,
        res_ids: list[int],
        res_ids_lang: dict[int, str] | None = None,
    ) -> None:
        template_values = self._prepare_template_vals(
            res_ids,
            [
                "email_to",
                "email_cc",
                "partner_ids",
                "report_template_ids",
                "scheduled_date",
            ],
            allow_suggested=(
                self.composition_mode == "comment"
                and not self.composition_batch
                and self.message_type == "comment"
                and not self.subtype_is_log
            ),
            find_or_create_partners=self.env.context.get(
                "mail_composer_force_partners", True
            ),
            res_ids_lang=res_ids_lang,
        )
        _debug.pipeline(
            "template_values_applied",
            wizard=self.id,
            template=self.template_id.id,
            records=len(res_ids),
            allow_suggested=self.composition_mode == "comment"
            and not self.composition_batch
            and self.message_type == "comment"
            and not self.subtype_is_log,
        )
        for res_id in res_ids:
            template_values[res_id].pop("attachment_ids", None)
            mail_values_all[res_id].update(template_values[res_id])

    def _update_mail_values_attachments(
        self, mail_values: dict, record: models.Model, email_mode: bool
    ) -> None:
        attachment_ids = self.attachment_ids.copy(
            {"res_model": self._name, "res_id": self.id}
        ).ids
        attachment_ids.reverse()
        decoded_attachments = [
            (name, base64.b64decode(enc_cont))
            for name, enc_cont in mail_values.pop("attachments", [])
        ]
        if not email_mode:
            mail_values["attachments"] = decoded_attachments
            mail_values["attachment_ids"] = attachment_ids
            return

        record_posts_attachments = hasattr(record, "_process_attachments_for_post")
        process_record = (
            record if record_posts_attachments else record.env["mixin.mail.thread"]
        )
        detach_from_record = not record_posts_attachments or (
            self.auto_delete and not self.auto_delete_keep_log
        )
        mail_values["attachment_ids"] = process_record._process_attachments_for_post(
            decoded_attachments,
            attachment_ids,
            {"model": "mail.message", "res_id": 0} if detach_from_record else {},
        )["attachment_ids"]

    def _update_mail_values_layout_body(
        self, mail_values: dict, record: models.Model, res_id: int, lang: str
    ) -> None:
        recipient_ids = [command[1] for command in mail_values["recipient_ids"]]
        msg_vals = {
            "email_layout_xmlid": self.email_layout_xmlid,
            "model": self.model,
            "res_id": res_id,
        }
        new_mail_message_values = {"body": mail_values["body"]}
        if self.template_id:
            new_mail_message_values["email_add_signature"] = False
        message_inmem = self.env["mail.message"].new(new_mail_message_values)
        classified = list(
            record._notify_get_classified_recipients_iterator(
                message_inmem,
                [
                    prepare_recipient_data(partner_id=pid, lang=lang)
                    for pid in recipient_ids
                ],
                msg_vals=msg_vals,
                model_description=False,
                force_email_lang=lang,
            )
        )
        if not classified:
            _debug.logic(
                "layout_body_skipped", wizard=self.id, record=res_id, reason="no_group"
            )
            return
        _lang, render_values, recipients_group = classified[-1]
        merged_group = {
            **recipients_group,
            "has_button_access": all(
                group["has_button_access"] for _lang, _values, group in classified
            ),
            **{
                key: [
                    item for _lang, _values, group in classified for item in group[key]
                ]
                for key in ("recipients_data", "recipients_emails", "recipients_ids")
            },
        }
        if any(values["show_unfollow"] for _lang, values, _group in classified):
            render_values = {**render_values, "show_unfollow": True}
        mail_values["body_html"] = record._notify_by_email_render_layout(
            message_inmem,
            merged_group,
            msg_vals=msg_vals,
            render_values=render_values,
        )

    def _prepare_mail_values_rendered(self, res_ids: list[int]) -> dict:
        self.check_singleton()
        email_mode = self.composition_mode == "mass_mail"

        if (
            self.composition_mode == "comment"
            and self.template_id
            and self.attachment_ids
        ):
            new_attachment_ids = []
            for attachment in self.attachment_ids:
                if attachment in self.template_id.attachment_ids:
                    new_attachment_ids.append(
                        attachment.copy(
                            {
                                "res_model": "mail.compose.message",
                                "res_id": self.id,
                            }
                        ).id
                    )
                else:
                    new_attachment_ids.append(attachment.id)
            new_attachment_ids.reverse()
            self.write({"attachment_ids": [Command.set(new_attachment_ids)]})

        return {
            res_id: {
                "attachment_ids": [attach.id for attach in self.attachment_ids],
                "body": self.body or "",
                "email_from": self.email_from,
                "partner_ids": self.partner_ids.ids,
                "scheduled_date": self.scheduled_date,
                "subject": self.subject or "",
                **(
                    {
                        "force_email_lang": self.lang,
                    }
                    if not email_mode
                    else {}
                ),
                **({"reply_to": self.reply_to} if self.reply_to else {}),
            }
            for res_id in res_ids
        }

    def _process_mail_values_state(self, mail_values_dict: dict) -> dict:
        recipients_info = self._get_recipients_data(mail_values_dict)
        blacklist_ids = self._get_blacklist_record_ids(
            mail_values_dict, recipients_info
        )
        optout_emails = self._get_optout_emails(mail_values_dict)
        done_emails = self._get_done_emails(mail_values_dict)
        sent_emails_mapping = self.env.context.get(SENT_EMAILS_MAPPING_CONTEXT_KEY)
        if sent_emails_mapping is None:
            sent_emails_mapping = {}

        for record_id, mail_values in mail_values_dict.items():
            recipients = recipients_info[record_id]

            invalid_email_state = self._invalid_email_state()
            if record_id in blacklist_ids:
                mail_values["state"] = "cancel"
                mail_values["failure_type"] = "mail_bl"
                mail_values["is_notification"] = False
            elif not any(recipients["mail_to"]):
                mail_values["state"] = invalid_email_state
                mail_values["failure_type"] = "mail_email_missing"
            elif not any(recipients["mail_to_normalized"]):
                mail_values["state"] = invalid_email_state
                mail_values["failure_type"] = "mail_email_invalid"
            elif optout_emails and all(
                mail_to in optout_emails for mail_to in recipients["mail_to_normalized"]
            ):
                mail_values["state"] = "cancel"
                mail_values["failure_type"] = "mail_optout"
            elif (
                done_emails
                and all(
                    mail_to in done_emails
                    for mail_to in recipients["mail_to_normalized"]
                )
            ) or (
                len(self.attachment_ids) == len(mail_values.get("attachment_ids", []))
                and all(
                    mail_to in sent_emails_mapping
                    for mail_to in recipients["mail_to_normalized"]
                )
                and any(
                    sent_mail.get("subject") == mail_values.get("subject")
                    and sent_mail.get("body") == mail_values.get("body")
                    for mail_to in recipients["mail_to_normalized"]
                    for sent_mail in sent_emails_mapping[mail_to]
                )
            ):
                mail_values["state"] = "cancel"
                mail_values["failure_type"] = "mail_dup"
            else:
                for mail_to in recipients["mail_to_normalized"]:
                    sent_emails_mapping.setdefault(mail_to, []).append(mail_values)

        if _debug.pipeline.enabled:
            _debug.pipeline(
                "mail_values_state",
                wizard=self.id,
                records=len(mail_values_dict),
                blacklisted=len(blacklist_ids),
                optout=len(optout_emails),
                done=len(done_emails),
                canceled=sum(
                    1 for v in mail_values_dict.values() if v.get("state") == "cancel"
                ),
                invalid=sum(
                    1
                    for v in mail_values_dict.values()
                    if v.get("failure_type")
                    in ("mail_email_missing", "mail_email_invalid")
                ),
            )
        return mail_values_dict

    def _prepare_template_vals(
        self,
        res_ids: list[int],
        render_fields: Collection[str],
        allow_suggested: bool = False,
        find_or_create_partners: bool = True,
        res_ids_lang: dict[int, str] | None = None,
    ) -> dict:
        self.check_singleton()

        template_fields = {
            COMPOSER_FIELD_TO_TEMPLATE_FIELD.get(fname, fname)
            for fname in render_fields
        }
        template_values = self.template_id._prepare_mail_vals(
            res_ids,
            template_fields,
            recipients_allow_suggested=allow_suggested,
            find_or_create_partners=find_or_create_partners,
            res_ids_lang=res_ids_lang,
        )

        excluded = {"email_cc", "email_to"} if find_or_create_partners else frozenset()
        return {
            res_id: {
                TEMPLATE_FIELD_TO_COMPOSER_FIELD.get(fname, fname): value
                for fname, value in template_values[res_id].items()
                if fname not in excluded and value
            }
            for res_id in res_ids
        }

    def _get_blacklist_record_ids(
        self, mail_values_dict: dict, recipients_info: dict | None = None
    ) -> set:
        blacklisted_rec_ids = set()
        if not self.use_exclusion_list:
            return blacklisted_rec_ids
        if self.composition_mode == "mass_mail":
            self.env["mail.blacklist"].flush_model(["email", "active"])
            self.env.cr.execute("SELECT email FROM mail_blacklist WHERE active=true")
            blacklist = {x[0] for x in self.env.cr.fetchall()}
            if not blacklist:
                return blacklisted_rec_ids
            if isinstance(
                self.env[self.model], self.pool["mixin.mail.thread.blacklist"]
            ):
                model = self.env[self.model]
                primary_email = model._primary_email
                targets = model.browse(mail_values_dict.keys())
                targets.fetch(["email_normalized", primary_email])
                blacklisted_rec_ids.update(
                    target.id
                    for target in targets
                    if blacklist
                    & set(
                        email_normalize_all(target[primary_email] or "")
                        or filter(None, [target.email_normalized])
                    )
                )
            if recipients_info:
                blacklisted_rec_ids.update(
                    res_id
                    for res_id, recipient_info in recipients_info.items()
                    if blacklist & set(recipient_info["mail_to_normalized"])
                )
            _debug.logic(
                "blacklist_applied",
                wizard=self.id,
                blacklist=len(blacklist),
                records=len(mail_values_dict),
                blacklisted=len(blacklisted_rec_ids),
            )
        return blacklisted_rec_ids

    def _get_done_emails(self, mail_values_dict: dict) -> list:
        return []

    def _get_optout_emails(self, mail_values_dict: dict) -> list:
        return []

    def _get_recipients_data(self, mail_values_dict: dict) -> dict:
        recipient_pids = [
            recipient_command[1]
            for mail_values in mail_values_dict.values()
            for recipient_command in mail_values.get("recipient_ids") or []
            if recipient_command[1]
        ]
        recipient_emails = (
            {p.id: p.email for p in self.env["res.partner"].browse(set(recipient_pids))}
            if recipient_pids
            else {}
        )

        recipients_info = {}
        for record_id, mail_values in mail_values_dict.items():
            mail_to = email_split_and_format(mail_values.get("email_to"))
            if not mail_to and mail_values.get("email_to"):
                mail_to.append(mail_values["email_to"])
            mail_to += [
                recipient_emails[recipient_command[1]]
                for recipient_command in mail_values.get("recipient_ids") or []
                if recipient_command[1]
            ]
            seen = set()
            mail_to = [
                email for email in mail_to if email not in seen and not seen.add(email)
            ]
            recipients_info[record_id] = {
                "mail_to": mail_to,
                "mail_to_normalized": [
                    email_normalize(mail, strict=False)
                    for mail in mail_to
                    if email_normalize(mail, strict=False)
                ],
            }
        return recipients_info

    def _evaluate_res_domain(self) -> Domain:
        self.check_singleton()
        if isinstance(self.res_domain, (str, bool)) and not self.res_domain:
            return Domain.FALSE
        try:
            domain = self.res_domain
            if isinstance(self.res_domain, str):
                domain = ast.literal_eval(domain)

            domain = Domain(domain)
            domain.check(self.env[self.model])
        except (ValueError, SyntaxError) as e:
            raise ValidationError(
                _(
                    "Invalid domain “%(domain)s” (type “%(domain_type)s”)",
                    domain=self.res_domain,
                    domain_type=type(self.res_domain),
                )
            ) from e

        return domain

    def _evaluate_res_ids(self) -> list[int] | str | bool | None:
        self.check_singleton()
        return (
            parse_res_ids(
                self.env.context.get("composer_force_res_ids")
                or self.res_ids
                or self.env.context.get("active_ids"),
                self.env,
            )
            or []
        )

    def _update_value_from_template(
        self, template_fname: str, composer_fname: str | Literal[False] = False
    ) -> Any:
        self.check_singleton()
        composer_fname = composer_fname or template_fname

        template_value = self.template_id[template_fname] if self.template_id else False
        if template_value and template_fname == "body_html":
            template_value = (
                template_value if not is_html_empty(template_value) else False
            )

        if template_value:
            if rendered_values := self.template_render_values:
                self[composer_fname] = rendered_values[template_fname]
            else:
                self[composer_fname] = self.template_id[template_fname]
            _debug.logic(
                "composer_value_from_template",
                wizard=self.id,
                field=composer_fname,
                by="rendered" if self.template_render_values else "raw",
            )
        return self[composer_fname]
