import json
import logging
from datetime import datetime
from itertools import batched
from urllib.parse import quote, urlencode

import lxml
from dateutil import relativedelta
from markupsafe import Markup

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import hmac
from odoo.tools.mail import (
    add_html_content,
    email_normalize,
    generate_tracking_message_id,
)

from odoo.addons.mail.models.mixin_mail_gateway import RouteVerdict
from odoo.addons.mail.tools.alias_error import AliasError

_logger = logging.getLogger(__name__)

GROUP_SEND_BATCH_SIZE = 500


class MailGroup(models.Model):
    _name = "mail.group"
    _description = "Mail Group"
    _inherit = ["mixin.mail.alias"]
    _order = "is_closed ASC, create_date DESC, id DESC"

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if "alias_contact" in fields and not res.get("alias_contact"):
            res["alias_contact"] = (
                "everyone" if res.get("access_mode") == "public" else "followers"
            )
        return res

    active = fields.Boolean(default=True)
    name = fields.Char(
        translate=True,
        required=True,
    )
    description = fields.Text()
    image_128 = fields.Image(
        string="Image",
        max_width=128,
        max_height=128,
    )
    is_closed = fields.Boolean(
        copy=False,
        help="Closed groups might still be accessed, but emails sent to it will bounce",
    )
    mail_group_message_ids = fields.One2many(
        comodel_name="mail.group.message",
        inverse_name="mail_group_id",
        string="Pending Messages",
    )
    mail_group_message_last_month_count = fields.Integer(
        string="Messages Per Month",
        compute="_compute_mail_group_message_last_month_count",
    )
    mail_group_message_count = fields.Integer(
        string="Messages Count",
        compute="_compute_mail_group_message_count",
        help="Number of message in this group",
    )
    mail_group_message_moderation_count = fields.Integer(
        string="Pending Messages Count",
        compute="_compute_mail_group_message_moderation_count",
        help="Messages that need an action",
    )
    is_member = fields.Boolean(compute="_compute_is_member")
    member_ids = fields.One2many(
        comodel_name="mail.group.member",
        inverse_name="mail_group_id",
        string="Members",
    )
    member_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Partners Member",
        compute="_compute_member_partner_ids",
        search="_search_member_partner_ids",
    )
    member_count = fields.Count(
        count_of="member_ids",
        string="Members Count",
    )
    is_moderator = fields.Boolean(
        string="Moderator",
        compute="_compute_is_moderator",
        help="Current user is a moderator of the group",
    )
    moderation = fields.Boolean(string="Moderate")
    moderation_rule_count = fields.Count(
        count_of="moderation_rule_ids",
        string="Moderated emails count",
    )
    moderation_rule_ids = fields.One2many(
        comodel_name="mail.group.moderation",
        inverse_name="mail_group_id",
        string="Moderated Emails",
    )
    moderator_ids = fields.Many2many(
        comodel_name="res.users",
        relation="mail_group_moderator_rel",
        string="Moderators",
        domain=lambda self: [
            ("all_group_ids", "in", self.env.ref("base.group_user").id)
        ],
    )
    moderation_notify = fields.Boolean(
        string="Automatic notification",
        help="People receive an automatic notification about their message being waiting for moderation.",
    )
    moderation_notify_msg = fields.Html(string="Notification message")
    moderation_guidelines = fields.Boolean(
        string="Send guidelines to new members",
        help="Newcomers on this moderated group will automatically receive the guidelines.",
    )
    moderation_guidelines_msg = fields.Html(string="Guidelines")
    access_mode = fields.Selection(
        selection=[
            ("public", "Everyone"),
            ("members", "Members only"),
            ("groups", "Selected group of users"),
        ],
        string="Privacy",
        default="public",
        required=True,
    )
    access_group_id = fields.Many2one(
        comodel_name="res.groups",
        string="Authorized Group",
        default=lambda self: self.env.ref("base.group_user"),
    )
    can_manage_group = fields.Boolean(
        string="Can Manage",
        compute="_compute_can_manage_group",
        help="Can manage the members",
    )

    @api.depends(
        "mail_group_message_ids.create_date", "mail_group_message_ids.moderation_status"
    )
    def _compute_mail_group_message_last_month_count(self):
        month_date = datetime.today() - relativedelta.relativedelta(months=1)
        messages_data = self.env["mail.group.message"]._read_group(
            [
                ("mail_group_id", "in", self.ids),
                ("create_date", ">=", fields.Datetime.to_string(month_date)),
                ("moderation_status", "=", "accepted"),
            ],
            ["mail_group_id"],
            ["__count"],
        )

        messages_data = {mail_group.id: count for mail_group, count in messages_data}

        for group in self:
            group.mail_group_message_last_month_count = messages_data.get(group.id, 0)

    @api.depends("mail_group_message_ids")
    def _compute_mail_group_message_count(self):
        if not self:
            self.mail_group_message_count = 0
            return

        results = self.env["mail.group.message"]._read_group(
            [("mail_group_id", "in", self.ids)],
            ["mail_group_id"],
            ["__count"],
        )
        result_per_group = {mail_group.id: count for mail_group, count in results}
        for group in self:
            group.mail_group_message_count = result_per_group.get(group.id, 0)

    @api.depends("mail_group_message_ids.moderation_status")
    def _compute_mail_group_message_moderation_count(self):
        results = self.env["mail.group.message"]._read_group(
            [
                ("mail_group_id", "in", self.ids),
                ("moderation_status", "=", "pending_moderation"),
            ],
            ["mail_group_id"],
            ["__count"],
        )
        result_per_group = {mail_group.id: count for mail_group, count in results}

        for group in self:
            group.mail_group_message_moderation_count = result_per_group.get(
                group.id, 0
            )

    @api.depends_context("uid")
    def _compute_is_member(self):
        if not self or self.env.user._is_public():
            self.is_member = False
            return

        members = (
            self.env["mail.group.member"]
            .sudo()
            .search(
                [
                    ("partner_id", "=", self.env.user.partner_id.id),
                    ("mail_group_id", "in", self.ids),
                ]
            )
        )
        is_member = {member.mail_group_id.id: True for member in members}

        for group in self:
            group.is_member = is_member.get(group.id, False)

    @api.depends("member_ids")
    def _compute_member_partner_ids(self):
        for group in self:
            group.member_partner_ids = group.member_ids.partner_id

    def _search_member_partner_ids(self, operator, operand):
        return [
            (
                "member_ids",
                "in",
                self.env["mail.group.member"]
                .sudo()
                ._search([("partner_id", operator, operand)]),
            )
        ]

    @api.depends("moderator_ids")
    @api.depends_context("uid")
    def _compute_is_moderator(self):
        for group in self:
            group.is_moderator = self.env.user.id in group.moderator_ids.ids

    @api.depends("is_moderator")
    @api.depends_context("uid")
    def _compute_can_manage_group(self):
        is_admin = (
            self.env.user.has_group("mail_group.group_mail_group_manager")
            or self.env.su
        )
        for group in self:
            group.can_manage_group = is_admin or group.is_moderator

    @api.onchange("access_mode")
    def _onchange_access_mode(self):
        if self.access_mode == "public":
            self.alias_contact = "everyone"
        else:
            self.alias_contact = "followers"

    @api.onchange("moderation")
    def _onchange_moderation(self):
        if self.moderation and self.env.user not in self.moderator_ids:
            self.moderator_ids |= self.env.user

    @api.constrains("moderator_ids")
    def _check_moderator_email(self):
        if any(
            not moderator.email for group in self for moderator in group.moderator_ids
        ):
            raise ValidationError(_("Moderators must have an email address."))

    @api.constrains("moderation_notify", "moderation_notify_msg")
    def _check_moderation_notify(self):
        if any(
            group.moderation_notify and not group.moderation_notify_msg
            for group in self
        ):
            raise ValidationError(_("The notification message is missing."))

    @api.constrains("moderation_guidelines", "moderation_guidelines_msg")
    def _check_moderation_guidelines(self):
        if any(
            group.moderation_guidelines and not group.moderation_guidelines_msg
            for group in self
        ):
            raise ValidationError(_("The guidelines description is missing."))

    @api.constrains("moderator_ids", "moderation")
    def _check_moderator_existence(self):
        if any(not group.moderator_ids for group in self if group.moderation):
            raise ValidationError(_("Moderated group must have moderators."))

    @api.constrains("access_mode", "access_group_id")
    def _check_access_mode(self):
        if any(
            group.access_mode == "groups" and not group.access_group_id
            for group in self
        ):
            raise ValidationError(_('The "Authorized Group" is missing.'))

    def _alias_get_creation_values(self):
        values = super()._alias_get_creation_values()
        values["alias_model_id"] = self.env["ir.model"]._get("mail.group").id
        values["alias_force_thread_id"] = self.id
        values["alias_defaults"] = self._prepare_alias_defaults()
        return values

    def action_close(self):
        self.check_singleton()
        self.is_closed = True

    def action_open(self):
        self.check_singleton()
        self.is_closed = False

    def _alias_resolve_error(self, message, message_dict, alias):
        self.check_singleton()

        email = email_normalize(message_dict.get("email_from", ""))
        email_has_access = email and self.search_count(
            [
                ("id", "=", self.id),
                ("access_group_id.user_ids.email_normalized", "=", email),
            ]
        )
        if self.access_mode == "groups" and not email_has_access:
            return AliasError(
                "error_mail_group_members_restricted",
                _("Only selected groups of users can send email to the mailing list."),
            )

        elif self.access_mode == "members" and not self._find_member(
            message_dict.get("email_from")
        ):
            return AliasError(
                "error_mail_group_members_restricted",
                _("Only members can send email to the mailing list."),
            )

        return None

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        return

    @api.model
    def message_update(self, msg_dict, update_vals=None):
        return

    def message_post(
        self, body="", subject=None, email_from=None, author_id=None, **kwargs
    ):
        self.check_singleton()
        Mailthread = self.env["mixin.mail.thread"]
        values = dict(
            (key, val)
            for key, val in kwargs.items()
            if key in self.env["mail.message"]._fields
        )
        author_id, email_from = Mailthread._message_compute_author(
            author_id, email_from
        )

        values.update(
            {
                "author_id": author_id,
                "body": Markup(self._clean_email_body(body)),
                "email_from": email_from,
                "model": self._name,
                "partner_ids": [],
                "res_id": self.id,
                "subject": subject,
            }
        )

        values["reply_to"] = self.env["mail.message"]._get_reply_to(values)

        if not values.get("message_id"):
            values["message_id"] = generate_tracking_message_id(
                "%s-mail.group" % self.id
            )

        values.update(
            Mailthread._process_attachments_for_post(
                kwargs.get("attachments") or [],
                kwargs.get("attachment_ids") or [],
                values,
            )
        )

        mail_message = Mailthread._message_create([values])

        group_message_parent_id = False
        if mail_message.parent_id:
            group_message_parent = self.env["mail.group.message"].search(
                [("mail_message_id", "=", mail_message.parent_id.id)]
            )
            group_message_parent_id = (
                group_message_parent.id if group_message_parent else False
            )

        moderation_status = "pending_moderation" if self.moderation else "accepted"

        group_message = self.env["mail.group.message"].create(
            {
                "mail_group_id": self.id,
                "mail_message_id": mail_message.id,
                "moderation_status": moderation_status,
                "group_message_parent_id": group_message_parent_id,
            }
        )

        email_normalized = email_normalize(email_from)
        moderation_rule = self.env["mail.group.moderation"].search(
            [
                ("mail_group_id", "=", self.id),
                ("email", "=", email_normalized),
            ],
            limit=1,
        )

        if not self.moderation:
            self._notify_members(group_message)

        elif moderation_rule and moderation_rule.status == "allow":
            group_message.action_moderate_accept()

        elif moderation_rule and moderation_rule.status == "ban":
            group_message.action_moderate_reject()

        elif self.moderation_notify:
            self.env["mail.mail"].sudo().create(
                {
                    "author_id": self.env.user.partner_id.id,
                    "auto_delete": True,
                    "body_html": group_message.mail_group_id.moderation_notify_msg,
                    "email_from": self.env.user.company_id.catchall_formatted
                    or self.env.user.company_id.email_formatted,
                    "email_to": email_from,
                    "subject": "Re: %s" % (subject or ""),
                    "state": "outgoing",
                }
            )

        return mail_message

    def action_send_guidelines(self, members=None):
        self.check_singleton()

        if not self.env.is_admin() and not self.is_moderator:
            raise UserError(
                _(
                    "Only an administrator or a moderator can send guidelines to group members."
                )
            )

        if not self.moderation_guidelines_msg:
            raise UserError(_("The guidelines description is empty."))

        if self.is_closed:
            raise UserError(_("You can not send guidelines for a closed group."))

        template = self.env.ref(
            "mail_group.mail_template_guidelines", raise_if_not_found=False
        )
        if not template:
            raise UserError(
                _(
                    'Template "mail_group.mail_template_guidelines" was not found. No email has been sent. Please contact an administrator to fix this issue.'
                )
            )

        banned_emails = (
            self.env["mail.group.moderation"]
            .sudo()
            .search(
                [
                    ("status", "=", "ban"),
                    ("mail_group_id", "=", self.id),
                ]
            )
            .mapped("email")
        )

        if members is None:
            members = self.member_ids
        members = members.filtered(
            lambda member: member.email_normalized not in banned_emails
        )

        for member in members:
            company = member.partner_id.company_id or self.env.company
            template.send_mail(
                member.id,
                email_values={
                    "author_id": self.env.user.partner_id.id,
                    "email_from": company.email_formatted or company.catchall_formatted,
                    "reply_to": company.email_formatted or company.catchall_formatted,
                },
            )

        _logger.info("Send guidelines to %i members", len(members))

    def _notify_members(self, message):
        self.check_singleton()

        if message.mail_group_id != self:
            raise UserError(_("The group of the message do not match."))

        if not message.mail_message_id.reply_to:
            _logger.error(
                "The alias or the catchall domain is missing, group might not work properly."
            )

        base_url = self.get_base_url()
        body = self.env["mixin.mail.render"]._replace_local_links(message.body)

        member_emails = {
            email_normalize(member.email): member.email for member in self.member_ids
        }

        batch_size = self.env["ir.config_parameter"]._get_positive_int_param(
            "mail.session.batch.size", GROUP_SEND_BATCH_SIZE
        )
        for batch_email_member in batched(member_emails.items(), batch_size):
            mail_values = []
            for email_member_normalized, email_member in batch_email_member:
                if email_member_normalized == message.email_from_normalized:
                    continue

                email_url_encoded = quote(email_member, safe="/:")
                unsubscribe_url = self._get_email_unsubscribe_url(
                    email_member_normalized
                )

                headers = {
                    **self._notify_by_email_get_headers(),
                    "List-Archive": f"<{base_url}/groups/{self.env['ir.http']._slug(self)}>",
                    "List-Subscribe": f"<{base_url}/groups?email={email_url_encoded}>",
                    "List-Unsubscribe": f"<{unsubscribe_url}>",
                    "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                    "Precedence": "list",
                    "X-Auto-Response-Suppress": "OOF",
                }
                if self.alias_email:
                    headers.update(
                        {
                            "List-Id": f"<{self.alias_email}>",
                            "List-Post": f"<mailto:{self.alias_email}>",
                            "X-Forge-To": f'"{self.name}" <{self.alias_email}>',
                        }
                    )

                if message.mail_message_id.parent_id:
                    headers["In-Reply-To"] = (
                        message.mail_message_id.parent_id.message_id
                    )

                template_values = {
                    "mailto": f"{self.alias_email}",
                    "group_url": f"{base_url}/groups/{self.env['ir.http']._slug(self)}",
                    "unsub_label": f"{base_url}/groups?unsubscribe",
                    "unsub_url": unsubscribe_url,
                }
                footer = self.env["ir.qweb"]._render(
                    "mail_group.mail_group_footer",
                    template_values,
                    minimal_qcontext=True,
                )
                member_body = add_html_content(body, footer, plaintext=False)

                mail_values.append(
                    {
                        "auto_delete": True,
                        "attachment_ids": message.attachment_ids.ids,
                        "body_html": member_body,
                        "email_from": message.email_from,
                        "email_to": email_member,
                        "headers": json.dumps(headers),
                        "mail_message_id": message.mail_message_id.id,
                        "message_id": message.mail_message_id.message_id,
                        "model": "mail.group",
                        "reply_to": message.mail_message_id.reply_to,
                        "res_id": self.id,
                        "subject": message.subject,
                    }
                )

            if mail_values:
                self.env["mail.mail"].sudo().create(mail_values)

    @api.model
    def _cron_notify_moderators(self):
        moderated_groups = self.env["mail.group"].search([("moderation", "=", True)])
        return moderated_groups._notify_moderators()

    def _notify_moderators(self):
        template = self.env.ref(
            "mail_group.mail_group_notify_moderation", raise_if_not_found=False
        )
        if not template:
            _logger.warning(
                'Template "mail_group.mail_group_notify_moderation" was not found. Cannot send reminder notifications.'
            )
            return

        results = self.env["mail.group.message"]._read_group(
            [
                ("mail_group_id", "in", self.ids),
                ("moderation_status", "=", "pending_moderation"),
            ],
            ["mail_group_id"],
        )
        groups = self.browse([mail_group.id for [mail_group] in results])

        for group in groups:
            moderators_to_notify = group.moderator_ids
            MixinMailThread = self.env["mixin.mail.thread"]
            for moderator in moderators_to_notify:
                body = self.env["ir.qweb"]._render(
                    "mail_group.mail_group_notify_moderation",
                    {
                        "moderator": moderator,
                        "group": group,
                    },
                    minimal_qcontext=True,
                )
                email_from = (
                    moderator.company_id.catchall_formatted
                    or moderator.company_id.email_formatted
                )
                MixinMailThread.message_notify(
                    partner_ids=moderator.partner_id.ids,
                    subject=_("Messages are pending moderation"),
                    body=body,
                    email_from=email_from,
                    model="mail.group",
                    res_id=group.id,
                )

    @api.model
    def _clean_email_body(self, body_html):
        tree = lxml.html.fromstring(body_html or "")
        xpath_footer = ".//div[contains(@id, 'o_mg_message_footer')]"
        for parent_footer in tree.xpath(xpath_footer + "/.."):
            for footer in parent_footer.xpath(xpath_footer):
                parent_footer.remove(footer)

        return lxml.etree.tostring(tree, encoding="utf-8").decode()

    @api.model
    def _routing_check_route(self, message, message_dict, route, raise_exception=True):
        if route[0] == "mail.group" and self.browse(route[1]).is_closed:
            body = self.env["ir.qweb"]._render(
                "mail_group.email_template_mail_group_closed"
            )
            self.env["mixin.mail.thread"]._routing_create_bounce_email(
                message_dict["from"],
                body,
                message,
                references=message_dict.get("message_id", ""),
            )
            return RouteVerdict.REFUSED
        return self.env["mixin.mail.thread"]._routing_check_route(
            message, message_dict, route, raise_exception
        )

    def action_join(self):
        self.check_access("read")
        if self.is_closed:
            raise UserError(_("You can not join a closed group."))
        partner = self.env.user.partner_id
        self.sudo()._join_group(partner.email, partner.id)

        _logger.info(
            '"%s" (#%s) joined mail.group "%s" (#%s)',
            partner.name,
            partner.id,
            self.name,
            self.id,
        )

    def action_leave(self):
        self.check_access("read")
        partner = self.env.user.partner_id
        self.sudo()._leave_group(partner.email, partner.id)

        _logger.info(
            '"%s" (#%s) leaved mail.group "%s" (#%s)',
            partner.name,
            partner.id,
            self.name,
            self.id,
        )

    def _join_group(self, email, partner_id=None):
        self.check_singleton()

        if partner_id:
            partner = self.env["res.partner"].browse(partner_id).exists()
            if not partner:
                raise ValidationError(_("The partner can not be found."))
            email = partner.email

        existing_member = self._find_member(email, partner_id)
        if existing_member:
            existing_member.write(
                {
                    "email": email,
                    "partner_id": partner_id,
                }
            )
            return

        member = self.env["mail.group.member"].create(
            {
                "partner_id": partner_id,
                "email": email,
                "mail_group_id": self.id,
            }
        )

        if self.moderation_guidelines:
            self.action_send_guidelines(member)

    def _leave_group(self, email, partner_id=None, all_members=False):
        self.check_singleton()
        if all_members and not partner_id:
            self.env["mail.group.member"].search(
                [
                    ("mail_group_id", "=", self.id),
                    ("email_normalized", "=", email_normalize(email)),
                ]
            ).unlink()
        else:
            member = self._find_member(email, partner_id)
            if member:
                member.unlink()

    def _send_subscribe_confirmation_email(self, email):
        self.check_singleton()
        confirm_action_url = self._generate_action_url(email, "subscribe")

        template = self.env.ref("mail_group.mail_template_list_subscribe")
        template.with_context(token_url=confirm_action_url).send_mail(
            self.id,
            email_layout_xmlid="mail.mail_notification_light",
            email_values={
                "author_id": self.create_uid.partner_id.id,
                "auto_delete": True,
                "email_from": self.env.company.email_formatted,
                "email_to": email,
                "message_type": "user_notification",
            },
            force_send=True,
        )
        _logger.info("Subscription email sent to %s.", email)

    def _send_unsubscribe_confirmation_email(self, email):
        self.check_singleton()
        confirm_action_url = self._generate_action_url(email, "unsubscribe")

        template = self.env.ref("mail_group.mail_template_list_unsubscribe")
        template.with_context(token_url=confirm_action_url).send_mail(
            self.id,
            email_layout_xmlid="mail.mail_notification_light",
            email_values={
                "author_id": self.create_uid.partner_id.id,
                "auto_delete": True,
                "email_from": self.env.company.email_formatted,
                "email_to": email,
                "message_type": "user_notification",
            },
            force_send=True,
        )
        _logger.info("Unsubscription email sent to %s.", email)

    def _generate_action_url(self, email, action):
        if action not in ["subscribe", "unsubscribe"]:
            raise ValueError(f"Invalid action for URL generation ({action})")
        self.check_singleton()

        confirm_action_url = "/group/%s-confirm?%s" % (
            action,
            urlencode(
                {
                    "group_id": self.id,
                    "email": email,
                    "token": self._generate_action_token(email, action),
                }
            ),
        )
        base_url = self.get_base_url()
        confirm_action_url = tools.urls.urljoin(base_url, confirm_action_url)
        return confirm_action_url

    def _generate_action_token(self, email, action):
        if action not in ["subscribe", "unsubscribe"]:
            raise ValueError(f"Invalid action for URL generation ({action})")
        self.check_singleton()

        email_normalized = email_normalize(email)
        if not email_normalized:
            raise UserError(_("Email %s is invalid", email))

        data = (self.id, email_normalized, action)
        return hmac(self.env(su=True), "mail_group-email-subscription", data)

    def _generate_email_access_token(self, email):
        return tools.hmac(
            self.env(su=True), "mail_group-access-token-portal-email", (self.id, email)
        )

    def _generate_group_access_token(self):
        self.check_singleton()
        return hmac(self.env(su=True), "mail_group-access-token-portal", self.id)

    def _get_email_unsubscribe_url(self, email_to):
        params = urlencode(
            {
                "email": email_to,
                "token": self._generate_email_access_token(email_to),
            }
        )
        return tools.urls.urljoin(
            self.get_base_url(),
            f"group/{self.id}/unsubscribe_oneclick?{params}",
        )

    def _find_member(self, email, partner_id=None):
        self.check_singleton()

        result = self._get_members(email, partner_id)
        return result.get(self.id)

    def _get_members(self, email, partner_id):
        order = "partner_id ASC"
        if not email_normalize(email):
            return {}

        domain = Domain("email_normalized", "=", email_normalize(email))
        if partner_id:
            domain = (Domain("partner_id", "=", False) & domain) | Domain(
                "partner_id", "=", partner_id
            )
            order = "partner_id DESC"

        domain &= Domain("mail_group_id", "in", self.ids)
        members_data = self.env["mail.group.member"].sudo().search(domain, order=order)
        return {member.mail_group_id.id: member for member in members_data}
