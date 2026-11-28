import { Rtc } from "@mail/discuss/call/common/rtc_service";
import { patch } from "@web/core/utils/patch";

/**
 * Tours cannot grant media access through <usermedia>, <camera> and
 * <microphone>: these elements need a trusted click and an answer to the
 * browser's permission prompt. Report them as unsupported so that the call
 * permission dialog shows its buttons, as it does in browsers without them.
 */
patch(Rtc.prototype, {
    supportsMediaCaptureElement() {
        return false;
    },
});
