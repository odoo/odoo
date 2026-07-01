import {
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    openMessagingMenu,
    start,
    startServer,
    triggerEvents,
} from "@mail/../tests/mail_test_helpers";

import { describe, mockPermission, test } from "@odoo/hoot";
import { rightClick } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";

import { Command, getService, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("chat tab displays message when empty", async () => {
    await start();
    await openMessagingMenu();
    await contains(".o-mail-MessagingMenuEmpty .fw-bold:text('No messages yet!')");
    await contains(
        ".o-mail-MessagingMenuEmpty :text('Chat with your coworkers on desktop or on mobile.')"
    );
});

test("unread filter shows only unread chats", async () => {
    const pyEnv = await startServer();
    const [aliceId, bobId] = pyEnv["res.partner"].create([{ name: "Alice" }, { name: "Bob" }]);
    const [aliceChatId, bobChatId] = pyEnv["discuss.channel"].create([
        {
            channel_type: "chat",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId, message_unread_counter: 0 }),
                Command.create({ partner_id: aliceId }),
            ],
        },
        {
            channel_type: "chat",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId, message_unread_counter: 1 }),
                Command.create({ partner_id: bobId }),
            ],
        },
    ]);
    const [, bobChatMessageId] = pyEnv["mail.message"].create([
        { author_id: aliceId, body: "hello", model: "discuss.channel", res_id: aliceChatId },
        { author_id: bobId, body: "hi", model: "discuss.channel", res_id: bobChatId },
    ]);
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", bobChatId],
        ["partner_id", "=", serverState.partnerId],
    ]);
    //
    pyEnv["discuss.channel.member"].write([memberId], {
        new_message_separator: bobChatMessageId + 1,
    });
    await start();
    await openMessagingMenu();
    await contains(".o-mail-NotificationItem", { count: 2 });
    await click("button:text(Unread)");
    await contains("button.active:text(Unread)");
    await contains(".o-mail-NotificationItem", { count: 1 });
    await contains(".o-mail-NotificationItem-name:text(Alice)");
    await click("button:text(Unread)");
    await contains("button.active:text(Unread)");
    await contains(".o-mail-NotificationItem", { count: 2 });
});

test("create new chat from chat tab", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "TestPartner" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    await start();
    await openMessagingMenu();
    await click("button:has(.fa-plus):text(Chat)");
    await contains(".o-discuss-ChannelInvitation");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner'))");
    await click("button[title='Create Chat']:enabled");
    await contains(".o-discuss-ChannelInvitation", { count: 0 });
    await contains(".o-mail-ChatWindow-displayName:text('TestPartner')");
});

test("create new group chat from chat tab", async () => {
    const pyEnv = await startServer();
    const [partner1Id, partner2Id] = pyEnv["res.partner"].create([
        { name: "TestPartner1" },
        { name: "TestPartner2" },
    ]);
    pyEnv["res.users"].create({ partner_id: partner1Id });
    pyEnv["res.users"].create({ partner_id: partner2Id });
    await start();
    await openMessagingMenu();
    await click("button:has(.fa-plus):text(Chat)");
    await contains(".o-discuss-ChannelInvitation");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner1'))");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner2'))");
    await click("button[title='Create Chat']:enabled");
    await contains(".o-discuss-ChannelInvitation", { count: 0 });
    await contains(
        ".o-mail-ChatWindow-displayName:text('Mitchell Admin, TestPartner1, and TestPartner2')"
    );
});

test("meeting tab displays message when empty", async () => {
    await start();
    await openMessagingMenu("meeting");
    await contains(".o-mail-MessagingMenuEmpty .fw-bold:text('No video conference planned!')");
    await contains(
        ".o-mail-MessagingMenuEmpty:contains('Collaborate with coworkers and customers in video calls.')"
    );
    await contains(".o-mail-MessagingMenuEmpty:contains('No install needed.')");
});

test("create new meeting from meeting tab", async () => {
    await start();
    await openMessagingMenu("meeting");
    await click("button:text(Meeting)");
    await contains(".o-mail-Meeting");
});

