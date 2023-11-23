/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { patchBrowserNotification } from "@mail/../tests/helpers/patch_notifications";
import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { start } from "@mail/../tests/helpers/test_utils";

import { browser } from "@web/core/browser/browser";
import {
    getFixture,
    makeDeferred,
    patchWithCleanup,
    triggerHotkey,
} from "@web/../tests/helpers/utils";
import { click, contains, insertText, triggerEvents } from "@web/../tests/utils";

QUnit.module("messaging menu");

QUnit.test("should have messaging menu button in systray", async () => {
    await start();
    await contains(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu", { count: 0 });
    await contains(".o_menu_systray i[aria-label='Messages'].fa-comments");
});

QUnit.test("messaging menu should have topbar buttons", async () => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu");
    await contains(".o-mail-MessagingMenu-header button", { count: 4 });
    await contains("button.fw-bold", { text: "All" });
    await contains("button:not(.fw-bold)", { text: "Chats" });
    await contains("button:not(.fw-bold)", { text: "Channels" });
    await contains("button", { text: "New Message" });
});

QUnit.test("counter is taking into account failure notification", async () => {
    patchBrowserNotification("denied");
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ display_name: "general" });
    const messageId = pyEnv["mail.message"].create({
        model: "discuss.channel",
        res_id: channelId,
        record_name: "general",
        res_model_name: "Channel",
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
    await contains(".o-mail-MessagingMenu-counter", { text: "1" });
});

QUnit.test("rendering with OdooBot has a request (default)", async (assert) => {
    patchBrowserNotification("default");
    await start();
    await contains(".o-mail-MessagingMenu-counter");
    await contains(".o-mail-MessagingMenu-counter", { text: "1" });
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem");
    assert.ok(
        $(".o-mail-NotificationItem img")
            .data("src")
            .includes("/web/image?field=avatar_128&id=2&model=res.partner")
    );
    await contains(".o-mail-NotificationItem", { text: "OdooBot has a request" });
});

QUnit.test("rendering without OdooBot has a request (denied)", async () => {
    patchBrowserNotification("denied");
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu-counter", { count: 0 });
    await contains(".o-mail-NotificationItem", { count: 0 });
});

QUnit.test("rendering without OdooBot has a request (accepted)", async () => {
    patchBrowserNotification("granted");
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu-counter", { count: 0 });
    await contains(".o-mail-NotificationItem", { count: 0 });
});

QUnit.test("respond to notification prompt (denied)", async () => {
    patchBrowserNotification("default", "denied");
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o_notification.border-warning", {
        text: "Odoo will not send notifications on this device.",
    });
    await contains(".o-mail-MessagingMenu-counter", { count: 0 });
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { count: 0 });
});

QUnit.test("respond to notification prompt (granted)", async () => {
    patchBrowserNotification("default", "granted");
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o_notification.border-success", {
        text: "Odoo will send notifications on this device!",
    });
});

