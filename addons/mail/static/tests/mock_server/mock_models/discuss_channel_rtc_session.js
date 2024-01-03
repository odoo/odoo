/** @odoo-module */

import { models } from "@web/../tests/web_test_helpers";

export class DiscussChannelRtcSession extends models.ServerModel {
    _name = "discuss.channel.rtc.session";

    /**
     * Simulates `_mail_rtc_session_format` on `discuss.channel.rtc.session`.
     *
     * @param {number} id
     * @param {{ extra?; boolean }} options
     */
    _mailRtcSessionFormat(id, { extra } = {}) {
        const [rtcSession] = this._filter([["id", "=", id]]);
        const vals = {
            id: rtcSession.id,
            channelMember: this.env["discuss.channel.member"]._discussChannelMemberFormat([
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
     * Simulates `_mail_rtc_session_format_by_channel` on `discuss.channel.rtc.session`.
     *
     * @param {number[]} ids
     * @param {{ extra?; boolean }} options
     */
    _mailRtcSessionFormatByChannel(ids, options) {
        const rtcSessions = this._filter([["id", "in", ids]]);
        /** @type {Record<string, any>} */
        const data = {};
        for (const rtcSession of rtcSessions) {
            if (!data[rtcSession.channel_id]) {
                data[rtcSession.channel_id] = [];
            }
            data[rtcSession.channel_id].push(this._mailRtcSessionFormat(rtcSession.id, options));
        }
        return data;
    }
}
