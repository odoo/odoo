/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, 'mail/controllers/discuss', {
    /**
     * @override
     */
    async _performRPC(route, args) {
        if (route === '/mail/channel/notify_typing') {
            const id = args.channel_id;
            const is_typing = args.is_typing;
            const context = args.context;
            return this._mockRouteMailChannelNotifyTyping(id, is_typing, context);
        }
        if (route === '/mail/channel/ping') {
            return;
        }
        if (route === '/mail/rtc/channel/join_call') {
            return this._mockRouteMailRtcChannelJoinCall(args.channel_id, args.check_rtc_session_ids);
        }
        if (route === '/mail/rtc/channel/leave_call') {
            return this._mockRouteMailRtcChannelLeaveCall(args.channel_id);
        }
        if (route === '/mail/rtc/session/update_and_broadcast') {
            return;
        }
        return this._super(route, args);
    },
    /**
     * Simulates the `/mail/channel/notify_typing` route.
     *
     * @private
     * @param {integer} channel_id
     * @param {integer} limit
     * @param {Object} [context={}]
     */
    async _mockRouteMailChannelNotifyTyping(channel_id, is_typing, context = {}) {
        const partnerId = context.mockedPartnerId || this.currentPartnerId;
        const [memberOfCurrentUser] = this.getRecords('mail.channel.member', [['channel_id', '=', channel_id], ['partner_id', '=', partnerId]]);
        if (!memberOfCurrentUser) {
            return;
        }
        this._mockMailChannelMember_NotifyTyping([memberOfCurrentUser.id], is_typing);
    },
    /**
     * Simulates the `/mail/rtc/channel/join_call` route.
     *
     * @private
     * @param {integer} channel_id
     * @returns {integer[]} [check_rtc_session_ids]
     */
    async _mockRouteMailRtcChannelJoinCall(channel_id, check_rtc_session_ids = []) {
        const [currentChannelMember] = this.getRecords('mail.channel.member', [
            ['channel_id', '=', channel_id],
            ['partner_id', '=', this.currentPartnerId],
        ]);
        const sessionId = this.pyEnv['mail.channel.rtc.session'].create({
            channel_member_id: currentChannelMember.id,
            channel_id, // on the server, this is a related field from channel_member_id and not explicitly set
        });
        const channelMembers = this.getRecords('mail.channel.member', [['channel_id', '=', channel_id]]);
        const rtcSessions = this.getRecords('mail.channel.rtc.session', [
            ['channel_member_id', 'in', channelMembers.map(channelMember => channelMember.id)],
        ]);
        return {
            'iceServers': false,
            'rtcSessions': [
                ['insert', rtcSessions.map(rtcSession => this._mockMailChannelRtcSession_MailChannelRtcSessionFormat(rtcSession.id))],
            ],
            'sessionId': sessionId,
        };
    },
    /**
     * Simulates the `/mail/rtc/channel/leave_call` route.
     *
     * @private
     * @param {integer} channelId
     */
    async _mockRouteMailRtcChannelLeaveCall(channel_id) {
        const channelMembers = this.getRecords('mail.channel.member', [['channel_id', '=', channel_id]]);
        const rtcSessions = this.getRecords('mail.channel.rtc.session', [
            ['channel_member_id', 'in', channelMembers.map(channelMember => channelMember.id)],
        ]);
        const notifications = [];
        const channelInfo = this._mockMailChannelRtcSession_MailChannelRtcSessionFormatByChannel(rtcSessions.map(rtcSession => rtcSession.id));
        for (const [channelId, sessionsData] of Object.entries(channelInfo)) {
            const notificationRtcSessions = sessionsData.map((sessionsDataPoint) => {
                return { 'id': sessionsDataPoint.id };
            });
            notifications.push([
                channelId,
                'mail.channel/rtc_sessions_update',
                {
                    'id': Number(channelId), // JS object keys are strings, but the type from the server is number
                    'rtcSessions': [['insert-and-unlink', notificationRtcSessions]],
                }
            ]);
        }
        for (const rtcSession of rtcSessions) {
            const target = rtcSession.guest_id || rtcSession.partner_id;
            notifications.push([
                target,
                'mail.channel.rtc.session/ended',
                { 'sessionId': rtcSession.id },
            ]);
        }
        this.pyEnv['bus.bus']._sendmany(notifications);
    },
});
