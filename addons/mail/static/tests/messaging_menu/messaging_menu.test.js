/** @odoo-module */

import { expect, test } from "@odoo/hoot";

import { rpc } from "@web/core/network/rpc";

import { browser } from "@web/core/browser/browser";
import { getOrigin } from "@web/core/utils/urls";
import {
    SIZES,
    assertSteps,
    click,
    contains,
    insertText,
    openDiscuss,
    openFormView,
    patchBrowserNotification,
    patchUiSize,
    start,
    startServer,
    step,
    triggerEvents,
    triggerHotkey,
} from "../mail_test_helpers";
import { Command, constants, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Deferred } from "@odoo/hoot-mock";
import { deserializeDateTime } from "@web/core/l10n/dates";

test.skip("should have messaging menu button in systray", async () => {
    await start();
    await contains(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu", { count: 0 });
    await contains(".o_menu_systray i[aria-label='Messages'].fa-comments");
});

test.skip("messaging menu should have topbar buttons", async () => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu");
    await contains(".o-mail-MessagingMenu-header button", { count: 4 });
    await contains("button.fw-bold", { text: "All" });
    await contains("button:not(.fw-bold)", { text: "Chats" });
    await contains("button:not(.fw-bold)", { text: "Channels" });
    await contains("button", { text: "New Message" });
});

test.skip("counter is taking into account failure notification", async () => {
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
        ["partner_id", "=", constants.PARTNER_ID],
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

test.skip("rendering with OdooBot has a request (default)", async () => {
    patchBrowserNotification("default");
    const pyEnv = await startServer();
    const odoobot = pyEnv["res.partner"].search([
        ["id", "in", constants.ODOOBOT_ID],
        ["active_test", "=", false],
    ])[0];
    await start();
    await contains(".o-mail-MessagingMenu-counter");
    await contains(".o-mail-MessagingMenu-counter", { text: "1" });
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem");
    await contains(
        `.o-mail-NotificationItem img[data-src='${getOrigin()}/web/image/res.partner/${
            constants.ODOOBOT_ID
        }/avatar_128?unique=${deserializeDateTime(odoobot.write_date).ts}']`
    );
    await contains(".o-mail-NotificationItem", { text: "OdooBot has a request" });
});

test.skip("rendering without OdooBot has a request (denied)", async () => {
    patchBrowserNotification("denied");
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu-counter", { count: 0 });
    await contains(".o-mail-NotificationItem", { count: 0 });
});

test.skip("rendering without OdooBot has a request (accepted)", async () => {
    patchBrowserNotification("granted");
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu-counter", { count: 0 });
    await contains(".o-mail-NotificationItem", { count: 0 });
});

test.skip("respond to notification prompt (denied)", async () => {
    patchBrowserNotification("default", "denied");
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o_notification:has(.o_notification_bar.bg-warning)", {
        text: "Odoo will not send notifications on this device.",
    });
    await contains(".o-mail-MessagingMenu-counter", { count: 0 });
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { count: 0 });
});

test.skip("respond to notification prompt (granted)", async () => {
    patchBrowserNotification("default", "granted");
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o_notification:has(.o_notification_bar.bg-success)", {
        text: "Odoo will send notifications on this device!",
    });
});

