import { waitNotifications } from "@bus/../tests/bus_test_helpers";

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
    MENU_ACTIVE_IDS,
    mockGetMedia,
} from "@mail/../tests/mail_test_helpers";
import { MENU_TABS } from "@mail/core/public_web/messaging_menu/messaging_menu_model";
import { messagingMenuHelpers } from "@mail/../tests/mock_server/controllers/discuss/messaging_menu";

import { describe, expect, mockPermission, test } from "@odoo/hoot";
import { rightClick } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";

import {
    Command,
    getService,
    mockService,
    patchWithCleanup,
    serverState,
    withUser,
} from "@web/../tests/web_test_helpers";

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
    await contains(".o-mail-MessagingMenuItem", { count: 2 });
    await contains(".o-mail-MessagingMenuItem:has(:text('Alice'))");
    await contains(".o-mail-MessagingMenuItem:has(:text('Bob'))");
    await click("button:text(Unread)");
    await contains("button.o-active:text(Unread)");
    await contains(".o-mail-NotificationItem", { count: 1 });
    await contains(".o-mail-NotificationItem-name:text(Alice)");
    await click("button:text(All)");
    await contains("button.o-active:text(All)");
    await contains(".o-mail-NotificationItem", { count: 2 });
    await contains(".o-mail-MessagingMenuItem:has(:text('Alice'))");
    await contains(".o-mail-MessagingMenuItem:has(:text('Bob'))");
});

test("unread filter shows only unread channels", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const [alphaChannelId, betaChannelId] = pyEnv["discuss.channel"].create([
        {
            name: "Alpha",
            channel_type: "channel",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId, is_pinned: true }),
                Command.create({ partner_id: partnerId }),
            ],
        },
        {
            name: "Beta",
            channel_type: "channel",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId, is_pinned: true }),
                Command.create({ partner_id: partnerId }),
            ],
        },
    ]);
    const [, betaMessageId] = pyEnv["mail.message"].create([
        { author_id: partnerId, body: "hello", model: "discuss.channel", res_id: alphaChannelId },
        { author_id: partnerId, body: "hi", model: "discuss.channel", res_id: betaChannelId },
    ]);
    const [betaMemberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", betaChannelId],
        ["partner_id", "=", serverState.partnerId],
    ]);
    // Beta is marked read: its separator is past its last message.
    pyEnv["discuss.channel.member"].write([betaMemberId], {
        new_message_separator: betaMessageId + 1,
    });
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-MessagingMenuItem", { count: 2 });
    await contains(".o-mail-MessagingMenuItem:has(:text('Alpha'))");
    await contains(".o-mail-MessagingMenuItem:has(:text('Beta'))");
    await click("button:text(Unread)");
    await contains("button.o-active:text(Unread)");
    await contains(".o-mail-NotificationItem", { count: 1 });
    await contains(".o-mail-NotificationItem-name:text(Alpha)");
    await click("button:text(All)");
    await contains("button.o-active:text(All)");
    await contains(".o-mail-NotificationItem", { count: 2 });
    await contains(".o-mail-MessagingMenuItem:has(:text('Alpha'))");
    await contains(".o-mail-MessagingMenuItem:has(:text('Beta'))");
});

test("group filter shows only group chats", async () => {
    const pyEnv = await startServer();
    const [aliceId, bobId] = pyEnv["res.partner"].create([{ name: "Alice" }, { name: "Bob" }]);
    pyEnv["discuss.channel"].create([
        {
            channel_type: "chat",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: aliceId }),
            ],
        },
        {
            name: "Team",
            channel_type: "group",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId, is_pinned: true }),
                Command.create({ partner_id: aliceId }),
                Command.create({ partner_id: bobId }),
            ],
        },
    ]);
    await start();
    await openMessagingMenu();
    await contains(".o-mail-MessagingMenuItem", { count: 2 });
    await contains(".o-mail-MessagingMenuItem:has(:text('Alice'))");
    await contains(".o-mail-MessagingMenuItem:has(:text('Team'))");
    await click("button:text(Group)");
    await contains("button.o-active:text(Group)");
    await contains(".o-mail-NotificationItem", { count: 1 });
    await contains(".o-mail-NotificationItem-name:text(Team)");
    await click("button:text(All)");
    await contains("button.o-active:text(All)");
    await contains(".o-mail-MessagingMenuItem", { count: 2 });
    await contains(".o-mail-MessagingMenuItem:has(:text('Alice'))");
    await contains(".o-mail-MessagingMenuItem:has(:text('Team'))");
});

