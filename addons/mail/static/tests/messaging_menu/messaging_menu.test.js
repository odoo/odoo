import {
    click,
    contains,
    defineMailModels,
    insertText,
    listenStoreFetch,
    onRpcBefore,
    openDiscuss,
    patchBrowserNotification,
    patchUiSize,
    SIZES,
    start,
    startServer,
    triggerEvents,
    triggerHotkey,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { describe, expect, test } from "@odoo/hoot";
import { Deferred, mockUserAgent } from "@odoo/hoot-mock";
import {
    asyncStep,
    Command,
    makeKwArgs,
    mockService,
    patchWithCleanup,
    serverState,
    waitForSteps,
    withUser,
} from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";
import { getOrigin } from "@web/core/utils/urls";

describe.current.tags("desktop");
defineMailModels();

test("should have messaging menu button in systray", async () => {
    await start();
    await contains(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu", { count: 0 });
    await contains(".o_menu_systray i[aria-label='Messages'].fa-comments");
});

test("messaging menu should have topbar buttons", async () => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu");
    await contains(".o-mail-MessagingMenu-header button", { count: 4 });
    await contains("button.fw-bold", { text: "Notifications" });
    await contains("button:not(.fw-bold)", { text: "Chats" });
    await contains("button:not(.fw-bold)", { text: "Channels" });
    await contains("button", { text: "New Message" });
});

test("counter is taking into account failure notification", async () => {
    patchBrowserNotification("denied");
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ display_name: "general" });
    const messageId = pyEnv["mail.message"].create({
        model: "discuss.channel",
        res_id: channelId,
        record_name: "general",
    });
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", serverState.partnerId],
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

test("rendering with chat push notification default permissions", async () => {
    patchBrowserNotification("default");
    const pyEnv = await startServer();
    const [odoobot] = pyEnv["res.partner"].read(serverState.odoobotId);
    await start();
    await contains(".o-mail-MessagingMenu-counter");
    await contains(".o-mail-MessagingMenu-counter", { text: "1" });
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem");
    await contains(
        `.o-mail-NotificationItem img[data-src='${getOrigin()}/web/image/res.partner/${
            serverState.odoobotId
        }/avatar_128?unique=${deserializeDateTime(odoobot.write_date).ts}']`
    );
    await contains(".o-mail-NotificationItem", { text: "Turn on notifications" });
});

test("can quickly dismiss 'Turn on notification' suggestion", async () => {
    patchBrowserNotification("default");
    await start();
    await contains(".o-mail-MessagingMenu-counter", { text: "1" });
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem");
    await contains(".o-mail-NotificationItem", { text: "Turn on notifications" });
    await click(".o-mail-NotificationItem:contains(Turn on notifications) [title='Dismiss']");
    await contains(".o-mail-NotificationItem", { text: "Turn on notifications", count: 0 });
    await contains(".o-mail-MessagingMenu-counter", { count: 0 });
});

test("rendering with chat push notification permissions denied", async () => {
    patchBrowserNotification("denied");
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu-counter", { count: 0 });
    await contains(".o-mail-NotificationItem", { count: 0 });
});

test("rendering with chat push notification permissions accepted", async () => {
    patchBrowserNotification("granted");
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu");
    await contains(".o-mail-MessagingMenu-counter", { count: 0 });
    await contains(".o-mail-NotificationItem", { count: 0 });
});

test("respond to notification prompt (denied)", async () => {
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

test("respond to notification prompt (granted)", async () => {
    patchBrowserNotification("default", "granted");
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o_notification:has(.o_notification_bar.bg-success)", {
        text: "Odoo will send notifications on this device!",
    });
});

test("no suggestion to enable chat push notifications in mobile app", async () => {
    patchBrowserNotification("default");
    // simulate Android Odoo App
    mockUserAgent("Chrome/0.0.0 Android (OdooMobile; Linux; Android 13; Odoo TestSuite)");
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu-counter", { count: 0 });
    await contains(".o-mail-NotificationItem", { count: 0 });
});

test("rendering with PWA installation request", async () => {
    patchWithCleanup(browser, {
        BeforeInstallPromptEvent: () => {},
    });
    patchWithCleanup(browser.localStorage, {
        getItem(key) {
            if (key === "pwaService.installationState") {
                asyncStep("getItem " + key);
                // in this test, installation has not yet proceeded
                return null;
            }
            return super.getItem(key);
        },
    });
    const pyEnv = await startServer();
    const [odoobot] = pyEnv["res.partner"].read(serverState.odoobotId);
    await start();
    mockService("pwa", {
        show() {
            asyncStep("show prompt");
        },
    });
    // This event must be triggered to initialize the pwa service properly
    // as if it was run by a browser supporting PWA (never triggered in a test otherwise).
    browser.dispatchEvent(new CustomEvent("beforeinstallprompt"));
    await waitForSteps(["getItem pwaService.installationState"]);
    await contains(".o-mail-MessagingMenu-counter");
    await contains(".o-mail-MessagingMenu-counter", { text: "1" });
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem");
    await contains(
        `.o-mail-NotificationItem img[data-src='${getOrigin()}/web/image/res.partner/${
            serverState.odoobotId
        }/avatar_128?unique=${deserializeDateTime(odoobot.write_date).ts}']`
    );
    await contains(".o-mail-NotificationItem-name", { text: "Install Odoo" });
    await contains(".o-mail-NotificationItem-text", {
        text: "Come here often? Install the app for quick and easy access!",
    });
    await click(".o-mail-NotificationItem a.btn-primary");
    await waitForSteps(["show prompt"]);
});

test("installation of the PWA request can be dismissed", async () => {
    patchWithCleanup(browser, {
        BeforeInstallPromptEvent: () => {},
    });
    patchWithCleanup(browser.localStorage, {
        getItem(key) {
            if (key === "pwaService.installationState") {
                asyncStep("getItem " + key);
                // in this test, installation has not yet proceeded
                return null;
            }
            return super.getItem(key);
        },
        setItem(key, value) {
            if (key === "pwaService.installationState") {
                asyncStep("installationState value:  " + value);
            }
            return super.setItem(key, value);
        },
    });
    await start();
    mockService("pwa", {
        show() {
            asyncStep("show prompt should not be triggered");
        },
    });
    // This event must be triggered to initialize the pwa service properly
    // as if it was run by a browser supporting PWA (never triggered in a test otherwise).
    browser.dispatchEvent(new CustomEvent("beforeinstallprompt"));
    await waitForSteps(["getItem pwaService.installationState"]);
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem .oi-close");
    await waitForSteps([
        "getItem pwaService.installationState",
        'installationState value:  {"/odoo":"dismissed"}',
    ]);
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { count: 0 });
});

