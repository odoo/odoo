import { onWillUnmount } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useBus, useService } from "@web/core/utils/hooks";

const REMINDER_DELAY = 2 * 60 * 1000;

export function useReminder({ shouldTrack, getPopover, onShowReminder }) {
    const presence = useService("presence");
    let hasBeenShown = false;
    let timeoutId = null;

    function reset() {
        browser.clearTimeout(timeoutId);
        timeoutId = null;
        getPopover()?.close();
    }

    function onActivity() {
        if (!shouldTrack() || !presence.isOdooFocused()) {
            reset();
            return;
        }
        if (hasBeenShown || timeoutId || getPopover()?.isOpen) {
            return;
        }
        timeoutId = browser.setTimeout(async () => {
            timeoutId = null;
            if (shouldTrack() && presence.isOdooFocused()) {
                hasBeenShown = await onShowReminder();
            }
        }, REMINDER_DELAY);
    }

    useBus(presence.bus, "presence", onActivity);
    onWillUnmount(reset);

    return { reset };
}