test("thread filter shows only channel threads", async () => {
    const pyEnv = await startServer();
    const generalId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, is_pinned: true }),
        ],
    });
    pyEnv["discuss.channel"].create({
        name: "Bug thread",
        parent_channel_id: generalId,
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, is_pinned: true }),
        ],
    });
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-MessagingMenuItem", { count: 2 });
    await contains(".o-mail-MessagingMenuItem:has(:text('General'))");
    await contains(".o-mail-MessagingMenuItem:has(:text('Bug thread'))");
    await click("button:text(Thread)");
    await contains("button.o-active:text(Thread)");
    await contains(".o-mail-NotificationItem", { count: 1 });
    await contains(".o-mail-NotificationItem:has(:text('Bug thread'))");
    await click("button:text(All)");
    await contains("button.o-active:text(All)");
    await contains(".o-mail-MessagingMenuItem", { count: 2 });
    await contains(".o-mail-MessagingMenuItem:has(:text('General'))");
    await contains(".o-mail-MessagingMenuItem:has(:text('Bug thread'))");
});

test("active filter with no match shows a neutral empty state, not the tab onboarding", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, is_pinned: true }),
        ],
    });
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-MessagingMenuItem", { count: 1 });
    await contains(".o-mail-MessagingMenuItem:has(:text('General'))");
    await click("button:text(Thread)");
    await contains("button.o-active:text(Thread)");
    await contains(".o-mail-MessagingMenuEmpty:has(:text('No conversation matches this filter.'))");
});

test("plugin filter narrows a tab's content, ANDed with the chip filter", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    const [aliceId, bobId] = pyEnv["res.partner"].create([{ name: "Alice" }, { name: "Bob" }]);
    const [aliceUnreadId, aliceReadId, bobUnreadId] = pyEnv["mail.message"].create([
        {
            author_id: aliceId,
            body: "hello",
            model: "res.partner",
            needaction: true,
            res_id: aliceId,
        },
        {
            author_id: aliceId,
            body: "old news",
            model: "res.partner",
            needaction: false,
            res_id: aliceId,
        },
        { author_id: bobId, body: "hi", model: "res.partner", needaction: true, res_id: bobId },
    ]);
    pyEnv["mail.notification"].create(
        [aliceUnreadId, aliceReadId, bobUnreadId].map((mail_message_id) => ({
            is_read: mail_message_id === aliceReadId,
            mail_message_id,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        }))
    );
    patchWithCleanup(messagingMenuHelpers, {
        _get_menu_tab_filter_domain(env, tab_id, filter_id) {
            if (tab_id === "notification" && filter_id === "test_author_alice") {
                return [["author_id", "=", aliceId]];
            }
            return super._get_menu_tab_filter_domain(env, tab_id, filter_id);
        },
    });
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.NOTIFICATION);
    await contains("button.o-active:text(Unread)");
    await click("button:text(All)");
    await contains("button.o-active:text(All)");
    await contains(".o-mail-MessagingMenuItem", { count: 3 });
    getService("mail.store").messagingMenuSystrayState.setPluginFilter("test.author", {
        id: "test_author_alice",
        includesMessage: (msg) => msg.author_id?.id === aliceId,
    });
    await contains(".o-mail-MessagingMenuItem", { count: 2 });
    await contains(".o-mail-MessagingMenuItem:has(:text('Alice: hello'))");
    await contains(".o-mail-MessagingMenuItem:has(:text('Alice: old news'))");
    await click("button:text(Unread)");
    await contains("button.o-active:text(Unread)");
    await contains(".o-mail-MessagingMenuItem", { count: 1 });
    await contains(".o-mail-MessagingMenuItem:has(:text('Alice: hello'))");
});

