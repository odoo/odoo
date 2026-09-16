# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

from odoo.addons.mail.tools.discuss import Store


class DiscussChannelMember(models.Model):
    _inherit = "discuss.channel.member"

    @api.model_create_multi
    def create(self, vals_list):
        members = super().create(vals_list)
        members._broadcast_meeting_invitation("ADD")
        return members

    def write(self, vals):
        # reading the conversation for the first time is what ends an invitation, joining
        # the call being pushed already (see `discuss.channel.rtc.session.create`)
        invited = self.browse()
        if vals.get("last_seen_dt"):
            invited = self.filtered(lambda member: not member.last_seen_dt and not member.rtc_session_ids)
        result = super().write(vals)
        invited._broadcast_meeting_invitation("DELETE")
        return result

    def _broadcast_meeting_invitation(self, mode):
        """ Push to their channel that these members of a meeting are now invited to it, or
        no longer are: that follows what they do rather than a ring (see
        `discuss.channel._compute_invited_member_ids`). """
        # sudo: calendar.event: whether a channel backs a meeting is not private
        meeting_members = self.filtered(lambda member: member.channel_id.sudo().calendar_event_ids)
        for channel, members in meeting_members.grouped("channel_id").items():
            Store(bus_channel=channel).add(
                channel,
                lambda res, members=members: res.many(
                    "invited_member_ids", "_store_avatar_card_fields", mode=mode, value=members,
                ),
            )