QUnit.test("no 'OdooBot has a request' in mobile app", async () => {
    patchBrowserNotification("default");
    // simulate Android Odoo App
    patchWithCleanup(browser.navigator, {
        userAgent: "Chrome/0.0.0 Android (OdooMobile; Linux; Android 13; Odoo TestSuite)",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu-counter", { count: 0 });
    await contains(".o-mail-NotificationItem", { count: 0 });
});

QUnit.test("rendering with PWA installation request", async (assert) => {
    const target = getFixture();

    patchWithCleanup(browser, {
        BeforeInstallPromptEvent: () => {},
    });
    patchWithCleanup(browser.localStorage, {
        getItem(key) {
            if (key === "pwa.installationState") {
                assert.step("getItem " + key);
                // in this test, installation has not yet proceeded
                return null;
            }
            return super.getItem(key);
        },
    });

    const { env } = await start();
    patchWithCleanup(env.services.installPrompt, {
        show() {
            assert.step("show prompt");
        },
    });
    assert.verifySteps(["getItem pwa.installationState"]);

    await contains(".o-mail-MessagingMenu-counter");
    await contains(".o-mail-MessagingMenu-counter", { text: "1" });
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem");
    assert.ok(
        target
            .querySelector(".o-mail-NotificationItem img")
            .dataset.src.includes("/web/image?field=avatar_128&id=2&model=res.partner")
    );
    assert.strictEqual(
        target.querySelector(".o-mail-NotificationItem-name").textContent,
        "OdooBot has a suggestion"
    );
    assert.strictEqual(
        target.querySelector(".o-mail-NotificationItem-text").textContent,
        "Come here often? Install Odoo on your device!"
    );

    await click(".o-mail-NotificationItem a.btn-primary");
    assert.verifySteps(["show prompt"]);
});

QUnit.test("rendering with PWA installation request (dismissed)", async (assert) => {
    const target = getFixture();

    patchWithCleanup(browser, {
        BeforeInstallPromptEvent: () => {},
    });
    patchWithCleanup(browser.localStorage, {
        getItem(key) {
            if (key === "pwa.installationState") {
                assert.step("getItem " + key);
                // in this test, installation has been previously dismissed by the user
                return "dismissed";
            }
            return super.getItem(key);
        },
    });

    await start();
    assert.verifySteps(["getItem pwa.installationState"]);
    assert.containsNone(target, ".o-mail-MessagingMenu-counter");

    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsNone(target, ".o-mail-NotificationItem");
});

QUnit.test("rendering with PWA installation request (already running as PWA)", async (assert) => {
    const target = getFixture();

    patchWithCleanup(browser, {
        BeforeInstallPromptEvent: () => {},
        matchMedia(media) {
            if (media === "(display-mode: standalone)") {
                return { matches: true };
            }
            return super.matchMedia(media);
        },
    });
    patchWithCleanup(browser.localStorage, {
        getItem(key) {
            if (key === "pwa.installationState") {
                assert.step("getItem " + key);
                // in this test, we remove any value that could contain localStorage so the service would be allowed to prompt
                return null;
            }
            return super.getItem(key);
        },
    });

    await start();
    assert.verifySteps(["getItem pwa.installationState"]);
    assert.containsNone(target, ".o-mail-MessagingMenu-counter");

    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsNone(target, ".o-mail-NotificationItem");
});

QUnit.test("Is closed after clicking on new message", async () => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "New Message" });
    await contains(".o-mail-MessagingMenu", { count: 0 });
});

QUnit.test("no 'New Message' button when discuss is open", async () => {
    const { openDiscuss, openView } = await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains("button", { text: "New Message" });

    await openDiscuss();
    await contains("button", { count: 0, text: "New Message" });

    await openView({
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains("button", { text: "New Message" });

    await openDiscuss();
    await contains("button", { count: 0, text: "New Message" });
});

QUnit.test("grouped notifications by document", async () => {
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
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click(".o-mail-NotificationItem", {
        text: "Partner",
        contains: [".badge", { text: "2" }],
    });
    await contains(".o-mail-ChatWindow");
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
    await click(".o-mail-NotificationItem", {
        text: "Partner",
        contains: [".badge", { text: "2" }],
    });
    assert.verifySteps(["do_action"]);
});

QUnit.test(
    "multiple grouped notifications by document model, sorted by the most recent message of each group",
    async () => {
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
        await contains(".o-mail-NotificationItem", { count: 2 });
        await contains(":nth-child(1 of .o-mail-NotificationItem)", { text: "Company" });
        await contains(":nth-child(2 of .o-mail-NotificationItem)", { text: "Partner" });
    }
);

QUnit.test("non-failure notifications are ignored", async () => {
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
    await contains(".o-mail-NotificationItem", { count: 0 });
});

QUnit.test("mark unread channel as read", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 1, partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        name: "My Channel",
    });
    const [messagId_1] = pyEnv["mail.message"].create([
        { author_id: partnerId, body: "not empty", model: "discuss.channel", res_id: channelId },
        { author_id: partnerId, body: "not empty", model: "discuss.channel", res_id: channelId },
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
    await triggerEvents(".o-mail-NotificationItem", ["mouseenter"]);
    await click(".o-mail-NotificationItem [title='Mark As Read']");
    await contains(".o-mail-NotificationItem.text-muted");
    assert.verifySteps(["set_last_seen_message"]);
    await triggerEvents(".o-mail-NotificationItem", ["mouseenter"]);
    await contains(".o-mail-NotificationItem [title='Mark As Read']", { count: 0 });
    await contains(".o-mail-ChatWindow", { count: 0 });
});

QUnit.test("mark failure as read", async () => {
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
    await triggerEvents(".o-mail-NotificationItem", ["mouseenter"], {
        contains: [
            [".o-mail-NotificationItem-name", { text: "Channel" }],
            [".o-mail-NotificationItem-text", { text: "An error occurred when sending an email" }],
        ],
    });
    await click("[title='Mark As Read']", {
        parent: [".o-mail-NotificationItem", { text: "Channel" }],
    });
    await contains(".o-mail-NotificationItem", { count: 0, text: "Channel" });
    await contains("o-mail-NotificationItem", {
        count: 0,
        text: "An error occurred when sending an email",
    });
});

QUnit.test("different discuss.channel are not grouped", async () => {
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
    await contains(".o-mail-NotificationItem", { count: 4 });
    await click(":nth-child(1 of .o-mail-NotificationItem)", { text: "Channel" });
    await contains(".o-mail-ChatWindow");
});

QUnit.test("mobile: active icon is highlighted", async () => {
    patchUiSize({ size: SIZES.SM });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-MessagingMenu-tab", { text: "Chat" });
    await contains(".o-mail-MessagingMenu-tab.fw-bolder", { text: "Chat" });
});

QUnit.test("open chat window from preview", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "test" });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
});

