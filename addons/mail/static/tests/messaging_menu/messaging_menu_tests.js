/* @odoo-module */

import { Command } from "@mail/../tests/helpers/command";
import {
    afterNextRender,
    click,
    insertText,
    start,
    startServer,
    waitUntil,
} from "@mail/../tests/helpers/test_utils";

import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import { patchWithCleanup, triggerEvent, triggerHotkey } from "@web/../tests/helpers/utils";
import { patchBrowserNotification } from "@mail/../tests/helpers/patch_notifications";
import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { browser } from "@web/core/browser/browser";

QUnit.module("messaging menu");

QUnit.test("should have messaging menu button in systray", async (assert) => {
    await start();
    assert.containsOnce($, ".o_menu_systray i[aria-label='Messages']");
    assert.containsNone($, ".o-mail-MessagingMenu", "messaging menu closed by default");
    assert.hasClass($(".o_menu_systray i[aria-label='Messages']"), "fa-comments");
});

QUnit.test("messaging menu should have topbar buttons", async (assert) => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce($, ".o-mail-MessagingMenu");
    assert.containsN($, ".o-mail-MessagingMenu-header button", 4);
    assert.containsOnce($, "button:contains(All)");
    assert.containsOnce($, "button:contains(Chat)");
    assert.containsOnce($, "button:contains(Channel)");
    assert.containsOnce($, "button:contains(New Message)");
    assert.hasClass($("button:contains(All)"), "fw-bolder");
    assert.doesNotHaveClass($("button:contains(Chat)"), "fw-bolder");
    assert.doesNotHaveClass($("button:contains(Channel)"), "fw-bolder");
});

QUnit.test("counter is taking into account failure notification", async (assert) => {
    patchBrowserNotification("denied");
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    const messageId = pyEnv["mail.message"].create({
        model: "discuss.channel",
        res_id: channelId,
    });
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", pyEnv.currentPartnerId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], {
        seen_message_id: messageId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "exception",
        notification_type: "email",
    });
    await start();
    assert.containsOnce($, ".o-mail-MessagingMenu-counter");
    assert.strictEqual($(".o-mail-MessagingMenu-counter.badge").text(), "1");
});

QUnit.test("rendering with OdooBot has a request (default)", async (assert) => {
    patchBrowserNotification("default");
    await start();
    assert.containsOnce($, ".o-mail-MessagingMenu-counter");
    assert.strictEqual($(".o-mail-MessagingMenu-counter").text(), "1");
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce($, ".o-mail-NotificationItem");
    assert.ok(
        $(".o-mail-NotificationItem img")
            .data("src")
            .includes("/web/image?field=avatar_128&id=2&model=res.partner")
    );
    assert.strictEqual($(".o-mail-NotificationItem-name").text().trim(), "OdooBot has a request");
});

QUnit.test("rendering without OdooBot has a request (denied)", async (assert) => {
    patchBrowserNotification("denied");
    await start();
    assert.containsNone($, ".o-mail-MessagingMenu-counter-badge");
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsNone($, ".o-mail-NotificationItem");
});

QUnit.test("rendering without OdooBot has a request (accepted)", async (assert) => {
    patchBrowserNotification("granted");
    await start();
    assert.containsNone($, ".o-mail-MessagingMenu-counter-badge");
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsNone($, ".o-mail-NotificationItem");
});

QUnit.test("respond to notification prompt (denied)", async (assert) => {
    patchBrowserNotification("default", "denied");
    await start({
        services: {
            notification: makeFakeNotificationService(() => {
                assert.step("confirmation_denied_toast");
            }),
        },
    });
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    assert.verifySteps(["confirmation_denied_toast"]);
    assert.containsNone($, ".o-mail-MessagingMenu-counter-badge");
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsNone($, ".o-mail-NotificationItem");
});

QUnit.test("respond to notification prompt (granted)", async (assert) => {
    patchBrowserNotification("default", "granted");
    await start({
        services: {
            notification: makeFakeNotificationService(() => {
                assert.step("confirmation_granted_toast");
            }),
        },
    });
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    assert.verifySteps(["confirmation_granted_toast"]);
});

QUnit.test("Is closed after clicking on new message", async (assert) => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button:contains(New Message)");
    assert.containsNone($, ".o-mail-MessagingMenu");
});

