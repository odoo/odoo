# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import http
from odoo.http import request
from odoo.tools import file_open


class RtcController(http.Controller):
    @http.route("/mail/rtc/session/notify_call_members", methods=["POST"], type="json", auth="public")
    def session_call_notify(self, peer_notifications):
        """Sends content to other session of the same channel, only works if the user is the user of that session.
        This is used to send peer to peer information between sessions.

        :param peer_notifications: list of tuple with the following elements:
            - int sender_session_id: id of the session from which the content is sent
            - list target_session_ids: list of the ids of the sessions that should receive the content
            - string content: the content to send to the other sessions
        """
        guest = request.env["mail.guest"]._get_guest_from_request(request)
        notifications_by_session = defaultdict(list)
        for sender_session_id, target_session_ids, content in peer_notifications:
            session_sudo = guest.env["discuss.channel.rtc.session"].sudo().browse(int(sender_session_id)).exists()
            if (
                not session_sudo
                or (session_sudo.guest_id and session_sudo.guest_id != guest)
                or (session_sudo.partner_id and session_sudo.partner_id != request.env.user.partner_id)
            ):
                continue
            notifications_by_session[session_sudo].append(([int(sid) for sid in target_session_ids], content))
        for session_sudo, notifications in notifications_by_session.items():
            session_sudo._notify_peers(notifications)

    @http.route("/mail/rtc/session/update_and_broadcast", methods=["POST"], type="json", auth="public")
    def session_update_and_broadcast(self, session_id, values):
        """Update a RTC session and broadcasts the changes to the members of its channel,
        only works of the user is the user of that session.
        :param int session_id: id of the session to update
        :param dict values: write dict for the fields to update
        """
        if request.env.user._is_public():
            guest = request.env["mail.guest"]._get_guest_from_request(request)
            if guest:
                session = guest.env["discuss.channel.rtc.session"].sudo().browse(int(session_id)).exists()
                if session and session.guest_id == guest:
                    session._update_and_broadcast(values)
                    return
            return
        session = request.env["discuss.channel.rtc.session"].sudo().browse(int(session_id)).exists()
        if session and session.partner_id == request.env.user.partner_id:
            session._update_and_broadcast(values)

    @http.route("/mail/rtc/channel/join_call", methods=["POST"], type="json", auth="public")
    def channel_call_join(self, channel_id, check_rtc_session_ids=None):
        """Joins the RTC call of a channel if the user is a member of that channel
        :param int channel_id: id of the channel to join
        """
        channel_member_sudo = request.env["discuss.channel.member"]._get_as_sudo_from_request_or_raise(
            request=request, channel_id=int(channel_id)
        )
        return channel_member_sudo._rtc_join_call(check_rtc_session_ids=check_rtc_session_ids)

    @http.route("/mail/rtc/channel/leave_call", methods=["POST"], type="json", auth="public")
    def channel_call_leave(self, channel_id):
        """Disconnects the current user from a rtc call and clears any invitation sent to that user on this channel
        :param int channel_id: id of the channel from which to disconnect
        """
        channel_member_sudo = request.env["discuss.channel.member"]._get_as_sudo_from_request_or_raise(
            request=request, channel_id=int(channel_id)
        )
        return channel_member_sudo._rtc_leave_call()

    @http.route("/mail/rtc/channel/cancel_call_invitation", methods=["POST"], type="json", auth="public")
    def channel_call_cancel_invitation(self, channel_id, member_ids=None):
        """
        :param member_ids: members whose invitation is to cancel
        :type member_ids: list(int) or None
        """
        channel_member_sudo = request.env["discuss.channel.member"]._get_as_sudo_from_request_or_raise(
            request=request, channel_id=int(channel_id)
        )
        return channel_member_sudo.channel_id._rtc_cancel_invitations(member_ids=member_ids)

    @http.route("/mail/rtc/audio_worklet_processor", methods=["GET"], type="http", auth="public")
    def audio_worklet_processor(self):
        """Returns a JS file that declares a WorkletProcessor class in
        a WorkletGlobalScope, which means that it cannot be added to the
        bundles like other assets.
        """
        return request.make_response(
            file_open("mail/static/src/worklets/audio_processor.js", "rb").read(),
            headers=[
                ("Content-Type", "application/javascript"),
                ("Cache-Control", "max-age=%s" % http.STATIC_CACHE),
            ],
        )

    @http.route("/discuss/channel/ping", methods=["POST"], type="json", auth="public")
    def channel_ping(self, channel_id, rtc_session_id=None, check_rtc_session_ids=None):
        channel_member_sudo = request.env["discuss.channel.member"]._get_as_sudo_from_request_or_raise(
            request=request, channel_id=int(channel_id)
        )
        if rtc_session_id:
            domain = [
                ("id", "=", int(rtc_session_id)),
                ("channel_member_id", "=", channel_member_sudo.id),
            ]
            channel_member_sudo.channel_id.rtc_session_ids.filtered_domain(domain).write({})  # update write_date
        current_rtc_sessions, outdated_rtc_sessions = channel_member_sudo._rtc_sync_sessions(check_rtc_session_ids)
        return {
            "rtcSessions": [
                ("insert", [rtc_session_sudo._mail_rtc_session_format() for rtc_session_sudo in current_rtc_sessions]),
                (
                    "insert-and-unlink",
                    [{"id": missing_rtc_session_sudo.id} for missing_rtc_session_sudo in outdated_rtc_sessions],
                ),
            ]
        }