test("join most popular channel from empty channel tab", async () => {
    const pyEnv = await startServer();
    const [partner1, partner2] = pyEnv["res.partner"].create([
        { name: "User 1" },
        { name: "User 2" },
    ]);
    pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            Command.create({ partner_id: partner1 }),
            Command.create({ partner_id: partner2 }),
        ],
    });
    await start();
    await openMessagingMenu("channel");
    await contains(".o-mail-MessagingMenuEmpty");
    await contains(".o-mail-MessagingMenuEmptyChannel-popularChannels :text(General)");
    await contains(".o-mail-MessagingMenuEmptyChannel-popularChannels :text('2 followers')");
    await contains("button:text(Follow)");
    await click("button:text(Follow)");
    await contains(".o-mail-NotificationItem-name:text(General)");
});

test("tabs sort items by last_interest_dt", async () => {
    mockDate("2023-01-03 12:00:00");
    const pyEnv = await startServer();
    const [, betaId] = pyEnv["discuss.channel"].create([
        {
            name: "Alpha",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    last_interest_dt: "2026-01-01 00:00:00",
                }),
            ],
        },
        {
            name: "Beta",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    last_interest_dt: "2025-01-01 00:00:00",
                }),
            ],
        },
        {
            name: "Gamma",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    last_interest_dt: "2024-01-01 00:00:00",
                }),
            ],
        },
    ]);
    pyEnv["discuss.channel"].create({
        name: "Sub",
        parent_channel_id: betaId,
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_interest_dt: "2024-06-01 00:00:00",
            }),
        ],
    });
    await start();
    await openMessagingMenu("channel");
    await contains(".o-mail-NotificationItem", { count: 4 });
    await contains(".o-mail-NotificationItem-name:eq(0):text(Alpha)");
    await contains(".o-mail-NotificationItem-name:eq(1):text(Beta)");
    await contains(".o-mail-NotificationItem-name:eq(2):has(:text(Sub))");
    await contains(".o-mail-NotificationItem-name:eq(3):text(Gamma)");
});

test("favorite channels are displayed first", async () => {
    mockDate("2023-01-03 12:00:00");
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        {
            name: "Alpha",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    last_interest_dt: "2022-06-01 00:00:00",
                }),
            ],
        },
        {
            name: "Gamma",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    last_interest_dt: "2021-01-01 00:00:00",
                    is_favorite: true,
                }),
            ],
        },
    ]);
    await start();
    await openMessagingMenu("channel");
    await contains(".o-mail-NotificationItem", { count: 2 });
    await contains(".o-mail-NotificationItem-name:eq(0):text(Gamma):has(.fa-star)");
    await contains(".o-mail-NotificationItem-name:eq(1):text(Alpha')");
});

test("channel tab counter: initial unread count combines with loaded channels state", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const [channel1Id, channel2Id] = pyEnv["discuss.channel"].create([
        {
            name: "Alpha",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    message_unread_counter: 1,
                }),
                Command.create({ partner_id: partnerId }),
            ],
        },
        {
            name: "Beta",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    message_unread_counter: 1,
                }),
                Command.create({ partner_id: partnerId }),
            ],
        },
    ]);
    pyEnv["mail.message"].create([
        { author_id: partnerId, body: "msg", model: "discuss.channel", res_id: channel1Id },
        { author_id: partnerId, body: "msg", model: "discuss.channel", res_id: channel2Id },
    ]);
    await start();
    await openMessagingMenu();
    // From init_counter_ids before channels are loaded.
    await contains(
        ".o-mail-MessagingMenu-tab:has(:text('Channels')) .o-mail-MessagingMenu-tabCounter:text(2)"
    );
    await openMessagingMenu("channel");
    await contains(".o-mail-NotificationItem", { count: 2 });
    // No double count after channels load.
    await contains(
        ".o-mail-MessagingMenu-tab:has(:text('Channels')) .o-mail-MessagingMenu-tabCounter:text(2)"
    );
    await triggerEvents(".o-mail-NotificationItem.o-interest:first", ["mouseenter"]);
    // Respond to mark as read.
    await click(".o-mail-MessagingMenu-actions:eq(0) button");
    await click(".o-dropdown-item:text(Mark Read)");
    await contains(
        ".o-mail-MessagingMenu-tab:has(:text('Channels')) .o-mail-MessagingMenu-tabCounter:text(1)"
    );
});

