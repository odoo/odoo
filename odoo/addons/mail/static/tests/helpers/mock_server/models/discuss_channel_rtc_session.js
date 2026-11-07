/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    mockCreate(model) {
        if (model !== "discuss.channel.rtc.session") {
            return super.mockCreate(...arguments);
        }
        const sessionIds = super.mockCreate(...arguments);
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
                    rtcSessions: [["ADD", sessionData]],
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
    _mockDiscussChannelRtcSession_DiscussChannelRtcSessionFormat(id, { extra = false } = {}) {
        const [rtcSession] = this.getRecords("discuss.channel.rtc.session", [["id", "=", id]]);
        const vals = {
            id: rtcSession.id,
            channelMember: this._mockDiscussChannelMember_DiscussChannelMemberFormat([
                rtcSession.channel_member_id,
            ])[0],
        };
        if (extra) {
            Object.assign(vals, {
                isCameraOn: rtcSession.is_camera_on,
                isDeaf: rtcSession.is_deaf,
                isSelfMuted: rtcSession.is_self_muted,
                isScreenSharingOn: rtcSession.is_screen_sharing_on,
            });
        }
        return vals;
    },
    /**
     * Simulates `_mail_rtc_session_format` on `discuss.channel.rtc.session`.
     *
     * @private
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockDiscussChannelRtcSession_DiscussChannelRtcSessionFormatByChannel(
        ids,
        { extra = false } = {}
    ) {
        const rtcSessions = this.getRecords("discuss.channel.rtc.session", [["id", "in", ids]]);
        const data = {};
        for (const rtcSession of rtcSessions) {
            if (!data[rtcSession.channel_id]) {
                data[rtcSession.channel_id] = [];
            }
            data[rtcSession.channel_id].push(
                this._mockDiscussChannelRtcSession_DiscussChannelRtcSessionFormat(rtcSession.id, {
                    extra,
                })
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
            ["id", "=", sessionData.channelMember.thread.id],
        ]);
        this.pyEnv["bus.bus"]._sendone(
            channel,
            "discuss.channel.rtc.session/update_and_broadcast",
            { data: sessionData, channelId: channel.id }
        );
    },
});
