import {
    SIZES,
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    patchBrowserNotification,
    patchUiSize,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { disableAnimations, mockTouch } from "@odoo/hoot-mock";
import {
    Command,
    contains as webContains,
    getService,
    serverState,
    swipeLeft,
    swipeRight,
    withUser,
} from "@web/../tests/web_test_helpers";

import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineMailModels();

test("can make DM chat in mobile", async () => {
    patchUiSize({ size: SIZES.SM });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Gandalf" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    await start();
    await openDiscuss();
    await contains("button.active", { text: "Notifications" });
    await click("button", { text: "Chats" });
    await click(".o-mail-DiscussSearch-inputContainer");
    await contains(".o_command_name", { count: 5 });
    await insertText("input[placeholder='Search a conversation']", "Gandalf");
    await contains(".o_command_name", { count: 3 });
    await click(".o_command_name", { text: "Gandalf" });
    await contains(".o-mail-ChatWindow", { text: "Gandalf" });
});

test("can search channel in mobile", async () => {
    patchUiSize({ size: SIZES.SM });
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "Gryffindors" });
    await start();
    await openDiscuss();
    await contains("button.active", { text: "Notifications" });
    await click("button", { text: "Channels" });
    await click(".o-mail-DiscussSearch-inputContainer");
    await contains(".o_command_name", { count: 5 });
    await insertText("input[placeholder='Search a conversation']", "Gryff");
    await contains(".o_command_name", { count: 3 });
    await click(".o_command_name", { text: "Gryffindors" });
    await contains(".o-mail-ChatWindow div[title='Gryffindors']");
});

test("can make new channel in mobile", async () => {
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss();
    await contains("button.active", { text: "Notifications" });
    await click("button", { text: "Channels" });
    await click(".o-mail-DiscussSearch-inputContainer");
    await insertText("input[placeholder='Search a conversation']", "slytherins");
    await click("a", { text: "Create Channel" });
    await contains(".o-mail-ChatWindow", { text: "slytherins" });
});

test("new message opens the @ command palette", async () => {
    await start();
    await click(".o_menu_systray .dropdown-toggle i[aria-label='Messages']");
    await click(".o-mail-MessagingMenu button", { text: "New Message" });
    await contains(".o_command_palette_search .o_namespace", { text: "@" });
    await contains(".o_command_palette input[placeholder='Search a conversation']");
});

test("channel preview show deleted messages", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "<p>before last</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "<p></p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { text: "before last" });
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await contains(".o-mail-NotificationItem-text", {
        text: "Demo: This message has been removed",
    });
});

test("deleted message should not show parent message reference and mentions", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const messageId = pyEnv["mail.message"].create({
        body: "<p>Parent Message</p>",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    pyEnv["mail.message"].create({
        body: "<p>reply message</p>",
        message_type: "comment",
        model: "discuss.channel",
        parent_id: messageId,
        partner_ids: [serverState.partnerId],
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-MessageInReply", { text: "Parent Message" });
    await webContains(
        ".o-mail-Message:has(.o-mail-Message-bubble.o-orange):contains('reply message')"
    ).hover();
    await webContains(
        ".o-mail-Message:has(.o-mail-Message-bubble.o-orange):contains('reply message') [title='Expand']"
    ).click();
    await click(".o-mail-Message-moreMenu .o-dropdown-item:contains(Delete)");
    await click(".o_dialog button:contains(Delete)");
    await contains(".o-mail-Message:not(:has(.o-mail-Message-bubble.o-orange))", {
        text: "This message has been removed",
    });
    await contains(".o-mail-MessageInReply", { count: 0 });
});

test("channel preview ignores transient message", async () => {
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
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/who");
    await click(".o-mail-Composer button[title='Send']:enabled");
    await contains(".o_mail_notification", { text: "You are alone in this channel." });
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await contains(".o-mail-NotificationItem-text", { text: "Demo: test" });
});

test("channel preview ignores messages from the past", async () => {
    disableAnimations();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const messageId = pyEnv["mail.message"].create({
        body: "first message",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    for (let i = 0; i < 100; i++) {
        pyEnv["mail.message"].create({
            body: `message ${i}`,
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const newestMessageId = pyEnv["mail.message"].create({
        body: "last message",
        message_type: "comment",
        model: "discuss.channel",
        parent_id: messageId,
        res_id: channelId,
    });
    const [selfMember] = pyEnv["discuss.channel.member"].search_read([
        ["partner_id", "=", serverState.partnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.member"].write([selfMember.id], {
        new_message_separator: newestMessageId + 1,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-Message-content", { text: "last message" });
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await click(".o-mail-MessageInReply-content", { text: "first message" });
    await contains(".o-mail-Message", { count: 31 });
    await contains(".o-mail-Message-content", { text: "first message" });
    await contains(".o-mail-Message-content", { text: "last message", count: 0 });
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await contains(".o-mail-NotificationItem-text", { text: "You: last message" });
    withUser(serverState.userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "it's a good idea", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-NotificationItem-text", { text: "You: it's a good idea" });
});

test("counter is taking into account non-fetched channels", async () => {
    patchBrowserNotification("denied");
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Jane" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            Command.create({ message_unread_counter: 1, partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "first message",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await contains(".o-mail-MessagingMenu-counter", { text: "1" });
    expect(
        Boolean(getService("mail.store").Thread.get({ model: "discuss.channel", id: channelId }))
    ).toBe(false);
});

test("counter is updated on receiving message on non-fetched channels", async () => {
    patchBrowserNotification("denied");
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Jane" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "first message",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await contains(".o_menu_systray .dropdown-toggle i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu-counter", { count: 0 });
    expect(
        Boolean(getService("mail.store").Thread.get({ model: "discuss.channel", id: channelId }))
    ).toBe(false);
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "good to know", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-MessagingMenu-counter", { text: "1" });
});

test("can use notification item swipe actions", async () => {
    mockTouch(true);
    patchUiSize({ size: SIZES.SM });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", email: "demo@odoo.com" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "A message",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss();
    await contains("button.active", { text: "Notifications" });
    await click("button", { text: "Chats" });
    await contains(".o-mail-NotificationItem .o-mail-NotificationItem-badge:contains(1)");
    await swipeRight(".o_actionswiper"); // marks as read
    await contains(".o-mail-NotificationItem-badge", { count: 0 });
    await swipeLeft(".o_actionswiper"); // unpins
    await contains(".o-mail-NotificationItem", { count: 0 });
});