test("rendering with PWA installation request (dismissed)", async () => {
    patchWithCleanup(browser, {
        BeforeInstallPromptEvent: () => {},
    });
    patchWithCleanup(browser.localStorage, {
        getItem(key) {
            if (key === "pwaService.installationState") {
                asyncStep("getItem " + key);
                // in this test, installation has been previously dismissed by the user
                return `{"/odoo":"dismissed"}`;
            }
            return super.getItem(key);
        },
    });
    await start();
    // This event must be triggered to initialize the pwa service properly
    // as if it was run by a browser supporting PWA (never triggered in a test otherwise).
    browser.dispatchEvent(new CustomEvent("beforeinstallprompt"));
    await waitForSteps(["getItem pwaService.installationState"]);
    await contains(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu-counter", { count: 0 });
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { count: 0 });
});

test("rendering with PWA installation request (already running as PWA)", async () => {
    patchWithCleanup(browser, {
        BeforeInstallPromptEvent: () => {},
    });
    patchWithCleanup(browser.localStorage, {
        getItem(key) {
            if (key === "pwaService.installationState") {
                asyncStep("getItem " + key);
                // in this test, we remove any value that could contain localStorage so the service would be allowed to prompt
                return null;
            }
            return super.getItem(key);
        },
    });
    await start();
    // The 'beforeinstallprompt' event is not triggered here, since the
    // browser wouldn't trigger it when the app is already launched
    await waitForSteps(["getItem pwaService.installationState"]);
    await contains(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu-counter", { count: 0 });
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { count: 0 });
});

test("Is closed after clicking on new message", async () => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "New Message" });
    await contains(".o-mail-MessagingMenu", { count: 0 });
});

