import { animationFrame, advanceTime } from "@odoo/hoot-mock";
import { browser } from "@web/core/browser/browser";
import { user } from "@web/core/user";

import {
    REMINDER_DELAY,
    REMINDER_FOCUS_DELAY,
    REMINDER_LS_KEY,
    reminderArmedKey,
} from "@hr/hooks/use_reminder";

export function clearReminderStorage() {
    browser.localStorage.removeItem(REMINDER_LS_KEY);
    browser.localStorage.removeItem(reminderArmedKey(user.userId));
}

export async function advanceReminderTimers(presence) {
    presence.bus.trigger("presence");
    await advanceTime(REMINDER_DELAY);
    presence.bus.trigger("presence");
    await advanceTime(REMINDER_FOCUS_DELAY);
    await animationFrame();
}
