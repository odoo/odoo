/** @odoo-module **/

import { afterNextRender, click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { getFixture, editInput, triggerEvent } from "@web/../tests/helpers/utils";

let target;
QUnit.module("call", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("basic rendering", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "General",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-discuss-actions button[title='Start a Call']");
    assert.containsOnce(target, ".o-mail-call");
    assert.containsOnce(target, ".o-mail-call-participant-card[aria-label='Mitchell Admin']");
    assert.containsOnce(target, ".o-mail-call-action-list");
    assert.containsN(target, ".o-mail-call-action-list button", 6);
    assert.containsOnce(target, "button[aria-label='Unmute'], button[aria-label='Mute']"); // FIXME depends on current browser permission
    assert.containsOnce(target, ".o-mail-call-action-list button[aria-label='Deafen']");
    assert.containsOnce(target, ".o-mail-call-action-list button[aria-label='Turn camera on']");
    assert.containsOnce(target, ".o-mail-call-action-list button[aria-label='Share screen']");
    assert.containsOnce(target, ".o-mail-call-action-list button[aria-label='Enter Full Screen']");
    assert.containsOnce(target, ".o-mail-call-action-list button[aria-label='Disconnect']");
});

QUnit.test(
    "should not display call UI when no more members (self disconnect)",
    async function (assert) {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({
            name: "General",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await click(".o-mail-discuss-actions button[title='Start a Call']");
        assert.containsOnce(target, ".o-mail-call");

        await click(".o-mail-call-action-list button[aria-label='Disconnect']");
        assert.containsNone(target, ".o-mail-call");
    }
);

QUnit.test("show call UI in chat window when in call", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({
        name: "General",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-messaging-menu .o-mail-notification-item:contains(General)");
    assert.containsOnce(target, ".o-mail-chat-window");
    assert.containsNone(target, ".o-mail-call");
    assert.containsOnce(target, ".o-mail-chat-window-header .o-mail-command[title='Start a Call']");

    await click(".o-mail-chat-window-header .o-mail-command[title='Start a Call']");
    assert.containsOnce(target, ".o-mail-call");
    assert.containsNone(target, ".o-mail-chat-window-header .o-mail-command[title='Start a Call']");
});

QUnit.test("should disconnect when closing page while in call", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "General",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-discuss-actions button[title='Start a Call']");
    assert.containsOnce(target, ".o-mail-call");

    // simulate page close
    await afterNextRender(() => window.dispatchEvent(new Event("beforeunload"), { bubble: true }));
    assert.containsNone(target, ".o-mail-call");
});

QUnit.test("no default rtc after joining a chat conversation", async (assert) => {
    const pyEnv = await startServer();
    const resPartnerId = pyEnv["res.partner"].create({
        name: "Mario",
    });
    pyEnv["res.users"].create({
        partner_id: resPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsNone(target, ".o-mail-category-item");

    await click(".o-mail-discuss-sidebar i[title='Start a conversation']");
    await afterNextRender(() => editInput(target, ".o-mail-channel-selector-input", "mario"));
    await click(".o-mail-channel-selector-suggestion");
    await triggerEvent(target, ".o-mail-channel-selector-input", "keydown", {
        key: "Enter",
    });
    assert.containsOnce(target, ".o-mail-category-item");
    assert.containsNone(target, ".o-mail-discuss-content .o-mail-message");
    assert.containsNone(target, ".o-mail-call");
});

QUnit.test("no default rtc after joining a group conversation", async (assert) => {
    const pyEnv = await startServer();
    const [resPartnerId1, resPartnerId2] = pyEnv["res.partner"].create([
        {
            name: "Mario",
        },
        { name: "Luigi" },
    ]);
    pyEnv["res.users"].create([
        {
            partner_id: resPartnerId1,
        },
        {
            partner_id: resPartnerId2,
        },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsNone(target, ".o-mail-category-item");
    await click(".o-mail-discuss-sidebar i[title='Start a conversation']");
    await afterNextRender(() => editInput(target, ".o-mail-channel-selector-input", "mario"));
    await click(".o-mail-channel-selector-suggestion");
    await afterNextRender(() => editInput(target, ".o-mail-channel-selector-input", "luigi"));
    await click(".o-mail-channel-selector-suggestion");
    await triggerEvent(target, ".o-mail-channel-selector-input", "keydown", {
        key: "Enter",
    });
    assert.containsOnce(target, ".o-mail-category-item");
    assert.containsNone(target, ".o-mail-discuss-content .o-mail-message");
    assert.containsNone(target, ".o-mail-call");
});