QUnit.test("no 'New Message' button when discuss is open", async (assert) => {
    const { openDiscuss, openView } = await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce($, "button:contains(New Message)");

    await openDiscuss();
    assert.containsNone($, "button:contains(New Message)");

    await openView({
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce($, "button:contains(New Message)");

    await openDiscuss();
    assert.containsNone($, "button:contains(New Message)");
});

QUnit.test("grouped notifications by document", async (assert) => {
    const pyEnv = await startServer();
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "email",
            model: "res.partner",
            res_id: 31,
            res_model_name: "Partner",
        },
        {
            message_type: "email",
            model: "res.partner",
            res_id: 31,
            res_model_name: "Partner",
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId_1,
            notification_status: "exception",
            notification_type: "email",
        },
        {
            mail_message_id: messageId_2,
            notification_status: "bounce",
            notification_type: "email",
        },
    ]);
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce($, ".o-mail-NotificationItem");
    assert.containsOnce($, ".o-mail-NotificationItem:contains(Partner) .badge:contains(2)");
    assert.containsNone($, ".o-mail-ChatWindow");

    await click(".o-mail-NotificationItem");
    assert.containsOnce($, ".o-mail-ChatWindow");
});

QUnit.test("grouped notifications by document model", async (assert) => {
    const pyEnv = await startServer();
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "email",
            model: "res.partner",
            res_id: 31,
            res_model_name: "Partner",
        },
        {
            message_type: "email",
            model: "res.partner",
            res_id: 32,
            res_model_name: "Partner",
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId_1,
            notification_status: "exception",
            notification_type: "email",
        },
        {
            mail_message_id: messageId_2,
            notification_status: "bounce",
            notification_type: "email",
        },
    ]);
    const { env } = await start();
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.step("do_action");
            assert.strictEqual(action.name, "Mail Failures");
            assert.strictEqual(action.type, "ir.actions.act_window");
            assert.strictEqual(action.view_mode, "kanban,list,form");
            assert.strictEqual(
                JSON.stringify(action.views),
                JSON.stringify([
                    [false, "kanban"],
                    [false, "list"],
                    [false, "form"],
                ])
            );
            assert.strictEqual(action.target, "current");
            assert.strictEqual(action.res_model, "res.partner");
            assert.strictEqual(
                JSON.stringify(action.domain),
                JSON.stringify([["message_has_error", "=", true]])
            );
        },
    });
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce($, ".o-mail-NotificationItem:contains(Partner) .badge:contains(2)");

    $(".o-mail-NotificationItem")[0].click();
    assert.verifySteps(["do_action"]);
});

QUnit.test(
    "multiple grouped notifications by document model, sorted by the most recent message of each group",
    async (assert) => {
        const pyEnv = await startServer();
        const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
            {
                message_type: "email",
                model: "res.partner",
                res_id: 31,
                res_model_name: "Partner",
            },
            {
                message_type: "email",
                model: "res.company",
                res_id: 32,
                res_model_name: "Company",
            },
        ]);
        pyEnv["mail.notification"].create([
            {
                mail_message_id: messageId_1,
                notification_status: "exception",
                notification_type: "email",
            },
            {
                mail_message_id: messageId_1,
                notification_status: "exception",
                notification_type: "email",
            },
            {
                mail_message_id: messageId_2,
                notification_status: "bounce",
                notification_type: "email",
            },
            {
                mail_message_id: messageId_2,
                notification_status: "bounce",
                notification_type: "email",
            },
        ]);
        await start();
        await click(".o_menu_systray i[aria-label='Messages']");
        assert.containsN($, ".o-mail-NotificationItem", 2);
        assert.ok($(".o-mail-NotificationItem:eq(0)").text().includes("Company"));
        assert.ok($(".o-mail-NotificationItem:eq(1)").text().includes("Partner"));
    }
);

