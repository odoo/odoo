import { Record } from "@mail/core/common/record";
import { Store } from "@mail/core/common/store_service";
import { RtcSession } from "@mail/discuss/call/common/rtc_session_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const StorePatch = {
    setup() {
        super.setup(...arguments);
        /** @type {typeof import("@mail/discuss/call/common/rtc_session_model").RtcSession} */
        this.RtcSession = RtcSession;
        this.rtc = Record.one("Rtc", {
            compute() {
                return {};
            },
        });
        this.ringingThreads = Record.many("Thread", {
            /** @this {import("models").Store} */
            onUpdate() {
                if (this.ringingThreads.length > 0) {
                    this.env.services["mail.sound_effects"].play("incoming-call", {
                        loop: true,
                    });
                } else {
                    this.env.services["mail.sound_effects"].stop("incoming-call");
                }
            },
        });
        this.allActiveRtcSessions = Record.many("RtcSession");
        this.nextTalkingTime = 1;
    },
    onStarted() {
        super.onStarted(...arguments);
        this.rtc.start();
    },
    sortMembers(m1, m2) {
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
                return super.sortMembers(m1, m2);
            }
        } else {
            return m2HasRtc - m1HasRtc;
        }
    },
};
patch(Store.prototype, StorePatch);