test("grouped notifications by document", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "email",
            model: "res.partner",
            res_id: partnerId,
        },
        {
            message_type: "email",
            model: "res.partner",
            res_id: partnerId,
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
    await contains(".o-mail-Chatter", { count: 0 });
    await click(".o-mail-NotificationItem", {
        text: "Email Failure: Contact",
        contains: [".badge", { text: "2" }],
    });
    await contains(".o-mail-Chatter");
});

test("grouped notifications by document model", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([{}, {}]);
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "email",
            model: "res.partner",
            res_id: partnerId_1,
        },
        {
            message_type: "email",
            model: "res.partner",
            res_id: partnerId_2,
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
    mockService("action", {
        doAction(action) {
            asyncStep("do_action");
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
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", {
        text: "Email Failure: Contact",
        contains: [".badge", { text: "2" }],
    });
    await waitForSteps(["do_action"]);
});

test("multiple grouped notifications by document model, sorted by the most recent message of each group", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const companyId = pyEnv["res.company"].create({});
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "email",
            model: "res.partner",
            res_id: partnerId,
        },
        {
            message_type: "email",
            model: "res.company",
            res_id: companyId,
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
    await contains(":nth-child(1 of .o-mail-NotificationItem)", {
        text: "Email Failure: Companies",
    });
    await contains(":nth-child(2 of .o-mail-NotificationItem)", { text: "Email Failure: Contact" });
});

test("non-failure notifications are ignored", async () => {
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

test("mark unread channel as read", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 1, partner_id: serverState.partnerId }),
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
        ["partner_id", "=", serverState.partnerId],
    ]);
    pyEnv["discuss.channel.member"].write([currentMemberId], { seen_message_id: messagId_1 });
    onRpcBefore("/discuss/channel/mark_as_read", (args) => asyncStep("mark_as_read"));
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await triggerEvents(".o-mail-NotificationItem", ["mouseenter"]);
    await click(".o-mail-NotificationItem [title='Mark As Read']");
    await contains(".o-mail-NotificationItem.text-muted");
    await waitForSteps(["mark_as_read"]);
    await triggerEvents(".o-mail-NotificationItem", ["mouseenter"]);
    await contains(".o-mail-NotificationItem [title='Mark As Read']", { count: 0 });
    await contains(".o-mail-ChatWindow", { count: 0 });
});

test("mark failure as read", async () => {
    const pyEnv = await startServer();
    const messageId = pyEnv["mail.message"].create({ message_type: "email" });
    pyEnv["discuss.channel"].create({
        name: "General",
        message_ids: [messageId],
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, seen_message_id: messageId }),
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
            [".o-mail-NotificationItem-name", { text: "Email Failure: Discussion Channel" }],
            [
                ".o-mail-NotificationItem-text",
                { text: "An error occurred when sending an email on “General”" },
            ],
        ],
    });
    await click("[title='Mark As Read']", {
        parent: [".o-mail-NotificationItem", { text: "Email Failure: Discussion Channel" }],
    });
    await contains(".o-mail-NotificationItem", {
        count: 0,
        text: "Email Failure: Discussion Channel",
    });
    await contains("o-mail-NotificationItem", {
        count: 0,
        text: "An error occurred when sending an email on “General”",
    });
});

test("different discuss.channel are not grouped", async () => {
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
        },
        {
            message_type: "email",
            model: "discuss.channel",
            res_id: channelId_2,
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
    await click(":nth-child(1 of .o-mail-NotificationItem)", {
        text: "Email Failure: Discussion Channel",
    });
    await contains(".o-mail-ChatWindow");
});

test("mobile: active icon is highlighted", async () => {
    patchUiSize({ size: SIZES.SM });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-MessagingMenu-tab", { text: "Chats" });
    await contains(".o-mail-MessagingMenu-tab.o-active", { text: "Chats" });
});

test("open chat window from preview", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "test" });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
});