QUnit.test("non-failure notifications are ignored", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const messageId = pyEnv["mail.message"].create({
        message_type: "email",
        model: "res.partner",
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "ready",
        notification_type: "email",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsNone($, ".o-mail-NotificationItem");
});

QUnit.test("mark unread channel as read", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 1, partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const [messagId_1] = pyEnv["mail.message"].create([
        { author_id: partnerId, model: "discuss.channel", res_id: channelId },
        { author_id: partnerId, model: "discuss.channel", res_id: channelId },
    ]);
    const [currentMemberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", pyEnv.currentPartnerId],
    ]);
    pyEnv["discuss.channel.member"].write([currentMemberId], { seen_message_id: messagId_1 });
    await start({
        async mockRPC(route, args) {
            if (route.includes("set_last_seen_message")) {
                assert.step("set_last_seen_message");
            }
        },
    });
    await click(".o_menu_systray i[aria-label='Messages']");
    await triggerEvent($(".o-mail-NotificationItem")[0], null, "mouseenter");
    assert.containsOnce($, ".o-mail-NotificationItem [title='Mark As Read']");

    await click(".o-mail-NotificationItem [title='Mark As Read']");
    assert.verifySteps(["set_last_seen_message"]);
    assert.hasClass($(".o-mail-NotificationItem"), "o-muted");
    await triggerEvent($(".o-mail-NotificationItem")[0], null, "mouseenter");
    assert.containsNone($, ".o-mail-NotificationItem [title='Mark As Read']");
    assert.containsNone($, ".o-mail-ChatWindow");
});

QUnit.test("mark failure as read", async (assert) => {
    const pyEnv = await startServer();
    const messageId = pyEnv["mail.message"].create({
        message_type: "email",
        res_model_name: "Channel",
    });
    pyEnv["discuss.channel"].create({
        message_ids: [messageId],
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId, seen_message_id: messageId }),
        ],
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "exception",
        notification_type: "email",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce($, ".o-mail-NotificationItem:contains(Channel)");
    assert.containsOnce(
        $,
        ".o-mail-NotificationItem:contains(An error occurred when sending an email)"
    );
    await triggerEvent($(".o-mail-NotificationItem:contains(Channel)")[0], null, "mouseenter");
    assert.containsOnce($, ".o-mail-NotificationItem:contains(Channel) [title='Mark As Read']");

    await click(".o-mail-NotificationItem [title='Mark As Read']");
    assert.containsNone($, ".o-mail-NotificationItem:contains(Channel)");
    assert.containsNone(
        $,
        ".o-mail-NotificationItem:contains(An error occurred when sending an email)"
    );
});

QUnit.test("different discuss.channel are not grouped", async (assert) => {
    const pyEnv = await startServer();
    const [channelId_1, channelId_2] = pyEnv["discuss.channel"].create([
        { name: "Channel_1" },
        { name: "Channel_2" },
    ]);
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "email",
            model: "discuss.channel",
            res_id: channelId_1,
            res_model_name: "Channel",
        },
        {
            message_type: "email",
            model: "discuss.channel",
            res_id: channelId_2,
            res_model_name: "Channel",
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId_1,
            notification_status: "exception",
            notification_type: "email",
        },
        {
            mail_message_id: messageId_1,
            notification_status: "exception",
            notification_type: "email",
        },
        {
            mail_message_id: messageId_2,
            notification_status: "bounce",
            notification_type: "email",
        },
        {
            mail_message_id: messageId_2,
            notification_status: "bounce",
            notification_type: "email",
        },
    ]);
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsN($, ".o-mail-NotificationItem", 4);

    const group_1 = $(".o-mail-NotificationItem:contains(Channel):first");
    await click(group_1);
    assert.containsOnce($, ".o-mail-ChatWindow");
});

QUnit.test("mobile: active icon is highlighted", async (assert) => {
    patchUiSize({ size: SIZES.SM });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-MessagingMenu-tab:contains(Chat)");
    assert.hasClass($(".o-mail-MessagingMenu-tab:contains(Chat)"), "fw-bolder");
});

QUnit.test("open chat window from preview", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "test" });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    assert.containsOnce($, ".o-mail-ChatWindow");
});

QUnit.test(
    '"Start a conversation" in mobile shows channel selector (+ click away)',
    async (assert) => {
        patchUiSize({ height: 360, width: 640 });
        const { openDiscuss } = await start();
        await openDiscuss();
        await click("button:contains(Chat)");
        assert.containsOnce($, "button:contains(Start a conversation)");
        assert.containsNone($, "input[placeholder='Start a conversation']");

        await click("button:contains(Start a conversation)");
        assert.containsNone($, "button:contains(Start a conversation)");
        assert.containsOnce($, "input[placeholder='Start a conversation']");

        await click(".o-mail-MessagingMenu");
        assert.containsOnce($, "button:contains(Start a conversation)");
        assert.containsNone($, "input[placeholder='Start a conversation']");
    }
);
QUnit.test('"New Channel" in mobile shows channel selector (+ click away)', async (assert) => {
    patchUiSize({ height: 360, width: 640 });
    const { openDiscuss } = await start();
    await openDiscuss();
    await click("button:contains(Channel)");
    assert.containsOnce($, "button:contains(New Channel)");
    assert.containsNone($, "input[placeholder='Add or join a channel']");

    await click("button:contains(New Channel)");
    assert.containsNone($, "button:contains(New Channel)");
    assert.containsOnce($, "input[placeholder='Add or join a channel']");

    await click(".o-mail-MessagingMenu");
    assert.containsOnce($, "button:contains(New Channel)");
    assert.containsNone($, "input[placeholder='Add or join a channel']");
});