QUnit.test('"Start a conversation" in mobile shows channel selector (+ click away)', async () => {
    patchUiSize({ height: 360, width: 640 });
    const { openDiscuss } = await start();
    await openDiscuss();
    await click("button", { text: "Chat" });
    await contains("button", { text: "Start a conversation" });
    await contains("input[placeholder='Start a conversation']", { count: 0 });

    await click("button", { text: "Start a conversation" });
    await contains("button", { count: 0, text: "Start a conversation" });

    await contains("input[placeholder='Start a conversation']");

    await click(".o-mail-MessagingMenu");
    await contains("button", { text: "Start a conversation" });
    await contains("input[placeholder='Start a conversation']", { count: 0 });
});
QUnit.test('"New Channel" in mobile shows channel selector (+ click away)', async () => {
    patchUiSize({ height: 360, width: 640 });
    const { openDiscuss } = await start();
    await openDiscuss();
    await click("button", { text: "Channel" });
    await contains("button", { text: "New Channel" });
    await contains("input[placeholder='Add or join a channel']", { count: 0 });

    await click("button", { text: "New Channel" });
    await contains("button", { count: 0, text: "New Channel" });

    await contains("input[placeholder='Add or join a channel']");

    await click(".o-mail-MessagingMenu");
    await contains("button", { text: "New Channel" });
    await contains("input[placeholder='Add or join a channel']", { count: 0 });
});

QUnit.test("'Start a conversation' button should open a thread in mobile", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    patchUiSize({ height: 360, width: 640 });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "Start a conversation" });
    await insertText("input[placeholder='Start a conversation']", "demo");
    await click(".o-discuss-ChannelSelector-suggestion", { text: "Demo" });
    triggerHotkey("enter");
    await contains(".o-mail-ChatWindow", { text: "Demo" });
});

QUnit.test("Counter is updated when receiving new message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Albert" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const { env, openDiscuss } = await start();
    await openDiscuss();
    pyEnv.withUser(userId, () =>
        env.services.rpc("/mail/message/post", {
            thread_id: channelId,
            thread_model: "discuss.channel",
            post_data: {
                body: "Hello world",
                message_type: "comment",
            },
            context: {
                partnerId,
            },
        })
    );
    await contains(".o-mail-MessagingMenu-counter", { text: "1" });
});

