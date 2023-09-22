/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";
import { removeFromArray } from "@mail/utils/common/arrays";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    update(data) {
        super.update(data);
        if ("rtc_inviting_session" in data) {
            const session = this._store.RtcSession.insert(data.rtc_inviting_session);
            if (session.notIn(this.rtcSessions)) {
                this.rtcSessions.push(session);
            }
            if (!this._store.ringingThreads.includes(this.localId)) {
                this._store.ringingThreads.push(this.localId);
            }
        }
        let rtcContinue = true;
        if ("rtcInvitingSession" in data) {
            if (Array.isArray(data.rtcInvitingSession)) {
                if (data.rtcInvitingSession[0][0] === "unlink") {
                    this.rtcInvitingSession = undefined;
                    removeFromArray(this._store.ringingThreads, this.localId);
                }
                rtcContinue = false;
            }
            const session = this._store.RtcSession.insert(data.rtcInvitingSession);
            if (session.notIn(this.rtcSessions)) {
                this.rtcSessions.push(session);
            }
            this._store.ringingThreads.push(this.localId);
        }
        if (rtcContinue && "rtcSessions" in data) {
            for (const command of data.rtcSessions) {
                const sessionsData = command[1];
                switch (command[0]) {
                    case "insert-and-unlink":
                        for (const rtcSessionData of sessionsData) {
                            this.Model.env.services["discuss.rtc"].deleteSession(rtcSessionData.id);
                        }
                        break;
                    case "insert":
                        for (const rtcSessionData of sessionsData) {
                            const session = this._store.RtcSession.insert(rtcSessionData);
                            if (session.notIn(this.rtcSessions)) {
                                this.rtcSessions.push(session);
                            }
                        }
                        break;
                }
            }
        }
    },
});
