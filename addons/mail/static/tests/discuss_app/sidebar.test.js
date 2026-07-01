import {
    click,
    contains,
    defineMailModels,
    insertText,
    listenStoreFetch,
    openDiscuss,
    openFormView,
    openMessagingMenu,
    setupChatHub,
    start,
    startServer,
    triggerHotkey,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test, waitFor } from "@odoo/hoot";
import { animationFrame, press, rightClick } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { Command, getService, onRpc, serverState } from "@web/../tests/web_test_helpers";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";
import { getOrigin } from "@web/core/utils/urls";
import { range } from "@web/core/utils/numbers";

describe.current.tags("desktop");
defineMailModels();

test("default thread rendering", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelIds = pyEnv["discuss.channel"].create([
        { name: "General", channel_type: "channel" },
        { name: "MyGroup", channel_type: "group" },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "chat",
        },
    ]);
    pyEnv["mail.message"].create({
        body: "Bookmarked message",
        bookmarked_partner_ids: [serverState.partnerId],
        model: "discuss.channel",
        res_id: channelIds[0],
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-MessagingMenu-tab:has(:text('Notifications'))");
    await click(".o-mail-MessagingMenu-tab[data-id='notification']");
    await contains(".o-mail-MessagingMenu-tab.active:has(:text('Notifications'))");
    await contains(".o-mail-MessagingMenuEmpty:has(:text('You\\'re all caught up!'))");
    await click(".o-mail-MessagingMenu-tab[data-id='channel']");
    await click(".o-mail-NotificationItem:has(:text('General'))");
    await contains(
        ".o-mail-MessagingMenuItem:has(.o-mail-NotificationItem.o-active):has(:text('General'))"
    );
    await contains(".o-mail-Thread:has(:text('Welcome to #General!'))");
    await click(".o-mail-MessagingMenu-tab[data-id='chat']");
    await click(".o-mail-NotificationItem:has(:text('MyGroup'))");
    await contains(
        ".o-mail-MessagingMenuItem:has(.o-mail-NotificationItem.o-active):has(:text('MyGroup'))"
    );
    await click(".o-mail-NotificationItem:has(:text('Demo'))");
    await contains(
        ".o-mail-MessagingMenuItem:has(.o-mail-NotificationItem.o-active):has(:text('Demo'))"
    );
    await contains(".o-mail-Thread:has(:text('Demo'))");
});

test("sidebar: basic chat rendering", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, channel_role: "owner" }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-MessagingMenuItem");
    await contains(".o-mail-MessagingMenuItem:has(:text('Demo'))");
    await contains(".o-mail-MessagingMenuItem img[alt='Thread Image']");
    await click("[title='Chat Actions']");
    await waitFor(".o-dropdown-item:count(7)", { timeout: 3000 });
    await waitFor(".o-mail-ActionList-group:count(4)");
    const group = range(0, 4).map((i) => `.o-mail-ActionList-group:eq(${i})`);
    await waitFor(`${group[0]} .o-dropdown-item:count(2)`);
    await waitFor(`${group[0]} .o-dropdown-item:eq(0):text('Start Video Call')`);
    await waitFor(`${group[0]} .o-dropdown-item:eq(1):text('Start Call')`);
    await waitFor(`${group[1]} .o-dropdown-item:count(2)`);
    await waitFor(`${group[1]} .o-dropdown-item:eq(0):text('Invite People')`);
    await waitFor(`${group[1]} .o-dropdown-item:eq(1):text('Add to Favorites')`);
    await waitFor(`${group[2]} .o-dropdown-item:count(2)`);
    await waitFor(`${group[2]} .o-dropdown-item:eq(0):text('Mute Conversation')`);
    await waitFor(`${group[2]} .o-dropdown-item:eq(1):text('Advanced Settings')`);
    await waitFor(`${group[3]} .o-dropdown-item:count(1)`);
    await waitFor(`${group[3]} .o-dropdown-item:text('Hide Until New Message')`);
    await contains(".o-mail-MessagingMenuItem .badge", { count: 0 });
});

test("sidebar: open pinned channel", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss("tab:channel");
    await click(".o-mail-NotificationItem:has(:text('General'))");
    await contains(".o-mail-Composer-input[placeholder='Message #General…']");
    await contains(".o-mail-DiscussContent-threadName", { value: "General" });
});