QUnit.test("basic rendering", async (assert) => {
    patchWithCleanup(browser, {
        Notification: {
            ...browser.Notification,
            permission: "denied",
        },
    });
    await start();
    await contains(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    assert.doesNotHaveClass(
        $('.o_menu_systray .dropdown-toggle:has(i[aria-label="Messages"])'),
        "show"
    );
    await contains(".o_menu_systray i[aria-label='Messages']");
    await contains('.o_menu_systray i[aria-label="Messages"].fa-comments');
    await contains(".o-mail-MessagingMenu", { count: 0 });
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await contains('.o_menu_systray .dropdown:has(i[aria-label="Messages"]).show');
    await contains(".o-mail-MessagingMenu");
    await contains(".o-mail-MessagingMenu-header");
    await contains(".o-mail-MessagingMenu-header button", { count: 4 });
    await contains(".o-mail-MessagingMenu button.fw-bold", { text: "All" });
    await contains(".o-mail-MessagingMenu button:not(.fw-bold)", { text: "Chats" });
    await contains(".o-mail-MessagingMenu button:not(.fw-bold)", { text: "Channels" });
    await contains("button", { text: "New Message" });
    await contains(".o-mail-MessagingMenu div.text-muted", { text: "No conversation yet..." });
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    assert.doesNotHaveClass(
        $('.o_menu_systray .dropdown-toggle:has(i[aria-label="Messages"])'),
        "show"
    );
});

QUnit.test("switch tab", async () => {
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await contains(".o-mail-MessagingMenu button.fw-bold", { text: "All" });
    await contains(".o-mail-MessagingMenu button:not(.fw-bold)", { text: "Chats" });
    await contains(".o-mail-MessagingMenu button:not(.fw-bold)", { text: "Channels" });
    await click(".o-mail-MessagingMenu button", { text: "Chats" });
    await contains(".o-mail-MessagingMenu button:not(.fw-bold)", { text: "All" });
    await contains(".o-mail-MessagingMenu button.fw-bold", { text: "Chats" });
    await contains(".o-mail-MessagingMenu button:not(.fw-bold)", { text: "Channels" });
    await click(".o-mail-MessagingMenu button", { text: "Channels" });
    await contains(".o-mail-MessagingMenu button:not(.fw-bold)", { text: "All" });
    await contains(".o-mail-MessagingMenu button:not(.fw-bold)", { text: "Chats" });
    await contains(".o-mail-MessagingMenu button.fw-bold", { text: "Channels" });
    await click(".o-mail-MessagingMenu button", { text: "All" });
    await contains(".o-mail-MessagingMenu button.fw-bold", { text: "All" });
    await contains(".o-mail-MessagingMenu button:not(.fw-bold)", { text: "Chats" });
    await contains(".o-mail-MessagingMenu button:not(.fw-bold)", { text: "Channels" });
});

QUnit.test("channel preview: basic rendering", async () => {
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
    await contains(".o-mail-NotificationItem");
    await contains(".o-mail-NotificationItem img");
    await contains(".o-mail-NotificationItem-name", { text: "General" });
    await contains(".o-mail-NotificationItem-text", { text: "Demo: test" });
});

QUnit.test("filtered previews", async () => {
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
    await contains(".o-mail-NotificationItem", { count: 2 });
    await contains(".o-mail-NotificationItem", { text: "Mitchell Admin" });
    await contains(".o-mail-NotificationItem", { text: "channel1" });
    await click(".o-mail-MessagingMenu button", { text: "Chats" });
    await contains(".o-mail-NotificationItem", { text: "Mitchell Admin" });
    await click(".o-mail-MessagingMenu button", { text: "Channels" });
    await contains(".o-mail-NotificationItem", { text: "channel1" });
    await click(".o-mail-MessagingMenu button", { text: "All" });
    await contains(".o-mail-NotificationItem", { count: 2 });
    await contains(".o-mail-NotificationItem", { text: "Mitchell Admin" });
    await click(".o-mail-MessagingMenu button", { text: "Channels" });
    await contains(".o-mail-NotificationItem", { text: "channel1" });
});

QUnit.test("no code injection in message body preview", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    pyEnv["mail.message"].create({
        body: "<p><em>&shoulnotberaised</em><script>throw new Error('CodeInjectionError');</script></p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await contains(".o-mail-NotificationItem-text", {
        text: "You: &shoulnotberaisedthrow new Error('CodeInjectionError');",
    });
    await contains(".o-mail-NotificationItem-text script", { count: 0 });
});

QUnit.test("no code injection in message body preview from sanitized message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    pyEnv["mail.message"].create({
        body: "<p>&lt;em&gt;&shoulnotberaised&lt;/em&gt;&lt;script&gt;throw new Error('CodeInjectionError');&lt;/script&gt;</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await contains(".o-mail-NotificationItem-text", {
        text: "You: <em>&shoulnotberaised</em><script>throw new Error('CodeInjectionError');</script>",
    });
    await contains(".o-mail-NotificationItem-text script", { count: 0 });
});