QUnit.test('"Start a conversation" item selection opens chat', async (assert) => {
    patchUiSize({ height: 360, width: 640 });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Gandalf" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const { openDiscuss } = await start();
    await openDiscuss();
    await click("button:contains(Chat)");
    await click("button:contains(Start a conversation)");
    await insertText("input[placeholder='Start a conversation']", "Gandalf");
    await click(".o-mail-ChannelSelector-suggestion");
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.containsOnce($, ".o-mail-ChatWindow-name[title='Gandalf']");
});

QUnit.test('"New channel" item selection opens channel (existing)', async (assert) => {
    patchUiSize({ height: 360, width: 640 });
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "Gryffindors" });
    const { openDiscuss } = await start();
    await openDiscuss();
    await click("button:contains(Channel)");
    await click("button:contains(New Channel)");
    await insertText("input[placeholder='Add or join a channel']", "Gryff");
    await click(".o-mail-ChannelSelector-suggestion");
    assert.containsOnce($, ".o-mail-ChatWindow-name[title='Gryffindors']");
});

QUnit.test('"New channel" item selection opens channel (new)', async (assert) => {
    patchUiSize({ height: 360, width: 640 });
    const { openDiscuss } = await start();
    await openDiscuss();
    await click("button:contains(Channel)");
    await click("button:contains(New Channel)");
    await insertText("input[placeholder='Add or join a channel']", "slytherins");
    await click(".o-mail-ChannelSelector-suggestion");
    assert.containsOnce($, ".o-mail-ChatWindow-name[title='slytherins']");
});

QUnit.test("'New Message' button should open a chat window in mobile", async (assert) => {
    patchUiSize({ height: 360, width: 640 });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button:contains(New Message)");
    assert.containsOnce($, ".o-mail-ChatWindow");
});

