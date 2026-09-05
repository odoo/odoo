import { animationFrame, advanceTime } from "@odoo/hoot-mock";
import { browser } from "@web/core/browser/browser";
import { user } from "@web/core/user";

import {
    clearWorkIntervalsCache,
    REMINDER_DELAY,
    REMINDER_FOCUS_DELAY,
    reminderArmedKey,
    reminderDoneKey,
} from "@hr/hooks/use_reminder";

export function clearReminderStorage() {
    browser.localStorage.removeItem(reminderDoneKey(user.userId));
    browser.localStorage.removeItem(reminderArmedKey(user.userId));
    clearWorkIntervalsCache();
}

export async function advanceReminderTimers(presence) {
    presence.bus.trigger("presence");
    await animationFrame();
    await advanceTime(REMINDER_DELAY);
    presence.bus.trigger("presence");
    await animationFrame();
    await advanceTime(REMINDER_FOCUS_DELAY);
    await animationFrame();
}
