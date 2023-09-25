/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    update(data) {
        super.update(data);
        if ("rtc_inviting_session" in data) {
            const session = this._store.RtcSession.insert(data.rtc_inviting_session);
            this.rtcSessions.add(session);
            this._store.discuss.ringingThreads.add(this);
        }
        let rtcContinue = true;
        if ("rtcInvitingSession" in data) {
            if (Array.isArray(data.rtcInvitingSession)) {
                if (data.rtcInvitingSession[0][0] === "DELETE") {
                    this.rtcInvitingSession = undefined;
                    this._store.discuss.ringingThreads.delete(this);
                }
                rtcContinue = false;
            } else {
                const session = this._store.RtcSession.insert(data.rtcInvitingSession);
                this.rtcSessions.add(session);
                this._store.discuss.ringingThreads.add(this);
            }
        }
        if (rtcContinue && "rtcSessions" in data) {
            for (const command of data.rtcSessions) {
                const sessionsData = command[1];
                switch (command[0]) {
                    case "DELETE":
                        for (const rtcSessionData of sessionsData) {
                            this.Model.env.services["discuss.rtc"].deleteSession(rtcSessionData.id);
                        }
                        break;
                    case "ADD":
                        for (const rtcSessionData of sessionsData) {
                            const session = this._store.RtcSession.insert(rtcSessionData);
                            this.rtcSessions.add(session);
                        }
                        break;
                }
            }
        }
    },
});
