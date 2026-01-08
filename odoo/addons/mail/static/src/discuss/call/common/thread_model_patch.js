/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    update(data) {
        super.update(data);
        if ("rtc_inviting_session" in data) {
            this.rtcInvitingSession = data.rtc_inviting_session;
        }
        if ("rtcInvitingSession" in data) {
            this.rtcInvitingSession = data.rtcInvitingSession;
        }
        if ("rtcSessions" in data) {
            this.rtcSessions = data.rtcSessions;
        }
    },
});