test("Counter is updated when receiving new message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Albert" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss();
    withUser(userId, () =>
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

test("basic rendering", async () => {
    patchWithCleanup(browser, {
        Notification: {
            ...browser.Notification,
            permission: "denied",
        },
    });
    await start();
    await contains(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    expect('.o_menu_systray .dropdown-toggle:has(i[aria-label="Messages"]):first').not.toHaveClass(
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
    await contains(".o-mail-MessagingMenu button.fw-bold", { text: "Notifications" });
    await contains(".o-mail-MessagingMenu button:not(.fw-bold)", { text: "Chats" });
    await contains(".o-mail-MessagingMenu button:not(.fw-bold)", { text: "Channels" });
    await contains("button", { text: "New Message" });
    await contains(".o-mail-MessagingMenu div.text-muted", { text: "No conversation yet..." });
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await contains(".o-dropdown--menu", { count: 0 });
    expect('.o_menu_systray .dropdown-toggle:has(i[aria-label="Messages"]):first').not.toHaveClass(
        "show"
    );
});

test("switch tab", async () => {
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await contains(".o-mail-MessagingMenu button.fw-bold", { text: "Notifications" });
    await contains(".o-mail-MessagingMenu button:not(.fw-bold)", { text: "Chats" });
    await contains(".o-mail-MessagingMenu button:not(.fw-bold)", { text: "Channels" });
    await click(".o-mail-MessagingMenu button", { text: "Chats" });
    await contains(".o-mail-MessagingMenu button:not(.fw-bold)", { text: "Notifications" });
    await contains(".o-mail-MessagingMenu button.fw-bold", { text: "Chats" });
    await contains(".o-mail-MessagingMenu button:not(.fw-bold)", { text: "Channels" });
    await click(".o-mail-MessagingMenu button", { text: "Channels" });
    await contains(".o-mail-MessagingMenu button:not(.fw-bold)", { text: "Notifications" });
    await contains(".o-mail-MessagingMenu button:not(.fw-bold)", { text: "Chats" });
    await contains(".o-mail-MessagingMenu button.fw-bold", { text: "Channels" });
    await click(".o-mail-MessagingMenu button", { text: "Notifications" });
    await contains(".o-mail-MessagingMenu button.fw-bold", { text: "Notifications" });
    await contains(".o-mail-MessagingMenu button:not(.fw-bold)", { text: "Chats" });
    await contains(".o-mail-MessagingMenu button:not(.fw-bold)", { text: "Channels" });
});

test("channel preview: basic rendering", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "<p>test<br/>hi</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await contains(".o-mail-NotificationItem");
    await contains(".o-mail-NotificationItem img");
    await contains(".o-mail-NotificationItem-name", { text: "General" });
    await contains(".o-mail-NotificationItem-text", { text: "Demo: test hi" });
});

test("chat preview should not display correspondent name in body", async () => {
    // DM chat with demo, the conversation is named "Demo" and body is simply message content
    // not prefix like "Demo:"
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", email: "demo@odoo.com" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "<p>test</p>",
                message_type: "comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-NotificationItem");
    await contains(".o-mail-NotificationItem img");
    await contains(".o-mail-NotificationItem-name", { text: "Demo" });
    await contains(".o-mail-NotificationItem-text", { text: "test" });
    expect(".o-mail-NotificationItem-text:only").toHaveText("test"); // exactly
});

test("filtered previews", async () => {
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
    await click(".o-mail-MessagingMenu button", { text: "Notifications" });
    await contains(".o-mail-NotificationItem", { count: 2 });
    await contains(".o-mail-NotificationItem", { text: "Mitchell Admin" });
    await click(".o-mail-MessagingMenu button", { text: "Channels" });
    await contains(".o-mail-NotificationItem", { text: "channel1" });
});

test("no code injection in message body preview", async () => {
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

test("no code injection in message body preview from sanitized message", async () => {
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

test("<br/> tags in message body preview are transformed in spaces", async () => {
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

test("Messaging menu notification body of chat should show author name once", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo User" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
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

test("Group chat should be displayed inside the chat section of the messaging menu", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ channel_type: "group" });
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await click(".o-mail-MessagingMenu button", { text: "Chats" });
    await contains(".o-mail-NotificationItem");
});

test("click on preview should mark as read and open the thread", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Frodo Baggins" });
    const messageId = pyEnv["mail.message"].create({
        model: "res.partner",
        body: "not empty",
        author_id: serverState.odoobotId,
        needaction: true,
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { text: "Frodo Baggins" });
    await contains(".o-mail-Chatter", { count: 0 });
    await click(".o-mail-NotificationItem", { text: "Frodo Baggins" });
    await contains(".o-mail-Chatter");
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { count: 0, text: "Frodo Baggins" });
});

test("preview should display last needaction message preview even if there is a more recent message that is not needaction in the thread", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Stranger" });
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "I am the oldest but needaction",
        model: "res.partner",
        needaction: true,
        res_id: partnerId,
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "I am more recent",
        model: "res.partner",
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem-text", {
        text: "Stranger: I am the oldest but needaction",
    });
});

test("Attachment-only message preview shows file type icon", async () => {
    const pyEnv = await startServer();
    const partners = pyEnv["res.partner"].create([
        { name: "Partner1" },
        { name: "Partner2" },
        { name: "Partner3" },
        { name: "Partner4" },
        { name: "Partner5" },
    ]);
    const channelIds = pyEnv["discuss.channel"].create([
        { name: "Channel1" },
        { name: "Channel2" },
        { name: "Channel3" },
        { name: "Channel4" },
        { name: "Channel5" },
    ]);
    const attachments = [
        {
            mimetype: "audio/mpeg",
            name: "voicemessage",
            icon: "fa-microphone",
            text: "Voice Message",
            voice_ids: [Command.create({ display_name: "voicemessage" })],
        },
        { mimetype: "video/mp4", name: "Video.mp4", icon: "fa-video-camera", text: "Video.mp4" },
        { mimetype: "application/pdf", name: "File.pdf", icon: "fa-file", text: "File.pdf" },
        { mimetype: "image/jpeg", name: "Image.jpeg", icon: "fa-picture-o", text: "Image.jpeg" },
        { mimetype: "audio/mpeg", name: "Audio.mp3", icon: "fa-headphones", text: "Audio.mp3" },
    ];

    pyEnv["mail.message"].create(
        attachments.map((attachment, i) => ({
            attachment_ids: [
                Command.create({
                    mimetype: attachment.mimetype,
                    name: attachment.name,
                    res_id: channelIds[i],
                    res_model: "discuss.channel",
                    voice_ids: attachment.voice_ids || [],
                }),
            ],
            author_id: partners[i],
            body: "",
            model: "discuss.channel",
            res_id: channelIds[i],
        }))
    );
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem:eq(0) i.fa-microphone");
    await contains(".o-mail-NotificationItem:eq(0)", { text: "Partner1: Voice Message" });
    await contains(".o-mail-NotificationItem:eq(1) i.fa-video-camera");
    await contains(".o-mail-NotificationItem:eq(1)", { text: "Partner2: Video.mp4" });
    await contains(".o-mail-NotificationItem:eq(2) i.fa-file");
    await contains(".o-mail-NotificationItem:eq(2)", { text: "Partner3: File.pdf" });
    await contains(".o-mail-NotificationItem:eq(3) i.fa-picture-o");
    await contains(".o-mail-NotificationItem:eq(3)", { text: "Partner4: Image.jpeg" });
    await contains(".o-mail-NotificationItem:eq(4) i.fa-headphones");
    await contains(".o-mail-NotificationItem:eq(4)", { text: "Partner5: Audio.mp3" });
});

test("Attachment-only message preview shows file names (2 files)", async () => {
    const pyEnv = await startServer();
    const partner1 = pyEnv["res.partner"].create({ name: "Partner" });
    const channel1 = pyEnv["discuss.channel"].create({ name: "test" });
    pyEnv["mail.message"].create({
        attachment_ids: [
            Command.create({
                mimetype: "application/pdf",
                name: "File.pdf",
                res_id: channel1,
                res_model: "discuss.channel",
            }),
            Command.create({
                mimetype: "image/jpeg",
                name: "Image.jpeg",
                res_id: channel1,
                res_model: "discuss.channel",
            }),
        ],
        author_id: partner1,
        body: "",
        model: "discuss.channel",
        res_id: channel1,
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem-text", {
        text: "Partner: File.pdf and Image.jpeg",
    });
});

test("Attachment-only message preview shows file names (3 files)", async () => {
    const pyEnv = await startServer();
    const partner1 = pyEnv["res.partner"].create({ name: "Partner" });
    const channel1 = pyEnv["discuss.channel"].create({ name: "test" });
    pyEnv["mail.message"].create({
        attachment_ids: [
            Command.create({
                mimetype: "application/pdf",
                name: "File.pdf",
                res_id: channel1,
                res_model: "discuss.channel",
            }),
            Command.create({
                mimetype: "image/jpeg",
                name: "Image.jpeg",
                res_id: channel1,
                res_model: "discuss.channel",
            }),
            Command.create({
                mimetype: "video/mp4",
                name: "Video.mp4",
                res_id: channel1,
                res_model: "discuss.channel",
            }),
        ],
        author_id: partner1,
        body: "",
        model: "discuss.channel",
        res_id: channel1,
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem-text", {
        text: "Partner: File.pdf and 2 other attachments",
    });
});

test("single preview for channel if it has unread and needaction messages", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner1" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Test",
        channel_member_ids: [
            Command.create({ message_unread_counter: 2, partner_id: serverState.partnerId }),
        ],
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "Message with needaction",
        model: "discuss.channel",
        needaction: true,
        res_id: channelId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
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

test("chat should show unread counter on receiving new messages", async () => {
    // unread and needaction are conceptually the same in chat
    // however message_needaction_counter is not updated
    // so special care for chat to simulate needaction with unread
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner1" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ message_unread_counter: 0, partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { text: "Partner1" });
    await contains(".o-mail-NotificationItem .badge", { count: 0, text: "1" });
    // simulate receiving a new message
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "Interesting idea",
                message_type: "comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-NotificationItem .badge", { text: "1" });
});

test("preview for channel shows deleted message preview when this is most recent", async () => {
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
        update_data: {
            body: "",
            attachment_ids: [],
        },
    });
    await contains(".o-mail-NotificationItem-text", {
        text: "Partner1: This message has been removed",
    });
});