test("sidebar: open channel and leave it", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    onRpc("discuss.channel", "action_unfollow", ({ args }) => {
        expect.step("action_unfollow");
        expect(args[0]).toBe(channelId);
    });
    setupChatHub({ opened: [channelId] });
    await start();
    await openDiscuss("tab:channel");
    await click(".o-mail-NotificationItem:has(:text('General'))");
    await contains(".o-mail-DiscussContent-threadName", { value: "General" });
    await expect.waitForSteps([]);
    await click("[title='Channel Actions']");
    await click(".o-dropdown-item:contains('Leave Channel')");
    await click("button:text('Leave Conversation')");
    await contains(".o-mail-MessagingMenuItem:has(:text('General'))", { count: 0 });
    await contains(".o-mail-DiscussContent:text(No conversation selected.)");
    await expect.waitForSteps(["action_unfollow"]);
});

test.tags("focus required");
test("chat - channel should count unread message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId, im_status: "offline" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 1, partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-MessagingMenu-tab:has(:text('Chats')) .o-discuss-badge:text(1)");
    await contains(".o-mail-NotificationItem:has(:text('Demo')) .o-discuss-badge:text(1)");
    await click(".o-mail-NotificationItem:has(:text('Demo'))");
    await contains(".o-mail-Message");
    await contains(".o-discuss-badge", { count: 0 });
});

test.tags("focus required");
test("mark channel as seen on last message visible", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ message_unread_counter: 1, partner_id: serverState.partnerId }),
        ],
    });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss("tab:channel");
    await click(".o-mail-NotificationItem.o-interest:has(:text(test))");
    await contains(".o-mail-Message");
    await contains(".o-mail-NotificationItem.o-interest:has(:text(test))", { count: 0 });
});

test("sidebar: public channel rendering", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "channel1",
        channel_type: "channel",
        group_public_id: false,
    });
    await start();
    await openDiscuss("tab:channel");
    await contains(".o-mail-MessagingMenuItem:has(:text('channel1'))", { contains: [".fa-globe"] });
});

test("channel - avatar: should have correct avatar", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        avatar_cache_key: "notaDateCache",
    });
    await start();
    await openDiscuss("tab:channel");
    await contains(".o-mail-MessagingMenuItem img");
    await contains(
        `img[data-src='${getOrigin()}/web/image/discuss.channel/${channelId}/avatar_128?unique=notaDateCache']`
    );
});

test("channel - avatar: should update avatar url from bus", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        avatar_cache_key: "notaDateCache",
        name: "test",
    });
    await start();
    await openDiscuss(channelId);
    await contains(
        `img[data-src='${getOrigin()}/web/image/discuss.channel/${channelId}/avatar_128?unique=notaDateCache']`,
        { count: 2 }
    );
    await getService("orm").call("discuss.channel", "write", [
        [channelId],
        { image_128: "This field does not matter" },
    ]);
    const result = pyEnv["discuss.channel"].search_read([["id", "=", channelId]]);
    const newCacheKey = result[0]["avatar_cache_key"];
    await contains(
        `img[data-src='${getOrigin()}/web/image/discuss.channel/${channelId}/avatar_128?unique=${newCacheKey}']`,
        { count: 3 }
    );
});

test("chat - avatar: should have correct avatar", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId, im_status: "offline" });
    const partner = pyEnv["res.partner"].search_read([["id", "=", partnerId]])[0];
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-MessagingMenuItem img");
    await contains(
        `img[data-src='${getOrigin()}/web/image/res.partner/${partnerId}/avatar_128?unique=${
            deserializeDateTime(partner.write_date).ts
        }']`
    );
});

test("chat should be sorted by last activity time", async () => {
    const pyEnv = await startServer();
    const [demo_id, yoshi_id] = pyEnv["res.partner"].create([{ name: "Demo" }, { name: "Yoshi" }]);
    pyEnv["res.users"].create([{ partner_id: demo_id }, { partner_id: yoshi_id }]);
    pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [
                Command.create({
                    last_interest_dt: "2000-01-01 10:00:00",
                    partner_id: serverState.partnerId,
                }),
                Command.create({ partner_id: demo_id }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({
                    last_interest_dt: "2000-02-01 10:00:00",
                    partner_id: serverState.partnerId,
                }),
                Command.create({ partner_id: yoshi_id }),
            ],
            channel_type: "chat",
        },
    ]);
    await start();
    await openDiscuss();
    await contains(".o-mail-MessagingMenuItem:has(:text('Yoshi'))", {
        before: [".o-mail-MessagingMenuItem:has(:text('Demo'))"],
    });
    await click(".o-mail-NotificationItem:has(:text('Demo'))");
    await insertText(".o-mail-Composer-input[placeholder='Message Demo…']", "Blabla");
    await press("Enter");
    await contains(".o-mail-Message:has(:text('Blabla'))");
    await contains(".o-mail-MessagingMenuItem:has(:text('Demo'))", {
        before: [".o-mail-MessagingMenuItem:has(:text('Yoshi'))"],
    });
});

