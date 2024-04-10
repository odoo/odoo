import { describe, expect, test } from "@odoo/hoot";

/** @type {ReturnType<import("@mail/utils/common/misc").rpcWithEnv>} */
let rpc;

import { browser } from "@web/core/browser/browser";
import { getOrigin } from "@web/core/utils/urls";
import {
    SIZES,
    assertSteps,
    click,
    contains,
    defineMailModels,
    insertText,
    onRpcBefore,
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
import {
    Command,
    mockService,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { Deferred } from "@odoo/hoot-mock";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { withUser } from "@web/../tests/_framework/mock_server/mock_server";
import { getMockEnv } from "@web/../tests/_framework/env_test_helpers";
import { actionService } from "@web/webclient/actions/action_service";
import { rpcWithEnv } from "@mail/utils/common/misc";

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
    await contains("button.fw-bold", { text: "All" });
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

test("rendering with OdooBot has a request (default)", async () => {
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
    await contains(".o-mail-NotificationItem", { text: "OdooBot has a request" });
});

test("rendering without OdooBot has a request (denied)", async () => {
    patchBrowserNotification("denied");
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu-counter", { count: 0 });
    await contains(".o-mail-NotificationItem", { count: 0 });
});

test("rendering without OdooBot has a request (accepted)", async () => {
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

test("no 'OdooBot has a request' in mobile app", async () => {
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

test("rendering with PWA installation request", async () => {
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
    const [odoobot] = pyEnv["res.partner"].read(serverState.odoobotId);
    const env = await start();
    patchWithCleanup(env.services.installPrompt, {
        show() {
            step("show prompt");
        },
    });
    // This event must be triggered to initialize the installPrompt service properly
    // as if it was run by a browser supporting PWA (never triggered in a test otherwise).
    browser.dispatchEvent(new CustomEvent("beforeinstallprompt"));
    await assertSteps(["getItem pwa.installationState"]);
    await contains(".o-mail-MessagingMenu-counter");
    await contains(".o-mail-MessagingMenu-counter", { text: "1" });
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem");
    await contains(
        `.o-mail-NotificationItem img[data-src='${getOrigin()}/web/image/res.partner/${
            serverState.odoobotId
        }/avatar_128?unique=${deserializeDateTime(odoobot.write_date).ts}']`
    );
    await contains(".o-mail-NotificationItem-name", { text: "OdooBot has a suggestion" });
    await contains(".o-mail-NotificationItem-text", {
        text: "Come here often? Install Odoo on your device!",
    });
    await click(".o-mail-NotificationItem a.btn-primary");
    await assertSteps(["show prompt"]);
});

test("installation of the PWA request can be dismissed", async () => {
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
    const env = await start();
    patchWithCleanup(env.services.installPrompt, {
        show() {
            step("show prompt should not be triggered");
        },
    });
    // This event must be triggered to initialize the installPrompt service properly
    // as if it was run by a browser supporting PWA (never triggered in a test otherwise).
    browser.dispatchEvent(new CustomEvent("beforeinstallprompt"));
    await assertSteps(["getItem pwa.installationState"]);
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem .fa-close");
    await assertSteps(["installationState value:  dismissed"]);
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { count: 0 });
});

test("rendering with PWA installation request (dismissed)", async () => {
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

test("rendering with PWA installation request (already running as PWA)", async () => {
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

test("Is closed after clicking on new message", async () => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "New Message" });
    await contains(".o-mail-MessagingMenu", { count: 0 });
});

test("no 'New Message' button when discuss is open", async () => {
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
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click(".o-mail-NotificationItem", {
        text: "Contact",
        contains: [".badge", { text: "2" }],
    });
    await contains(".o-mail-ChatWindow");
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
    mockService("action", () => ({
        ...actionService.start(getMockEnv()),
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
    }));
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", {
        text: "Contact",
        contains: [".badge", { text: "2" }],
    });
    await assertSteps(["do_action"]);
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
    await contains(":nth-child(1 of .o-mail-NotificationItem)", { text: "Companies" });
    await contains(":nth-child(2 of .o-mail-NotificationItem)", { text: "Contact" });
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
    onRpcBefore("/discuss/channel/set_last_seen_message", (args) => step("set_last_seen_message"));
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

test("mark failure as read", async () => {
    const pyEnv = await startServer();
    const messageId = pyEnv["mail.message"].create({ message_type: "email" });
    pyEnv["discuss.channel"].create({
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
            [".o-mail-NotificationItem-name", { text: "Discussion Channel" }],
            [".o-mail-NotificationItem-text", { text: "An error occurred when sending an email" }],
        ],
    });
    await click("[title='Mark As Read']", {
        parent: [".o-mail-NotificationItem", { text: "Discussion Channel" }],
    });
    await contains(".o-mail-NotificationItem", { count: 0, text: "Discussion Channel" });
    await contains("o-mail-NotificationItem", {
        count: 0,
        text: "An error occurred when sending an email",
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
    await click(":nth-child(1 of .o-mail-NotificationItem)", { text: "Discussion Channel" });
    await contains(".o-mail-ChatWindow");
});

test("mobile: active icon is highlighted", async () => {
    patchUiSize({ size: SIZES.SM });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-MessagingMenu-tab", { text: "Chat" });
    await contains(".o-mail-MessagingMenu-tab.fw-bolder", { text: "Chat" });
});

test("open chat window from preview", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "test" });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
});

test('"Start a conversation" in mobile shows channel selector (+ click away)', async () => {
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
test('"New Channel" in mobile shows channel selector (+ click away)', async () => {
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

test("'Start a conversation' button should open a thread in mobile", async () => {
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
    const env = await start();
    rpc = rpcWithEnv(env);
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

test("switch tab", async () => {
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

test("channel preview: basic rendering", async () => {
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
    await click(".o-mail-MessagingMenu button", { text: "All" });
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
        needaction_partner_ids: [serverState.partnerId],
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
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click(".o-mail-NotificationItem", { text: "Frodo Baggins" });
    await contains(".o-mail-ChatWindow");
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { count: 0, text: "Frodo Baggins" });
});

test("click on expand from chat window should close the chat window and open the form view", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Frodo Baggins" });
    const messageId = pyEnv["mail.message"].create({
        model: "res.partner",
        body: "not empty",
        author_id: serverState.odoobotId,
        needaction: true,
        needaction_partner_ids: [serverState.partnerId],
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    mockService("action", () => ({
        ...actionService.start(getMockEnv()),
        doAction(action) {
            step("do_action");
            expect(action.res_id).toBe(partnerId);
            expect(action.res_model).toBe("res.partner");
        },
    }));
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Frodo Baggins" });
    await click(".o-mail-ChatWindow-command i.fa-expand");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await assertSteps(["do_action"], "should have done an action to open the form view");
});

test("preview should display last needaction message preview even if there is a more recent message that is not needaction in the thread", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Stranger" });
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "I am the oldest but needaction",
        model: "res.partner",
        needaction: true,
        needaction_partner_ids: [serverState.partnerId],
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
        needaction_partner_ids: [serverState.partnerId],
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
    const channel = pyEnv["discuss.channel"].search_read([["id", "=", channelId]])[0];
    pyEnv["bus.bus"]._sendone(channel, "discuss.channel/new_message", {
        id: channelId,
        message: {
            author: await pyEnv["res.partner"].mail_partner_format([partnerId])[partnerId],
            body: "Interesting idea",
            id: 126,
            model: "discuss.channel",
            res_id: channelId,
        },
    });
    await contains(".o-mail-NotificationItem .badge", { text: "1" });
});

test("preview for channel should show latest non-deleted message", async () => {
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
    const env = await start();
    rpc = rpcWithEnv(env);
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
        text: "An error occurred when sending an email",
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
        needaction_partner_ids: [serverState.partnerId],
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    const [formattedMessage] = pyEnv["mail.message"]._message_format(messageId);
    const [partner] = pyEnv["res.partner"].read(serverState.partnerId);
    pyEnv["bus.bus"]._sendone(partner, "mail.message/inbox", formattedMessage);
    await contains(".o-mail-NotificationItem-text", { text: "Frodo Baggins: @Mitchel Admin" });
});

test("can open messaging menu even if messaging is not initialized", async () => {
    patchBrowserNotification("default");
    await startServer();
    const def = new Deferred();
    onRpcBefore("/mail/action", async (args) => {
        if (args.init_messaging) {
            await def;
        }
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { text: "OdooBot has a request" });
});

test("can open messaging menu even if channels are not fetched", async () => {
    patchBrowserNotification("denied");
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    const def = new Deferred();
    onRpcBefore("/mail/action", async (args) => {
        if (args.channels_as_member) {
            await def;
        }
    });
    onRpcBefore("/mail/data", async (args) => {
        if (args.channels_as_member) {
            await def;
        }
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-DiscussSystray", { text: "No conversation yet..." });
    def.resolve();
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
            needaction_partner_ids: [serverState.partnerId],
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