test.skip("no 'OdooBot has a request' in mobile app", async () => {
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

test.skip("rendering with PWA installation request", async () => {
    patchWithCleanup(browser, {
        BeforeInstallPromptEvent: () => {},
    });
    patchWithCleanup(browser.localStorage, {
        getItem(key) {
            if (key === "pwa.installationState") {
                step("getItem " + key);
                // in this test, installation has not yet proceeded
                return null;
            }
            return super.getItem(key);
        },
    });
    const pyEnv = await startServer();
    const odoobot = pyEnv["res.partner"].search_read([["id", "in", constants.ODOOBOT_ID]], {
        context: { active_test: false },
    })[0];
    const { env } = await start();
    // This event must be triggered to initialize the installPrompt service properly
    // as if it was run by a browser supporting PWA (never triggered in a test otherwise).
    browser.dispatchEvent(new CustomEvent("beforeinstallprompt"));
    patchWithCleanup(env.services.installPrompt, {
        show() {
            step("show prompt");
        },
    });
    await assertSteps(["getItem pwa.installationState"]);
    await contains(".o-mail-MessagingMenu-counter");
    await contains(".o-mail-MessagingMenu-counter", { text: "1" });
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem");
    await contains(
        `.o-mail-NotificationItem img[data-src='${getOrigin()}/web/image/res.partner/${
            constants.ODOOBOT_ID
        }/avatar_128?unique=${deserializeDateTime(odoobot.write_date).ts}']`
    );
    await contains(".o-mail-NotificationItem-name", { text: "OdooBot has a suggestion" });
    await contains(".o-mail-NotificationItem-text", {
        text: "Come here often? Install Odoo on your device!",
    });
    await click(".o-mail-NotificationItem a.btn-primary");
    await assertSteps(["show prompt"]);
});

test.skip("installation of the PWA request can be dismissed", async () => {
    patchWithCleanup(browser, {
        BeforeInstallPromptEvent: () => {},
    });
    patchWithCleanup(browser.localStorage, {
        getItem(key) {
            if (key === "pwa.installationState") {
                step("getItem " + key);
                // in this test, installation has not yet proceeded
                return null;
            }
            return super.getItem(key);
        },
        setItem(key, value) {
            if (key === "pwa.installationState") {
                step("installationState value:  " + value);
            }
            return super.setItem(key, value);
        },
    });
    const { env } = await start();
    // This event must be triggered to initialize the installPrompt service properly
    // as if it was run by a browser supporting PWA (never triggered in a test otherwise).
    browser.dispatchEvent(new CustomEvent("beforeinstallprompt"));
    patchWithCleanup(env.services.installPrompt, {
        show() {
            step("show prompt should not be triggered");
        },
    });
    await assertSteps(["getItem pwa.installationState"]);
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem .fa-close");
    await assertSteps(["installationState value:  dismissed"]);
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { count: 0 });
});

test.skip("rendering with PWA installation request (dismissed)", async () => {
    patchWithCleanup(browser, {
        BeforeInstallPromptEvent: () => {},
    });
    patchWithCleanup(browser.localStorage, {
        getItem(key) {
            if (key === "pwa.installationState") {
                step("getItem " + key);
                // in this test, installation has been previously dismissed by the user
                return "dismissed";
            }
            return super.getItem(key);
        },
    });
    await start();
    // This event must be triggered to initialize the installPrompt service properly
    // as if it was run by a browser supporting PWA (never triggered in a test otherwise).
    browser.dispatchEvent(new CustomEvent("beforeinstallprompt"));
    await assertSteps(["getItem pwa.installationState"]);
    await contains(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu-counter", { count: 0 });
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { count: 0 });
});

test.skip("rendering with PWA installation request (already running as PWA)", async () => {
    patchWithCleanup(browser, {
        BeforeInstallPromptEvent: () => {},
    });
    patchWithCleanup(browser.localStorage, {
        getItem(key) {
            if (key === "pwa.installationState") {
                step("getItem " + key);
                // in this test, we remove any value that could contain localStorage so the service would be allowed to prompt
                return null;
            }
            return super.getItem(key);
        },
    });
    await start();
    // The 'beforeinstallprompt' event is not triggered here, since the
    // browser wouldn't trigger it when the app is already launched
    await assertSteps(["getItem pwa.installationState"]);
    await contains(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu-counter", { count: 0 });
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { count: 0 });
});

test.skip("Is closed after clicking on new message", async () => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "New Message" });
    await contains(".o-mail-MessagingMenu", { count: 0 });
});

test.skip("no 'New Message' button when discuss is open", async () => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains("button", { text: "New Message" });
    await openDiscuss();
    await contains("button", { count: 0, text: "New Message" });
    await openFormView("res.partner");
    await contains("button", { text: "New Message" });
    await openDiscuss();
    await contains("button", { count: 0, text: "New Message" });
});

test.skip("grouped notifications by document", async () => {
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

test.skip("grouped notifications by document model", async () => {
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
            step("do_action");
            expect(action.name).toBe("Mail Failures");
            expect(action.type).toBe("ir.actions.act_window");
            expect(action.view_mode).toBe("kanban,list,form");
            expect(JSON.stringify(action.views)).toBe(
                JSON.stringify([
                    [false, "kanban"],
                    [false, "list"],
                    [false, "form"],
                ])
            );
            expect(action.target).toBe("current");
            expect(action.res_model).toBe("res.partner");
            expect(JSON.stringify(action.domain)).toBe(
                JSON.stringify([["message_has_error", "=", true]])
            );
        },
    });
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", {
        text: "Partner",
        contains: [".badge", { text: "2" }],
    });
    await assertSteps(["do_action"]);
});

test.skip("multiple grouped notifications by document model, sorted by the most recent message of each group", async () => {
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
});

