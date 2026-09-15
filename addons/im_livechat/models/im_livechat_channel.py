import random
import re
from collections import defaultdict
from datetime import timedelta
from urllib.parse import urlparse

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain

from odoo.addons.bus.websocket import WebsocketConnectionHandler
from odoo.addons.mail.tools.discuss import Store

BUFFER_TIME = 120


class Im_LivechatChannel(models.Model):
    _name = "im_livechat.channel"
    _inherit = ["mixin.rating.parent"]
    _description = "Livechat Channel"
    _rating_satisfaction_days = 14

    def _default_user_ids(self):
        return [(6, 0, [self.env.uid])]

    def _default_button_text(self):
        return _("Need help? Chat with us.")

    def _default_default_message(self):
        return _("How may I help you?")

    name = fields.Char(
        string="Channel Name",
        required=True,
    )
    button_text = fields.Char(
        string="Text of the Button",
        translate=True,
        default=_default_button_text,
    )
    default_message = fields.Char(
        string="Welcome Message",
        translate=True,
        default=_default_default_message,
        help="This is an automated 'welcome' message that your visitor will see when they initiate a new conversation.",
    )
    header_background_color = fields.Char(
        default="#875A7B",
        help="Default background color of the channel header once open",
    )
    title_color = fields.Char(
        default="#FFFFFF",
        help="Default title color of the channel once open",
    )
    button_background_color = fields.Char(
        default="#875A7B",
        help="Default background color of the Livechat button",
    )
    button_text_color = fields.Char(
        default="#FFFFFF",
        help="Default text color of the Livechat button",
    )
    max_sessions_mode = fields.Selection(
        selection=[("unlimited", "Unlimited"), ("limited", "Limited")],
        string="Sessions per Operator",
        default="unlimited",
        help="If limited, operators will only handle the selected number of sessions at a time.",
    )
    max_sessions = fields.Integer(
        string="Maximum Sessions",
        default=10,
        help="Maximum number of concurrent sessions per operator.",
    )
    block_assignment_during_call = fields.Boolean(
        string="No Chats During Call",
        help="While on a call, agents will not receive new conversations.",
    )
    review_link = fields.Char(
        help="Visitors who leave a positive review will be redirected to this optional link."
    )

    web_page = fields.Char(
        compute="_compute_web_page_link",
        store=False,
        readonly=True,
        help="URL to a static page where you client can discuss with the operator of the channel.",
    )
    are_you_inside = fields.Boolean(
        string="Are you inside the matrix?",
        compute="_compute_are_you_inside",
        store=False,
        readonly=True,
    )
    available_operator_ids = fields.Many2many(
        comodel_name="res.users",
        compute="_compute_available_operator_ids",
    )
    script_external = fields.Html(
        string="Script (external)",
        sanitize=False,
        compute="_compute_script_external",
        store=False,
        readonly=True,
    )
    nbr_channel = fields.Integer(
        string="Number of conversation",
        compute="_compute_nbr_channel",
        store=False,
        readonly=True,
    )

    user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="im_livechat_channel_im_user",
        column1="channel_id",
        column2="user_id",
        string="Agents",
        default=_default_user_ids,
    )
    channel_ids = fields.One2many(
        comodel_name="discuss.channel",
        inverse_name="livechat_channel_id",
        string="Sessions",
    )
    chatbot_script_count = fields.Integer(
        string="Number of Chatbot",
        compute="_compute_chatbot_script_count",
    )
    rule_ids = fields.One2many(
        comodel_name="im_livechat.channel.rule",
        inverse_name="channel_id",
        string="Rules",
    )
    ongoing_session_count = fields.Integer(
        string="Number of Ongoing Sessions",
        compute="_compute_ongoing_sessions_count",
    )
    remaining_session_capacity = fields.Integer(
        compute="_compute_remaining_session_capacity"
    )

    _max_sessions_mode_greater_than_zero = models.Constraint(
        "CHECK(max_sessions > 0)",
        "Concurrent session number should be greater than zero.",
    )

    def web_read(self, specification: dict[str, dict]) -> list[dict]:
        user_context = specification.get("user_ids", {}).get("context", {})
        if len(self) == 1 and user_context.pop("add_livechat_channel_ctx", None):
            user_context["im_livechat_channel_id"] = self.id
        return super().web_read(specification)

    def _compute_are_you_inside(self):
        for channel in self:
            channel.are_you_inside = self.env.user in channel.user_ids

    @api.depends("channel_ids.livechat_end_dt")
    def _compute_ongoing_sessions_count(self):
        count_by_channel = defaultdict(int)
        for (
            key,
            count,
        ) in self._get_ongoing_session_count_by_agent_livechat_channel().items():
            count_by_channel[key[1]] += count
        for channel in self:
            channel.ongoing_session_count = count_by_channel.get(channel, 0)

    @api.depends(
        "block_assignment_during_call",
        "max_sessions",
        "user_ids.livechat_is_in_call",
        "user_ids.livechat_ongoing_session_count",
    )
    def _compute_remaining_session_capacity(self):
        count = self._get_ongoing_session_count_by_agent_livechat_channel()
        for channel in self:
            users = channel.user_ids
            if channel.block_assignment_during_call:
                users = users.filtered(lambda u: not u.livechat_is_in_call)
            total_capacity = channel.max_sessions * len(users)
            capacity = total_capacity - sum(
                count.get((user.partner_id, channel), 0) for user in users
            )
            channel.remaining_session_capacity = max(capacity, 0)

    @api.depends(
        "user_ids.channel_ids.last_interest_dt",
        "user_ids.channel_ids.livechat_end_dt",
        "user_ids.channel_ids.livechat_channel_id",
        "user_ids.channel_ids.livechat_operator_id",
        "user_ids.channel_member_ids",
        "user_ids.im_status",
        "user_ids.is_in_call",
        "user_ids.partner_id",
    )
    def _compute_available_operator_ids(self):
        operators_by_livechat_channel = (
            self._get_available_operators_by_livechat_channel()
        )
        for livechat_channel in self:
            livechat_channel.available_operator_ids = operators_by_livechat_channel[
                livechat_channel
            ]

    @api.constrains("review_link")
    def _check_review_link(self):
        for record in self.filtered("review_link"):
            url = urlparse(record.review_link)
            if url.scheme not in ("http", "https") or not url.netloc:
                raise ValidationError(
                    self.env._(
                        "Invalid URL '%s'. The Review Link must start with 'http://' or 'https://'."
                    )
                    % record.review_link
                )

    def _get_available_operators_by_livechat_channel(self, users=None):
        counts = {}
        if livechat_channels := self.filtered(
            lambda c: c.max_sessions_mode == "limited"
        ):
            counts = (
                livechat_channels._get_ongoing_session_count_by_agent_livechat_channel(
                    users, filter_online=True
                )
            )

        def is_available(user, channel):
            return (
                user.sudo().presence_ids.status == "online"
                and (
                    channel.max_sessions_mode == "unlimited"
                    or counts.get((user.partner_id, channel), 0) < channel.max_sessions
                )
                and (
                    not channel.block_assignment_during_call
                    or not user.sudo().is_in_call
                )
            )

        operators_by_livechat_channel = {}
        for livechat_channel in self:
            possible_users = users if users is not None else livechat_channel.user_ids
            operators_by_livechat_channel[livechat_channel] = possible_users.filtered(
                lambda user, livechat_channel=livechat_channel: is_available(
                    user, livechat_channel
                )
            )
        return operators_by_livechat_channel

    def _get_ongoing_session_count_by_agent_livechat_channel(
        self, users=None, filter_online=False
    ):
        user_domain = Domain(False)
        for channel in self:
            active_users = users if users is not None else channel.user_ids
            if filter_online:
                active_users = active_users.filtered(
                    lambda u: u.sudo().presence_ids.status == "online"
                )
            user_domain |= Domain(
                [
                    ("partner_id", "in", active_users.partner_id.ids),
                    ("channel_id.livechat_channel_id", "in", channel.ids),
                ]
            )
        counts = self.env["discuss.channel.member"]._read_group(
            Domain("channel_id.livechat_end_dt", "=", False)
            & Domain("channel_id.last_interest_dt", ">=", "-15M")
            & user_domain,
            groupby=["partner_id", "channel_id.livechat_channel_id"],
            aggregates=["__count"],
        )
        return {(partner, channel): count for (partner, channel, count) in counts}

    @api.depends("rule_ids.chatbot_script_id")
    def _compute_chatbot_script_count(self):
        data = self.env["im_livechat.channel.rule"]._read_group(
            [("channel_id", "in", self.ids)],
            ["channel_id"],
            ["chatbot_script_id:count_distinct"],
        )
        mapped_data = {channel.id: count_distinct for channel, count_distinct in data}
        for channel in self:
            channel.chatbot_script_count = mapped_data.get(channel.id, 0)

    def _compute_script_external(self):
        values = {
            "dbname": self.env.cr.dbname,
        }
        for record in self:
            values["channel_id"] = record.id
            values["url"] = record.get_base_url()
            record.script_external = (
                self.env["ir.qweb"]._render("im_livechat.external_loader", values)
                if record.id
                else False
            )

    def _compute_web_page_link(self):
        for record in self:
            record.web_page = (
                "%s/im_livechat/support/%i" % (record.get_base_url(), record.id)
                if record.id
                else False
            )

    @api.depends("channel_ids")
    def _compute_nbr_channel(self):
        data = self.env["discuss.channel"]._read_group(
            [
                ("livechat_channel_id", "in", self.ids),
            ],
            ["livechat_channel_id"],
            ["__count"],
        )
        channel_count = {livechat_channel.id: count for livechat_channel, count in data}
        for record in self:
            record.nbr_channel = channel_count.get(record.id, 0)

    def action_join(self):
        self.check_singleton()
        if not self.env.user.has_group("im_livechat.im_livechat_group_user"):
            raise AccessError(_("Only Live Chat operators can join Live Chat channels"))
        self.sudo().user_ids = [Command.link(self.env.user.id)]
        Store(bus_channel=self.env.user).add(
            self, ["are_you_inside", "name"]
        ).bus_send()

    def action_quit(self):
        self.check_singleton()
        self.sudo().user_ids = [Command.unlink(self.env.user.id)]
        Store(bus_channel=self.env.user).add(
            self.sudo(), ["are_you_inside", "name"]
        ).bus_send()

    def action_view_rating(self):
        self.check_singleton()
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "im_livechat.discuss_channel_action_from_livechat_channel"
        )
        action["context"] = {
            "search_default_parent_res_name": self.name,
            "search_default_fiter_session_rated": "1",
        }
        return action

    def action_view_chatbot_scripts(self):
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "im_livechat.chatbot_script_action"
        )
        chatbot_script_ids = (
            self.env["im_livechat.channel.rule"]
            .search([("channel_id", "in", self.ids)])
            .mapped("chatbot_script_id")
        )
        if len(chatbot_script_ids) == 1:
            action["res_id"] = chatbot_script_ids.id
            action["view_mode"] = "form"
            action["views"] = [(False, "form")]
        else:
            action["domain"] = [("id", "in", chatbot_script_ids.ids)]
        return action

    def _prepare_livechat_discuss_channel_vals(
        self,
        /,
        *,
        chatbot_script=None,
        agent=None,
        operator_partner,
        operator_model,
        **kwargs,
    ):
        now = fields.Datetime.now()
        last_interest_dt = now - timedelta(seconds=1)
        members_to_add = [
            Command.create(
                self._prepare_agent_member_vals(
                    last_interest_dt=last_interest_dt,
                    now=now,
                    chatbot_script=chatbot_script,
                    operator_partner=operator_partner,
                    operator_model=operator_model,
                    **kwargs,
                )
            )
        ]
        guest = self.env["mail.guest"]._get_guest_from_context()
        if guest and self.env.user._is_public():
            members_to_add.append(
                Command.create(
                    {"livechat_member_type": "visitor", "guest_id": guest.id}
                )
            )
        visitor_user = self.env["res.users"]
        if not self.env.user._is_public():
            visitor_user = self.env.user
            if visitor_user and visitor_user != agent:
                members_to_add.append(
                    Command.create(
                        {
                            "livechat_member_type": "visitor",
                            "partner_id": visitor_user.partner_id.id,
                        }
                    )
                )

        channel_name = self._get_channel_name(
            visitor_user=visitor_user,
            guest=guest,
            agent=agent,
            chatbot_script=chatbot_script,
            operator_model=operator_model,
            **kwargs,
        )
        is_chatbot_script = operator_model == "chatbot.script"
        is_agent = operator_model == "res.users"
        return {
            "channel_member_ids": members_to_add,
            "last_interest_dt": last_interest_dt,
            "livechat_operator_id": operator_partner.id,
            "livechat_channel_id": self.id,
            "livechat_failure": "no_answer" if is_agent else "no_failure",
            "livechat_status": "in_progress",
            "chatbot_current_step_id": chatbot_script._get_welcome_steps()[-1].id
            if is_chatbot_script
            else False,
            "channel_type": "livechat",
            "name": channel_name,
        }

    def _prepare_agent_member_vals(
        self,
        /,
        *,
        last_interest_dt,
        now,
        chatbot_script,
        operator_partner,
        operator_model,
        **kwargs,
    ):
        return {
            "chatbot_script_id": chatbot_script.id
            if operator_model == "chatbot.script"
            else False,
            "last_interest_dt": last_interest_dt,
            "livechat_member_type": "agent" if operator_model == "res.users" else "bot",
            "partner_id": operator_partner.id,
            "unpin_dt": now,
        }

    def _get_channel_name(
        self,
        /,
        *,
        visitor_user=None,
        guest=None,
        agent,
        chatbot_script,
        operator_model,
        **kwargs,
    ):
        if operator_model == "chatbot.script":
            channel_name = chatbot_script.title
        else:
            channel_name = " ".join(
                [
                    visitor_user.display_name if visitor_user else guest.name,
                    agent.livechat_username or agent.name,
                ]
            )
        return channel_name

    def _get_operator_info(
        self,
        /,
        *,
        lang,
        country_id,
        previous_operator_id=None,
        chatbot_script_id=None,
        **kwargs,
    ):
        agent = self.env["res.users"]
        chatbot_script = self.env["chatbot.script"]
        operator_partner = self.env["res.partner"]
        operator_model = ""

        if (
            chatbot_script_id
            and chatbot_script_id in self.rule_ids.chatbot_script_id.ids
        ):
            chatbot_script = (
                self.env["chatbot.script"]
                .sudo()
                .with_context(lang=self.env["chatbot.script"]._get_chatbot_language())
                .search([("id", "=", chatbot_script_id)])
            )
            operator_partner = chatbot_script.operator_partner_id
            operator_model = "chatbot.script"

        if not operator_model:
            agent = self._get_operator(
                previous_operator_id=previous_operator_id,
                lang=lang,
                country_id=country_id,
            )
            operator_partner = agent.partner_id
            operator_model = "res.users"

        return {
            "agent": agent,
            "chatbot_script": chatbot_script,
            "operator_partner": operator_partner,
            "operator_model": operator_model,
        }

    def _get_less_active_operator(self, operator_statuses, operators):
        if not operators:
            return False

        operator_statuses = [
            s
            for s in operator_statuses
            if s["partner_id"] in set(operators.partner_id.ids)
        ]

        active_op_partner_ids = {s["partner_id"] for s in operator_statuses}
        candidates = operators.filtered(
            lambda o: o.partner_id.id not in active_op_partner_ids
        )
        if candidates:
            return random.choice(candidates)

        best_status = operator_statuses[0]
        best_status_op_partner_ids = {
            s["partner_id"]
            for s in operator_statuses
            if (s["count"], s["in_call"])
            == (best_status["count"], best_status["in_call"])
        }
        candidates = operators.filtered(
            lambda o: o.partner_id.id in best_status_op_partner_ids
        )
        return random.choice(candidates)

    def _get_operator(
        self,
        previous_operator_id=None,
        lang=None,
        country_id=None,
        expertises=None,
        users=None,
    ):
        self.check_singleton()
        self.env["discuss.channel.rtc.session"].sudo()._gc_inactive_sessions()
        users = users if users is not None else self.available_operator_ids
        if not users:
            return self.env["res.users"]
        if expertises is None:
            expertises = self.env["im_livechat.expertise"]
        self.env.cr.execute(
            """
                WITH operator_rtc_session AS (
                    SELECT COUNT(DISTINCT s.id) as nbr, member.partner_id as partner_id
                      FROM discuss_channel_rtc_session s
                      JOIN discuss_channel_member member ON (member.id = s.channel_member_id)
                  GROUP BY member.partner_id
                )
               SELECT COUNT(DISTINCT h.channel_id), COALESCE(rtc.nbr, 0) > 0 as in_call, h.partner_id
                 FROM im_livechat_channel_member_history h
                 JOIN discuss_channel c ON h.channel_id = c.id
      LEFT OUTER JOIN operator_rtc_session rtc ON rtc.partner_id = h.partner_id
                WHERE c.livechat_end_dt IS NULL
                  AND c.last_interest_dt > ((now() at time zone 'UTC') - interval '30 minutes')
                  AND h.partner_id = ANY(%s)
             GROUP BY h.partner_id, rtc.nbr
             ORDER BY COUNT(DISTINCT h.channel_id) < 2 OR rtc.nbr IS NULL DESC,
                      COUNT(DISTINCT h.channel_id) ASC,
                      rtc.nbr IS NULL DESC
            """,
            (list(users.partner_id.ids),),
        )
        operator_statuses = self.env.cr.dictfetchall()
        if previous_operator_id in users.partner_id.ids:
            previous_operator_status = next(
                (
                    status
                    for status in operator_statuses
                    if status["partner_id"] == previous_operator_id
                ),
                None,
            )
            if (
                not previous_operator_status
                or previous_operator_status["count"] < 2
                or not previous_operator_status["in_call"]
            ):
                return next(
                    available_user
                    for available_user in users
                    if available_user.partner_id.id == previous_operator_id
                )

        agents_failing_buffer = {
            group[0]
            for group in self.env["im_livechat.channel.member.history"]._read_group(
                [
                    ("livechat_member_type", "=", "agent"),
                    ("partner_id", "in", users.partner_id.ids),
                    ("channel_id.livechat_end_dt", "=", False),
                    (
                        "create_date",
                        ">",
                        fields.Datetime.now() - timedelta(seconds=BUFFER_TIME),
                    ),
                ],
                groupby=["partner_id"],
            )
        }

        def same_language(operator):
            return (
                operator.partner_id.lang == lang
                or lang in operator.livechat_lang_ids.mapped("code")
            )

        def all_expertises(operator):
            return operator.livechat_expertise_ids >= expertises

        def one_expertise(operator):
            return operator.livechat_expertise_ids & expertises

        def same_country(operator):
            return operator.partner_id.country_id.id == country_id

        preferences_list = [
            [same_language, all_expertises],
            [same_language, one_expertise],
            [same_language],
            [same_country, all_expertises],
            [same_country, one_expertise],
            [same_country],
            [all_expertises],
            [one_expertise],
        ]
        for preferences in preferences_list:
            operators = users
            for preference in preferences:
                operators = operators.filtered(preference)
            if operators:
                if agents_respecting_buffer := operators.filtered(
                    lambda op: op.partner_id not in agents_failing_buffer
                ):
                    operators = agents_respecting_buffer
                return self._get_less_active_operator(operator_statuses, operators)
        return self._get_less_active_operator(operator_statuses, users)

    def _get_channel_infos(self):
        self.check_singleton()

        return {
            "header_background_color": self.header_background_color,
            "button_background_color": self.button_background_color,
            "title_color": self.title_color,
            "button_text_color": self.button_text_color,
            "button_text": self.button_text,
            "default_message": self.default_message,
            "channel_name": self.name,
            "channel_id": self.id,
            "review_link": self.review_link,
        }

    def get_livechat_info(self, username=None):
        self.check_singleton()

        if username is None:
            username = _("Visitor")
        info = {}
        info["available"] = self._is_livechat_available()
        info["server_url"] = self.get_base_url()
        info["websocket_worker_version"] = WebsocketConnectionHandler._VERSION
        if info["available"]:
            info["options"] = self._get_channel_infos()
            info["options"]["default_username"] = username
        return info

    def _is_livechat_available(self):
        return self.chatbot_script_count or len(self.available_operator_ids) > 0


