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
        this.allActiveRtcSessions = Record.many("RtcSession");
    },
    onStarted() {
        super.onStarted(...arguments);
        this.rtc.start();
    },
};
patch(Store.prototype, StorePatch);