test("create new chat from chat tab", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "TestPartner" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    await start();
    await openMessagingMenu();
    await click("button:has([data-icon='add']):text(Chat)");
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
    await click("button:has([data-icon='add']):text(Chat)");
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
    await openMessagingMenu(MENU_ACTIVE_IDS.MEETING);
    await contains(".o-mail-MessagingMenuEmpty .fw-bold:text('No video conference planned!')");
    await contains(
        ".o-mail-MessagingMenuEmpty:contains('Collaborate with coworkers and customers in video calls.')"
    );
    await contains(".o-mail-MessagingMenuEmpty:contains('No install needed.')");
});

test("create new meeting from meeting tab", async () => {
    mockGetMedia();
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.MEETING);
    await click("button:text(Meeting)");
    await click(".o-dropdown-item:text('Start Now')");
    await contains(".o-mail-Meeting");
});

test("unread filter shows only unread meetings", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const [standupId, retroId] = pyEnv["discuss.channel"].create([
        {
            name: "Standup",
            channel_type: "group",
            default_display_mode: "video_full_screen",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId, is_pinned: true }),
                Command.create({ partner_id: partnerId }),
            ],
        },
        {
            name: "Retro",
            channel_type: "group",
            default_display_mode: "video_full_screen",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId, is_pinned: true }),
                Command.create({ partner_id: partnerId }),
            ],
        },
    ]);
    const [, retroMessageId] = pyEnv["mail.message"].create([
        { author_id: partnerId, body: "hello", model: "discuss.channel", res_id: standupId },
        { author_id: partnerId, body: "hi", model: "discuss.channel", res_id: retroId },
    ]);
    const [retroMemberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", retroId],
        ["partner_id", "=", serverState.partnerId],
    ]);
    // Retro is marked read: its separator is past its last message.
    pyEnv["discuss.channel.member"].write([retroMemberId], {
        new_message_separator: retroMessageId + 1,
    });
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.MEETING);
    await contains(".o-mail-MessagingMenuItem", { count: 2 });
    await contains(".o-mail-MessagingMenuItem:has(:text('Standup'))");
    await contains(".o-mail-MessagingMenuItem:has(:text('Retro'))");
    await click("button:text(Unread)");
    await contains("button.o-active:text(Unread)");
    await contains(".o-mail-NotificationItem", { count: 1 });
    await contains(".o-mail-NotificationItem:has(:text('Standup'))");
    await click("button:text(All)");
    await contains("button.o-active:text(All)");
    await contains(".o-mail-MessagingMenuItem", { count: 2 });
    await contains(".o-mail-MessagingMenuItem:has(:text('Standup'))");
    await contains(".o-mail-MessagingMenuItem:has(:text('Retro'))");
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
    mockService("action", {
        doAction(action) {
            expect.step("mail.discuss_channel_action");
            expect(action).toBe("mail.discuss_channel_action");
        },
    });
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-MessagingMenu .o-mail-MessagingMenuEmpty");
    await contains(".o-mail-MessagingMenuEmptyChannel-popularChannels :text(General)");
    await contains(".o-mail-MessagingMenuEmptyChannel-popularChannels :text('2 followers')");
    await click("button:text('Find more channels')");
    await expect.waitForSteps(["mail.discuss_channel_action"]);
    await contains(".o-mail-MessagingMenu", { count: 0 });
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
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
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
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
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-MessagingMenuItem", { count: 2 });
    await contains(".o-mail-MessagingMenuItem:eq(0):has(:text(Gamma):has([data-icon='star']))");
    await contains(".o-mail-MessagingMenuItem:eq(1):has(:text(Alpha'))");
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
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-MessagingMenuItem", { count: 2 });
    await contains(".o-mail-MessagingMenuItem:has(:text('Alpha'))");
    await contains(".o-mail-MessagingMenuItem:has(:text('Beta'))");
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
    await openMessagingMenu(MENU_ACTIVE_IDS.NOTIFICATION);
    await contains(".o-mail-MessagingMenuItem", { count: 2 });
    await contains(".o-mail-MessagingMenuItem:has(:text('Demo: msg 1'))");
    await contains(".o-mail-MessagingMenuItem:has(:text('Demo: msg 2'))");
    // Respond to mark as read.
    await contains(
        ".o-mail-MessagingMenu-tab:has(:text('Notifications')) .o-mail-MessagingMenu-tabCounter:text(2)"
    );
    await triggerEvents(".o-mail-MessagingMenuItem:first", ["mouseenter"]);
    await click(".o-mail-MessagingMenu-actions:eq(0) button");
    await click(".o-dropdown-item:text('Mark as Read')");
    await contains(
        ".o-mail-MessagingMenu-tab:has(:text('Notifications')) .o-mail-MessagingMenu-tabCounter:text(1)"
    );
});