test.skip("non-failure notifications are ignored", async () => {
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

test.skip("mark unread channel as read", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 1, partner_id: constants.PARTNER_ID }),
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
        ["partner_id", "=", constants.PARTNER_ID],
    ]);
    pyEnv["discuss.channel.member"].write([currentMemberId], { seen_message_id: messagId_1 });
    onRpc((route) => {
        if (route === "/discuss/channel/set_last_seen_message") {
            step("set_last_seen_message");
        }
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await triggerEvents(".o-mail-NotificationItem", ["mouseenter"]);
    await click(".o-mail-NotificationItem [title='Mark As Read']");
    await contains(".o-mail-NotificationItem.text-muted");
    await assertSteps(["set_last_seen_message"]);
    await triggerEvents(".o-mail-NotificationItem", ["mouseenter"]);
    await contains(".o-mail-NotificationItem [title='Mark As Read']", { count: 0 });
    await contains(".o-mail-ChatWindow", { count: 0 });
});

test.skip("mark failure as read", async () => {
    const pyEnv = await startServer();
    const messageId = pyEnv["mail.message"].create({
        message_type: "email",
        res_model_name: "Channel",
    });
    pyEnv["discuss.channel"].create({
        message_ids: [messageId],
        channel_member_ids: [
            Command.create({ partner_id: constants.PARTNER_ID, seen_message_id: messageId }),
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

test.skip("different discuss.channel are not grouped", async () => {
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

test.skip("mobile: active icon is highlighted", async () => {
    patchUiSize({ size: SIZES.SM });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-MessagingMenu-tab", { text: "Chat" });
    await contains(".o-mail-MessagingMenu-tab.fw-bolder", { text: "Chat" });
});

test.skip("open chat window from preview", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "test" });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
});

test.skip('"Start a conversation" in mobile shows channel selector (+ click away)', async () => {
    patchUiSize({ height: 360, width: 640 });
    await start();
    await openDiscuss();
    await contains("button.active", { text: "Inbox" });
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
test.skip('"New Channel" in mobile shows channel selector (+ click away)', async () => {
    patchUiSize({ height: 360, width: 640 });
    await start();
    await openDiscuss();
    await contains("button.active", { text: "Inbox" });
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

test.skip("'Start a conversation' button should open a thread in mobile", async () => {
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

test.skip("Counter is updated when receiving new message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Albert" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            Command.create({ partner_id: constants.PARTNER_ID }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss();
    pyEnv.withUser(userId, () =>
        rpc("/mail/message/post", {
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

test.skip("basic rendering", async () => {
    patchWithCleanup(browser, {
        Notification: {
            ...browser.Notification,
            permission: "denied",
        },
    });
    await start();
    await contains(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    expect($('.o_menu_systray .dropdown-toggle:has(i[aria-label="Messages"])')[0]).not.toHaveClass(
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
    await contains(".o-dropdown--menu", { count: 0 });
    expect($('.o_menu_systray .dropdown-toggle:has(i[aria-label="Messages"])')[0]).not.toHaveClass(
        "show"
    );
});

test.skip("switch tab", async () => {
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

test.skip("channel preview: basic rendering", async () => {
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

test.skip("filtered previews", async () => {
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

test.skip("no code injection in message body preview", async () => {
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

test.skip("no code injection in message body preview from sanitized message", async () => {
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

test.skip("<br/> tags in message body preview are transformed in spaces", async () => {
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

test.skip("Messaging menu notification body of chat should show author name once", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo User" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: constants.PARTNER_ID }),
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

test.skip("Group chat should be displayed inside the chat section of the messaging menu", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ channel_type: "group" });
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await click(".o-mail-MessagingMenu button", { text: "Chats" });
    await contains(".o-mail-NotificationItem");
});

test.skip("click on preview should mark as read and open the thread", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Frodo Baggins" });
    const messageId = pyEnv["mail.message"].create({
        model: "res.partner",
        body: "not empty",
        author_id: constants.ODOOBOT_ID,
        needaction: true,
        needaction_partner_ids: [constants.PARTNER_ID],
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: constants.PARTNER_ID,
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

test.skip("click on expand from chat window should close the chat window and open the form view", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Frodo Baggins" });
    const messageId = pyEnv["mail.message"].create({
        model: "res.partner",
        body: "not empty",
        author_id: constants.ODOOBOT_ID,
        needaction: true,
        needaction_partner_ids: [constants.PARTNER_ID],
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: constants.PARTNER_ID,
    });
    const { env } = await start();
    patchWithCleanup(env.services.action, {
        doAction(action) {
            step("do_action");
            expect(action.res_id).toBe(partnerId);
            expect(action.res_model).toBe("res.partner");
        },
    });
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Frodo Baggins" });
    await click(".o-mail-ChatWindow-command i.fa-expand");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await assertSteps(["do_action"], "should have done an action to open the form view");
});

test.skip("preview should display last needaction message preview even if there is a more recent message that is not needaction in the thread", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Stranger" });
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "I am the oldest but needaction",
        model: "res.partner",
        needaction: true,
        needaction_partner_ids: [constants.PARTNER_ID],
        res_id: partnerId,
    });
    pyEnv["mail.message"].create({
        author_id: constants.PARTNER_ID,
        body: "I am more recent",
        model: "res.partner",
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: constants.PARTNER_ID,
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem-text", {
        text: "Stranger: I am the oldest but needaction",
    });
});

test.skip("single preview for channel if it has unread and needaction messages", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner1" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Test",
        channel_member_ids: [
            Command.create({ message_unread_counter: 2, partner_id: constants.PARTNER_ID }),
        ],
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "Message with needaction",
        model: "discuss.channel",
        needaction: true,
        needaction_partner_ids: [constants.PARTNER_ID],
        res_id: channelId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: constants.PARTNER_ID,
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

test.skip("chat should show unread counter on receiving new messages", async () => {
    // unread and needaction are conceptually the same in chat
    // however message_needaction_counter is not updated
    // so special care for chat to simulate needaction with unread
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner1" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ message_unread_counter: 0, partner_id: constants.PARTNER_ID }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { text: "Partner1" });
    await contains(".o-mail-NotificationItem .badge", { count: 0, text: "1" });

    // simulate receiving a new message
    const channel = pyEnv["discuss.channel"].search_read([["id", "=", channelId]])[0];
    pyEnv["bus.bus"]._sendone(channel, "discuss.channel/new_message", {
        id: channelId,
        message: {
            author: await pyEnv["res.partner"].mail_partner_format([partnerId])[partnerId],
            body: "new message",
            id: 126,
            model: "discuss.channel",
            res_id: channelId,
        },
    });
    await contains(".o-mail-NotificationItem .badge", { text: "1" });
});

test.skip("preview for channel should show latest non-deleted message", async () => {
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
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem-text", { text: "Partner1: message-2" });
    // Simulate deletion of message-2
    rpc("/mail/message/update_content", {
        message_id: messageId_2,
        body: "",
        attachment_ids: [],
    });
    await contains(".o-mail-NotificationItem-text", { text: "Partner1: message-1" });
});

test.skip("failure notifications are shown before channel preview", async () => {
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
        ["partner_id", "=", constants.PARTNER_ID],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], { seen_message_id: messageId });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem-text", {
        text: "An error occurred when sending an email",
        before: [".o-mail-NotificationItem-text", { text: "Partner1: message" }],
    });
});

test.skip("messaging menu should show new needaction messages from chatter", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Frodo Baggins" });
    const { env } = await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem-text", {
        count: 0,
        text: "Frodo Baggins: @Mitchel Admin",
    });
    // simulate receiving a new needaction message
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "@Mitchel Admin",
        needaction: true,
        model: "res.partner",
        res_id: partnerId,
        needaction_partner_ids: [constants.PARTNER_ID],
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: constants.PARTNER_ID,
    });
    const [formattedMessage] = await env.services.orm.call("mail.message", "message_format", [
        [messageId],
    ]);
    pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.message/inbox", formattedMessage);
    await contains(".o-mail-NotificationItem-text", { text: "Frodo Baggins: @Mitchel Admin" });
});

test.skip("can open messaging menu even if messaging is not initialized", async () => {
    patchBrowserNotification("default");
    await startServer();
    const def = new Deferred();
    onRpc(async (route, args) => {
        if (route === "/mail/action" && args.init_messaging) {
            await def;
        }
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { text: "OdooBot has a request" });
});

test.skip("can open messaging menu even if channels are not fetched", async () => {
    patchBrowserNotification("denied");
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    const def = new Deferred();
    onRpc(async (route, args) => {
        if (["/mail/action", "/mail/data"].includes(route) && args.channels_as_member) {
            await def;
        }
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { text: "General" });
});

QUnit.test("Latest needaction is shown in thread preview", async () => {
    const pyEnv = await startServer();
    for (let i = 1; i <= 2; i++) {
        const messageId = pyEnv["mail.message"].create({
            body: `message ${i}`,
            message_type: "comment",
            model: "res.partner",
            needaction: true,
            needaction_partner_ids: [pyEnv.currentPartnerId],
            res_id: pyEnv.currentPartnerId,
        });
        pyEnv["mail.notification"].create({
            mail_message_id: messageId,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        });
    }
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { text: pyEnv.currentPartner.name });
    await contains(".o-mail-NotificationItem", { text: "You: message 2" });
});
