/** @odoo-module **/

import { afterNextRender, click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { editInput, triggerEvent } from "@web/../tests/helpers/utils";

QUnit.module("call");

QUnit.test("basic rendering", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "General",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-discuss-header button[title='Start a Call']");
    assert.containsOnce($, ".o-mail-call");
    assert.containsOnce($, ".o-mail-call-participant-card[aria-label='Mitchell Admin']");
    assert.containsOnce($, ".o-mail-call-action-list");
    assert.containsN($, ".o-mail-call-action-list button", 6);
    assert.containsOnce($, "button[aria-label='Unmute'], button[aria-label='Mute']"); // FIXME depends on current browser permission
    assert.containsOnce($, ".o-mail-call-action-list button[aria-label='Deafen']");
    assert.containsOnce($, ".o-mail-call-action-list button[aria-label='Turn camera on']");
    assert.containsOnce($, ".o-mail-call-action-list button[aria-label='Share screen']");
    assert.containsOnce($, ".o-mail-call-action-list button[aria-label='Enter Full Screen']");
    assert.containsOnce($, ".o-mail-call-action-list button[aria-label='Disconnect']");
});

QUnit.test("should not display call UI when no more members (self disconnect)", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-discuss-header button[title='Start a Call']");
    assert.containsOnce($, ".o-mail-call");

    await click(".o-mail-call-action-list button[aria-label='Disconnect']");
    assert.containsNone($, ".o-mail-call");
});

QUnit.test("show call UI in chat window when in call", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({ name: "General" });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-notification-item:contains(General)");
    assert.containsOnce($, ".o-mail-chat-window");
    assert.containsNone($, ".o-mail-call");
    assert.containsOnce($, ".o-mail-chat-window-header .o-mail-command[title='Start a Call']");

    await click(".o-mail-chat-window-header .o-mail-command[title='Start a Call']");
    assert.containsOnce($, ".o-mail-call");
    assert.containsNone($, ".o-mail-chat-window-header .o-mail-command[title='Start a Call']");
});

QUnit.skipRefactoring("should disconnect when closing page while in call", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-discuss-header button[title='Start a Call']");
    assert.containsOnce($, ".o-mail-call");

    // simulate page close
    await afterNextRender(() => window.dispatchEvent(new Event("pagehide"), { bubble: true }));
    assert.containsNone($, ".o-mail-call");
});

QUnit.test("no default rtc after joining a chat conversation", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Mario" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsNone($, ".o-mail-category-item");

    await click(".o-mail-discuss-sidebar i[title='Start a conversation']");
    await afterNextRender(() =>
        editInput(document.body, ".o-mail-channel-selector input", "mario")
    );
    await click(".o-mail-channel-selector-suggestion");
    await triggerEvent(document.body, ".o-mail-channel-selector input", "keydown", {
        key: "Enter",
    });
    assert.containsOnce($, ".o-mail-category-item");
    assert.containsNone($, ".o-mail-discuss-content .o-mail-message");
    assert.containsNone($, ".o-mail-call");
});

QUnit.test("no default rtc after joining a group conversation", async (assert) => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Mario" },
        { name: "Luigi" },
    ]);
    pyEnv["res.users"].create([{ partner_id: partnerId_1 }, { partner_id: partnerId_2 }]);
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsNone($, ".o-mail-category-item");
    await click(".o-mail-discuss-sidebar i[title='Start a conversation']");
    await afterNextRender(() =>
        editInput(document.body, ".o-mail-channel-selector input", "mario")
    );
    await click(".o-mail-channel-selector-suggestion");
    await afterNextRender(() =>
        editInput(document.body, ".o-mail-channel-selector input", "luigi")
    );
    await click(".o-mail-channel-selector-suggestion");
    await triggerEvent(document.body, ".o-mail-channel-selector input", "keydown", {
        key: "Enter",
    });
    assert.containsOnce($, ".o-mail-category-item");
    assert.containsNone($, ".o-mail-discuss-content .o-mail-message");
    assert.containsNone($, ".o-mail-call");
});
