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
    await click(".o-Discuss-header button[title='Start a Call']");
    assert.containsOnce($, ".o-Call");
    assert.containsOnce($, ".o-CallParticipantCard[aria-label='Mitchell Admin']");
    assert.containsOnce($, ".o-CallActionList");
    assert.containsN($, ".o-CallActionList button", 6);
    assert.containsOnce($, "button[aria-label='Unmute'], button[aria-label='Mute']"); // FIXME depends on current browser permission
    assert.containsOnce($, ".o-CallActionList button[aria-label='Deafen']");
    assert.containsOnce($, ".o-CallActionList button[aria-label='Turn camera on']");
    assert.containsOnce($, ".o-CallActionList button[aria-label='Share screen']");
    assert.containsOnce($, ".o-CallActionList button[aria-label='Enter Full Screen']");
    assert.containsOnce($, ".o-CallActionList button[aria-label='Disconnect']");
});

QUnit.test("should not display call UI when no more members (self disconnect)", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-Discuss-header button[title='Start a Call']");
    assert.containsOnce($, ".o-Call");

    await click(".o-CallActionList button[aria-label='Disconnect']");
    assert.containsNone($, ".o-Call");
});

QUnit.test("show call UI in chat window when in call", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({ name: "General" });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-NotificationItem:contains(General)");
    assert.containsOnce($, ".o-ChatWindow");
    assert.containsNone($, ".o-Call");
    assert.containsOnce($, ".o-ChatWindow-header .o-ChatWindow-command[title='Start a Call']");

    await click(".o-ChatWindow-header .o-ChatWindow-command[title='Start a Call']");
    assert.containsOnce($, ".o-Call");
    assert.containsNone($, ".o-ChatWindow-header .o-ChatWindow-command[title='Start a Call']");
});

QUnit.skipRefactoring("should disconnect when closing page while in call", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-Discuss-header button[title='Start a Call']");
    assert.containsOnce($, ".o-Call");

    // simulate page close
    await afterNextRender(() => window.dispatchEvent(new Event("pagehide"), { bubble: true }));
    assert.containsNone($, ".o-Call");
});

QUnit.test("no default rtc after joining a chat conversation", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Mario" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsNone($, ".o-DiscussCategoryItem");

    await click(".o-DiscussSidebar i[title='Start a conversation']");
    await afterNextRender(() => editInput(document.body, ".o-ChannelSelector input", "mario"));
    await click(".o-ChannelSelector-suggestion");
    await triggerEvent(document.body, ".o-ChannelSelector input", "keydown", {
        key: "Enter",
    });
    assert.containsOnce($, ".o-DiscussCategoryItem");
    assert.containsNone($, ".o-Discuss-content .o-Message");
    assert.containsNone($, ".o-Call");
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
    assert.containsNone($, ".o-DiscussCategoryItem");
    await click(".o-DiscussSidebar i[title='Start a conversation']");
    await afterNextRender(() => editInput(document.body, ".o-ChannelSelector input", "mario"));
    await click(".o-ChannelSelector-suggestion");
    await afterNextRender(() => editInput(document.body, ".o-ChannelSelector input", "luigi"));
    await click(".o-ChannelSelector-suggestion");
    await triggerEvent(document.body, ".o-ChannelSelector input", "keydown", {
        key: "Enter",
    });
    assert.containsOnce($, ".o-DiscussCategoryItem");
    assert.containsNone($, ".o-Discuss-content .o-Message");
    assert.containsNone($, ".o-Call");
});
