import { click, defineMailModels, focus, start } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test, waitFor } from "@odoo/hoot";
import { animationFrame, hover, press } from "@odoo/hoot-dom";
import { getService, onRpc } from "@web/../tests/web_test_helpers";

defineMailModels();
describe.current.tags("desktop");

async function openSettings() {
    await getService("action").doAction({
        tag: "mail.discuss_notification_settings_action",
        type: "ir.actions.client",
        target: "new",
        context: { dialog_size: "medium", footer: false },
    });
}

const all = ".o-mail-DiscussNotificationSettings-option:contains('All Messages')";
const mentions = ".o-mail-DiscussNotificationSettings-option:contains('Mentions Only')";
const nothing = ".o-mail-DiscussNotificationSettings-option:contains('Nothing')";
const sound = ".o-mail-DiscussNotificationSettings [role='switch']";

test("Tab leaves and re-enters the group on the active option", async () => {
    await start();
    await openSettings();
    await waitFor(".o-mail-DiscussNotificationSettings:count(1)");
    await focus(sound);
    await press(["shift", "tab"]);
    expect(mentions).toBeFocused();
    expect(mentions).toHaveAttribute("aria-checked", "true");
    await press("arrowdown");
    await animationFrame();
    expect(nothing).toBeFocused();
    await press("tab");
    expect(sound).toBeFocused();
    await press(["shift", "tab"]);
    expect(nothing).toBeFocused();
});

test("Arrow navigation wraps without changing the settings", async () => {
    onRpc("/discuss/settings/custom_notifications", () => {
        expect.step("custom_notifications");
    });
    await start();
    await openSettings();
    await waitFor(".o-mail-DiscussNotificationSettings:count(1)");
    await focus(mentions);
    for (const [key, target] of [
        ["arrowdown", nothing],
        ["arrowdown", all],
        ["arrowup", nothing],
        ["arrowup", mentions],
    ]) {
        await press(key);
        await animationFrame();
        expect(target).toBeFocused();
        expect(mentions).toHaveAttribute("aria-checked", "true");
        expect(`${mentions} input`).toBeChecked();
    }
    expect.verifySteps([]);
});

test("Select a notification option with Enter, Space and click", async () => {
    onRpc("/discuss/settings/custom_notifications", async (request) => {
        const { params } = await request.json();
        expect.step(params.custom_notifications);
    });
    await start();
    await openSettings();
    await waitFor(".o-mail-DiscussNotificationSettings:count(1)");
    await focus(mentions);
    await press("arrowdown");
    await animationFrame();
    expect(nothing).toBeFocused();
    await hover(all);
    await press("enter");
    await waitFor(`${nothing}[aria-checked='true']`);
    expect.verifySteps(["no_notif"]);
    await press("arrowdown");
    await animationFrame();
    expect(all).toBeFocused();
    await press("space");
    await waitFor(`${all}[aria-checked='true']`);
    expect.verifySteps(["all"]);
    await click(mentions);
    await waitFor(`${mentions}[aria-checked='true']`);
    expect.verifySteps([false]);
});
