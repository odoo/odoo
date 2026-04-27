import {
    click,
    contains,
    defineMailModels,
    patchUiSize,
    SIZES,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { Command, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";
import { methods } from "@web_mobile/js/services/core";

describe.current.tags("desktop");
defineMailModels();

test("'backbutton' event should close chat window", async () => {
    // simulate the feature is available on the current device
    // component must and will be destroyed before the overrideBackButton is unpatched
    patchWithCleanup(methods, {
        overrideBackButton({ enabled }) {},
    });
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                fold_state: "open",
                partner_id: serverState.partnerId,
            }),
        ],
    });
    await start();

    await contains(".o-mail-ChatWindow");
    // simulate 'backbutton' event triggered by the mobile app
    const backButtonEvent = new Event("backbutton");
    document.dispatchEvent(backButtonEvent);
    await contains(".o-mail-ChatWindow", { count: 0 });
});

test("[technical] chat window should properly override the back button", async () => {
    // simulate the feature is available on the current device
    // component must and will be destroyed before the overrideBackButton is unpatched
    let overrideBackButton = false;
    patchWithCleanup(methods, {
        overrideBackButton({ enabled }) {
            overrideBackButton = enabled;
        },
    });
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "test" });
    patchUiSize({ size: SIZES.SM });
    await start();

    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu");
    await click(".o-mail-NotificationItem", { text: "test" });
    await contains(".o-mail-ChatWindow");
    await contains(".o-mail-MessagingMenu", { count: 0 });
    expect(overrideBackButton).toBe(true);

    await click(".o-mail-ChatWindow [title*='Close']");
    await contains(".o-mail-MessagingMenu");
    // The messaging menu is re-open when a chat window is closed,
    // so we need to close it because it overrides the back button too.
    // As long as something overrides the back button, it can't be disabled.
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await contains(".o-mail-MessagingMenu", { count: 0 });
    expect(overrideBackButton).toBe(false);
});
