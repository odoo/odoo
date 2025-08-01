import {
    click,
    contains,
    defineMailModels,
    insertText,
    listenStoreFetch,
    openDiscuss,
    openFormView,
    setupChatHub,
    start,
    startServer,
    triggerHotkey,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";
import { DISCUSS_SIDEBAR_COMPACT_LS } from "@mail/core/public_web/discuss_app_model";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, drag, press, queryFirst } from "@odoo/hoot-dom";
import { Deferred, mockDate } from "@odoo/hoot-mock";
import {
    asyncStep,
    Command,
    getService,
    mockService,
    onRpc,
    serverState,
    waitForSteps,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";
import { getOrigin } from "@web/core/utils/urls";

describe.current.tags("desktop");
defineMailModels();

test("toggling category button hide category items", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    await start();
    await openDiscuss();
    await contains("button.o-active", { text: "Inbox" });
    await contains(".o-mail-DiscussSidebarChannel");
    await click(
        ":nth-child(1 of .o-mail-DiscussSidebarCategory) .o-mail-DiscussSidebarCategory-icon"
    );
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
});

test("toggling category button does not hide active category items", async () => {
    const pyEnv = await startServer();
    const [channelId] = pyEnv["discuss.channel"].create([
        { name: "abc", channel_type: "channel" },
        { name: "def", channel_type: "channel" },
    ]);
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussSidebarChannel", { count: 2 });
    await contains(".o-mail-DiscussSidebarChannel.o-active");
    await click(
        ":nth-child(1 of .o-mail-DiscussSidebarCategory) .o-mail-DiscussSidebarCategory-icon"
    );
    await contains(".o-mail-DiscussSidebarChannel");
    await contains(".o-mail-DiscussSidebarChannel.o-active");
});

test("toggling category button does not hide active sub thread", async () => {
    const pyEnv = await startServer();
    const mainChannelId = pyEnv["discuss.channel"].create({ name: "Main Channel" });
    const subChannelId = pyEnv["discuss.channel"].create({
        name: "Sub Channel",
        parent_channel_id: mainChannelId,
    });
    await start();
    await openDiscuss(subChannelId);
    await contains(".o-mail-DiscussSidebar-item", { text: "Main Channel" });
    await contains(".o-mail-DiscussSidebar-item", { text: "Sub Channel" });
    await click(".o-mail-DiscussSidebar button", { text: "Channels" });
    await contains(".o-mail-DiscussSidebar-item", { text: "Main Channel" });
    await contains(".o-mail-DiscussSidebar-item", { text: "Sub Channel" });
});

test("Closing a category sends the updated user setting to the server.", async () => {
    onRpc("res.users.settings", "set_res_users_settings", ({ kwargs }) => {
        asyncStep("/web/dataset/call_kw/res.users.settings/set_res_users_settings");
        expect(kwargs.new_settings.is_discuss_sidebar_category_channel_open).toBe(false);
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory:contains('Channels') .oi"); // wait fully loaded
    await click(
        ":nth-child(1 of .o-mail-DiscussSidebarCategory) .o-mail-DiscussSidebarCategory-icon"
    );
    await waitForSteps(["/web/dataset/call_kw/res.users.settings/set_res_users_settings"]);
});

test("Opening a category sends the updated user setting to the server.", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_channel_open: false,
    });
    onRpc("res.users.settings", "set_res_users_settings", ({ kwargs }) => {
        asyncStep("/web/dataset/call_kw/res.users.settings/set_res_users_settings");
        expect(kwargs.new_settings.is_discuss_sidebar_category_channel_open).toBe(true);
    });
    await start();
    await openDiscuss();
    await click(
        ".o-mail-DiscussSidebarCategory-channel .o-mail-DiscussSidebarCategory-icon.oi-chevron-right"
    );
    await waitForSteps(["/web/dataset/call_kw/res.users.settings/set_res_users_settings"]);
});

test("channel - command: should have view command when category is unfolded", async () => {
    await start();
    await openDiscuss();
    await contains("[title='View or join channels']");
});

