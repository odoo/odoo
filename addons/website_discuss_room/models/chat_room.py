# Part of Odoo. See LICENSE file for full copyright and licensing details.

from uuid import uuid4

from odoo import api, fields, models


class ChatRoom(models.Model):
    """ Store all useful information to manage chat room.
    This model embeds all information about the chat room. We do not
    store them in the related mixin (see chat.room.mixin) to avoid to add too
    many fields on the models which want to use the chat room mixin as the
    behavior can be optional in those models.
    """
    _name = "chat.room"
    _description = "Chat Room"

    def _default_name(self, objname='room'):
        return "odoo-%s-%s" % (objname, str(uuid4())[:8])

    name = fields.Char(
        "Room Name", required=True, copy=False,
        default=lambda self: self._default_name())
    chat_room_provider = fields.Selection(
        [('discuss', 'Discuss')],
        string="Chat Room Provider", default='discuss', required=True)
    discuss_channel_id = fields.Many2one("discuss.channel", "Discuss Channel", copy=False)
    is_full = fields.Boolean("Full", compute="_compute_is_full")
    lang_id = fields.Many2one(
        "res.lang", "Language",
        default=lambda self: self.env['res.lang']._lang_get(self.env.user.lang))
    max_capacity = fields.Selection(
        [("4", "4"), ("8", "8"), ("12", "12"), ("16", "16"),
         ("20", "20"), ("no_limit", "No limit")], string="Max capacity",
        default="8", required=True)
    participant_count = fields.Integer("Participant count", store=False, compute="_compute_participant_count", copy=False)
    # reporting fields
    last_activity = fields.Datetime(
        "Last Activity", copy=False, readonly=True,
        default=lambda self: fields.Datetime.now())
    max_participant_reached = fields.Integer(
        "Max participant reached", copy=False, readonly=True,
        help="Maximum number of participant reached in the room at the same time")

    @api.depends("max_capacity", "participant_count")
    def _compute_is_full(self):
        for room in self:
            if room.max_capacity == "no_limit":
                room.is_full = False
            else:
                room.is_full = room.participant_count >= int(room.max_capacity)

    @api.depends("discuss_channel_id.rtc_session_ids")
    def _compute_participant_count(self):
        for room in self:
            room.participant_count = len(room.discuss_channel_id.rtc_session_ids)

    def get_room_url(self):
        self.ensure_one()
        channel = self._get_or_create_discuss_channel()
        return channel.invitation_url

    def _get_or_create_discuss_channel(self):
        self.ensure_one()
        if not self.discuss_channel_id:
            self.discuss_channel_id = self.env["discuss.channel"].channel_create(
                self.name,
                [],
            )
            self.discuss_channel_id.default_display_mode = 'video_full_screen'
        return self.discuss_channel_id
