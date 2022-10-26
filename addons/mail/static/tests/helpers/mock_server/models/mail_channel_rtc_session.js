/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, 'mail/models/mail_channel_rtc_session', {
    /**
     * Simulates `_mail_rtc_session_format` on `mail.channel.rtc.session`.
     *
     * @private
     * @param {integer} id
     * @returns {Object}
     */
    _mockMailChannelRtcSession_MailChannelRtcSessionFormat(id) {
        const [rtcSession] = this.getRecords('mail.channel.rtc.session', [['id', '=', id]]);
        return {
            'id': rtcSession.id,
            'channelMember': this._mockMailChannelMember_MailChannelMemberFormat([rtcSession.channel_member_id])[0],
            'isCameraOn': rtcSession.is_camera_on,
            'isDeaf': rtcSession.is_deaf,
            'isSelfMuted': rtcSession.is_self_muted,
            'isScreenSharingOn': rtcSession.is_screen_sharing_on,
        };
    },
    /**
     * Simulates `_mail_rtc_session_format` on `mail.channel.rtc.session`.
     *
     * @private
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockMailChannelRtcSession_MailChannelRtcSessionFormatByChannel(ids) {
        const rtcSessions = this.getRecords('mail.channel.rtc.session', [['id', 'in', ids]]);
        const data = {};
        for (const rtcSession of rtcSessions) {
            if (!data[rtcSession.channel_id]) {
                data[rtcSession.channel_id] = [];
            }
            data[rtcSession.channel_id].push(this._mockMailChannelRtcSession_MailChannelRtcSessionFormat(rtcSession.id));
        }
        return data;
    }
});
