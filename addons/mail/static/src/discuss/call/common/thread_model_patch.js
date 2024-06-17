import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread, {
    sortOnlineMembers(m1, m2) {
        const m1HasRtc = Boolean(m1.rtcSession);
        const m2HasRtc = Boolean(m2.rtcSession);
        if (m1HasRtc === m2HasRtc) {
            /**
             * If raisingHand is falsy, it gets an Infinity value so that when
             * we sort by [oldest/lowest-value]-first, falsy values end up last.
             */
            const m1RaisingValue = m1.rtcSession?.raisingHand || Infinity;
            const m2RaisingValue = m2.rtcSession?.raisingHand || Infinity;
            if (m1HasRtc && m1RaisingValue !== m2RaisingValue) {
                return m1RaisingValue - m2RaisingValue;
            } else {
                return super.sortOnlineMembers(m1, m2);
            }
        } else {
            return m2HasRtc - m1HasRtc;
        }
    },
});

/** @type {import("models").Thread} */
const ThreadPatch = {
    setup() {
        super.setup(...arguments);
        this.activeRtcSession = Record.one("RtcSession");
        this.rtcInvitingSession = Record.one("RtcSession", {
            /** @this {import("models").Thread} */
            onAdd(r) {
                this.rtcSessions.add(r);
                this.store.discuss.ringingThreads.add(this);
            },
            /** @this {import("models").Thread} */
            onDelete(r) {
                this.store.discuss.ringingThreads.delete(this);
            },
        });
        this.rtcSessions = Record.many("RtcSession", {
            /** @this {import("models").Thread} */
            onDelete(r) {
                this.store.env.services["discuss.rtc"].deleteSession(r.id);
            },
        });
    },
    get videoCount() {
        return Object.values(this.store.RtcSession.records).filter((session) => session.hasVideo)
            .length;
    },
};
patch(Thread.prototype, ThreadPatch);
