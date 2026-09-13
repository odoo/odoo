import json

from markupsafe import Markup

from odoo import _, api, fields, models, tools
from odoo.libs.datetime import timezone
from odoo.libs.filesystem import get_extension
from odoo.tools import email_normalize, email_split, html2plaintext, plaintext2html

from odoo.addons.mail.models.discuss.discuss_channel import ChannelTypePolicy
from odoo.addons.mail.tools.discuss import Store


def is_livechat_channel(channel):
    return channel.channel_type == "livechat"


class DiscussChannel(models.Model):
    _name = "discuss.channel"
    _inherit = ["mixin.rating", "discuss.channel"]

    channel_type = fields.Selection(
        selection_add=[("livechat", "Livechat Conversation")],
        ondelete={"livechat": "cascade"},
    )
    duration = fields.Float(
        compute="_compute_duration",
        help="Duration of the session in hours",
    )
    livechat_lang_id = fields.Many2one(
        comodel_name="res.lang",
        string="Language",
        help="Lang of the visitor of the channel.",
    )
    livechat_end_dt = fields.Datetime(
        string="Session end date",
        help="Session is closed when either the visitor or the last agent leaves the conversation.",
    )
    livechat_channel_id = fields.Many2one(
        comodel_name="im_livechat.channel",
        string="Channel",
        index="btree_not_null",
    )
    livechat_operator_id = fields.Many2one(
        comodel_name="res.partner",
        string="Operator",
        index="btree_not_null",
    )
    livechat_channel_member_history_ids = fields.One2many(
        comodel_name="im_livechat.channel.member.history",
        inverse_name="channel_id",
    )
    livechat_expertise_ids = fields.Many2many(
        comodel_name="im_livechat.expertise",
        relation="discuss_channel_im_livechat_expertise_rel",
        column1="discuss_channel_id",
        column2="im_livechat_expertise_id",
        store=True,
    )
    livechat_agent_history_ids = fields.One2many(
        comodel_name="im_livechat.channel.member.history",
        string="Agents (History)",
        compute="_compute_livechat_agent_history_ids",
        search="_search_livechat_agent_history_ids",
    )
    livechat_bot_history_ids = fields.One2many(
        comodel_name="im_livechat.channel.member.history",
        string="Bots (History)",
        compute="_compute_livechat_bot_history_ids",
        search="_search_livechat_bot_history_ids",
    )
    livechat_customer_history_ids = fields.One2many(
        comodel_name="im_livechat.channel.member.history",
        string="Customers (History)",
        compute="_compute_livechat_customer_history_ids",
        search="_search_livechat_customer_history_ids",
    )
    livechat_agent_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="im_livechat_channel_member_history_discuss_channel_agent_rel",
        string="Agents",
        compute="_compute_livechat_agent_partner_ids",
        store=True,
    )
    livechat_bot_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="im_livechat_channel_member_history_discuss_channel_bot_rel",
        string="Bots",
        compute="_compute_livechat_bot_partner_ids",
        store=True,
        context={"active_test": False},
    )
    livechat_customer_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="im_livechat_channel_member_history_discuss_channel_customer_rel",
        string="Customers (Partners)",
        compute="_compute_livechat_customer_partner_ids",
        store=True,
    )
    livechat_customer_guest_ids = fields.Many2many(
        comodel_name="mail.guest",
        string="Customers (Guests)",
        compute="_compute_livechat_customer_guest_ids",
    )
    livechat_agent_requesting_help_history = fields.Many2one(
        comodel_name="im_livechat.channel.member.history",
        string="Help Requested (Agent)",
        compute="_compute_livechat_agent_requesting_help_history",
        store=True,
    )
    livechat_agent_providing_help_history = fields.Many2one(
        comodel_name="im_livechat.channel.member.history",
        string="Help Provided (Agent)",
        compute="_compute_livechat_agent_providing_help_history",
        store=True,
    )
    livechat_note = fields.Html(
        string="Live Chat Note",
        sanitize_style=True,
        groups="base.group_user",
        help="Note about the session, visible to all internal users having access to the session.",
    )
    livechat_status = fields.Selection(
        selection=[
            ("in_progress", "In progress"),
            ("waiting", "Waiting for customer"),
            ("need_help", "Looking for help"),
        ],
        compute="_compute_livechat_status",
        store=True,
        readonly=False,
        groups="base.group_user",
    )
    livechat_outcome = fields.Selection(
        selection=[
            ("no_answer", "Never Answered"),
            ("no_agent", "No one Available"),
            ("no_failure", "Success"),
            ("escalated", "Escalated"),
        ],
        compute="_compute_livechat_outcome",
        store=True,
    )
    livechat_conversation_tag_ids = fields.Many2many(
        comodel_name="im_livechat.conversation.tag",
        relation="livechat_conversation_tag_rel",
        string="Live Chat Conversation Tags",
        groups="im_livechat.im_livechat_group_user",
        help="Tags to qualify the conversation.",
    )
    livechat_start_hour = fields.Float(
        string="Session Start Hour",
        compute="_compute_livechat_start_hour",
        store=True,
    )
    livechat_week_day = fields.Selection(
        selection=[
            ("0", "Monday"),
            ("1", "Tuesday"),
            ("2", "Wednesday"),
            ("3", "Thursday"),
            ("4", "Friday"),
            ("5", "Saturday"),
            ("6", "Sunday"),
        ],
        string="Day of the Week",
        compute="_compute_livechat_week_day",
        store=True,
    )
    livechat_matches_self_lang = fields.Boolean(
        compute="_compute_livechat_matches_self_lang",
        search="_search_livechat_matches_self_lang",
    )
    livechat_matches_self_expertise = fields.Boolean(
        compute="_compute_livechat_matches_self_expertise",
        search="_search_livechat_matches_self_expertise",
    )

    chatbot_current_step_id = fields.Many2one(comodel_name="chatbot.script.step")
    chatbot_message_ids = fields.One2many(
        comodel_name="chatbot.message",
        inverse_name="discuss_channel_id",
        string="Chatbot Messages",
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        help="Country of the visitor of the channel",
    )
    livechat_failure = fields.Selection(
        selection=[
            ("no_answer", "Never Answered"),
            ("no_agent", "No one Available"),
            ("no_failure", "No Failure"),
        ],
        string="Live Chat Session Failure",
    )
    livechat_is_escalated = fields.Boolean(
        string="Is session escalated",
        compute="_compute_livechat_is_escalated",
        store=True,
    )
    rating_last_text = fields.Selection(store=True)

    _livechat_operator_id = models.Constraint(
        "CHECK((channel_type = 'livechat' and livechat_operator_id is not null) or (channel_type != 'livechat'))",
        "Livechat Operator ID is required for a channel of type livechat.",
    )
    _livechat_end_dt_status_constraint = models.Constraint(
        "CHECK(livechat_end_dt IS NULL or livechat_status IS NULL)",
        "Closed Live Chat session should not have a status.",
    )
    _livechat_end_dt_idx = models.Index(
        "(livechat_end_dt) WHERE livechat_end_dt IS NULL"
    )
    _livechat_failure_idx = models.Index(
        "(livechat_failure) WHERE livechat_failure IN ('no_answer', 'no_agent')"
    )
    _livechat_is_escalated_idx = models.Index(
        "(livechat_is_escalated) WHERE livechat_is_escalated IS TRUE"
    )
    _livechat_channel_type_create_date_idx = models.Index(
        "(channel_type, create_date) WHERE channel_type = 'livechat'"
    )

    def write(self, vals):
        if "livechat_status" not in vals and "livechat_expertise_ids" not in vals:
            return super().write(vals)
        need_help_before = self.filtered(lambda c: c.livechat_status == "need_help")
        result = super().write(vals)
        need_help_after = self.filtered(lambda c: c.livechat_status == "need_help")
        group_livechat_user = self.env.ref("im_livechat.im_livechat_group_user")
        store = Store(
            bus_channel=group_livechat_user, bus_subchannel="LOOKING_FOR_HELP"
        )
        added_need_help = need_help_after - need_help_before
        removed_need_help = need_help_before - need_help_after
        store.add(added_need_help)
        store.add(removed_need_help, ["livechat_status"])
        if "livechat_expertise_ids" in vals:
            store.add(self, Store.Many("livechat_expertise_ids"))
        if added_need_help or removed_need_help:
            group_livechat_user._bus_send(
                "im_livechat.looking_for_help/update",
                {
                    "added_channel_ids": added_need_help.ids,
                    "removed_channel_ids": removed_need_help.ids,
                },
                subchannel="LOOKING_FOR_HELP",
            )
        store.bus_send()
        return result

    @api.depends("livechat_end_dt")
    def _compute_duration(self):
        for record in self:
            end = record.livechat_end_dt or fields.Datetime.now()
            start = record.create_date or fields.Datetime.now()
            record.duration = (end - start).total_seconds() / 3600

    @api.depends("livechat_end_dt")
    def _compute_livechat_status(self):
        for channel in self.filtered(lambda c: c.livechat_end_dt):
            channel.livechat_status = False

    @api.depends("livechat_agent_history_ids")
    def _compute_livechat_is_escalated(self):
        for channel in self:
            channel.livechat_is_escalated = len(channel.livechat_agent_history_ids) > 1

    @api.depends("livechat_channel_member_history_ids.livechat_member_type")
    def _compute_livechat_agent_history_ids(self):
        for channel in self:
            channel.livechat_agent_history_ids = (
                channel.livechat_channel_member_history_ids.filtered(
                    lambda h: h.livechat_member_type == "agent",
                )
            )

    @api.depends("livechat_channel_member_history_ids.livechat_member_type")
    def _compute_livechat_bot_history_ids(self):
        for channel in self:
            channel.livechat_bot_history_ids = (
                channel.livechat_channel_member_history_ids.filtered(
                    lambda h: h.livechat_member_type == "bot",
                )
            )

    def _search_livechat_bot_history_ids(self, operator, value):
        if operator != "in":
            return NotImplemented
        bot_history_query = self.env["im_livechat.channel.member.history"]._search(
            [
                ("livechat_member_type", "=", "bot"),
                ("id", "in", value),
            ],
        )
        return [("id", "in", bot_history_query.subselect("channel_id"))]

    @api.depends("livechat_channel_member_history_ids.livechat_member_type")
    def _compute_livechat_customer_history_ids(self):
        for channel in self:
            channel.livechat_customer_history_ids = (
                channel.livechat_channel_member_history_ids.filtered(
                    lambda h: h.livechat_member_type == "visitor",
                )
            )

    def _search_livechat_customer_history_ids(self, operator, value):
        if operator != "in":
            return NotImplemented
        customer_history_query = self.env["im_livechat.channel.member.history"]._search(
            [
                ("livechat_member_type", "=", "visitor"),
                ("id", "in", value),
            ],
        )
        return [("id", "in", customer_history_query.subselect("channel_id"))]

    @api.depends("livechat_agent_history_ids.partner_id")
    def _compute_livechat_agent_partner_ids(self):
        for channel in self:
            channel.livechat_agent_partner_ids = (
                channel.livechat_agent_history_ids.partner_id
            )

    def _search_livechat_agent_history_ids(self, operator, value):
        if operator not in ("any", "in"):
            return NotImplemented
        if operator == "in" and len(value) == 1 and not next(iter(value)):
            return [
                (
                    "id",
                    "not in",
                    self.env["im_livechat.channel.member.history"]
                    ._search([("livechat_member_type", "=", "agent")])
                    .subselect("channel_id"),
                ),
            ]
        query = (
            self.env["im_livechat.channel.member.history"]._search(value)
            if isinstance(value, fields.Domain)
            else value
        )
        agent_history_query = self.env["im_livechat.channel.member.history"]._search(
            [
                ("livechat_member_type", "=", "agent"),
                ("id", "in", query),
            ],
        )
        return [("id", "in", agent_history_query.subselect("channel_id"))]

    @api.depends("livechat_bot_history_ids.partner_id")
    def _compute_livechat_bot_partner_ids(self):
        for channel in self:
            channel.livechat_bot_partner_ids = (
                channel.livechat_bot_history_ids.partner_id
            )

    @api.depends("livechat_customer_history_ids.partner_id")
    def _compute_livechat_customer_partner_ids(self):
        for channel in self:
            channel.livechat_customer_partner_ids = (
                channel.livechat_customer_history_ids.partner_id
            )

    def _compute_livechat_customer_guest_ids(self):
        for channel in self:
            channel.livechat_customer_guest_ids = (
                channel.livechat_customer_history_ids.guest_id
            )

    @api.depends("livechat_agent_history_ids")
    def _compute_livechat_agent_requesting_help_history(self):
        for channel in self:
            channel.livechat_agent_requesting_help_history = (
                channel.livechat_agent_history_ids.sorted(
                    lambda h: (h.create_date, h.id)
                )[0]
                if channel.livechat_is_escalated
                else None
            )

    @api.depends("livechat_agent_history_ids")
    def _compute_livechat_agent_providing_help_history(self):
        for channel in self:
            channel.livechat_agent_providing_help_history = (
                channel.livechat_agent_history_ids.sorted(
                    lambda h: (h.create_date, h.id), reverse=True
                )[0]
                if channel.livechat_is_escalated
                else None
            )

    @api.depends("livechat_is_escalated", "livechat_failure")
    def _compute_livechat_outcome(self):
        for channel in self:
            self.livechat_outcome = (
                "escalated"
                if channel.livechat_is_escalated
                else channel.livechat_failure
            )

    @api.depends_context("user")
    def _compute_livechat_matches_self_lang(self):
        for channel in self:
            channel.livechat_matches_self_lang = (
                channel.livechat_lang_id in self.env.user.livechat_lang_ids
                or channel.livechat_lang_id.code == self.env.user.lang
            )

    def _search_livechat_matches_self_lang(self, operator, value):
        if operator != "in" or value not in ({True}, {False}):
            return NotImplemented
        operator = "in" if value == {True} else "not in"
        lang_codes = self.env.user.livechat_lang_ids.mapped("code")
        lang_codes.append(self.env.user.lang)
        return [("livechat_lang_id.code", operator, lang_codes)]

    @api.depends_context("user")
    def _compute_livechat_matches_self_expertise(self):
        for channel in self:
            channel.livechat_matches_self_expertise = bool(
                channel.livechat_expertise_ids & self.env.user.livechat_expertise_ids
            )

    def _search_livechat_matches_self_expertise(self, operator, value):
        if operator != "in" or value not in ({True}, {False}):
            return NotImplemented
        operator = "in" if value == {True} else "not in"
        return [
            (
                "livechat_expertise_ids",
                operator,
                self.env.user.livechat_expertise_ids.ids,
            )
        ]

    @api.depends("create_date")
    def _compute_livechat_start_hour(self):
        for channel in self:
            channel.livechat_start_hour = channel.create_date.hour

    @api.depends("create_date")
    def _compute_livechat_week_day(self):
        for channel in self:
            channel.livechat_week_day = str(channel.create_date.weekday())

    def _sync_field_names(self):
        field_names = super()._sync_field_names()
        field_names[None].append(
            Store.One(
                "livechat_operator_id",
                self.env["discuss.channel"]._store_livechat_operator_id_fields(),
                predicate=is_livechat_channel,
            ),
        )
        field_names["internal_users"].extend(
            [
                Store.Attr("description", predicate=is_livechat_channel),
                Store.Attr("livechat_note", predicate=is_livechat_channel),
                Store.Attr("livechat_status", predicate=is_livechat_channel),
                Store.Many(
                    "livechat_expertise_ids", ["name"], predicate=is_livechat_channel
                ),
                Store.Many(
                    "livechat_conversation_tag_ids",
                    ["name", "color"],
                    predicate=is_livechat_channel,
                    sudo=True,
                ),
            ],
        )
        return field_names

    def _store_livechat_operator_id_fields(self):
        return [
            "avatar_128",
            *self.env["res.partner"]._get_fields_store_livechat_username(),
        ]

    def _to_store_defaults(self, target: Store.Target):
        fields = [
            "chatbot_current_step",
            Store.One("country_id", ["code", "name"], predicate=is_livechat_channel),
            Store.One(
                "livechat_lang_id",
                ["name"],
                predicate=is_livechat_channel,
            ),
            Store.Attr("livechat_end_dt", predicate=is_livechat_channel),
            Store.One(
                "livechat_operator_id",
                self.env["discuss.channel"]._store_livechat_operator_id_fields(),
                predicate=is_livechat_channel,
                sudo=True,
            ),
        ]
        if target.is_internal(self.env):
            fields.append(
                Store.One(
                    "livechat_channel_id",
                    ["name"],
                    predicate=is_livechat_channel,
                    sudo=True,
                )
            )
            fields.extend(
                [
                    Store.Attr("description", predicate=is_livechat_channel),
                    Store.Attr("livechat_note", predicate=is_livechat_channel),
                    Store.Attr("livechat_outcome", predicate=is_livechat_channel),
                    Store.Attr("livechat_status", predicate=is_livechat_channel),
                    Store.Many(
                        "livechat_expertise_ids",
                        ["name"],
                        predicate=is_livechat_channel,
                    ),
                    Store.Many(
                        "livechat_conversation_tag_ids",
                        ["name", "color"],
                        predicate=is_livechat_channel,
                        sudo=True,
                    ),
                ],
            )
        return super()._to_store_defaults(target) + fields

    def _to_store(self, store: Store, fields):
        super()._to_store(store, [f for f in fields if f != "chatbot_current_step"])
        if "chatbot_current_step" not in fields:
            return
        lang = self.env["chatbot.script"]._get_chatbot_language()
        for channel in self.filtered(lambda channel: channel.chatbot_current_step_id):
            current_step_sudo = channel.chatbot_current_step_id.sudo().with_context(
                lang=lang
            )
            chatbot_script = current_step_sudo.chatbot_script_id
            step_message = self.env["chatbot.message"]
            if not current_step_sudo.is_forward_operator:
                step_message = channel.sudo().chatbot_message_ids.filtered(
                    lambda m: (
                        m.script_step_id == current_step_sudo
                        and m.mail_message_id.author_id
                        == chatbot_script.operator_partner_id
                    )
                )[:1]
            current_step = {
                "scriptStep": current_step_sudo.id,
                "message": step_message.mail_message_id.id,
                "operatorFound": current_step_sudo.is_forward_operator
                and channel.livechat_operator_id != chatbot_script.operator_partner_id,
            }
            store.add(current_step_sudo)
            store.add(chatbot_script)
            chatbot_data = {
                "script": chatbot_script.id,
                "steps": [current_step],
                "currentStep": current_step,
            }
            store.add(channel, {"chatbot": chatbot_data})

    @api.autovacuum
    def _gc_empty_livechat_sessions(self):
        hours = 1
        self.env.cr.execute(
            """
            SELECT id as id
            FROM discuss_channel C
            WHERE NOT EXISTS (
                SELECT 1
                FROM mail_message M
                WHERE M.res_id = C.id AND m.model = 'discuss.channel'
            ) AND C.channel_type = 'livechat' AND livechat_channel_id IS NOT NULL AND
                COALESCE(write_date, create_date, (now() at time zone 'UTC'))::timestamp
                < ((now() at time zone 'UTC') - interval %s)""",
            ("%s hours" % hours,),
        )
        empty_channel_ids = [item["id"] for item in self.env.cr.dictfetchall()]
        self.browse(empty_channel_ids).unlink()

    @api.autovacuum
    def _gc_bot_only_ongoing_sessions(self):
        stale_sessions = self.search(
            [
                ("channel_type", "=", "livechat"),
                ("livechat_end_dt", "=", False),
                ("last_interest_dt", "<=", "-1d"),
                ("livechat_agent_partner_ids", "=", False),
            ]
        )
        stale_sessions.livechat_end_dt = fields.Datetime.now()

    def execute_command_history(self, **kwargs):
        self._bus_send(
            "im_livechat.history_command",
            {"id": self.id, "partner_id": self.env.user.partner_id.id},
        )

    def _get_visitor_leave_message(self, operator=False, cancel=False):
        return _("Visitor left the conversation.")

    def _close_livechat_session(self, **kwargs):
        self.check_singleton()
        if not self.livechat_end_dt:
            member = self.channel_member_ids.filtered(lambda m: m.is_self)
            if member:
                member.sudo()._rtc_leave_call()
            self.sudo().livechat_end_dt = fields.Datetime.now()
            Store(bus_channel=self).add(self, "livechat_end_dt").bus_send()
            if not self.message_ids:
                return
            self.sudo().message_post(
                author_id=self.env.ref("base.partner_root").id,
                body=Markup('<div class="o_mail_notification o_hide_author">%s</div>')
                % self._get_visitor_leave_message(**kwargs),
                message_type="notification",
                subtype_xmlid="mail.mt_comment",
            )

    def _rating_get_parent_field_name(self):
        return "livechat_channel_id"

    def _email_livechat_transcript(self, email):
        company = self.env.user.company_id
        tz = "UTC"
        for customer in self.sudo().livechat_customer_history_ids:
            customer_tz = customer.partner_id.tz or customer.guest_id.timezone
            if customer_tz:
                tz = customer_tz
                break
        render_context = {
            "company": company,
            "channel": self,
            "tz": timezone(tz),
        }
        mail_body = self.env["ir.qweb"]._render(
            "im_livechat.livechat_email_template", render_context, minimal_qcontext=True
        )
        mail_body = self.env["mixin.mail.render"]._replace_local_links(mail_body)
        mail = (
            self.env["mail.mail"]
            .sudo()
            .create(
                {
                    "subject": _(
                        "Conversation with %s",
                        self.livechat_operator_id.user_livechat_username
                        or self.livechat_operator_id.name,
                    ),
                    "email_from": company.catchall_formatted or company.email_formatted,
                    "author_id": self.env.user.partner_id.id,
                    "email_to": email_split(email)[0],
                    "body_html": mail_body,
                }
            )
        )
        mail.send()

    def _attachment_to_html(self, attachment):
        if attachment.mimetype.startswith("image/"):
            return Markup(
                "<img src='%s?access_token=%s' alt='%s' style='max-width: 75%%; height: auto; padding: 5px;'>",
            ) % (
                attachment.image_src,
                attachment.generate_access_token()[0],
                attachment.name,
            )
        file_extension = get_extension(attachment.display_name)
        attachment_data = {
            "id": attachment.id,
            "access_token": attachment.generate_access_token()[0],
            "checksum": attachment.checksum,
            "extension": file_extension.lstrip("."),
            "mimetype": attachment.mimetype,
            "filename": attachment.display_name,
            "url": attachment.url,
        }
        return Markup(
            "<div data-embedded='file' data-oe-protected='true' contenteditable='false' data-embedded-props='%s'/>",
        ) % json.dumps({"fileData": attachment_data})

    def _get_channel_history(self):
        self.check_singleton()
        parts = []
        previous_message_author = None
        messages = (
            self.message_ids.sudo().filtered(lambda m: m.message_type != "notification")
            - self.message_ids.sudo()._filtered_empty()
        )
        for message in messages.sorted("id"):
            message_author = message.author_id.sudo() or message.author_guest_id
            if previous_message_author != message_author:
                parts.append(
                    Markup("<br/><strong>%s:</strong><br/>")
                    % (
                        (
                            message_author.user_livechat_username
                            if message_author._name == "res.partner"
                            else None
                        )
                        or message_author.name
                    ),
                )
            if not tools.is_html_empty(message.body):
                parts.append(Markup("%s<br/>") % html2plaintext(message.body))
                previous_message_author = message_author
            for attachment in message.attachment_ids:
                previous_message_author = message_author
                parts.append(
                    Markup("%s<br/>") % self._attachment_to_html(attachment.sudo())
                )
        return Markup("").join(parts)

    def _get_livechat_session_fields_to_store(self):
        return [
            Store.One(
                "livechat_lang_id",
                ["name"],
                predicate=is_livechat_channel,
            ),
        ]

    def _chatbot_find_customer_values_in_messages(self, step_type_to_field):
        values = {}
        filtered_message_ids = self.chatbot_message_ids.filtered(
            lambda m: m.script_step_id.sudo().step_type in step_type_to_field
        )
        for message_id in filtered_message_ids:
            field_name = step_type_to_field[message_id.script_step_id.step_type]
            if not values.get(field_name):
                values[field_name] = html2plaintext(message_id.user_raw_answer or "")

        return values

    def _chatbot_post_message(self, chatbot_script, body):
        return (
            self.with_context(mail_post_autofollow_author_skip=True)
            .sudo()
            .message_post(
                author_id=chatbot_script.sudo().operator_partner_id.id,
                body=body,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
        )

    def _chatbot_validate_email(self, email_address, chatbot_script):
        email_address = html2plaintext(email_address)
        email_normalized = email_normalize(email_address)

        posted_message = False
        error_message = False
        if not email_normalized:
            error_message = _(
                "'%(input_email)s' does not look like a valid email. Can you please try again?",
                input_email=email_address,
            )
            posted_message = self._chatbot_post_message(
                chatbot_script, plaintext2html(error_message)
            )

        return {
            "success": bool(email_normalized),
            "posted_message": posted_message,
            "error_message": error_message,
        }

    def _add_members(
        self,
        *,
        guests=None,
        partners=None,
        users=None,
        create_member_params=None,
        invite_to_rtc_call=False,
        post_joined_message=True,
        inviting_partner=None,
    ):
        all_new_members = super()._add_members(
            guests=guests,
            partners=partners,
            users=users,
            create_member_params=create_member_params,
            invite_to_rtc_call=invite_to_rtc_call,
            post_joined_message=post_joined_message,
            inviting_partner=inviting_partner,
        )
        for channel in all_new_members.channel_id:
            if channel.sudo().livechat_status == "need_help":
                channel.sudo().livechat_status = "in_progress"
        return all_new_members

    def _message_post_after_hook(self, message, msg_vals):
        if self.chatbot_current_step_id and not self.livechat_agent_history_ids:
            selected_answer = (
                self.env["chatbot.script.answer"]
                .browse(self.env.context.get("selected_answer_id"))
                .exists()
            )
            if (
                selected_answer
                and selected_answer in self.chatbot_current_step_id.answer_ids
            ):
                question_msg = (
                    self.env["chatbot.message"]
                    .sudo()
                    .search(
                        [
                            ("discuss_channel_id", "=", self.id),
                            ("script_step_id", "=", self.chatbot_current_step_id.id),
                        ],
                        order="id DESC",
                        limit=1,
                    )
                )
                question_msg.user_script_answer_id = selected_answer
                question_msg.user_raw_script_answer_id = selected_answer.id
                if store := self.env.context.get("message_post_store"):
                    store.add(message).add(question_msg.mail_message_id)
                partner, guest = self.env["res.partner"]._get_current_persona()
                Store(bus_channel=partner or guest).add_model_values(
                    "ChatbotStep",
                    {
                        "id": (
                            self.chatbot_current_step_id.id,
                            question_msg.mail_message_id.id,
                        ),
                        "scriptStep": self.chatbot_current_step_id.id,
                        "message": question_msg.mail_message_id.id,
                        "selectedAnswer": selected_answer.id,
                    },
                ).bus_send()

            self.env["chatbot.message"].sudo().create(
                {
                    "mail_message_id": message.id,
                    "discuss_channel_id": self.id,
                    "script_step_id": self.chatbot_current_step_id.id,
                }
            )

        author_history = self.env["im_livechat.channel.member.history"]
        if message.author_id or message.author_guest_id:
            author_history = self.sudo().livechat_channel_member_history_ids.filtered(
                lambda h: (
                    h.partner_id == message.author_id
                    if message.author_id
                    else h.guest_id == message.author_guest_id
                )
            )
        if author_history:
            if message.message_type not in ("notification", "user_notification"):
                author_history.message_count += 1
        if (
            author_history.livechat_member_type == "agent"
            and not author_history.response_time_hour
        ):
            author_history.response_time_hour = (
                fields.Datetime.now() - author_history.create_date
            ).total_seconds() / 3600
        if not self.livechat_end_dt and author_history.livechat_member_type == "agent":
            self.livechat_failure = "no_failure"
        if (
            not self.livechat_end_dt
            and self.sudo().livechat_status == "waiting"
            and author_history.livechat_member_type == "visitor"
        ):
            self.sudo().livechat_status = "in_progress"
        return super()._message_post_after_hook(message, msg_vals)

    def _chatbot_restart(self, chatbot_script):
        self.sudo().chatbot_current_step_id = False
        self.sudo().livechat_end_dt = False
        self.sudo().chatbot_message_ids.unlink()
        return self._chatbot_post_message(
            chatbot_script,
            Markup('<div class="o_mail_notification">%s</div>')
            % _("Restarting conversation..."),
        )

    def _get_allowed_channel_member_create_params(self):
        return super()._get_allowed_channel_member_create_params() + [
            "chatbot_script_id",
            "livechat_member_type",
        ]

    @classmethod
    def _channel_type_policies(cls):
        return {
            **super()._channel_type_policies(),
            "livechat": ChannelTypePolicy(
                supports_group_authorization=False,
                narrates_membership_changes=True,
                auto_invites_members_to_call=True,
                allows_seen_infos=True,
                allows_unfollow=True,
                member_based_naming=False,
                lazy_loads_members=False,
                supports_sub_channels=False,
                has_description=False,
                default_avatar=None,
                max_members=None,
                email_invite="never",
                push_title="name",
                push_icon_is_sender=False,
                searchable_by_name=True,
                describes_as_channel=False,
                sub_channel_invites_mentioned=False,
                notify_opted_in_only=False,
            ),
        }

    def _action_unfollow(self, partner=None, guest=None, post_leave_message=True):
        super()._action_unfollow(partner, guest, post_leave_message)
        channel_sudo = self.sudo()
        if (
            channel_sudo.channel_type == "livechat"
            and not channel_sudo.livechat_end_dt
            and channel_sudo.member_count == 1
        ):
            channel_sudo.livechat_end_dt = fields.Datetime.now()
            Store(bus_channel=self).add(channel_sudo, "livechat_end_dt").bus_send()

    def livechat_join_channel_needing_help(self):
        self.check_singleton()
        if self.livechat_status != "need_help":
            return False
        self._add_members(users=self.env.user)
        return True

    def _forward_human_operator(self, chatbot_script_step=None, users=None):
        human_operator = False
        posted_message = self.env["mail.message"]
        if chatbot_script_step is None:
            chatbot_script_step = self.env["chatbot.script.step"]

        if self.livechat_channel_id:
            human_operator = self._get_human_operator(users, chatbot_script_step)

        if human_operator and human_operator != self.env.user:
            posted_message = self._post_current_chatbot_step_message(
                chatbot_script_step
            )

            channel_sudo = self.sudo()
            bot_partner_id = channel_sudo.channel_member_ids.filtered(
                lambda m: m.livechat_member_type == "bot"
            ).partner_id

            create_member_params = {"livechat_member_type": "agent"}
            if chatbot_script_step.operator_expertise_ids:
                create_member_params["agent_expertise_ids"] = (
                    chatbot_script_step.operator_expertise_ids.ids
                )
                channel_sudo.livechat_expertise_ids |= (
                    chatbot_script_step.operator_expertise_ids
                )
            channel_sudo._add_new_members_to_channel(
                create_member_params=create_member_params,
                inviting_partner=bot_partner_id,
                users=human_operator,
            )
            channel_sudo._action_unfollow(
                partner=bot_partner_id, post_leave_message=False
            )

            channel_sudo._update_forwarded_channel_data(
                livechat_failure="no_answer",
                livechat_operator_id=human_operator.partner_id,
                operator_name=human_operator.livechat_username or human_operator.name,
            )
            channel_sudo._add_next_step_message_to_store(chatbot_script_step)
            channel_sudo._broadcast(human_operator.partner_id.ids)
            self.channel_pin(pinned=True)
        else:
            self.sudo().livechat_failure = "no_agent"

        return posted_message

    def _get_human_operator(self, users, chatbot_script_step):
        operator_params = {
            "lang": self.env.context.get("lang"),
            "country_id": self.country_id.id,
            "users": users,
        }
        if chatbot_script_step:
            operator_params["expertises"] = chatbot_script_step.operator_expertise_ids
        human_operator = self.livechat_channel_id.sudo()._get_operator(
            **operator_params
        )
        return human_operator

    def _post_current_chatbot_step_message(self, chatbot_script_step):
        posted_message = self.env["mail.message"]
        if chatbot_script_step and chatbot_script_step.message:
            posted_message = self._chatbot_post_message(
                chatbot_script_step.chatbot_script_id, chatbot_script_step.message
            )
        return posted_message

    def _add_new_members_to_channel(
        self, create_member_params, inviting_partner, users=None, partners=None
    ):
        member_params = {
            "create_member_params": create_member_params,
            "inviting_partner": inviting_partner,
        }
        if users:
            member_params["users"] = users
        if partners:
            member_params["partners"] = partners
        self._add_members(**member_params)

    def _update_forwarded_channel_data(
        self, /, *, livechat_failure, livechat_operator_id, operator_name
    ):
        self.write(
            {
                "livechat_failure": livechat_failure,
                "livechat_operator_id": livechat_operator_id,
                "name": " ".join(
                    [
                        self.env.user.display_name
                        if not self.env.user._is_public()
                        else self.sudo().self_member_id.guest_id.name,
                        operator_name,
                    ]
                ),
            }
        )

    def _add_next_step_message_to_store(self, chatbot_script_step):
        if chatbot_script_step:
            step_message = next(
                (
                    m.mail_message_id
                    for m in self.sudo().chatbot_message_ids.sorted("id")
                    if m.script_step_id == chatbot_script_step
                    and m.mail_message_id.author_id
                    == chatbot_script_step.chatbot_script_id.operator_partner_id
                ),
                self.env["mail.message"],
            )
            Store(bus_channel=self).add_model_values(
                "ChatbotStep",
                {
                    "id": (chatbot_script_step.id, step_message.id),
                    "scriptStep": chatbot_script_step.id,
                    "message": step_message.id,
                    "operatorFound": True,
                },
            ).bus_send()
