/** @odoo-module */

import { models } from "@web/../tests/web_test_helpers";

export class DiscussChannelRtcSession extends models.ServerModel {
    _name = "discuss.channel.rtc.session";

    /**
     * @param {number} id
     * @param {{ extra?; boolean }} options
     */
    _mail_rtc_session_format(id, { extra } = {}) {
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];

        const [rtcSession] = this._filter([["id", "=", id]]);
        const vals = {
            id: rtcSession.id,
            channelMember: DiscussChannelMember._discuss_channel_member_format([
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
    }

    /**
     * @param {number[]} ids
     * @param {{ extra?; boolean }} options
     */
    _mail_rtc_session_format_by_channel(ids, options) {
        const rtcSessions = this._filter([["id", "in", ids]]);
        /** @type {Record<string, any>} */
        const data = {};
        for (const rtcSession of rtcSessions) {
            if (!data[rtcSession.channel_id]) {
                data[rtcSession.channel_id] = [];
            }
            data[rtcSession.channel_id].push(this._mail_rtc_session_format(rtcSession.id, options));
        }
        return data;
    }
}