test("channel - command: should have view command when category is folded", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_channel_open: false,
    });
    await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebarCategory-channel .btn", { text: "Channels" });
    await contains("[title='View or join channels']");
});

test("channel - command: should not have add command when category is folded", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_channel_open: false,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory", { text: "Channels" });
    await contains("[title='Add or join a channel']", { count: 0 });
});

test("channel - states: close manually by clicking the title", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "general" });
    pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_channel_open: true,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { text: "general" });
    await click(".o-mail-DiscussSidebarCategory-channel .btn", { text: "Channels" });
    await contains(".o-mail-DiscussSidebarChannel", { count: 0, text: "general" });
});

test("channel - states: open manually by clicking the title", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "general" });
    pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_channel_open: false,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory:contains('Channels') .oi"); // wait fully loaded
    await contains(".o-mail-DiscussSidebarCategory-channel", { text: "Channels" });
    await contains(".o-mail-DiscussSidebarChannel", { count: 0, text: "general" });
    await click(".o-mail-DiscussSidebarCategory-channel .btn", { text: "Channels" });
    await contains(".o-mail-DiscussSidebarChannel", { text: "general" });
});

test("sidebar: inbox with counter", async () => {
    const pyEnv = await startServer();
    pyEnv["mail.notification"].create({
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await contains("button", { text: "Inbox", contains: [".badge", { text: "1" }] });
});

test("default thread rendering", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["discuss.channel"].create([
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
    await start();
    await openDiscuss();
    await contains("button", { text: "Inbox" });
    await contains("button", { text: "Starred messages" });
    await contains("button", { text: "History" });
    await contains(".o-mail-DiscussSidebar-item", { text: "General" });
    await contains("button.o-active", { text: "Inbox" });
    await contains(".o-mail-Thread", {
        text: "Your inbox is emptyChange your preferences to receive new notifications in your inbox.",
    });
    await click("button", { text: "Starred messages" });
    await contains("button.o-active", { text: "Starred messages" });
    await contains(".o-mail-Thread", {
        text: "No starred messages You can mark any message as 'starred', and it shows up in this mailbox.",
    });
    await click("button", { text: "History" });
    await contains("button.o-active", { text: "History" });
    await contains(".o-mail-Thread", {
        text: "No history messages Messages marked as read will appear in the history.",
    });
    await click(".o-mail-DiscussSidebar-item", { text: "General" });
    await contains(".o-mail-DiscussSidebar-item.o-active", { text: "General" });
    await contains(".o-mail-Thread", { text: "Welcome to #General!" });
    await click(".o-mail-DiscussSidebar-item", { text: "MyGroup" });
    await contains(".o-mail-DiscussSidebar-item.o-active", { text: "MyGroup" });
    await click(".o-mail-DiscussSidebar-item", { text: "Demo" });
    await contains(".o-mail-DiscussSidebar-item.o-active", { text: "Demo" });
    await contains(".o-mail-Thread", { text: "Demo" });
});

test("sidebar: basic chat rendering", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel");
    await contains(".o-mail-DiscussSidebarChannel", { text: "Demo" });
    await contains(".o-mail-DiscussSidebarChannel img[alt='Thread Image']");
    await click("[title='Chat Actions']");
    await contains(".o-dropdown-item:contains('Unpin Conversation')");
    await contains(".o-mail-DiscussSidebarChannel .badge", { count: 0 });
});

test("sidebar: show pinned channel", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { text: "General" });
});

test("sidebar: open pinned channel", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebarChannel", { text: "General" });
    await contains(".o-mail-Composer-input[placeholder='Message #General…']");
    await contains(".o-mail-Discuss-threadName", { value: "General" });
});