test("message tab counter: initial unread count decrements after marking unloaded message as read", async () => {
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
    // Simulate mark as read from another device.
    await getService("orm").call("mail.message", "set_message_done", [[messageId1]]);
    await contains(
        ".o-mail-MessagingMenu-tab:has(:text('Notifications')) .o-mail-MessagingMenu-tabCounter:text(1)"
    );
});

test("marking unloaded message as read when notifications are handled by email", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "msg",
        model: "res.partner",
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
    await openMessagingMenu();
    await contains(".o-mail-MessagingMenu-tab", { count: 3 });
    await contains(".o-mail-MessagingMenu-tab:has(:text('Chats'))");
    await contains(".o-mail-MessagingMenu-tab:has(:text('Channels'))");
    await contains(".o-mail-MessagingMenu-tab:has(:text('Meetings'))");
    // Notifications are handled by email: no tab counts them.
    await contains(".o-mail-MessagingMenu-tab:has(:text('Notifications'))", { count: 0 });
    // Simulate mark as read from another device.
    await getService("orm").call("mail.message", "set_message_done", [[messageId]]);
    await waitNotifications(["mail.message/mark_as_read"]);
});

test("inbox tab displays message when empty", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.NOTIFICATION);
    await contains(".o-mail-MessagingMenuEmpty .fw-bold:text('You\\'re all caught up!')");
    await contains(
        ".o-mail-MessagingMenuEmpty :text('Notifications of the documents you follow will appear here.')"
    );
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
    await contains(".o-mail-MessagingMenu-tab:has(:text('Chats'))");
    await contains(".o-mail-MessagingMenu-tab:has(:text('Channels'))");
    await contains(".o-mail-MessagingMenu-tab:has(:text('Meetings'))");
    await contains(".o-mail-Message");
    await rightClick(".o-mail-Message");
    await click(".o-dropdown-item:contains(Bookmark)");
    await contains(".o-mail-MessagingMenu-tab", { count: 4 });
    await contains(".o-mail-MessagingMenu-tab:has(:text('Bookmarks')):has(.badge:text(1))");
    await contains(".o-mail-MessagingMenu-tab:has(:text('Chats'))");
    await contains(".o-mail-MessagingMenu-tab:has(:text('Channels'))");
    await contains(".o-mail-MessagingMenu-tab:has(:text('Meetings'))");
    await click(`.o-mail-MessagingMenu-tab[data-id='${MENU_TABS.BOOKMARK}']`);
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
    await openDiscuss(MENU_ACTIVE_IDS.BOOKMARK);
    await contains(".o-mail-MessagingMenuItem:has(:text('You: This is a message'))");
    await insertText(".o-mail-DiscussSearch input", "message");
    await contains(".o-mail-MessagingMenuItem:has(:text('You: This is a message'))");
    await insertText(".o-mail-DiscussSearch input", "something different", { replace: true });
    await contains(".o-mail-MessagingMenuEmpty:text('No results for \"something different\".')");
});

