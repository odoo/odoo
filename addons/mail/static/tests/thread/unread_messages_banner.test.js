import {
    click,
    contains,
    defineMailModels,
    focus,
    openDiscuss,
    patchUiSize,
    scroll,
    SIZES,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { mockUserAgent, tick } from "@odoo/hoot-mock";
import {
    asyncStep,
    Command,
    onRpc,
    serverState,
    waitForSteps,
    withUser,
} from "@web/../tests/web_test_helpers";
import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineMailModels();

test("show unread messages banner when there are unread messages", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const bobPartnerId = pyEnv["res.partner"].create({ name: "Bob" });
    for (let i = 0; i < 30; ++i) {
        pyEnv["mail.message"].create({
            author_id: bobPartnerId,
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 30 });
    await contains("span", { text: "30 new messagesMark as Read" });
});

test("mark thread as read from unread messages banner", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const bobPartnerId = pyEnv["res.partner"].create({ name: "Bob" });
    for (let i = 0; i < 30; ++i) {
        pyEnv["mail.message"].create({
            author_id: bobPartnerId,
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 30 });
    await click("span", {
        text: "Mark as Read",
        parent: ["span", { text: "30 new messagesMark as Read" }],
    });
});

test("reset new message separator from unread messages banner", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const bobPartnerId = pyEnv["res.partner"].create({ name: "Bob" });
    for (let i = 0; i < 30; ++i) {
        pyEnv["mail.message"].create({
            author_id: bobPartnerId,
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    pyEnv["discuss.channel.member"].search([
        ["partner_id", "=", serverState.partnerId],
        ["channel_id", "=", channelId],
    ]);
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-Message", {
        text: "message 0",
    });
    await click("span", {
        text: "Mark as Read",
        parent: ["span", { text: "30 new messagesMark as Read" }],
    });
    await contains("span", { text: "30 new messagesMark as Read", count: 0 });
});

test("remove banner when scrolling to bottom", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const bobPartnerId = pyEnv["res.partner"].create({ name: "Bob" });
    for (let i = 0; i < 50; ++i) {
        pyEnv["mail.message"].create({
            author_id: bobPartnerId,
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    onRpc("/discuss/channel/mark_as_read", () => asyncStep("mark_as_read"));
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-Composer.o-focused");
    await focus(".o-mail-Thread");
    await contains(".o-mail-Thread-banner", { text: "50 new messages" });
    await tick(); // wait for the scroll to first unread to complete
    await scroll(".o-mail-Thread", "bottom");
    await contains(".o-mail-Message", { count: 50 });
    // Banner is still present as there are more messages to load so we did not
    // reach the actual bottom.
    await contains(".o-mail-Thread-banner", { text: "50 new messages" });
    await scroll(".o-mail-Thread", "bottom");
    await contains(".o-mail-Thread-banner", { text: "50 new messages", count: 0 });
    await waitForSteps(["mark_as_read"]);
});

test("remove banner when opening thread at the bottom", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const bobPartnerId = pyEnv["res.partner"].create({ name: "Bob" });
    const messageId = pyEnv["mail.message"].create({
        author_id: bobPartnerId,
        body: `Hello World`,
        model: "discuss.channel",
        res_id: channelId,
    });
    const [selfMemberId] = pyEnv["discuss.channel.member"].search([
        ["partner_id", "=", serverState.partnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.member"].write([selfMemberId], { new_message_separator: messageId + 1 });
    await start();
    await openDiscuss(channelId);
    await click("[title='Expand']", { parent: [".o-mail-Message", { text: "Hello World" }] });
    await click(".o-dropdown-item:contains('Mark as Unread')");
    await contains(".o-mail-Thread-banner", { text: "1 new message" });
    await click(".o-mail-DiscussSidebar-item", { text: "Inbox" });
    await contains(".o-mail-Discuss-threadName[title='Inbox']");
    await click(".o-mail-DiscussSidebarChannel", { text: "general" });
    await contains(".o-mail-Discuss-threadName[title='general']");
    await contains(".o-mail-Thread-banner", { text: "1 new message", count: 0 });
});

test("keep banner after mark as unread when scrolling to bottom", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const bobPartnerId = pyEnv["res.partner"].create({ name: "Bob" });
    for (let i = 0; i < 30; ++i) {
        pyEnv["mail.message"].create({
            author_id: bobPartnerId,
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await click("[title='Expand']", { parent: [".o-mail-Message", { text: "message 29" }] });
    await click(".o-dropdown-item:contains('Mark as Unread')");
    await scroll(".o-mail-Thread", "bottom");
    await contains(".o-mail-Thread-banner", { text: "30 new messages" });
});

test("sidebar and banner counters display same value", async () => {
    const pyEnv = await startServer();
    const bobPartnerId = pyEnv["res.partner"].create({ name: "Bob" });
    const bobUserId = pyEnv["res.users"].create({ name: "Bob", partner_id: bobPartnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: bobPartnerId }),
        ],
    });
    for (let i = 0; i < 30; ++i) {
        pyEnv["mail.message"].create({
            author_id: bobPartnerId,
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebar-badge", {
        text: "30",
        parent: [".o-mail-DiscussSidebarChannel", { text: "Bob" }],
    });
    await click(".o-mail-DiscussSidebarChannel", { text: "Bob" });
    await contains(".o-mail-Thread-banner", { text: "30 new messages" });
    await contains(".o-mail-DiscussSidebar-badge", { text: "30" });
    await withUser(bobUserId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "Hello!",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Thread-banner", { text: "31 new messages" });
    await contains(".o-mail-DiscussSidebar-badge", {
        text: "31",
        parent: [".o-mail-DiscussSidebarChannel", { text: "Bob" }],
    });
});

test("mobile: mark as read when opening chat", async () => {
    mockUserAgent("android");
    const pyEnv = await startServer();
    const bobPartnerId = pyEnv["res.partner"].create({ name: "bob" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: bobPartnerId }),
        ],
    });
    pyEnv["mail.message"].create({
        body: "Hello!",
        model: "discuss.channel",
        author_id: bobPartnerId,
        res_id: channelId,
    });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss();
    await contains("button.o-active", { text: "Notifications" });
    await click("button:has(.badge:contains('1'))", { text: "Chats" });
    await contains(".o-mail-NotificationItem:has(.badge:contains(1))", { text: "bob" });
    await click(".o-mail-NotificationItem", { text: "bob" });
    await contains(".o-mail-Message");
    await contains(".o-mail-Thread.o-focused");
    await contains(".o-mail-Composer:not(.o-focused)");
    await click(".o-mail-ChatWindow-command[title*='Close Chat Window']");
    await contains(".o-mail-NotificationItem:has(.badge:contains(1))", { text: "bob", count: 0 });
});