test("Can unpin chat channel", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ channel_type: "chat" });
    await start();
    await openDiscuss();
    await contains(".o-mail-MessagingMenuItem:has(:text('Mitchell Admin'))");
    await click("[title='Chat Actions']");
    await click(".o-dropdown-item:text('Hide Until New Message')");
    await contains(".o-mail-MessagingMenuItem:has(:text('Mitchell Admin'))", { count: 0 });
});

test("No 'Hide Until New Message' on conversation with self in call", async () => {
    const pyEnv = await startServer();
    onRpc("/mail/rtc/session/notify_call_members", () => true);
    const partnerId = pyEnv["res.partner"].create({ name: "Partner1" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["partner_id", "=", partnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.rtc.session"].create({
        channel_id: channelId,
        channel_member_id: memberId,
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Join Call']");
    await contains(".o-discuss-Call.o-selfInCall");
    await click("[title='Chat Actions']");
    await contains(".o-dropdown-item:text('Invite People')");
    await contains(".o-dropdown-item:text('Hide Until New Message')", { count: 0 });
    await click("button[title='Disconnect']");
    await contains(".o-discuss-Call.o-selfInCall", { count: 0 });
    await click("[title='Chat Actions']");
    await contains(".o-dropdown-item:text('Hide Until New Message')");
});

test("opening a hidden channel re-pins it", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        {
            channel_type: "channel",
            name: "InitialChannel",
        },
        {
            channel_type: "channel",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    unpin_dt: "2021-01-01 12:00:00",
                }),
            ],
            name: "General",
        },
    ]);
    await start();
    await openDiscuss("tab:channel");
    await contains(".o-mail-MessagingMenuItem:has(:text('InitialChannel'))");
    await contains(".o-mail-MessagingMenuItem:has(:text('General'))", { count: 0 });
    await triggerHotkey("control+k");
    await click(".o-mail-DiscussCommand-nameContainer:text('General')");
    await contains(".o-mail-MessagingMenuItem:has(:text('General'))");
});

test("Can leave channel", async () => {
    mockDate("2023-01-03 12:00:00");
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_interest_dt: "2021-01-03 12:00:00",
            }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-MessagingMenuItem:has(:text('General'))");
    await click("[title='Channel Actions']");
    await click(".o-dropdown-item:contains('Leave Channel')");
    await click("button:text('Leave Conversation')");
    await contains(".o-mail-MessagingMenuItem:has(:text('General'))", { count: 0 });
});

test("Do no channel_info after unpin", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    listenStoreFetch("discuss.channel");
    setupChatHub({ opened: [channelId] });
    await start();
    // ensure onRpc is at least set up properly (because then it is asserted negatively)
    await waitStoreFetch("discuss.channel");
    await openDiscuss(channelId);
    await click("[title='Chat Actions']");
    await click(".o-dropdown-item:contains('Hide Until New Message')");
    rpc("/mail/message/post", {
        thread_id: channelId,
        thread_model: "discuss.channel",
        post_data: {
            body: "Hello world",
            message_type: "comment",
        },
    });
    // weak test, no guarantee that we waited long enough for the potential rpc to be done
    await animationFrame();
    await waitStoreFetch();
});

test.tags("focus required");
test("Tab unread counter up to date after mention is marked as seen", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Chuck" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "group",
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        model: "discuss.channel",
        res_id: channelId,
        body: "@Mitchell Admin",
        needaction: true,
    });
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId,
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
    ]);
    await start();
    await openDiscuss();
    await contains(".o-mail-MessagingMenuItem .o-discuss-badge");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-MessagingMenuItem .o-discuss-badge", { count: 0 });
});

test("Unpinning channel closes its chat window", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "Sales" });
    await start();
    await openFormView("discuss.channel");
    await openMessagingMenu("channel");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow:text('Sales')");
    await openDiscuss("tab:channel");
    await click("[title='Channel Actions']");
    await click(".o-dropdown-item:contains('Leave Channel')");
    await openFormView("discuss.channel");
    await contains(".o-mail-ChatWindow:text('Sales')", { count: 0 });
});

test.tags("focus required");
test("Update channel data via bus notification", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "Sales",
        channel_type: "channel",
        create_uid: serverState.userId,
    });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true, waitUntilSubscribe: false });
    await openDiscuss(channelId, { target: env1 });
    await openDiscuss(channelId, { target: env2 });
    await contains(`${env1.selector} .o-mail-MessagingMenuItem:has(:text('Sales'))`);
    await insertText(`${env1.selector} .o-mail-DiscussContent-threadName`, "test");
    await triggerHotkey("Enter");
    await contains(`${env2.selector} .o-mail-MessagingMenuItem:has(:text('Salestest'))`);
});

