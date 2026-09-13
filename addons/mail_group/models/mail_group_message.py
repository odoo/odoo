import logging

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.fields import Domain
from odoo.tools.mail import add_html_content, email_normalize

_logger = logging.getLogger(__name__)


class MailGroupMessage(models.Model):
    _name = "mail.group.message"
    _description = "Mailing List Message"
    _rec_name = "subject"
    _order = "create_date DESC"
    _primary_email = "email_from"

    attachment_ids = fields.Many2many(
        related="mail_message_id.attachment_ids",
        readonly=False,
    )
    author_id = fields.Many2one(
        related="mail_message_id.author_id",
        readonly=False,
    )
    email_from = fields.Char(
        related="mail_message_id.email_from",
        readonly=False,
    )
    email_from_normalized = fields.Char(
        string="Normalized From",
        compute="_compute_email_from_normalized",
        store=True,
    )
    body = fields.Html(
        related="mail_message_id.body",
        readonly=False,
    )
    subject = fields.Char(
        related="mail_message_id.subject",
        readonly=False,
    )
    mail_group_id = fields.Many2one(
        comodel_name="mail.group",
        string="Group",
        index=True,
        required=True,
        ondelete="cascade",
    )
    mail_message_id = fields.Many2one(
        comodel_name="mail.message",
        index=True,
        copy=False,
        required=True,
        ondelete="cascade",
    )
    group_message_parent_id = fields.Many2one(
        comodel_name="mail.group.message",
        string="Parent",
        store=True,
        index=True,
    )
    group_message_child_ids = fields.One2many(
        comodel_name="mail.group.message",
        inverse_name="group_message_parent_id",
        string="Children",
    )
    author_moderation = fields.Selection(
        selection=[("ban", "Banned"), ("allow", "Whitelisted")],
        string="Author Moderation Status",
        compute="_compute_author_moderation",
    )
    is_group_moderated = fields.Boolean(
        related="mail_group_id.moderation",
        string="Is Group Moderated",
    )
    moderation_status = fields.Selection(
        selection=[
            ("pending_moderation", "Pending Moderation"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
        ],
        string="Status",
        default="pending_moderation",
        index=True,
        copy=False,
        required=True,
    )
    moderator_id = fields.Many2one(
        comodel_name="res.users",
        string="Moderated By",
    )
    create_date = fields.Datetime(string="Posted")

    @api.depends("email_from")
    def _compute_email_from_normalized(self):
        for message in self:
            message.email_from_normalized = email_normalize(message.email_from)

    @api.depends("email_from_normalized", "mail_group_id")
    def _compute_author_moderation(self):
        moderations = self.env["mail.group.moderation"].search(
            [
                ("mail_group_id", "in", self.mail_group_id.ids),
            ]
        )
        all_emails = set(self.mapped("email_from_normalized"))
        moderations = {
            (moderation.mail_group_id, moderation.email): moderation.status
            for moderation in moderations
            if moderation.email in all_emails
        }
        for message in self:
            message.author_moderation = moderations.get(
                (message.mail_group_id, message.email_from_normalized), False
            )

    @api.constrains("mail_message_id")
    def _constrains_mail_message_id(self):
        for message in self:
            if message.mail_message_id.model != "mail.group":
                raise AccessError(
                    _(
                        "Group message can only be linked to mail group. Current model is %s.",
                        message.mail_message_id.model,
                    )
                )
            if message.mail_message_id.res_id != message.mail_group_id.id:
                raise AccessError(_("The record of the message should be the group."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("mail_message_id"):
                vals.update(
                    {
                        "res_id": vals.get("mail_group_id"),
                        "model": "mail.group",
                    }
                )
                vals["mail_message_id"] = (
                    self.env["mail.message"]
                    .sudo()
                    .create(
                        {
                            field: vals.pop(field)
                            for field in self.env["mail.message"]._fields
                            if field in vals
                            and field
                            in self.env[
                                "mixin.mail.thread"
                            ]._get_message_create_valid_field_names()
                        }
                    )
                    .id
                )
        return super().create(vals_list)

    def copy_data(self, default=None):
        vals_list = super().copy_data(default)
        for message, vals in zip(self, vals_list):
            vals["mail_message_id"] = message.mail_message_id.copy().id
        return vals_list

    def action_moderate_accept(self):
        self._assert_moderable()
        self.write(
            {
                "moderation_status": "accepted",
                "moderator_id": self.env.uid,
            }
        )

        for message in self:
            message.mail_group_id._notify_members(message)

    def action_moderate_reject_with_comment(self, reject_subject, reject_comment):
        self._assert_moderable()
        if reject_subject or reject_comment:
            self._moderate_send_reject_email(reject_subject, reject_comment)
        self.action_moderate_reject()

    def action_moderate_reject(self):
        self._assert_moderable()
        self.write(
            {
                "moderation_status": "rejected",
                "moderator_id": self.env.uid,
            }
        )

    def action_moderate_allow(self):
        self._create_moderation_rule("allow")

        same_author = self._get_pending_same_author_same_group()
        same_author.action_moderate_accept()

    def action_moderate_ban(self):
        self._create_moderation_rule("ban")

        same_author = self._get_pending_same_author_same_group()
        same_author.action_moderate_reject()

    def action_moderate_ban_with_comment(self, ban_subject, ban_comment):
        self._create_moderation_rule("ban")

        if ban_subject or ban_comment:
            self._moderate_send_reject_email(ban_subject, ban_comment)

        same_author = self._get_pending_same_author_same_group()
        same_author.action_moderate_reject()

    def _get_pending_same_author_same_group(self):
        return self.search(
            Domain.OR(
                [
                    [
                        ("mail_group_id", "=", message.mail_group_id.id),
                        ("email_from_normalized", "=", message.email_from_normalized),
                    ]
                    for message in self
                ]
            )
            & Domain("moderation_status", "=", "pending_moderation")
        )

    def _create_moderation_rule(self, status):
        if status not in ("ban", "allow"):
            raise ValueError(f"Wrong status ({status})")

        for message in self:
            if not email_normalize(message.email_from):
                raise UserError(_('The email "%s" is not valid.', message.email_from))

        existing_moderation = self.env["mail.group.moderation"].search(
            Domain.OR(
                [
                    [
                        ("email", "=", email_normalize(message.email_from)),
                        ("mail_group_id", "=", message.mail_group_id.id),
                    ]
                    for message in self
                ]
            )
        )
        existing_moderation.status = status

        moderation_to_create = {
            (email_normalize(message.email_from), message.mail_group_id.id)
            for message in self
            if email_normalize(message.email_from)
            not in existing_moderation.mapped("email")
        }

        self.env["mail.group.moderation"].create(
            [
                {
                    "email": email,
                    "mail_group_id": mail_group_id,
                    "status": status,
                }
                for email, mail_group_id in moderation_to_create
            ]
        )

    def _assert_moderable(self):
        non_moderable_messages = self.filtered_domain(
            [
                ("moderation_status", "!=", "pending_moderation"),
            ]
        )
        if non_moderable_messages:
            if len(self) == 1:
                raise UserError(_("This message can not be moderated"))
            raise UserError(
                _(
                    "Those messages can not be moderated: %s.",
                    ", ".join(non_moderable_messages.mapped("subject")),
                )
            )

    def _moderate_send_reject_email(self, subject, comment):
        for message in self:
            if not message.email_from:
                continue

            body_html = add_html_content(
                Markup("<div>%s</div>") % comment, message.body, plaintext=False
            )
            body_html = self.env["mixin.mail.render"]._replace_local_links(body_html)
            self.env["mail.mail"].sudo().create(
                {
                    "author_id": self.env.user.partner_id.id,
                    "auto_delete": True,
                    "body_html": body_html,
                    "email_from": self.env.user.email_formatted
                    or self.env.company.catchall_formatted,
                    "email_to": message.email_from,
                    "references": message.mail_message_id.message_id,
                    "subject": subject,
                    "state": "outgoing",
                }
            )