test("failure notifications are shown before channel preview", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner1" });
    const failedMessageId = pyEnv["mail.message"].create({ message_type: "email" });
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
        ["partner_id", "=", serverState.partnerId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], { seen_message_id: messageId });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem-text", {
        text: "An error occurred when sending an email on “Test”",
        before: [".o-mail-NotificationItem-text", { text: "Partner1: message" }],
    });
});

test("messaging menu should show new needaction messages from chatter", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Frodo Baggins" });
    await start();
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
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    const [partner] = pyEnv["res.partner"].read(serverState.partnerId);
    pyEnv["bus.bus"]._sendone(
        partner,
        "mail.message/inbox",
        new mailDataHelpers.Store(
            pyEnv["mail.message"].browse(messageId),
            makeKwArgs({ for_current_user: true, add_followers: true })
        ).get_result()
    );
    await contains(".o-mail-NotificationItem-text", { text: "Frodo Baggins: @Mitchel Admin" });
});

test("can open messaging menu even if messaging is not initialized", async () => {
    patchBrowserNotification("default");
    await startServer();
    const def = new Deferred();
    listenStoreFetch("init_messaging", {
        async onRpc() {
            asyncStep("before init_messaging");
            await def;
        },
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { text: "Turn on notifications" });
    await waitForSteps(["before init_messaging"]);
    def.resolve();
    await waitStoreFetch("init_messaging");
});

test("can open messaging menu even if channels are not fetched", async () => {
    patchBrowserNotification("denied");
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    const def = new Deferred();
    listenStoreFetch("channels_as_member", {
        async onRpc() {
            asyncStep("before channels_as_member");
            await def;
        },
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-DiscussSystray", { text: "Loading…" });
    await waitForSteps(["before channels_as_member"]);
    def.resolve();
    await waitStoreFetch("channels_as_member");
    await contains(".o-mail-NotificationItem", { text: "General" });
});

test("Latest needaction is shown in thread preview", async () => {
    const pyEnv = await startServer();
    for (let i = 1; i <= 2; i++) {
        const messageId = pyEnv["mail.message"].create({
            body: `message ${i}`,
            message_type: "comment",
            model: "res.partner",
            needaction: true,
            res_id: serverState.partnerId,
        });
        pyEnv["mail.notification"].create({
            mail_message_id: messageId,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        });
    }
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { text: serverState.partnerName });
    await contains(".o-mail-NotificationItem", { text: "You: message 2" });
});

test("Can quick search when more than 20 items", async () => {
    const pyEnv = await startServer();
    for (let id = 1; id <= 20; id++) {
        pyEnv["discuss.channel"].create({ name: `channel${id}` });
    }
    pyEnv["discuss.channel"].create([
        { channel_type: "chat" },
        { name: "Cool channel" },
        { name: "Nice channel" },
    ]);
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await contains(".o-mail-NotificationItem", { count: 23 });
    await contains(".o-mail-NotificationItem", { text: "Mitchell Admin" });
    await contains(".o-mail-NotificationItem", { text: "Cool channel" });
    await contains(".o-mail-NotificationItem", { text: "Nice channel" });
    await click("[title='Quick search']");
    await insertText(".o-mail-MessagingMenu input", "nice");
    await contains(".o-mail-NotificationItem", { count: 1 });
    await contains(".o-mail-NotificationItem", { text: "Nice channel" });
    await click("[title='Close search']");
    await click("[title='Quick search']");
    await insertText(".o-mail-MessagingMenu input", "admin");
    await contains(".o-mail-NotificationItem", { count: 1 });
    await contains(".o-mail-NotificationItem", { text: "Mitchell Admin" });
    await insertText(".o-mail-MessagingMenu input", "no threads", { replace: true });
    await contains(".o-mail-MessagingMenu div.text-muted", { text: "No thread found." });
    expect(".o-mail-MessagingMenu-list").toHaveText("No thread found."); // list should contain only this text
});

test("keyboard navigation", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        { channel_type: "chat" },
        { name: "Channel-1" },
        { name: "Channel-2" },
    ]);
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await contains(".o-mail-NotificationItem", { count: 3 }); // Expected order: Channel-2, Channel-1, Mitchell Admin
    triggerHotkey("ArrowDown");
    await contains(".o-mail-NotificationItem:eq(0).o-active", { name: "Channel-2" });
    triggerHotkey("ArrowDown");
    await contains(".o-mail-NotificationItem:eq(1).o-active", { name: "Channel-1" });
    triggerHotkey("ArrowUp");
    await contains(".o-mail-NotificationItem:eq(0).o-active", { name: "Channel-2" });
    triggerHotkey("ArrowUp");
    await contains(".o-mail-NotificationItem:last.o-active", { name: "Mitchell Admin" });
    triggerHotkey("Enter");
    await contains(".o-mail-ChatWindow", { text: "Mitchell Admin" });
});

