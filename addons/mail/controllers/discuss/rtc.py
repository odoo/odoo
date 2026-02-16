# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from collections import defaultdict
from datetime import datetime

from werkzeug.exceptions import NotFound, BadRequest

from odoo.http import Controller, request, route
from odoo.http.stream import STATIC_CACHE
from odoo.tools import file_open

from odoo.addons.mail.tools.discuss import Store, add_guest_to_context, get_derived_sfu_key
from odoo.addons.mail.tools.jwt import verify, Algorithm

_logger = logging.getLogger(__name__)


def _check_jwt(request, channel):
    if not channel:
        raise NotFound()
    auth_header = request.httprequest.headers.get("Authorization")
    if not auth_header:
        raise NotFound()
    try:
        jwt = auth_header.split(" ")[1]
    except IndexError:
        raise NotFound()
    if not jwt:
        raise NotFound()
    sfu_key = get_derived_sfu_key(request.env, channel.id)
    try:
        return verify(jwt, sfu_key, algorithm=Algorithm.HS256)
    except ValueError:
        raise NotFound()


class RtcController(Controller):
    @route("/mail/rtc/session/notify_call_members", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def session_call_notify(self, peer_notifications):
        """Sends content to other session of the same channel, only works if the user is the user of that session.
        This is used to send peer to peer information between sessions.

        :param peer_notifications: list of tuple with the following elements:
            - int sender_session_id: id of the session from which the content is sent
            - list target_session_ids: list of the ids of the sessions that should receive the content
            - string content: the content to send to the other sessions
        """
        guest = request.env["mail.guest"]._get_guest_from_context()
        notifications_by_session = defaultdict(list)
        for sender_session_id, target_session_ids, content in peer_notifications:
            # sudo: discuss.channel.rtc.session - only keeping sessions matching the current user
            session_sudo = request.env["discuss.channel.rtc.session"].sudo().browse(int(sender_session_id)).exists()
            if (
                not session_sudo
                or (session_sudo.guest_id and session_sudo.guest_id != guest)
                or (session_sudo.partner_id and session_sudo.partner_id != request.env.user.partner_id)
            ):
                continue
            notifications_by_session[session_sudo].append(([int(sid) for sid in target_session_ids], content))
        for session_sudo, notifications in notifications_by_session.items():
            session_sudo._notify_peers(notifications)

    @route("/mail/rtc/session/update_and_broadcast", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def session_update_and_broadcast(self, session_id, values):
        """Update a RTC session and broadcasts the changes to the members of its channel,
        only works of the user is the user of that session.
        :param int session_id: id of the session to update
        :param dict values: write dict for the fields to update
        """
        if request.env.user._is_public():
            guest = request.env["mail.guest"]._get_guest_from_context()
            if guest:
                # sudo: discuss.channel.rtc.session - only keeping sessions matching the current user
                session = guest.env["discuss.channel.rtc.session"].sudo().browse(int(session_id)).exists()
                if session and session.guest_id == guest:
                    session._update_and_broadcast(values)
                    return
            return
        # sudo: discuss.channel.rtc.session - only keeping sessions matching the current user
        session = request.env["discuss.channel.rtc.session"].sudo().browse(int(session_id)).exists()
        if session and session.partner_id == request.env.user.partner_id:
            session._update_and_broadcast(values)

    @route("/mail/rtc/channel/join_call", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def channel_call_join(self, channel_id, check_rtc_session_ids=None, camera=False):
        """Joins the RTC call of a channel if the user is a member of that channel
        :param int channel_id: id of the channel to join
        """
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise request.not_found()
        member = channel._find_or_create_member_for_self()
        if not member:
            raise NotFound()
        store = Store()
        # sudo: discuss.channel.rtc.session - member of current user can join call
        member.sudo()._rtc_join_call(store, check_rtc_session_ids=check_rtc_session_ids, camera=camera)
        return store.get_result()

    @route("/mail/rtc/channel/leave_call", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def channel_call_leave(self, channel_id, session_id=None):
        """Disconnects the current user from a rtc call and clears any invitation sent to that user on this channel
        :param int channel_id: id of the channel from which to disconnect
        :param int session_id: id of the leaving session
        """
        member = request.env["discuss.channel.member"].search([("channel_id", "=", channel_id), ("is_self", "=", True)])
        if not member:
            raise NotFound()
        # sudo: discuss.channel.rtc.session - member of current user can leave call
        member.sudo()._rtc_leave_call(session_id)

    @route("/mail/rtc/channel/upgrade_connection", methods=["POST"], type="jsonrpc", auth="user")
    def channel_upgrade(self, channel_id):
        member = request.env["discuss.channel.member"].search([("channel_id", "=", channel_id), ("is_self", "=", True)])
        if not member:
            raise NotFound()
        member.sudo()._join_sfu(force=True)

    @route("/mail/rtc/channel/cancel_call_invitation", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def channel_call_cancel_invitation(self, channel_id, member_ids=None):
        """
        :param member_ids: members whose invitation is to cancel
        :type member_ids: list(int) or None
        """
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        # sudo: discuss.channel.rtc.session - can cancel invitations in accessible channel
        channel.sudo()._rtc_cancel_invitations(member_ids=member_ids)

    @route("/mail/rtc/audio_worklet_processor_v2", methods=["GET"], type="http", auth="public", readonly=True)
    def audio_worklet_processor(self):
        """Returns a JS file that declares a WorkletProcessor class in
        a WorkletGlobalScope, which means that it cannot be added to the
        bundles like other assets.
        """
        with file_open("mail/static/src/worklets/audio_processor.js", "rb") as f:
            data = f.read()
        return request.make_response(
            data,
            headers=[
                ("Content-Type", "application/javascript"),
                ("Cache-Control", f"max-age={STATIC_CACHE}"),
            ],
        )

    @route("/discuss/channel/ping", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def channel_ping(self, channel_id, rtc_session_id=None, check_rtc_session_ids=None):
        member = request.env["discuss.channel.member"].search([("channel_id", "=", channel_id), ("is_self", "=", True)])
        if not member:
            raise NotFound()
        # sudo: discuss.channel.rtc.session - member of current user can access related sessions
        channel_member_sudo = member.sudo()
        if rtc_session_id:
            domain = [
                ("id", "=", int(rtc_session_id)),
                ("channel_member_id", "=", member.id),
            ]
            channel_member_sudo.channel_id.rtc_session_ids.filtered_domain(domain).write({})  # update write_date
        rtc_updates = channel_member_sudo._rtc_sync_sessions(check_rtc_session_ids)
        store = Store().add(
            member.channel_id,
            "_store_rtc_update_fields",
            fields_params={"added": rtc_updates[0], "removed": rtc_updates[1]},
        )
        return store.get_result()

    ##########
    # Recording / Transcription
    ##########

    def _get_recording_destination(self, channel_id):
        """Save the recording, to be overriden by (cloud) storage modules"""

    def _handleAudioFile(self, channel_id, start_dt, end_dt, transcribe=False, main_media=False):
        """
        TODO move to call_history model
        Handle the audio file received from the SFU, to be overriden by the AI for transcription"""
        file_data = request.httprequest.get_data()
        if not file_data:
            raise BadRequest()
        call_history = request.env["discuss.call.history"].sudo().create({
            "channel_id": channel_id.id,
            "start_dt": start_dt,
            "end_dt": end_dt,
        })
        content_type = request.httprequest.content_type or "audio/ogg"
        attachment = request.env["ir.attachment"].sudo().create({
            "name": f"audio_{call_history.id}",
            "type": "binary",
            "raw": file_data,
            "res_model": "discuss.call.history",
            "res_id": call_history.id,
            "mimetype": content_type,
        })
        _logger.warning("Attachment created: %s", attachment.name)
        if main_media:
            # TODO: field not availaible until merge of PR #233836
            call_history.media_id = attachment
            _logger.warning("Attachment set as main media: %s", call_history.media_id.name)
        return attachment, call_history

    @route(
        '/mail/rtc/recording/<model("discuss.channel"):channel>/audio',
        type="http",
        auth="public",
        methods=["POST"],
        cors="*",
        csrf=False,
    )
    def audio_recording(self, channel, start, end, transcribe=False, main_media=False):
        _check_jwt(request, channel)
        if not start or not end:
            raise BadRequest()
        start_dt = datetime.fromtimestamp(int(start) / 1000)
        end_dt = datetime.fromtimestamp(int(end) / 1000)
        attachment, call_history = self._handleAudioFile(channel, start_dt, end_dt, transcribe, main_media)
        return request.make_json_response({"status": "OK", "channel_id": channel.id, "attachment_id": attachment.id, "call_history_id": call_history.id}, status=200)

    @route(
        '/mail/rtc/recording/<model("discuss.channel"):channel>/routing',
        type="http",
        auth="public",
        cors="*",
    )
    def get_routing(self, channel):
        _check_jwt(request, channel)
        return request.make_json_response({
            "destination": self._get_recording_destination(channel),
        }, status=200)
