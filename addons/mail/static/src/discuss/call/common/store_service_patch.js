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
    },
    onStarted() {
        super.onStarted(...arguments);
        this.rtc.start();
    },
};
patch(Store.prototype, StorePatch);