QUnit.test("Counter is updated when receiving new message", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const partnerId = pyEnv["res.partner"].create({ name: "Albert" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const { env, openDiscuss } = await start();
    await openDiscuss();
    await afterNextRender(() =>
        env.services.rpc("/mail/message/post", {
            thread_id: channelId,
            thread_model: "discuss.channel",
            post_data: {
                body: "Hello world",
                message_type: "comment",
            },
            context: {
                mockedUserId: userId,
                partnerId,
            },
        })
    );
    assert.containsOnce($, ".o-mail-MessagingMenu-counter.badge:contains(1)");
});

QUnit.test("basic rendering", async (assert) => {
    patchWithCleanup(browser, {
        Notification: {
            ...browser.Notification,
            permission: "denied",
        },
    });
    await start();
    assert.containsOnce($, ".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    assert.doesNotHaveClass(
        $('.o_menu_systray .dropdown-toggle:has(i[aria-label="Messages"])'),
        "show"
    );
    assert.containsOnce($, ".o_menu_systray i[aria-label='Messages']");
    assert.hasClass($('.o_menu_systray i[aria-label="Messages"]'), "fa-comments");
    assert.containsNone($, ".o-mail-MessagingMenu");
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    assert.hasClass($('.o_menu_systray .dropdown:has(i[aria-label="Messages"])'), "show");
    assert.containsOnce($, ".o-mail-MessagingMenu");
    assert.containsOnce($, ".o-mail-MessagingMenu-header");
    assert.containsN($, ".o-mail-MessagingMenu-header button", 4);
    assert.containsOnce($, '.o-mail-MessagingMenu button:contains("All")');
    assert.containsOnce($, '.o-mail-MessagingMenu button:contains("Chats")');
    assert.containsOnce($, '.o-mail-MessagingMenu button:contains("Channels")');
    assert.hasClass($('.o-mail-MessagingMenu button:contains("All")'), "fw-bolder");
    assert.doesNotHaveClass($('.o-mail-MessagingMenu button:contains("Chats")'), "fw-bolder");
    assert.doesNotHaveClass($('.o-mail-MessagingMenu button:contains("Channels")'), "fw-bolder");
    assert.containsOnce($, "button:contains(New Message)");
    assert.containsOnce($, '.o-mail-MessagingMenu:contains("No conversation yet...")');
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    assert.doesNotHaveClass(
        $('.o_menu_systray .dropdown-toggle:has(i[aria-label="Messages"])'),
        "show"
    );
});

QUnit.test("switch tab", async (assert) => {
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    assert.containsOnce($, '.o-mail-MessagingMenu button:contains("All")');
    assert.containsOnce($, '.o-mail-MessagingMenu button:contains("Chats")');
    assert.containsOnce($, '.o-mail-MessagingMenu button:contains("Channels")');
    assert.hasClass($('.o-mail-MessagingMenu button:contains("All")'), "fw-bolder");
    assert.doesNotHaveClass($('.o-mail-MessagingMenu button:contains("Chats")'), "fw-bolder");
    assert.doesNotHaveClass($('.o-mail-MessagingMenu button:contains("Channels")'), "fw-bolder");
    await click('.o-mail-MessagingMenu button:contains("Chats")');
    assert.doesNotHaveClass($('.o-mail-MessagingMenu button:contains("All")'), "fw-bolder");
    assert.hasClass($('.o-mail-MessagingMenu button:contains("Chats")'), "fw-bolder");
    assert.doesNotHaveClass($('.o-mail-MessagingMenu button:contains("Channels")'), "fw-bolder");
    await click('.o-mail-MessagingMenu button:contains("Channels")');
    assert.doesNotHaveClass($('.o-mail-MessagingMenu button:contains("All")'), "fw-bolder");
    assert.doesNotHaveClass($('.o-mail-MessagingMenu button:contains("Chats")'), "fw-bolder");
    assert.hasClass($('.o-mail-MessagingMenu button:contains("Channels")'), "fw-bolder");
    await click('.o-mail-MessagingMenu button:contains("All")');
    assert.hasClass($('.o-mail-MessagingMenu button:contains("All")'), "fw-bolder");
    assert.doesNotHaveClass($('.o-mail-MessagingMenu button:contains("Chats")'), "fw-bolder");
    assert.doesNotHaveClass($('.o-mail-MessagingMenu button:contains("Channels")'), "fw-bolder");
});

QUnit.test("new message [REQUIRE FOCUS]", async (assert) => {
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await click('.o-mail-MessagingMenu button:contains("New Message")');
    assert.containsOnce($, ".o-mail-ChatWindow");
    assert.containsOnce($, ".o-mail-ChatWindow .o-mail-ChannelSelector");
    assert.containsOnce($, ".o-mail-ChannelSelector input:focus");
});

QUnit.test("channel preview: basic rendering", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "<p>test</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    assert.containsOnce($, ".o-mail-NotificationItem");
    assert.containsOnce($, ".o-mail-NotificationItem img");
    assert.containsOnce($, '.o-mail-NotificationItem:contains("General")');
    assert.containsOnce($, '.o-mail-NotificationItem:contains("Demo: test")');
});

QUnit.test("filtered previews", async (assert) => {
    const pyEnv = await startServer();
    const [channelId_1, channelId_2] = pyEnv["discuss.channel"].create([
        { channel_type: "chat" },
        { name: "channel1" },
    ]);
    pyEnv["mail.message"].create([
        {
            model: "discuss.channel", // to link message to channel
            res_id: channelId_1, // id of related channel
        },
        {
            model: "discuss.channel", // to link message to channel
            res_id: channelId_2, // id of related channel
        },
    ]);
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    assert.containsN($, ".o-mail-NotificationItem", 2);
    assert.containsOnce($, '.o-mail-NotificationItem:contains("Mitchell Admin")');
    assert.containsOnce($, '.o-mail-NotificationItem:contains("channel1")');
    await click('.o-mail-MessagingMenu button:contains("Chats")');
    assert.containsOnce($, '.o-mail-NotificationItem:contains("Mitchell Admin")');
    await click('.o-mail-MessagingMenu button:contains("Channels")');
    assert.containsOnce($, '.o-mail-NotificationItem:contains("channel1")');
    await click('.o-mail-MessagingMenu button:contains("All")');
    assert.containsN($, ".o-mail-NotificationItem", 2);
    assert.containsOnce($, '.o-mail-NotificationItem:contains("Mitchell Admin")');
    await click('.o-mail-MessagingMenu button:contains("Channels")');
    assert.containsOnce($, '.o-mail-NotificationItem:contains("channel1")');
});