test("keyboard navigation with quick search", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        { channel_type: "chat" },
        { name: "Channel-1" },
        { name: "Channel-2" },
    ]);
    for (let id = 1; id <= 20; id++) {
        // need at least 20 channels for enabling quick search
        pyEnv["discuss.channel"].create({ name: `other-${id}` });
    }
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await contains(".o-mail-NotificationItem", { count: 23 });
    triggerHotkey("ArrowDown");
    await contains(".o-mail-NotificationItem:eq(0).o-active");
    await click("[title='Quick search']");
    await insertText(".o-mail-MessagingMenu input", "C");
    await contains(".o-mail-NotificationItem", { count: 3 });
    await contains(".o-mail-NotificationItem:eq(0).o-active");
    triggerHotkey("ArrowDown");
    await contains(".o-mail-NotificationItem:eq(1).o-active");
    await insertText(".o-mail-MessagingMenu input", "ha");
    await contains(".o-mail-NotificationItem", { count: 2 });
    await contains(".o-mail-NotificationItem:eq(0).o-active");
    triggerHotkey("ArrowDown");
    await contains(".o-mail-NotificationItem:eq(1).o-active");
    await insertText(".o-mail-MessagingMenu input", "", { replace: true });
    await contains(".o-mail-NotificationItem", { count: 23 });
    await contains(".o-mail-NotificationItem.o-active", { count: 0 });
});

test("failure is removed from messaging menu when message is deleted", async () => {
    const pyEnv = await startServer();
    const recipientId = pyEnv["res.partner"].create({ name: "James" });
    const messageId = pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "res.partner",
        partner_ids: [recipientId],
        res_id: serverState.partnerId,
    });
    pyEnv["mail.notification"].create({
        failure_type: "mail_email_invalid",
        mail_message_id: messageId,
        notification_status: "exception",
        notification_type: "email",
        res_partner_id: serverState.partnerId,
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", {
        contains: [
            [".o-mail-NotificationItem-name", { text: "Email Failure: Contact" }],
            [
                ".o-mail-NotificationItem-text",
                { text: "An error occurred when sending an email on “Mitchell Admin”" },
            ],
        ],
    });
    pyEnv["mail.message"].unlink([messageId]);
    await contains(".o-mail-NotificationItem", { count: 0 });
});