test("sidebar: open channel and leave it", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    onRpc("discuss.channel", "action_unfollow", ({ args }) => {
        asyncStep("action_unfollow");
        expect(args[0]).toBe(channelId);
    });
    setupChatHub({ opened: [channelId] });
    await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebarChannel", { text: "General" });
    await contains(".o-mail-Discuss-threadName", { value: "General" });
    await waitForSteps([]);
    await click("[title='Channel Actions']");
    await click(".o-dropdown-item:contains('Leave Channel')");
    await click("button", { text: "Leave Conversation" });
    await contains(".o-mail-DiscussSidebarChannel", { count: 0, text: "General" });
    await contains(".o-mail-Discuss-threadName", { value: "Inbox" });
    await waitForSteps(["action_unfollow"]);
});

test("sidebar: unpin chat from bus", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { text: "Demo" });
    await click(".o-mail-DiscussSidebarChannel", { text: "Demo" });
    await contains(".o-mail-Composer-input[placeholder='Message Demo…']");
    await contains(".o-mail-Discuss-threadName", { value: "Demo" });
    // Simulate receiving a unpin chat notification
    // (e.g. from user interaction from another device or browser tab)
    pyEnv["discuss.channel"].channel_pin([channelId], false);
    await contains(".o-mail-DiscussSidebarChannel", { count: 0, text: "Demo" });
    await contains(".o-mail-Discuss-threadName", { count: 0, value: "Demo" });
});

test.tags("focus required");
test("chat - channel should count unread message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Demo",
        im_status: "offline",
    });
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
    await contains(".o-discuss-badge", { text: "1" });
    await click(".o-mail-DiscussSidebarChannel", { text: "Demo" });
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
    await openDiscuss();
    await click(".o-mail-DiscussSidebarChannel.o-unread", { text: "test" });
    await contains(".o-mail-DiscussSidebarChannel:not(.o-unread)", { text: "test" });
});

test("channel - counter: should not have a counter if the category is unfolded and without needaction messages", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_channel_open: true,
    });
    pyEnv["discuss.channel"].create({ name: "general" });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory", {
        contains: [
            ["i.oi.oi-chevron-down"],
            ["span", { text: "Channels" }],
            [".badge", { count: 0 }],
        ],
    });
});

test("channel - counter: should not have a counter if the category is unfolded and with needaction messages", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_channel_open: true,
    });
    const [channelId_1, channelId_2] = pyEnv["discuss.channel"].create([
        { name: "channel1" },
        { name: "channel2" },
    ]);
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            body: "message 1",
            model: "discuss.channel",
            res_id: channelId_1,
        },
        {
            body: "message_2",
            model: "discuss.channel",
            res_id: channelId_2,
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId_1,
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
        {
            mail_message_id: messageId_2,
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
    ]);
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory", {
        contains: [
            ["i.oi.oi-chevron-down"],
            ["span", { text: "Channels" }],
            [".badge", { count: 0 }],
        ],
    });
});

test("channel - counter: should not have a counter if category is folded and without needaction messages", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({});
    pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_channel_open: false,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory", {
        contains: [
            ["i.oi.oi-chevron-right"],
            ["span", { text: "Channels" }],
            [".badge", { count: 0 }],
        ],
    });
});

test("channel - counter: should have correct value of needaction threads if category is folded and with needaction messages", async () => {
    const pyEnv = await startServer();
    const [channelId_1, channelId_2] = pyEnv["discuss.channel"].create([
        { name: "Channel_1" },
        { name: "Channel_2" },
    ]);
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            body: "message 1",
            model: "discuss.channel",
            res_id: channelId_1,
        },
        {
            body: "message_2",
            model: "discuss.channel",
            res_id: channelId_2,
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId_1,
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
        {
            mail_message_id: messageId_2,
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
    ]);
    pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_channel_open: false,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory", {
        contains: [
            ["i.oi.oi-chevron-right"],
            ["span", { text: "Channels" }],
            [".badge", { text: "2" }],
        ],
    });
});

test("chat - counter: should not have a counter if the category is unfolded and without unread messages", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_chat_open: true,
    });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 0, partner_id: serverState.partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory", {
        contains: [
            ["i.oi.oi-chevron-down"],
            ["span", { text: "Direct messages" }],
            [".badge", { count: 0 }],
        ],
    });
});