QUnit.test("no code injection in message body preview", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    pyEnv["mail.message"].create({
        body: "<p><em>&shoulnotberaised</em><script>throw new Error('CodeInjectionError');</script></p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    assert.containsOnce($, ".o-mail-NotificationItem");
    assert.strictEqual(
        $(".o-mail-NotificationItem-text").text().replace(/\s/g, ""),
        "You:&shoulnotberaisedthrownewError('CodeInjectionError');"
    );
    assert.containsNone($(".o-mail-NotificationItem-text"), "script");
});

QUnit.test("no code injection in message body preview from sanitized message", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    pyEnv["mail.message"].create({
        body: "<p>&lt;em&gt;&shoulnotberaised&lt;/em&gt;&lt;script&gt;throw new Error('CodeInjectionError');&lt;/script&gt;</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    assert.containsOnce($, ".o-mail-NotificationItem");
    assert.containsOnce($, ".o-mail-NotificationItem-text");
    assert.strictEqual(
        $(".o-mail-NotificationItem-text").text().replace(/\s/g, ""),
        "You:<em>&shoulnotberaised</em><script>thrownewError('CodeInjectionError');</script>"
    );
    assert.containsNone($(".o-mail-NotificationItem-text"), "script");
});

QUnit.test("<br/> tags in message body preview are transformed in spaces", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    pyEnv["mail.message"].create({
        body: "<p>a<br/>b<br>c<br   />d<br     ></p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    assert.containsOnce($, ".o-mail-NotificationItem");
    assert.containsOnce($, ".o-mail-NotificationItem-text");
    assert.strictEqual($(".o-mail-NotificationItem-text").text(), "You: a b c d");
});

QUnit.test(
    "Group chat should be displayed inside the chat section of the messaging menu",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["discuss.channel"].create({ channel_type: "group" });
        await start();
        await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
        await click('.o-mail-MessagingMenu button:contains("Chats")');
        assert.containsOnce($, ".o-mail-NotificationItem");
    }
);

QUnit.test("click on preview should mark as read and open the thread", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Frodo Baggins" });
    const messageId = pyEnv["mail.message"].create({
        model: "res.partner",
        body: "not empty",
        author_id: pyEnv.odoobotId,
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce($, ".o-mail-NotificationItem:contains(Frodo Baggins)");
    assert.containsNone($, ".o-mail-ChatWindow");
    await click(".o-mail-NotificationItem:contains(Frodo Baggins)");
    assert.containsOnce($, ".o-mail-ChatWindow");
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsNone($, ".o-mail-NotificationItem:contains(Frodo Baggins)");
});

QUnit.test(
    "click on expand from chat window should close the chat window and open the form view",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Frodo Baggins" });
        const messageId = pyEnv["mail.message"].create({
            model: "res.partner",
            body: "not empty",
            author_id: pyEnv.odoobotId,
            needaction: true,
            needaction_partner_ids: [pyEnv.currentPartnerId],
            res_id: partnerId,
        });
        pyEnv["mail.notification"].create({
            mail_message_id: messageId,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        });
        const { env } = await start();
        patchWithCleanup(env.services.action, {
            doAction(action) {
                assert.step("do_action");
                assert.strictEqual(action.res_id, partnerId);
                assert.strictEqual(action.res_model, "res.partner");
            },
        });
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-NotificationItem:contains(Frodo Baggins)");
        await click(".o-mail-ChatWindow-command i.fa-expand");
        assert.containsNone($, ".o-mail-ChatWindow");
        assert.verifySteps(["do_action"], "should have done an action to open the form view");
    }
);

QUnit.test(
    "preview should display last needaction message preview even if there is a more recent message that is not needaction in the thread",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Stranger" });
        const messageId = pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "I am the oldest but needaction",
            model: "res.partner",
            needaction: true,
            needaction_partner_ids: [pyEnv.currentPartnerId],
            res_id: partnerId,
        });
        pyEnv["mail.message"].create({
            author_id: pyEnv.currentPartnerId,
            body: "I am more recent",
            model: "res.partner",
            res_id: partnerId,
        });
        pyEnv["mail.notification"].create({
            mail_message_id: messageId,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        });
        await start();
        await click(".o_menu_systray i[aria-label='Messages']");
        assert.containsOnce($, ".o-mail-NotificationItem:contains(I am the oldest but needaction)");
    }
);