test("Redirect to the thread containing the bookmark and highlight the message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        model: "discuss.channel",
        res_id: channelId,
        body: "<p>Hello there!!!</p>",
    });
    await start();
    await openDiscuss("tab:channel");
    await click(".o-mail-NotificationItem:has(:text('General'))");
    await contains(".o-mail-Message");
    await rightClick(".o-mail-Message");
    await click(".o-dropdown-item:contains('Bookmark')");
    await click(".o-mail-MessagingMenu-tab[data-id='bookmark']:has(.badge:text(1))");
    await contains(".o-mail-MessagingMenu-tab.active:has(:text('Bookmarks'))");
    await click(".o-mail-NotificationItem:has(:text('You: Hello there!!!'))");
    await contains(".o-mail-NotificationItem:has(:text('General'))");
    await contains(".o-mail-Message.o-highlighted:has(:text('Hello there!!!'))");
});

test("Sidebar channels show correct notification counter based on settings", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        channel_notifications: "all",
    });
    const partnerId = pyEnv["res.partner"].create({ name: "Chuck" });
    const mentionsChannelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "channel",
        name: "Mentions",
    });
    const regularChannelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "channel",
        name: "Regular",
    });
    const mentionMessageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        model: "discuss.channel",
        res_id: mentionsChannelId,
        body: "@Mitchell Admin",
        needaction: true,
    });
    pyEnv["mail.notification"].create([
        {
            mail_message_id: mentionMessageId,
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
    ]);
    pyEnv["mail.message"].create([
        {
            author_id: partnerId,
            model: "discuss.channel",
            res_id: mentionsChannelId,
            body: "test",
        },
        {
            author_id: partnerId,
            model: "discuss.channel",
            res_id: regularChannelId,
            body: "test",
        },
    ]);
    await start();
    await openDiscuss("tab:channel");
    await contains(".o-mail-MessagingMenuItem:has(:text('Mentions')) .badge:text('2')");
    await contains(".o-mail-MessagingMenuItem:has(:text('Regular')) .badge:text('1')");
    rpc("/discuss/settings/custom_notifications", { custom_notifications: false }); // default: @mention only
    await contains(".o-mail-MessagingMenuItem:has(:text('Mentions')) .badge:text('1')");
    await contains(".o-mail-MessagingMenuItem:has(:text('Regular')) .badge.o-empty");
    rpc("/discuss/settings/custom_notifications", { custom_notifications: "no_notif" });
    await contains(".o-mail-MessagingMenuItem:has(:text('Mentions')) .badge.o-empty");
    await contains(".o-mail-MessagingMenuItem:has(:text('Regular')) .badge.o-empty");
});

test("add and remove channel from favorites updates sidebar", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    await start();
    await openDiscuss("tab:channel");
    await click(".o-mail-NotificationItem:has(:text('General')) button .oi-ellipsis-h");
    await click(".o-dropdown-item:contains('Add to Favorites')");
    await contains(".o-mail-MessagingMenuItem:has(:text('General')) .fa-star");
    await click(".o-mail-NotificationItem:has(:text('General')) button .oi-ellipsis-h");
    await click(".o-dropdown-item:contains('Remove from Favorites')");
    await contains(".o-mail-MessagingMenuItem:has(:text('General')) .fa-star", { count: 0 });
});

test("Muted group chats show notification counter from mentions-only", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Chuck" });
    const [channelId_1, channelId_2] = pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "group",
            name: "Sales Team",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "group",
            name: "Development Team",
        },
    ]);
    const messageIds = pyEnv["mail.message"].create([
        {
            author_id: partnerId,
            model: "discuss.channel",
            res_id: channelId_2,
            body: "@Mitchell Admin",
            needaction: true,
        },
        {
            author_id: partnerId,
            model: "discuss.channel",
            res_id: channelId_1,
            body: "test",
        },
        {
            author_id: partnerId,
            model: "discuss.channel",
            res_id: channelId_2,
            body: "test",
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageIds[0],
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
    ]);
    await start();
    await openDiscuss();
    await contains(".o-mail-MessagingMenuItem:has(:text('Sales Team')) .badge:text('1')");
    await contains(".o-mail-MessagingMenuItem:has(:text('Development Team')) .badge:text('2')");
    rpc("/discuss/settings/mute", { minutes: -1, channel_id: channelId_1 });
    rpc("/discuss/settings/mute", { minutes: -1, channel_id: channelId_2 });
    await contains(".o-mail-MessagingMenuItem:has(:text('Sales Team')) .badge", { count: 0 });
    await contains(".o-mail-MessagingMenuItem:has(:text('Development Team')) .badge:text('1')");
});