test("chat - counter: should not have a counter if the category is unfolded and with unread messages", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_chat_open: true,
    });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                message_unread_counter: 10,
                partner_id: serverState.partnerId,
            }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory", {
        contains: [
            ["i.oi.oi-chevron-down"],
            ["span", { text: "Direct messages" }],
            [".badge", { count: 0 }],
        ],
    });
});

test("chat - counter: should not have a counter if category is folded and without unread messages", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_chat_open: false,
    });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 0, partner_id: serverState.partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory", {
        contains: [
            ["i.oi.oi-chevron-right"],
            ["span", { text: "Direct messages" }],
            [".badge", { count: 0 }],
        ],
    });
});

test("chat - counter: should have correct value of unread threads if category is folded and with unread messages", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_chat_open: false,
    });
    const bobUserId = pyEnv["res.users"].create({ name: "Bob" });
    const bobPartnerId = pyEnv["res.partner"].create({ name: "Bob", user_id: bobUserId.id });
    const channelIds = pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: bobPartnerId.id }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: bobPartnerId.id }),
            ],
            channel_type: "chat",
        },
    ]);
    pyEnv["mail.message"].create([
        {
            author_id: bobPartnerId,
            body: `hello channel 1`,
            model: "discuss.channel",
            res_id: channelIds[0],
            message_type: "comment",
        },
        {
            author_id: bobPartnerId,
            body: "hello channel 2",
            model: "discuss.channel",
            res_id: channelIds[1],
            message_type: "comment",
        },
    ]);
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory", {
        contains: [
            ["i.oi.oi-chevron-right"],
            ["span", { text: "Direct messages" }],
            [".badge", { text: "2" }],
        ],
    });
});

test("chat - command: should not have add command when category is folded", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_chat_open: false,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory", { text: "Direct messages" });
    await contains(".o-mail-DiscussSidebarCategory", {
        contains: [
            ["i.oi.oi-chevron-right"],
            ["span", { text: "Direct messages" }],
            ["[title='Start a conversation']", { count: 0 }],
        ],
    });
});

test("chat - states: close manually by clicking the title", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ channel_type: "chat" });
    pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_chat_open: true,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel");
    await click(".o-mail-DiscussSidebarCategory .btn", { text: "Direct messages" });
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
});

test("sidebar channels should be ordered case insensitive alphabetically", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        { name: "Xyz" },
        { name: "abc" },
        { name: "Abc" },
        { name: "Est" },
        { name: "Xyz" },
        { name: "Équipe" },
        { name: "époque" },
    ]);
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", {
        text: "abc",
        before: [".o-mail-DiscussSidebarChannel", { text: "Abc" }],
    });
    await contains(".o-mail-DiscussSidebarChannel", {
        text: "Abc",
        before: [".o-mail-DiscussSidebarChannel", { text: "époque" }],
    });
    await contains(".o-mail-DiscussSidebarChannel", {
        text: "époque",
        before: [".o-mail-DiscussSidebarChannel", { text: "Équipe" }],
    });
    await contains(".o-mail-DiscussSidebarChannel", {
        text: "Équipe",
        before: [".o-mail-DiscussSidebarChannel", { text: "Est" }],
    });
    await contains(".o-mail-DiscussSidebarChannel", {
        text: "Est",
        before: [".o-mail-DiscussSidebarChannel", { text: "Xyz", count: 2 }],
    });
});

test("sidebar: public channel rendering", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "channel1",
        channel_type: "channel",
        group_public_id: false,
    });
    await start();
    await openDiscuss();
    await contains("button", { text: "channel1", contains: [".fa-globe"] });
});

test("channel - avatar: should have correct avatar", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        avatar_cache_key: "notaDateCache",
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel img");
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

test("channel - states: close should update the value on the server", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "test" });
    pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_channel_open: true,
    });
    await start();
    mockService("orm", {
        async call(model, method, _, params) {
            const result = await super.call(...arguments);
            if (model === "res.users.settings" && method === "set_res_users_settings") {
                asyncStep(
                    `set_res_users_settings - ${params.new_settings.is_discuss_sidebar_category_channel_open}`
                );
            }
            return result;
        },
    });
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory:contains('Channels') .oi.oi-chevron-down"); // wait fully loaded
    await click(".o-mail-DiscussSidebarCategory .btn", { text: "Channels" });
    await waitForSteps(["set_res_users_settings - false"]);
});

