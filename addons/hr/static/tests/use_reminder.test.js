import { beforeEach, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { user } from "@web/core/user";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import { reminderDoneKey, useReminder } from "@hr/hooks/use_reminder";
import { advanceReminderTimers, clearReminderStorage } from "./reminder_test_helpers";
import { defineHrModels } from "./hr_test_helpers";

defineHrModels();

beforeEach(clearReminderStorage);

test("useReminder: arms on presence, shows after delay", async () => {
    const calls = { show: 0 };
    class ReminderHost extends Component {
        static template = xml`<div/>`;
        setup() {
            useReminder({
                isEligible: () => true,
                show: async () => calls.show++,
                getPopover: () => ({ isOpen: false }),
                getSessionKey: () => 0,
            });
        }
    }
    const comp = await mountWithCleanup(ReminderHost, { noMainContainer: true });
    await advanceReminderTimers(comp.env.services.presence);
    expect(calls.show).toBe(1);
    expect(browser.localStorage.getItem(reminderDoneKey(user.userId))?.at(-1)).toBe("1");
});

test("useReminder: syncStorage resets when prefix changes", async () => {
    const date = luxon.DateTime.now().toFormat("yyyy-MM-dd");
    browser.localStorage.setItem(reminderDoneKey(user.userId), `0.${date}.1`);
    class ReminderHost extends Component {
        static template = xml`<div/>`;
        setup() {
            useReminder({
                isEligible: () => true,
                show: async () => {},
                getPopover: () => ({ isOpen: false }),
                getSessionKey: () => 1,
            });
        }
    }
    await mountWithCleanup(ReminderHost, { noMainContainer: true });
    await animationFrame();
    expect(browser.localStorage.getItem(reminderDoneKey(user.userId))?.at(-1)).toBe("0");
});