QUnit.test(
    "single preview for channel if it has unread and needaction messages",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Partner1" });
        const channelId = pyEnv["discuss.channel"].create({
            name: "Test",
            channel_member_ids: [
                Command.create({ message_unread_counter: 2, partner_id: pyEnv.currentPartnerId }),
            ],
        });
        const messageId = pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "Message with needaction",
            model: "discuss.channel",
            needaction: true,
            needaction_partner_ids: [pyEnv.currentPartnerId],
            res_id: channelId,
        });
        pyEnv["mail.notification"].create({
            mail_message_id: messageId,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        });
        pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "Most-recent Message",
            model: "discuss.channel",
            res_id: channelId,
        });

        await start();
        await click(".o_menu_systray i[aria-label='Messages']");
        assert.containsN($, ".o-mail-NotificationItem", 1);
        assert.ok($(".o-mail-NotificationItem").text().includes("Test"));
        assert.ok($(".o-mail-NotificationItem .badge").text().includes("1"));
        assert.ok($(".o-mail-NotificationItem").text().includes("Message with needaction"));
    }
);

QUnit.test("chat should show unread counter on receiving new messages", async (assert) => {
    // unread and needaction are conceptually the same in chat
    // however message_needaction_counter is not updated
    // so special care for chat to simulate needaction with unread
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner1" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ message_unread_counter: 0, partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce($, ".o-mail-NotificationItem");
    assert.containsOnce($, ".o-mail-NotificationItem:contains(Partner1)");
    assert.containsNone($, ".o-mail-NotificationItem .badge:contains('1')");
    // simulate receiving a new message
    const channel = pyEnv["discuss.channel"].searchRead([["id", "=", channelId]])[0];
    pyEnv["bus.bus"]._sendone(channel, "discuss.channel/new_message", {
        id: channelId,
        message: {
            author_id: partnerId,
            body: "new message",
            id: 126,
            model: "discuss.channel",
            res_id: channelId,
        },
    });
    await waitUntil(".o-mail-NotificationItem .badge:contains('1')");
});

QUnit.test("preview for channel should show latest non-deleted message", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner1" });
    const channelId = pyEnv["discuss.channel"].create({ name: "Test" });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "message-1",
        model: "discuss.channel",
        res_id: channelId,
    });
    const messageId_2 = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "message-2",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { env } = await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce($, ".o-mail-NotificationItem:contains(message-2)");
    // Simulate deletion of message-2
    await afterNextRender(() =>
        env.services.rpc("/mail/message/update_content", {
            message_id: messageId_2,
            body: "",
            attachment_ids: [],
        })
    );
    assert.containsOnce($, ".o-mail-NotificationItem:contains(message-1)");
});

QUnit.test("failure notifications are shown before channel preview", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner1" });
    const failedMessageId = pyEnv["mail.message"].create({
        message_type: "email",
        res_model_name: "Channel",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "Test" });
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "message",
        model: "discuss.channel",
        res_id: channelId,
    });
    pyEnv["discuss.channel"].write([channelId], { message_ids: [messageId, failedMessageId] });
    pyEnv["mail.notification"].create({
        mail_message_id: failedMessageId,
        notification_status: "exception",
        notification_type: "email",
    });
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", pyEnv.currentPartnerId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], { seen_message_id: messageId });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce(
        $,
        ".o-mail-NotificationItem:contains(An error occurred when sending an email)"
    );
    assert.containsOnce($, ".o-mail-NotificationItem:contains(message)");
    assert.containsOnce(
        $,
        ".o-mail-NotificationItem:contains(An error occurred when sending an email) ~ .o-mail-NotificationItem:contains(message)"
    );
});

QUnit.test("messaging menu should show new needaction messages from chatter", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Frodo Baggins" });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsNone($, ".o-mail-NotificationItem:contains(@Mitchell Admin)");

    // simulate receiving a new needaction message
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.message/inbox", {
            body: "@Mitchell Admin",
            id: 100,
            needaction_partner_ids: [pyEnv.currentPartnerId],
            model: "res.partner",
            res_id: partnerId,
            record_name: "Frodo Baggins",
        });
    });
    assert.containsOnce($, ".o-mail-NotificationItem:contains(@Mitchell Admin)");
});