class Im_LivechatChannelRule(models.Model):
    _name = "im_livechat.channel.rule"
    _description = "Livechat Channel Rules"
    _order = "sequence asc"

    regex_url = fields.Char(
        string="URL Regex",
        help="Regular expression specifying the web pages this rule will be applied on.",
    )
    action = fields.Selection(
        selection=[
            ("display_button", "Show"),
            ("display_button_and_text", "Show with notification"),
            ("auto_popup", "Open automatically"),
            ("hide_button", "Hide"),
        ],
        string="Live Chat Button",
        default="display_button",
        required=True,
        help="* 'Show' displays the chat button on the pages.\n"
        "* 'Show with notification' is 'Show' in addition to a floating text just next to the button.\n"
        "* 'Open automatically' displays the button and automatically opens the conversation pane.\n"
        "* 'Hide' hides the chat button on the pages.\n",
    )
    auto_popup_timer = fields.Integer(
        string="Time to Open",
        default=0,
        help="Delay (in seconds) to automatically open the conversation window. Note: the selected action must be 'Open automatically' otherwise this parameter will not be taken into account.",
    )
    chatbot_script_id = fields.Many2one(
        comodel_name="chatbot.script",
        string="Chatbot",
    )
    chatbot_enabled_condition = fields.Selection(
        selection=[
            ("always", "Always"),
            ("only_if_no_operator", "Only when no operator is available"),
            ("only_if_operator", "Only when an operator is available"),
        ],
        string="Enable ChatBot",
        default="always",
        required=True,
    )
    channel_id = fields.Many2one(
        comodel_name="im_livechat.channel",
        index="btree_not_null",
        help="The channel of the rule",
    )
    country_ids = fields.Many2many(
        comodel_name="res.country",
        relation="im_livechat_channel_country_rel",
        column1="channel_id",
        column2="country_id",
        string="Countries",
        help="The rule will only be applied for these countries. Example: if you select 'Belgium' and 'United States' and that you set the action to 'Hide', the chat button will be hidden on the specified URL from the visitors located in these 2 countries. This feature requires GeoIP installed on your server.",
    )
    sequence = fields.Integer(
        string="Matching order",
        default=10,
        help="Given the order to find a matching rule. If 2 rules are matching for the given url/country, the one with the lowest sequence will be chosen.",
    )

    def match_rule(self, channel_id, url, country_id=False):
        def _match(rules):
            for rule in rules:
                if not re.search(rule.regex_url or "", url or ""):
                    continue
                if rule.chatbot_script_id and (
                    not rule.chatbot_script_id.active
                    or not rule.chatbot_script_id.script_step_ids
                ):
                    continue
                if (
                    rule.chatbot_enabled_condition == "only_if_operator"
                    and not rule.channel_id.available_operator_ids
                ) or (
                    rule.chatbot_enabled_condition == "only_if_no_operator"
                    and rule.channel_id.available_operator_ids
                ):
                    continue
                return rule
            return self.env["im_livechat.channel.rule"]

        if country_id:
            domain = [
                ("country_ids", "in", [country_id]),
                ("channel_id", "=", channel_id),
            ]
            rule = _match(self.search(domain))
            if rule:
                return rule
        domain = [("country_ids", "=", False), ("channel_id", "=", channel_id)]
        return _match(self.search(domain))

    def _is_bot_configured(self):
        return bool(self.chatbot_script_id)

    def _to_store_defaults(self, target):
        return [
            "action",
            "auto_popup_timer",
            Store.One("chatbot_script_id"),
        ]