test("channel - states: open should update the value on the server", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "test" });
    pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_channel_open: false,
    });
    await start();
    mockService("orm", {
        async call(model, method, _, params) {
            const result = await super.call(...arguments);
            if (model === "res.users.settings" && method === "set_res_users_settings") {
                asyncStep(
                    `set_res_users_settings - ${params.new_settings.is_discuss_sidebar_category_channel_open}`
                );
            }
            return result;
        },
    });
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory:contains('Channels') .oi"); // wait fully loaded
    await click(".o-mail-DiscussSidebarCategory .btn", { text: "Channels" });
    await waitForSteps(["set_res_users_settings - true"]);
});

test("channel - states: close from the bus", async () => {
    mockDate("2023-01-03 12:00:00");
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "channel1",
        channel_type: "channel",
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_interest_dt: "2021-01-03 10:00:00",
            }),
        ],
    });
    const userSettingsId = pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_channel_open: true,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory-channel .oi-chevron-down");
    await contains("button", { text: "channel1" });
    const [partner] = pyEnv["res.partner"].read(serverState.partnerId);
    pyEnv["bus.bus"]._sendone(partner, "res.users.settings", {
        id: userSettingsId,
        is_discuss_sidebar_category_channel_open: false,
    });
    await contains(".o-mail-DiscussSidebarCategory-channel .oi-chevron-right");
    await contains("button", { count: 0, text: "channel1" });
});

test("channel - states: open from the bus", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "channel1" });
    const userSettingsId = pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_channel_open: false,
    });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    // send after init_messaging because bus subscription is done after init_messaging
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory-channel .oi-chevron-right");
    const [partner] = pyEnv["res.partner"].read(serverState.partnerId);
    pyEnv["bus.bus"]._sendone(partner, "res.users.settings", {
        id: userSettingsId,
        is_discuss_sidebar_category_channel_open: true,
    });
    await contains(".o-mail-DiscussSidebarCategory-channel .oi-chevron-down");
    await contains("button", { text: "channel1" });
});

test("channel - states: the active category item should be visible even if the category is closed", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "channel1" });
    await start();
    await openDiscuss();
    await click("button", { text: "channel1" });
    await contains(".o-mail-DiscussSidebarChannel-container", { text: "channel1" });
    await click(".o-mail-DiscussSidebarCategory .btn", { text: "Channels" });
    await contains(".o-mail-DiscussSidebarCategory-channel .oi-chevron-right");
    await contains("button", { text: "channel1" });
    await click("button", { text: "Inbox" });
    await contains("button", { count: 0, text: "channel1" });
});

test("chat - states: open manually by clicking the title", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        channel_type: "chat",
    });
    pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_chat_open: false,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory-chat .oi-chevron-right");
    await contains(".o-mail-DiscussSidebar button", { count: 0, text: "Mitchell Admin" });
    await click(".o-mail-DiscussSidebarCategory-chat .btn", { text: "Direct messages" });
    await contains(".o-mail-DiscussSidebarCategory-chat .oi-chevron-down");
    await contains(".o-mail-DiscussSidebar button", { text: "Mitchell Admin" });
});

test("chat - states: close should call update server data", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "test" });
    pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_chat_open: true,
    });
    await start();
    mockService("orm", {
        async call(model, method) {
            const result = await super.call(...arguments);
            if (model === "res.users.settings" && method === "set_res_users_settings") {
                asyncStep("set_res_users_settings");
            }
            return result;
        },
    });
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory-chat .oi-chevron-down");
    await click(".o-mail-DiscussSidebarCategory-chat .btn", { text: "Direct messages" });
    await waitForSteps(["set_res_users_settings"]);
    const newSettings = await getService("orm").call(
        "res.users.settings",
        "_find_or_create_for_user",
        [serverState.userId]
    );
    expect(newSettings.is_discuss_sidebar_category_chat_open).toBe(false);
});

