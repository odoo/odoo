import { describe, expect, test, waitFor } from "@odoo/hoot";
import { animationFrame, press } from "@odoo/hoot-dom";
import { defineMailModels, focus, start } from "../../../mail_test_helpers";
import { getService } from "../../../../../../web/static/tests/web_test_helpers";

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

test("Tab enters the selected notification option and leaves the group", async () => {
    await start();
    await openSettings();
    await waitFor(".o-mail-DiscussNotificationSettings:count(1)");
    const all = ".o-mail-DiscussNotificationSettings [role='radio']:contains('All Messages')";
    const mentions = ".o-mail-DiscussNotificationSettings [role='radio']:contains('Mentions Only')";
    const nothing = ".o-mail-DiscussNotificationSettings [role='radio']:contains('Nothing')";
    const sound = ".o-mail-DiscussNotificationSettings [role='switch']";
    await focus(sound);
    await press(["shift", "tab"]);
    expect(mentions).toBeFocused();
    expect(mentions).toHaveAttribute("aria-checked", "true");
    for (const option of [mentions, nothing, all]) {
        expect(option).toBeFocused();
        await press("tab");
        expect(sound).toBeFocused();
        await press(["shift", "tab"]);
        expect(option).toBeFocused();
        await press("arrowdown");
        await animationFrame();
    }
});