test("message tab counter: initial unread count decrements after marking loaded message as read", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const [messageId1, messageId2] = pyEnv["mail.message"].create([
        {
            author_id: partnerId,
            body: "msg 1",
            model: "res.partner",
            needaction: true,
            res_id: partnerId,
        },
        {
            author_id: partnerId,
            body: "msg 2",
            model: "res.partner",
            needaction: true,
            res_id: partnerId,
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId1,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
        {
            mail_message_id: messageId2,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
    ]);
    await start();
    await openMessagingMenu();
    // From init_counter_ids before messages are loaded.
    await contains(
        ".o-mail-MessagingMenu-tab:has(:text('Notifications')) .o-mail-MessagingMenu-tabCounter:text(2)"
    );
    await openMessagingMenu("notification");
    await contains(".o-mail-NotificationItem", { count: 2 });
    // Respond to mark as read.
    await contains(
        ".o-mail-MessagingMenu-tab:has(:text('Notifications')) .o-mail-MessagingMenu-tabCounter:text(2)"
    );
    await triggerEvents(".o-mail-NotificationItem:first", ["mouseenter"]);
    await click(".o-mail-MessagingMenu-actions:eq(0) button");
    await click(".o-dropdown-item:text('Mark as Read')");
    await contains(
        ".o-mail-MessagingMenu-tab:has(:text('Notifications')) .o-mail-MessagingMenu-tabCounter:text(1)"
    );
});

test("inbox tab displays message when empty", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    await start();
    await openMessagingMenu("notification");
    await contains(".o-mail-MessagingMenuEmpty .fw-bold:text('You\\'re all caught up!')");
    await contains(".o-mail-MessagingMenuEmpty :text('New messages will appear here.')");
});

test("bookmark tab is only shown when there are bookmarked messages", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "<p>Hello there!</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-MessagingMenu-tab", { count: 3 });
    await contains(".o-mail-MessagingMenu-tab:text('Bookmarks')", { count: 0 });
    await contains(".o-mail-Message");
    await rightClick(".o-mail-Message");
    await click(".o-dropdown-item:contains(Bookmark)");
    await contains(".o-mail-MessagingMenu-tab:has(:text('Bookmarks')):has(.badge:text(1))");
    await contains(".o-mail-MessagingMenu-tab", { count: 4 });
    await click(".o-mail-MessagingMenu-tab[data-id='bookmark']");
    await contains(".o-mail-MessagingMenuItem .o-mail-NotificationItem-name:text(General)");
    await contains(
        ".o-mail-MessagingMenuItem .o-mail-NotificationItem-text:text('You: Hello there!')"
    );
});

test("can search messages", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "This is a message",
        model: "discuss.channel",
        res_id: channelId,
        bookmarked_partner_ids: [serverState.partnerId],
    });
    await start();
    await openDiscuss("tab:bookmark");
    await contains(".o-mail-MessagingMenuItem:has(:text('You: This is a message'))");
    await insertText(".o-mail-DiscussSearch input", "message");
    await contains(".o-mail-MessagingMenuItem:has(:text('You: This is a message'))");
    await insertText(".o-mail-DiscussSearch input", "something different", { replace: true });
    await contains(".o-mail-MessagingMenuEmpty:text('No results for \"something different\".')");
    await contains(".o-mail-MessagingMenuItem:has(:text('You: This is a message'))", { count: 0 });
});

test("push notification request stays on the chat tab regardless of user notification preference", async () => {
    mockPermission("notifications", "prompt");
    await start();
    await openMessagingMenu("chat");
    await contains(
        ".o-mail-MessagingMenu-tab:has(:text('Chats')) .o-mail-MessagingMenu-tabCounter:text(1)"
    );
    await contains(".o-mail-NotificationItem-name:text('Turn on notifications')");
    getService("mail.store").self_user.notification_type = "inbox";
    await contains(
        ".o-mail-MessagingMenu-tab:has(:text('Chats')) .o-mail-MessagingMenu-tabCounter:text(1)"
    );
    await contains(".o-mail-MessagingMenu-tab:has(:text('Notifications'))");
    await openMessagingMenu("notification");
    await contains(".o-mail-NotificationItem-name:text('Turn on notifications')", { count: 0 });
});