test("chat - states: open should call update server data", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "test" });
    pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_chat_open: false,
    });
    await start();
    mockService("orm", {
        async call(model, method) {
            const result = await super.call(...arguments);
            if (model === "res.users.settings" && method === "set_res_users_settings") {
                asyncStep("set_res_users_settings");
            }
            return result;
        },
    });
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory-chat .oi-chevron-right");
    await click(".o-mail-DiscussSidebarCategory-chat .btn", { text: "Direct messages" });
    await waitForSteps(["set_res_users_settings"]);
    const newSettings = await getService("orm").call(
        "res.users.settings",
        "_find_or_create_for_user",
        [serverState.userId]
    );
    expect(newSettings.is_discuss_sidebar_category_chat_open).toBe(true);
});

test("chat - states: close from the bus", async () => {
    mockDate("2023-01-03 12:00:00");
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_interest_dt: "2021-01-03 10:00:00",
            }),
        ],
    });
    const userSettingsId = pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_chat_open: true,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory-chat .oi-chevron-down");
    await contains(".o-mail-DiscussSidebar button", { text: "Mitchell Admin" });
    const [partner] = pyEnv["res.partner"].read(serverState.partnerId);
    pyEnv["bus.bus"]._sendone(partner, "res.users.settings", {
        id: userSettingsId,
        is_discuss_sidebar_category_chat_open: false,
    });
    await contains(".o-mail-DiscussSidebarCategory-chat .oi-chevron-right");
    await contains(".o-mail-DiscussSidebar button", { count: 0, text: "Mitchell Admin" });
});

test("chat - states: open from the bus", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ channel_type: "chat" });
    const userSettingsId = pyEnv["res.users.settings"].create({
        user_id: serverState.userId,
        is_discuss_sidebar_category_chat_open: false,
    });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    // send after init_messaging because bus subscription is done after init_messaging
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory-chat .oi-chevron-right");
    await contains(".o-mail-DiscussSidebar button", { count: 0, text: "Mitchell Admin" });
    const [partner] = pyEnv["res.partner"].read(serverState.partnerId);
    pyEnv["bus.bus"]._sendone(partner, "res.users.settings", {
        id: userSettingsId,
        is_discuss_sidebar_category_chat_open: true,
    });
    await contains(".o-mail-DiscussSidebarCategory-chat .oi-chevron-down");
    await contains(".o-mail-DiscussSidebar button", { text: "Mitchell Admin" });
});

test("chat - states: the active category item should be visible even if the category is closed", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ channel_type: "chat" });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory-chat .oi-chevron-down");
    await contains(".o-mail-DiscussSidebar button", { text: "Mitchell Admin" });
    await click("button", { text: "Mitchell Admin" });
    await contains("button.o-active", { text: "Mitchell Admin" });
    await click(".o-mail-DiscussSidebarCategory-chat .btn", { text: "Direct messages" });
    await contains(".o-mail-DiscussSidebarCategory-chat .oi-chevron-right");
    await contains(".o-mail-DiscussSidebar button", { text: "Mitchell Admin" });
    await click("button", { text: "Inbox" });
    await contains(".o-mail-DiscussSidebarCategory-chat .oi-chevron-right");
    await contains(".o-mail-DiscussSidebar button", { count: 0, text: "Mitchell Admin" });
});

