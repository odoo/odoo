import {
    SIZES,
    click,
    contains,
    defineMailModels,
    isInViewportOf,
    openDiscuss,
    patchUiSize,
    scroll,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";
import {
    asyncStep,
    Command,
    getService,
    onRpc,
    serverState,
    waitForSteps,
    withUser,
} from "@web/../tests/web_test_helpers";
import { rpc } from "@web/core/network/rpc";
import { waitNotifications } from "@bus/../tests/bus_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("show unread messages banner when there are unread messages", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    for (let i = 0; i < 30; ++i) {
        pyEnv["mail.message"].create({
            author_id: serverState.partnerId,
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", {
        text: "message 0",
    });
    await contains("span", { text: "30 new messagesMark as Read" });
});

test("mark thread as read from unread messages banner", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    for (let i = 0; i < 30; ++i) {
        pyEnv["mail.message"].create({
            author_id: serverState.partnerId,
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", {
        text: "message 0",
    });
    await click("span", {
        text: "Mark as Read",
        parent: ["span", { text: "30 new messagesMark as Read" }],
    });
});

test("reset new message separator from unread messages banner", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    let lastMessageId;
    for (let i = 0; i < 30; ++i) {
        lastMessageId = pyEnv["mail.message"].create({
            author_id: serverState.partnerId,
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const [selfMember] = pyEnv["discuss.channel.member"].search([
        ["partner_id", "=", serverState.partnerId],
        ["channel_id", "=", channelId],
    ]);
    const env = await start();
    // Wait for the mark as read notification to update the local state.
    const markAsReadNotification = [
        env,
        "mail.record/insert",
        {
            "discuss.channel.member": [
                {
                    id: selfMember,
                    thread: { id: channelId, model: "discuss.channel" },
                    persona: { id: serverState.partnerId, type: "partner" },
                    seen_message_id: lastMessageId,
                },
            ],
            "res.partner": [{ id: serverState.partnerId, name: "Mitchell Admin" }],
        },
    ];
    await Promise.all([openDiscuss(channelId), waitNotifications(markAsReadNotification)]);
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", {
        text: "message 0",
    });
    await click("span", {
        text: "Mark as Read",
        parent: ["span", { text: "30 new messagesMark as Read" }],
    });
    await contains("span", { text: "30 new messagesMark as Read", count: 0 });
});

test.skip("scroll to unread notification", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const bobPartnerId = pyEnv["res.partner"].create({ name: "Bob" });
    const bobUserId = pyEnv["res.users"].create({ name: "Bob", partner_id: bobPartnerId });
    let lastMessageId;
    for (let i = 0; i < 60; ++i) {
        lastMessageId = pyEnv["mail.message"].create({
            author_id: serverState.partnerId,
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["partner_id", "=", serverState.partnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], { new_message_separator: lastMessageId + 1 });
    await start();
    await withUser(bobUserId, () => {
        getService("orm").call("discuss.channel", "add_members", [[channelId]], {
            partner_ids: [bobPartnerId],
        });
    });
    await openDiscuss(channelId);
    await contains(".o-mail-Thread-newMessage ~ .o-mail-NotificationMessage", {
        text: "Bob joined the channel",
    });
    await tick(); // wait for the scroll to first unread to complete
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await scroll(".o-mail-Thread", 0);
    await click("span", {
        text: "1 new message",
        parent: ["span", { text: "1 new messageMark as Read" }],
    });
    await isInViewportOf(
        ".o-mail-NotificationMessage:contains(Bob joined the channel)",
        ".o-mail-Thread"
    );
});

test("remove banner when scrolling to bottom", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    for (let i = 0; i < 50; ++i) {
        pyEnv["mail.message"].create({
            author_id: serverState.partnerId,
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    onRpc("/discuss/channel/mark_as_read", () => asyncStep("mark_as_read"));
    await start();
    await openDiscuss(channelId);
    await waitForSteps(["mark_as_read"]);
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-Thread-banner", { text: "50 new messages" });
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", { text: "message 0" });
    await tick(); // wait for the scroll to first unread to complete
    await scroll(".o-mail-Thread", "bottom");
    await contains(".o-mail-Message", { count: 50 });
    // Banner is still present as there are more messages to load so we did not
    // reach the actual bottom.
    await contains(".o-mail-Thread-banner", { text: "50 new messages" });
    await scroll(".o-mail-Thread", "bottom");
    await contains(".o-mail-Thread-banner", { text: "50 new messages", count: 0 });
});

test("remove banner when opening thread at the bottom", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messageId = pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
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
    await click(".o-mail-Message-moreMenu [title='Mark as Unread']");
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
    for (let i = 0; i < 30; ++i) {
        pyEnv["mail.message"].create({
            author_id: serverState.partnerId,
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await click("[title='Expand']", { parent: [".o-mail-Message", { text: "message 29" }] });
    await click(".o-mail-Message-moreMenu [title='Mark as Unread']");
    await scroll(".o-mail-Thread", "bottom");
    await contains(".o-mail-Thread-banner", { text: "30 new messages" });
});

test("sidebar and banner counters display same value", async () => {
    const pyEnv = await startServer();
    const bobPatnerId = pyEnv["res.partner"].create({ name: "Bob" });
    const bobUserId = pyEnv["res.users"].create({ name: "Bob", partner_id: bobPatnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: bobPatnerId }),
        ],
    });
    for (let i = 0; i < 30; ++i) {
        pyEnv["mail.message"].create({
            author_id: serverState.partnerId,
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
    await contains(".o-mail-DiscussSidebar-badge", { text: "30", count: 0 });
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
    await contains("button.active", { text: "Inbox" });
    await click("button", { text: "Chat" });
    await contains(".o-mail-NotificationItem:has(.badge:contains(1))", { text: "bob" });
    await click(".o-mail-NotificationItem", { text: "bob" });
    await click(".o-mail-ChatWindow-command[title*='Close Chat Window']");
    await contains(".o-mail-NotificationItem:has(.badge:contains(1))", { text: "bob", count: 0 });
});