QUnit.test("<br/> tags in message body preview are transformed in spaces", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    pyEnv["mail.message"].create({
        body: "<p>a<br/>b<br>c<br   />d<br     ></p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await contains(".o-mail-NotificationItem-text", { text: "You: a b c d" });
});

QUnit.test("Messaging menu notification body of chat should show author name once", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo User" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "<p>Hey!</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { text: "Demo User" });
    await contains(".o-mail-NotificationItem-text", { textContent: "Hey!" });
});

QUnit.test(
    "Group chat should be displayed inside the chat section of the messaging menu",
    async () => {
        const pyEnv = await startServer();
        pyEnv["discuss.channel"].create({ channel_type: "group" });
        await start();
        await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
        await click(".o-mail-MessagingMenu button", { text: "Chats" });
        await contains(".o-mail-NotificationItem");
    }
);

QUnit.test("click on preview should mark as read and open the thread", async () => {
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
    await contains(".o-mail-NotificationItem", { text: "Frodo Baggins" });
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click(".o-mail-NotificationItem", { text: "Frodo Baggins" });
    await contains(".o-mail-ChatWindow");
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { count: 0, text: "Frodo Baggins" });
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
        await click(".o-mail-NotificationItem", { text: "Frodo Baggins" });
        await click(".o-mail-ChatWindow-command i.fa-expand");
        await contains(".o-mail-ChatWindow", { count: 0 });
        assert.verifySteps(["do_action"], "should have done an action to open the form view");
    }
);

QUnit.test(
    "preview should display last needaction message preview even if there is a more recent message that is not needaction in the thread",
    async () => {
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
        await contains(".o-mail-NotificationItem-text", {
            text: "Stranger: I am the oldest but needaction",
        });
    }
);

QUnit.test("single preview for channel if it has unread and needaction messages", async () => {
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
    await contains(".o-mail-NotificationItem");
    await contains(".o-mail-NotificationItem-name", { text: "Test" });
    await contains(".o-mail-NotificationItem .badge", { text: "1" });
    await contains(".o-mail-NotificationItem-text", { text: "Partner1: Message with needaction" });
});

QUnit.test("chat should show unread counter on receiving new messages", async () => {
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
    await contains(".o-mail-NotificationItem", { text: "Partner1" });
    await contains(".o-mail-NotificationItem .badge", { count: 0, text: "1" });

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
    await contains(".o-mail-NotificationItem .badge", { text: "1" });
});

QUnit.test("preview for channel should show latest non-deleted message", async () => {
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
    await contains(".o-mail-NotificationItem-text", { text: "Partner1: message-2" });
    // Simulate deletion of message-2
    env.services.rpc("/mail/message/update_content", {
        message_id: messageId_2,
        body: "",
        attachment_ids: [],
    });
    await contains(".o-mail-NotificationItem-text", { text: "Partner1: message-1" });
});

QUnit.test("failure notifications are shown before channel preview", async () => {
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
    await contains(".o-mail-NotificationItem-text", {
        text: "An error occurred when sending an email",
        before: [".o-mail-NotificationItem-text", { text: "Partner1: message" }],
    });
});

QUnit.test("messaging menu should show new needaction messages from chatter", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Frodo Baggins" });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem-text", { count: 0, text: "@Mitchell Admin" });
    // simulate receiving a new needaction message
    pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.message/inbox", {
        author_id: partnerId,
        body: "@Mitchell Admin",
        id: 100,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        model: "res.partner",
        res_id: partnerId,
        record_name: "Frodo Baggins",
    });
    await contains(".o-mail-NotificationItem-text", { text: "@Mitchell Admin" });
});

QUnit.test("can open messaging menu even if messaging is not initialized", async () => {
    patchBrowserNotification("default");
    await startServer();
    const def = makeDeferred();
    await start({
        async mockRPC(route) {
            if (route === "/mail/init_messaging") {
                await def;
            }
        },
    });
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-DiscussSystray", { text: "No conversation yet..." });
    def.resolve();
    await contains(".o-mail-NotificationItem", { text: "OdooBot has a request" });
});