test("chat - avatar: should have correct avatar", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Demo",
        im_status: "offline",
    });
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
    await contains(".o-mail-DiscussSidebarChannel img");
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
                    last_interest_dt: "2021-01-01 10:00:00",
                    partner_id: serverState.partnerId,
                }),
                Command.create({ partner_id: demo_id }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({
                    last_interest_dt: "2021-02-01 10:00:00",
                    partner_id: serverState.partnerId,
                }),
                Command.create({ partner_id: yoshi_id }),
            ],
            channel_type: "chat",
        },
    ]);
    await start();
    await openDiscuss();
    await contains(
        ".o-mail-DiscussSidebarChannel",
        { text: "Yoshi" },
        { before: [".o-mail-DiscussSidebarChannel", { text: "Demo" }] }
    );
    await click(".o-mail-DiscussSidebarChannel", { text: "Demo" });
    // post a new message on the last channel
    await insertText(".o-mail-Composer-input[placeholder='Message Demo…']", "Blabla");
    await press("Enter");
    await contains(".o-mail-Message", { text: "Blabla" });
    await contains(
        ".o-mail-DiscussSidebarChannel",
        { text: "Demo" },
        { before: [".o-mail-DiscussSidebarChannel", { text: "Yoshi" }] }
    );
});

test("Can unpin chat channel", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ channel_type: "chat" });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { text: "Mitchell Admin" });
    await click("[title='Chat Actions']");
    await click(".o-dropdown-item:contains('Unpin Conversation')");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0, text: "Mitchell Admin" });
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
    await contains(".o-mail-DiscussSidebarChannel", { text: "General" });
    await click("[title='Channel Actions']");
    await click(".o-dropdown-item:contains('Leave Channel')");
    await click("button", { text: "Leave Conversation" });
    await contains(".o-mail-DiscussSidebarChannel", { count: 0, text: "General" });
});

test("Do no channel_info after unpin", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General", channel_type: "chat" });
    listenStoreFetch("discuss.channel");
    setupChatHub({ opened: [channelId] });
    await start();
    // ensure onRpc is at least set up properly (because then it is asserted negatively)
    await waitStoreFetch("discuss.channel");
    await openDiscuss(channelId);
    await click("[title='Chat Actions']");
    await click(".o-dropdown-item:contains('Advanced Settings')");
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
test("Group unread counter up to date after mention is marked as seen", async () => {
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
    await contains(".o-mail-DiscussSidebarChannel .o-discuss-badge");
    await click(".o-mail-DiscussSidebarChannel");
    await contains(".o-discuss-badge", { count: 0 });
});

test("Unpinning channel closes its chat window", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "Sales" });
    await start();
    await openFormView("discuss.channel");
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow", { text: "Sales" });
    await openDiscuss();
    await click("[title='Channel Actions']");
    await click(".o-dropdown-item:contains('Leave Channel')");
    await openFormView("discuss.channel");
    await contains(".o-mail-ChatWindow", { count: 0, text: "Sales" });
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
    const env2 = await start({ asTab: true });
    await openDiscuss(channelId, { target: env1 });
    await openDiscuss(channelId, { target: env2 });
    await contains(".o-mail-DiscussSidebarChannel", { text: "Sales", target: env1 });
    await insertText(".o-mail-Discuss-threadName", "test", { target: env1 });
    await triggerHotkey("Enter");
    await contains(".o-mail-DiscussSidebarChannel", { text: "Salestest", target: env2 });
});

test("sidebar: show loading on initial opening", async () => {
    // This could load a lot of data (all pinned conversations)
    const def = new Deferred();
    listenStoreFetch("channels_as_member", {
        async onRpc() {
            asyncStep("before channels_as_member");
            await def;
        },
    });
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss();
    await contains(
        ".o-mail-DiscussSidebarCategory:contains('Channels') .fa.fa-circle-o-notch.fa-spin"
    );
    await contains(".o-mail-DiscussSidebarChannel", { text: "General", count: 0 });
    await waitForSteps(["before channels_as_member"]);
    def.resolve();
    await waitStoreFetch("channels_as_member");
    await contains(
        ".o-mail-DiscussSidebarCategory:contains('Channels') .fa.fa-circle-o-notch.fa-spin",
        { count: 0 }
    );
    await contains(".o-mail-DiscussSidebarChannel", { text: "General" });
});

