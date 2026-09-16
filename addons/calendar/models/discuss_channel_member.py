# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.addons.mail.tools.discuss import Store


class DiscussChannelMember(models.Model):
    _inherit = "discuss.channel.member"

    @api.model_create_multi
    def create(self, vals_list):
        members = super().create(vals_list)
        members._broadcast_meeting_invitation("ADD")
        return members

    def write(self, vals):
        # reading the conversation or joining its call for the first time ends an invitation
        invited = self.browse()
        if vals.get("last_seen_dt"):
            invited = self.filtered(lambda member: not member.last_seen_dt)
        result = super().write(vals)
        invited._broadcast_meeting_invitation("DELETE")
        return result

    def _rtc_join_call(self, store: Store = None, check_rtc_session_ids=None, camera=False):
        # sudo: calendar.event: whether a channel backs a meeting is not private
        if not self.last_seen_dt and self.channel_id.sudo().calendar_event_ids:
            self.last_seen_dt = fields.Datetime.now()
        return super()._rtc_join_call(store=store, check_rtc_session_ids=check_rtc_session_ids, camera=camera)

    def _broadcast_meeting_invitation(self, mode):
        """ Push to their channel that these members of a meeting are now invited to it, or
        no longer are: that follows what they do rather than a ring (see
        `discuss.channel._compute_meeting_invited_member_ids`). """
        # sudo: calendar.event: whether a channel backs a meeting is not private
        meeting_members = self.filtered(lambda member: member.channel_id.sudo().calendar_event_ids)
        for channel, members in meeting_members.grouped("channel_id").items():
            Store(bus_channel=channel).add(
                channel,
                lambda res, members=members: res.many(
                    "meeting_invited_member_ids", "_store_avatar_card_fields", mode=mode, value=members,
                ),
            )
