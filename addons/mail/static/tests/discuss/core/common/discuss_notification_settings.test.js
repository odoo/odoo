import { contains, defineMailModels, focus, start } from "@mail/../tests/mail_test_helpers";

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, hover, press } from "@odoo/hoot-dom";
import { getService, onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

const settings = ".o-mail-DiscussNotificationSettings";
const all = `${settings} [role='radio']:contains('All Messages')`;
const mentions = `${settings} [role='radio']:contains('Mentions Only')`;
const nothing = `${settings} [role='radio']:contains('Nothing')`;
const sound = `${settings} [role='switch']`;

async function openSettings() {
    await start();
    await getService("action").doAction({
        tag: "mail.discuss_notification_settings_action",
        type: "ir.actions.client",
        target: "new",
        context: { dialog_size: "medium", footer: false },
    });
    await contains(settings);
}

test("notification settings: Tab enters the selected option and leaves the group", async () => {
    await openSettings();
    await focus(sound);
    await press(["shift", "tab"]);
    expect(mentions).toBeFocused();
    expect(mentions).toHaveAttribute("aria-checked", "true");

    for (const option of [mentions, nothing, all]) {
        expect(option).toBeFocused();
        await press("tab");
        expect(sound).toBeFocused();
        await press("arrowup");
        await animationFrame();
        expect(sound).toBeFocused();
        await press(["shift", "tab"]);
        expect(option).toBeFocused();
        await press("arrowdown");
        await animationFrame();
    }
});

test("notification settings: arrow navigation wraps without changing the setting", async () => {
    await openSettings();
    await focus(mentions);
    for (const [key, target] of [
        ["arrowdown", nothing],
        ["arrowdown", all],
        ["arrowup", nothing],
        ["arrowup", mentions],
        ["home", all],
        ["end", nothing],
    ]) {
        await press(key);
        await animationFrame();
        expect(target).toBeFocused();
        expect(mentions).toHaveAttribute("aria-checked", "true");
        expect(`${mentions} input`).toBeChecked();
    }
});

test("notification settings: select with Enter, Space, and click", async () => {
    await openSettings();
    onRpc("/discuss/settings/custom_notifications", async (request) => {
        const { params } = await request.json();
        expect.step(params.custom_notifications);
    });
    await focus(mentions);
    await press("arrowdown");
    await animationFrame();
    await hover(all);
    await press("enter");
    await contains(`${nothing}[aria-checked='true']`);
    expect(`${nothing} input`).toBeChecked();
    expect.verifySteps(["no_notif"]);
    await press("tab");
    expect(sound).toBeFocused();
    await press(["shift", "tab"]);
    expect(nothing).toBeFocused();

    await press("arrowdown");
    await animationFrame();
    await press("space");
    await contains(`${all}[aria-checked='true']`);
    expect(`${all} input`).toBeChecked();
    expect.verifySteps(["all"]);
    await press("tab");
    expect(sound).toBeFocused();

    await click(mentions);
    expect(mentions).toBeFocused();
    await contains(`${mentions}[aria-checked='true']`);
    expect(`${mentions} input`).toBeChecked();
    expect.verifySteps([false]);
    await press("tab");
    expect(sound).toBeFocused();
});
