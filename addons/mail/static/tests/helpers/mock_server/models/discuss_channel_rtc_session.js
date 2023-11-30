/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, "mail/models/discuss_channel_rtc_session", {
    mockCreate(model) {
        if (model !== "discuss.channel.rtc.session") {
            return this._super(...arguments);
        }
        const sessionIds = this._super(...arguments);
        const channelInfo =
            this._mockDiscussChannelRtcSession_DiscussChannelRtcSessionFormatByChannel(sessionIds);
        const notifications = [];
        for (const [channelId, sessionData] of Object.entries(channelInfo)) {
            const [channel] = this.pyEnv["discuss.channel"].searchRead([
                ["id", "=", Number(channelId)],
            ]);
            notifications.push([
                channel,
                "discuss.channel/rtc_sessions_update",
                {
                    id: channel.id,
                    rtcSessions: [["insert", sessionData]],
                },
            ]);
        }
        this.pyEnv["bus.bus"]._sendmany(notifications);
        return sessionIds;
    },
    /**
     * Simulates `_mail_rtc_session_format` on `discuss.channel.rtc.session`.
     *
     * @private
     * @param {integer} id
     * @returns {Object}
     */
    _mockDiscussChannelRtcSession_DiscussChannelRtcSessionFormat(id) {
        const [rtcSession] = this.getRecords("discuss.channel.rtc.session", [["id", "=", id]]);
        return {
            id: rtcSession.id,
            channelMember: this._mockDiscussChannelMember_DiscussChannelMemberFormat([
                rtcSession.channel_member_id,
            ])[0],
            isCameraOn: rtcSession.is_camera_on,
            isDeaf: rtcSession.is_deaf,
            isSelfMuted: rtcSession.is_self_muted,
            isScreenSharingOn: rtcSession.is_screen_sharing_on,
        };
    },
    /**
     * Simulates `_mail_rtc_session_format` on `discuss.channel.rtc.session`.
     *
     * @private
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockDiscussChannelRtcSession_DiscussChannelRtcSessionFormatByChannel(ids) {
        const rtcSessions = this.getRecords("discuss.channel.rtc.session", [["id", "in", ids]]);
        const data = {};
        for (const rtcSession of rtcSessions) {
            if (!data[rtcSession.channel_id]) {
                data[rtcSession.channel_id] = [];
            }
            data[rtcSession.channel_id].push(
                this._mockDiscussChannelRtcSession_DiscussChannelRtcSessionFormat(rtcSession.id)
            );
        }
        return data;
    },
    /**
     * Simulates `_update_and_broadcast` on `discuss.channel.rtc.session`.
     *
     * @param {object} values
     */
    _mockDiscussChannelRtcSession__updateAndBroadcast(id, values) {
        this.pyEnv["discuss.channel.rtc.session"].write([id], values);
        const sessionData = this._mockDiscussChannelRtcSession_DiscussChannelRtcSessionFormat(id);
        const [channel] = this.pyEnv["discuss.channel"].searchRead([
            ["id", "=", sessionData.channelMember.channel.id],
        ]);
        this.pyEnv["bus.bus"]._sendone(channel, "mail.record/insert", { RtcSession: sessionData });
    },
});