test("Can make sidebar smaller", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebar");
    const normalWidth = queryFirst(".o-mail-DiscussSidebar").getBoundingClientRect().width;
    await (
        await drag(".o-mail-DiscussSidebar-resizablePanelContainer .o_resizable_panel_handle")
    ).drop(".o-mail-DiscussSidebar-resizablePanelContainer .o_resizable_panel_handle", {
        position: { x: 0 },
    });
    await contains(".o-mail-DiscussSidebar.o-compact");
    const compactWidth = queryFirst(".o-mail-DiscussSidebar").getBoundingClientRect().width;
    expect(normalWidth).toBeGreaterThan(compactWidth);
    expect(normalWidth).toBeGreaterThan(compactWidth / 2, {
        message: "compact mode is at least twice smaller than nomal mode",
    });
});

test("Sidebar compact is locally persistent (saved in local storage)", async () => {
    browser.localStorage.setItem(DISCUSS_SIDEBAR_COMPACT_LS, true);
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebar.o-compact");
    await (
        await drag(".o-mail-DiscussSidebar-resizablePanelContainer .o_resizable_panel_handle")
    ).drop(".o-mail-DiscussSidebar-resizablePanelContainer .o_resizable_panel_handle", {
        position: { x: 1000 },
    });
    await contains(".o-mail-DiscussSidebar:not(.o-compact)");
    expect(browser.localStorage.getItem(DISCUSS_SIDEBAR_COMPACT_LS)).toBe(null);
    await (
        await drag(".o-mail-DiscussSidebar-resizablePanelContainer .o_resizable_panel_handle")
    ).drop(".o-mail-DiscussSidebar-resizablePanelContainer .o_resizable_panel_handle", {
        position: { x: 0 },
    });
    await contains(".o-mail-DiscussSidebar.o-compact");
    expect(browser.localStorage.getItem(DISCUSS_SIDEBAR_COMPACT_LS)).toBe("true");
});

test("Sidebar compact is crosstab synced", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        create_uid: serverState.userId,
        name: "General",
    });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true });
    await openDiscuss(channelId, { target: env1 });
    await openDiscuss(channelId, { target: env2 });
    await contains(".o-mail-DiscussSidebar:not(.o-compact)", { target: env1 });
    await contains(".o-mail-DiscussSidebar:not(.o-compact)", { target: env2 });
    await (
        await drag(
            `.o-mail-Discuss-asTabContainer[data-as-tab-id='${env1.discussAsTabId}']
            .o-mail-DiscussSidebar-resizablePanelContainer
            .o_resizable_panel_handle`
        )
    ).drop(
        `.o-mail-Discuss-asTabContainer[data-as-tab-id='${env1.discussAsTabId}']
        .o-mail-DiscussSidebar-resizablePanelContainer
        .o_resizable_panel_handle`,
        { position: { x: 0 } }
    );
    await contains(".o-mail-DiscussSidebar.o-compact", { target: env1 });
    await contains(".o-mail-DiscussSidebar.o-compact", { target: env2 });
});

test("Redirect to the thread containing the starred message and highlight the message", async () => {
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
    await openDiscuss();
    await click(".o-mail-DiscussSidebarChannel", { text: "General" });
    await click(".o-mail-Message [title='Mark as Todo']");
    await click("button", { text: "Starred messages", contains: [".badge", { count: 1 }] });
    await click(".o-mail-Message-header a", { text: "#General" });
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "General" });
    await contains(".o-mail-Message.o-highlighted", { text: "Hello there!!!" });
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
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel:contains(Mentions) .badge", { text: "2" });
    await contains(".o-mail-DiscussSidebarChannel:contains(Regular) .badge", { text: "1" });
    rpc("/discuss/settings/custom_notifications", { custom_notifications: false }); // default: @mention only
    await contains(".o-mail-DiscussSidebarChannel:contains(Mentions) .badge", { text: "1" });
    await contains(".o-mail-DiscussSidebarChannel:contains(Regular) .badge", { count: 0 });
    rpc("/discuss/settings/custom_notifications", { custom_notifications: "no_notif" });
    await contains(".o-mail-DiscussSidebarChannel:contains(Mentions) .badge", { count: 0 });
    await contains(".o-mail-DiscussSidebarChannel:contains(Regular) .badge", { count: 0 });
});
