from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ImLivechatChannelMemberHistory(models.Model):
    _name = "im_livechat.channel.member.history"
    _description = "Keep the channel member history"
    _rec_names_search = ["partner_id", "guest_id"]

    member_id = fields.Many2one(
        comodel_name="discuss.channel.member",
        index="btree_not_null",
    )
    livechat_member_type = fields.Selection(
        selection=[("agent", "Agent"), ("visitor", "Visitor"), ("bot", "Chatbot")],
        compute="_compute_member_fields",
        store=True,
    )
    channel_id = fields.Many2one(
        comodel_name="discuss.channel",
        compute="_compute_member_fields",
        store=True,
        index=True,
        ondelete="cascade",
    )
    guest_id = fields.Many2one(
        comodel_name="mail.guest",
        compute="_compute_member_fields",
        store=True,
        index="btree_not_null",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        compute="_compute_member_fields",
        store=True,
        index="btree_not_null",
    )
    chatbot_script_id = fields.Many2one(
        comodel_name="chatbot.script",
        compute="_compute_member_fields",
        store=True,
        index="btree_not_null",
    )
    agent_expertise_ids = fields.Many2many(
        comodel_name="im_livechat.expertise",
        compute="_compute_member_fields",
        store=True,
    )
    conversation_tag_ids = fields.Many2many(
        comodel_name="im_livechat.conversation.tag",
        related="channel_id.livechat_conversation_tag_ids",
    )
    avatar_128 = fields.Binary(compute="_compute_avatar_128")

    session_country_id = fields.Many2one(
        comodel_name="res.country",
        related="channel_id.country_id",
    )
    session_livechat_channel_id = fields.Many2one(
        comodel_name="im_livechat.channel",
        related="channel_id.livechat_channel_id",
        string="Live chat channel",
    )
    session_outcome = fields.Selection(related="channel_id.livechat_outcome")
    session_start_hour = fields.Float(related="channel_id.livechat_start_hour")
    session_week_day = fields.Selection(related="channel_id.livechat_week_day")
    session_duration_hour = fields.Float(
        string="Session Duration",
        compute="_compute_session_duration_hour",
        store=True,
        aggregator="avg",
        help="Time spent by the persona in the session in hours",
    )
    rating_id = fields.Many2one(
        comodel_name="rating.rating",
        compute="_compute_rating_id",
        store=True,
    )
    rating = fields.Float(related="rating_id.rating")
    rating_text = fields.Selection(
        related="rating_id.rating_text",
        string="Rating text",
    )
    call_history_ids = fields.Many2many(comodel_name="discuss.call.history")
    has_call = fields.Float(
        compute="_compute_has_call",
        store=True,
    )
    call_count = fields.Float(
        related="has_call",
        string="# of Sessions with Calls",
        aggregator="sum",
    )
    call_percentage = fields.Float(
        related="has_call",
        string="Session with Calls (%)",
        aggregator="avg",
    )
    call_duration_hour = fields.Float(
        string="Call Duration",
        compute="_compute_call_duration_hour",
        store=True,
        aggregator="sum",
    )
    message_count = fields.Integer(
        string="# of Messages per Session",
        aggregator="avg",
    )
    help_status = fields.Selection(
        selection=[
            ("requested", "Help Requested"),
            ("provided", "Help Provided"),
        ],
        compute="_compute_help_status",
        store=True,
    )
    response_time_hour = fields.Float(
        string="Response Time",
        aggregator="avg",
    )

    _member_id_unique = models.Constraint(
        "UNIQUE(member_id)", "Members can only be linked to one history"
    )
    _channel_id_partner_id_unique = models.UniqueIndex(
        "(channel_id, partner_id) WHERE partner_id IS NOT NULL",
        "One partner can only be linked to one history on a channel",
    )
    _channel_id_guest_id_unique = models.UniqueIndex(
        "(channel_id, guest_id) WHERE guest_id IS NOT NULL",
        "One guest can only be linked to one history on a channel",
    )
    _partner_id_or_guest_id_constraint = models.Constraint(
        "CHECK(partner_id IS NULL OR guest_id IS NULL)",
        "History should either be linked to a partner or a guest but not both",
    )

    @api.constrains("channel_id")
    def _constraint_channel_id(self):
        if failing_histories := self.sudo().filtered(
            lambda h: h.channel_id.channel_type != "livechat"
        ):
            raise ValidationError(
                self.env._(
                    "Cannot create history as it is only available for live chats: %(histories)s.",
                    histories=failing_histories.member_id.mapped("display_name"),
                )
            )

    @api.depends("member_id")
    def _compute_member_fields(self):
        for history in self:
            history.channel_id = history.channel_id or history.member_id.channel_id
            history.guest_id = history.guest_id or history.member_id.guest_id
            history.partner_id = history.partner_id or history.member_id.partner_id
            history.livechat_member_type = (
                history.livechat_member_type or history.member_id.livechat_member_type
            )
            history.chatbot_script_id = (
                history.chatbot_script_id or history.member_id.chatbot_script_id
            )
            history.agent_expertise_ids = (
                history.agent_expertise_ids or history.member_id.agent_expertise_ids
            )

    @api.depends(
        "livechat_member_type",
        "partner_id.name",
        "partner_id.display_name",
        "guest_id.name",
    )
    def _compute_display_name(self):
        for history in self:
            name = history.partner_id.name or history.guest_id.name
            if history.partner_id and history.livechat_member_type == "visitor":
                name = history.partner_id.display_name
            history.display_name = name or self.env._("Unknown")

    @api.depends("partner_id.avatar_128", "guest_id.avatar_128")
    def _compute_avatar_128(self):
        for history in self:
            history.avatar_128 = (
                history.partner_id.avatar_128 or history.guest_id.avatar_128
            )

    @api.depends("call_history_ids")
    def _compute_has_call(self):
        for history in self:
            history.has_call = 1 if history.call_history_ids else 0

    @api.depends("call_history_ids.duration_hour")
    def _compute_call_duration_hour(self):
        for history in self:
            history.call_duration_hour = sum(
                history.call_history_ids.mapped("duration_hour")
            )

    @api.depends(
        "channel_id.livechat_agent_requesting_help_history",
        "channel_id.livechat_agent_providing_help_history",
    )
    def _compute_help_status(self):
        agent_histories = self.filtered(lambda h: h.livechat_member_type == "agent")
        (self - agent_histories).help_status = None
        for history in agent_histories:
            if history.channel_id.livechat_agent_requesting_help_history == history:
                history.help_status = "requested"
            elif history.channel_id.livechat_agent_providing_help_history == history:
                history.help_status = "provided"

    @api.depends("channel_id.rating_ids")
    def _compute_rating_id(self):
        agent_histories = self.filtered(
            lambda h: h.livechat_member_type in ("agent", "bot")
        )
        (self - agent_histories).rating_id = None
        for history in agent_histories:
            history.rating_id = history.channel_id.rating_ids.filtered(
                lambda r: r.rated_partner_id == history.partner_id
            )[:1]

    @api.depends("create_date", "channel_id.livechat_end_dt", "channel_id.message_ids")
    def _compute_session_duration_hour(self):
        ongoing_chats = self.channel_id.filtered(lambda c: not c.livechat_end_dt)
        last_msg_dt_by_channel_id = {
            message.res_id: message.create_date
            for message in ongoing_chats._get_last_messages()
        }
        for history in self:
            end = history.channel_id.livechat_end_dt or last_msg_dt_by_channel_id.get(
                history.channel_id.id, fields.Datetime.now()
            )
            history.session_duration_hour = (
                end - history.create_date
            ).total_seconds() / 3600

    @api.model
    def action_view_discuss_channel_view(self, domain=()):
        discuss_channels = self.search_fetch(domain, ["channel_id"]).channel_id
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "im_livechat.discuss_channel_action"
        )
        if len(discuss_channels) == 1:
            action["res_id"] = discuss_channels.id
            action["view_mode"] = "form"
            action["views"] = [view for view in action["views"] if view[1] == "form"]
            return action
        action["context"] = {}
        action["domain"] = [("id", "in", discuss_channels.ids)]
        action["mobile_view_mode"] = "list"
        action["view_mode"] = "list"
        action["views"] = [
            view for view in action["views"] if view[1] in ("list", "form")
        ]
        return action
