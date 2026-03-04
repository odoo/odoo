import { expect, test } from "@odoo/hoot";

import { browser } from "@web/core/browser/browser";
import { Chatter } from "@mail/chatter/web_portal/chatter";

import "@muk_web_chatter/chatter/chatter";

test.tags("muk_web_chatter");
test("notifications toggle updates localStorage and state", async () => {
    browser.localStorage.removeItem("muk_web_chatter.notifications");
    browser.localStorage.setItem(
        "muk_web_chatter.notifications", JSON.stringify(false)
    );
    const chatter = {
        state: {
            showNotificationMessages: false,
        },
    };
    Chatter.prototype.onClickNotificationsToggle.call(chatter);
    expect(chatter.state.showNotificationMessages).toBe(true);
    expect(
        JSON.parse(browser.localStorage.getItem(
            "muk_web_chatter.notifications"
        ))
    ).toBe(true);
    Chatter.prototype.onClickNotificationsToggle.call(chatter);
    expect(chatter.state.showNotificationMessages).toBe(false);
    expect(
        JSON.parse(browser.localStorage.getItem(
            "muk_web_chatter.notifications"
        ))
    ).toBe(false);
});
