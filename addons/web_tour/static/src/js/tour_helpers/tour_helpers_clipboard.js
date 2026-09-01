import { patch } from "@web/core/utils/patch";
import { TourHelpers } from "./tour_helpers";

const originalClipboardWriteText = window.navigator.clipboard?.writeText;

patch(TourHelpers.prototype, {
    /**
     * Makes `navigator.clipboard.writeText` resolve without actually writing
     * anything.
     * @description Some actions trigger a clipboard write as a side effect
     * (e.g. a "copy link" button); clipboard access can be denied in a
     * test/CI browser context, which would otherwise break the flow with an
     * unhandled rejection. Pair with {@link restoreClipboardWrite} once done
     * to avoid affecting the rest of the session.
     * @example
     *  run: "allowClipboardWrite",
     */
    allowClipboardWrite() {
        if (window.navigator.clipboard) {
            window.navigator.clipboard.writeText = () => Promise.resolve();
        }
    },

    /**
     * Restores `navigator.clipboard.writeText` after {@link allowClipboardWrite}.
     * @example
     *  run: "restoreClipboardWrite",
     */
    restoreClipboardWrite() {
        if (window.navigator.clipboard) {
            window.navigator.clipboard.writeText = originalClipboardWriteText;
        }
    },
});