test("push notification request stays on the chat tab regardless of user notification preference", async () => {
    mockPermission("notifications", "prompt");
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHAT);
    await contains(
        ".o-mail-MessagingMenu-tab:has(:text('Chats')) .o-mail-MessagingMenu-tabCounter:text(1)"
    );
    await contains(".o-mail-NotificationItem-name:text('Turn on notifications')");
    getService("mail.store").self_user.notification_type = "inbox";
    await contains(
        ".o-mail-MessagingMenu-tab:has(:text('Chats')) .o-mail-MessagingMenu-tabCounter:text(1)"
    );
    await contains(".o-mail-NotificationItem-name:text('Turn on notifications')");
    await contains(".o-mail-MessagingMenu-tab:has(:text('Notifications'))");
    await openMessagingMenu(MENU_ACTIVE_IDS.NOTIFICATION);
    await contains(".o-mail-MessagingMenuEmpty:has(:text('You're all caught up!'))");
});

test("convert meeting to group chat (self)", async () => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId, channel_role: "owner" }),
            ],
            channel_type: "group",
            default_display_mode: "video_full_screen",
            name: "Meeting 1",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId, channel_role: "owner" }),
            ],
            channel_type: "group",
            default_display_mode: "video_full_screen",
            name: "Meeting 2",
        },
    ]);
    await start();
    await openDiscuss(channelIds[0]);
    await contains(".o-mail-MessagingMenu-tab:has(:text('Meetings')).active");
    await contains(".o-mail-MessagingMenuItem", { count: 2 });
    await contains(".o-mail-MessagingMenuItem .o-active:has(:text('Meeting 1'))");
    await click(".o-mail-MessagingMenuItem:has(:text('Meeting 2')) [title='Chat Actions']");
    await click(".o-dropdown-item:text('Convert to Chat')");
    await contains(".o-mail-MessagingMenuItem");
    await click(".o-mail-MessagingMenuItem:has(:text('Meeting 1')) [title='Chat Actions']");
    await click(".o-dropdown-item:text('Convert to Chat')");
    await contains(".o-mail-MessagingMenu-tab:has(:text('Chats')).active");
    await contains(".o-mail-MessagingMenuItem", { count: 2 });
    await contains(".o-mail-MessagingMenuItem:has(:text('Meeting 1'))");
    await contains(
        `.o-mail-NotificationMessage:has(:text('${serverState.partnerName} converted this meeting into a group chat'))`
    );
});

test("sync the meeting when another member converts it to a group chat", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Alice", im_status: "online" });
    const partnerId = pyEnv["res.partner"].create({ name: "Alice", user_ids: [userId] });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId, channel_role: "owner" }),
        ],
        channel_type: "group",
        default_display_mode: "video_full_screen",
        name: "Meeting 1",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-MessagingMenu-tab:has(:text('Meetings')).active");
    await contains(".o-mail-MessagingMenuItem .o-active:has(:text('Meeting 1'))");
    await withUser(userId, () =>
        getService("mail.store").fetchStoreData("/discuss/channel/meeting_to_group_chat", {
            channel_id: channelId,
        })
    );
    await contains(".o-mail-MessagingMenu-tab:has(:text('Chats')).active");
    await contains(".o-mail-MessagingMenuItem .o-active:has(:text('Meeting 1'))");
    await contains(
        "   .o-mail-NotificationMessage:has(:text('Alice converted this meeting into a group chat'))"
    );
});
