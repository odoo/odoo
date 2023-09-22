/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";
import { removeFromArray } from "@mail/utils/common/arrays";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    update(data) {
        super.update(data);
        if ("rtc_inviting_session" in data) {
            this.Model.env.bus.trigger("RTC-SERVICE:UPDATE_RTC_SESSIONS", {
                thread: this,
                record: data.rtc_inviting_session,
            });
            this.rtcInvitingSession = this._store.RtcSession.insert({
                id: data.rtc_inviting_session.id,
            });
            if (!this._store.ringingThreads.includes(this.localId)) {
                this._store.ringingThreads.push(this.localId);
            }
        }
        if ("rtcInvitingSession" in data) {
            if (Array.isArray(data.rtcInvitingSession)) {
                if (data.rtcInvitingSession[0][0] === "unlink") {
                    this.rtcInvitingSession = undefined;
                    removeFromArray(this._store.ringingThreads, this.localId);
                }
                return;
            }
            this.Model.env.bus.trigger("RTC-SERVICE:UPDATE_RTC_SESSIONS", {
                thread: this,
                record: data.rtcInvitingSession,
            });
            this.rtcInvitingSession = this._store.RtcSession.insert({
                id: data.rtcInvitingSession.id,
            });
            this._store.ringingThreads.push(this.localId);
        }
        if ("rtcSessions" in data) {
            this.Model.env.bus.trigger("RTC-SERVICE:UPDATE_RTC_SESSIONS", {
                thread: this,
                commands: data.rtcSessions,
            });
        }
    },
});
