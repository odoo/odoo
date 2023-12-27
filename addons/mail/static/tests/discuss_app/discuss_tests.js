/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { makeFakePresenceService } from "@bus/../tests/helpers/mock_services";
import { TEST_USER_IDS } from "@bus/../tests/helpers/test_constants";
import { waitNotifications } from "@bus/../tests/helpers/websocket_event_deferred";

import { Command } from "@mail/../tests/helpers/command";
import { patchUiSize } from "@mail/../tests/helpers/patch_ui_size";
import { start } from "@mail/../tests/helpers/test_utils";

import {
    editInput,
    makeDeferred,
    nextTick,
    patchWithCleanup,
    triggerHotkey,
} from "@web/../tests/helpers/utils";
import {
    assertSteps,
    click,
    contains,
    createFile,
    focus,
    insertText,
    scroll,
    step,
} from "@web/../tests/utils";

QUnit.module("discuss");

QUnit.test("sanity check", async () => {
    const { openDiscuss } = await start({
        mockRPC(route, args, originRPC) {
            if (route.startsWith("/mail")) {
                step(route);
            }
            return originRPC(route, args);
        },
    });
    await assertSteps(["/mail/init_messaging", "/mail/load_message_failures"]);
    await openDiscuss();
    await assertSteps(["/mail/inbox/messages"]);
    await contains(".o-mail-DiscussSidebar");
    await contains("h4", { text: "Congratulations, your inbox is empty" });
});

QUnit.test("can change the thread name of #general [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
        create_uid: pyEnv.currentUserId,
    });
    const { openDiscuss } = await start({
        mockRPC(route, params) {
            if (route === "/web/dataset/call_kw/discuss.channel/channel_rename") {
                step(route);
            }
        },
    });
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input:focus");
    await contains("input.o-mail-Discuss-threadName", { value: "general" });
    await insertText("input.o-mail-Discuss-threadName:enabled", "special", { replace: true });
    triggerHotkey("Enter");
    await assertSteps(["/web/dataset/call_kw/discuss.channel/channel_rename"]);
    await contains(".o-mail-DiscussSidebarChannel", { text: "special" });
    await contains("input.o-mail-Discuss-threadName", { value: "special" });
});

QUnit.test("can active change thread from messaging menu", async () => {
    const pyEnv = await startServer();
    const [, teamId] = pyEnv["discuss.channel"].create([
        { name: "general", channel_type: "channel" },
        { name: "team", channel_type: "channel" },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss(teamId);
    await contains(".o-mail-DiscussSidebar-item", { text: "general" });
    await contains(".o-mail-DiscussSidebar-item.o-active", { text: "team" });
    await click(".o_main_navbar i[aria-label='Messages']");
    await click(".o-mail-DiscussSidebar-item", { text: "general" });
    await contains(".o-mail-DiscussSidebar-item.o-active", { text: "general" });
    await contains(".o-mail-DiscussSidebar-item", { text: "team" });
});

QUnit.test("can change the thread description of #general [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
        description: "General announcements...",
        create_uid: pyEnv.currentUserId,
    });
    const { openDiscuss } = await start({
        mockRPC(route, params) {
            if (route === "/web/dataset/call_kw/discuss.channel/channel_change_description") {
                step(route);
            }
        },
    });
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input:focus");
    await contains("input.o-mail-Discuss-threadDescription", {
        value: "General announcements...",
    });
    await insertText("input.o-mail-Discuss-threadDescription:enabled", "I want a burger today!", {
        replace: true,
    });
    triggerHotkey("Enter");
    await assertSteps(["/web/dataset/call_kw/discuss.channel/channel_change_description"]);
    await contains("input.o-mail-Discuss-threadDescription", {
        value: "I want a burger today!",
    });
});

QUnit.test("Message following a notification should not be squashed", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: '<div class="o_mail_notification">created <a href="#" class="o_channel_redirect">#general</a></div>',
        model: "discuss.channel",
        res_id: channelId,
        message_type: "notification",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Hello world!");
    await click(".o-mail-Composer button:enabled", { text: "Send" });
    await contains(".o-mail-Message-sidebar .o-mail-Message-avatarContainer");
});

QUnit.test("Posting message should transform links.", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "test https://www.odoo.com/");
    await click(".o-mail-Composer-send:enabled");
    await contains("a[href='https://www.odoo.com/']");
});

QUnit.test("Posting message should transform relevant data to emoji.", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "test :P :laughing:");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-body", { text: "test 😛 😆" });
});

QUnit.test(
    "posting a message immediately after another one is displayed in 'simple' mode (squashed)",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            name: "general",
            channel_type: "channel",
        });
        const { openDiscuss } = await start();

        openDiscuss(channelId);
        await insertText(".o-mail-Composer-input", "abc");
        await click(".o-mail-Composer button:enabled", { text: "Send" });
        await contains(".o-mail-Message", { count: 1 });
        await insertText(".o-mail-Composer-input", "def");
        await click(".o-mail-Composer button:enabled", { text: "Send" });
        await contains(".o-mail-Message", { count: 2 });
        await contains(".o-mail-Message-header"); // just 1, because 2nd message is squashed
    }
);

QUnit.test("Click on avatar opens its partner chat window", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "testPartner" });
    pyEnv["res.users"].create({
        partner_id: partnerId,
        name: "testPartner",
        email: "test@partner.com",
        phone: "+45687468",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "Test",
        attachment_ids: [],
        model: "res.partner",
        res_id: partnerId,
    });
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Message-sidebar .o-mail-Message-avatarContainer img");
    await click(".o-mail-Message-sidebar .o-mail-Message-avatarContainer img");
    await contains(".o_avatar_card");
    await contains(".o_card_user_infos > span", { text: "testPartner" });
    await contains(".o_card_user_infos > a", { text: "test@partner.com" });
    await contains(".o_card_user_infos > a", { text: "+45687468" });
});

QUnit.test("Can use channel command /who", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "my-channel",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/who");
    await click(".o-mail-Composer button:enabled", { text: "Send" });
    await contains(".o_mail_notification", { text: "You are alone in this channel." });
});

QUnit.test("sidebar: chat im_status rendering", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2, partnerId_3] = pyEnv["res.partner"].create([
        { im_status: "offline", name: "Partner1" },
        { im_status: "online", name: "Partner2" },
        { im_status: "away", name: "Partner3" },
    ]);
    pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId_1 }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId_2 }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId_3 }),
            ],
            channel_type: "chat",
        },
    ]);
    const { openDiscuss } = await start({ hasTimeControl: true });
    openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel-threadIcon", { count: 3 });
    await contains(".o-mail-DiscussSidebarChannel", {
        text: "Partner1",
        contains: [".o-mail-ThreadIcon div[title='Offline']"],
    });
    await contains(".o-mail-DiscussSidebarChannel", {
        text: "Partner2",
        contains: [".fa-circle.text-success"],
    });
    await contains(".o-mail-DiscussSidebarChannel", {
        text: "Partner3",
        contains: [".o-mail-ThreadIcon div[title='Away']"],
    });
});

QUnit.test("No load more when fetch below fetch limit of 30", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["res.partner"].create({});
    for (let i = 28; i >= 0; i--) {
        pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "not empty",
            date: "2019-04-20 10:00:00",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/discuss/channel/messages") {
                assert.strictEqual(args.limit, 30);
            }
        },
    });
    openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 29 });
    await contains("button", { count: 0, text: "Load More" });
});

QUnit.test("show date separator above mesages of similar date", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["res.partner"].create({});
    for (let i = 28; i >= 0; i--) {
        pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "not empty",
            date: "2019-04-20 10:00:00",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Message", {
        count: 29,
        after: [".o-mail-DateSection", { text: "April 20, 2019" }],
    });
});

QUnit.test("sidebar: chat custom name", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Marc Demo" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ custom_channel_name: "Marc", partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { text: "Marc" });
});

QUnit.test("reply to message from inbox (message linked to document) [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Refactoring" });
    const messageId = pyEnv["mail.message"].create({
        body: "<p>Test</p>",
        date: "2019-04-20 11:00:00",
        message_type: "comment",
        needaction: true,
        model: "res.partner",
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss, openFormView } = await start();
    openDiscuss();
    await contains(".o-mail-Message");
    await contains(".o-mail-Message-header small", { text: "on Refactoring" });
    await click("[title='Expand']");
    await click("[title='Reply']");
    await contains(".o-mail-Message.o-selected");
    await contains(".o-mail-Composer");
    await contains(".o-mail-Composer-coreHeader", { text: "on: Refactoring" });
    await insertText(".o-mail-Composer-input:focus", "Hello");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Composer", { count: 0 });
    await contains(".o-mail-Message:not(.o-selected)");
    await contains(".o_notification.border-info", { text: 'Message posted on "Refactoring"' });
    openFormView("res.partner", partnerId);
    await contains(".o-mail-Message", { count: 2 });
    await contains(".o-mail-Message-content", { text: "Hello" });
});

QUnit.test("Can reply to starred message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "RandomName" });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        starred_partner_ids: [pyEnv.currentPartnerId],
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    openDiscuss("mail.box_starred");
    await click("[title='Reply']");
    await contains(".o-mail-Composer-coreHeader", { text: "RandomName" });
    await insertText(".o-mail-Composer-input", "abc");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Composer-send", { count: 0 });
    await contains(".o_notification", { text: 'Message posted on "RandomName"' });
    await click(".o-mail-DiscussSidebarChannel", { text: "RandomName" });
    await contains(".o-mail-Message-content", { text: "abc" });
});

QUnit.test("Can reply to history message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "RandomName" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        history_partner_ids: [pyEnv.currentPartnerId],
        res_id: channelId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
        is_read: true,
    });
    const { openDiscuss } = await start();
    openDiscuss("mail.box_history");
    await click("[title='Reply']");
    await contains(".o-mail-Composer-coreHeader", { text: "RandomName" });
    await insertText(".o-mail-Composer-input", "abc");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Composer-send", { count: 0 });
    await contains(".o_notification", { text: 'Message posted on "RandomName"' });
    await click(".o-mail-DiscussSidebarChannel", { text: "RandomName" });
    await contains(".o-mail-Message-content", { text: "abc" });
});

QUnit.test("receive new needaction messages", async () => {
    const { openDiscuss, pyEnv } = await start();
    openDiscuss();
    await contains("button.o-active", { text: "Inbox", contains: [".badge", { count: 0 }] });
    await contains(".o-mail-Thread .o-mail-Message", { count: 0 });

    // simulate receiving a new needaction message
    pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.message/inbox", {
        body: "not empty 1",
        id: 100,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        model: "res.partner",
        res_id: 20,
    });
    await contains("button", { text: "Inbox", contains: [".badge", { text: "1" }] });
    await contains(".o-mail-Message");
    await contains(".o-mail-Message-content", { text: "not empty 1" });

    // simulate receiving another new needaction message
    pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.message/inbox", {
        body: "not empty 2",
        id: 101,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        model: "res.partner",
        res_id: 20,
    });
    await contains("button", { text: "Inbox", contains: [".badge", { text: "2" }] });
    await contains(".o-mail-Message", { count: 2 });
    await contains(".o-mail-Message-content", { text: "not empty 1" });
    await contains(".o-mail-Message-content", { text: "not empty 2" });
});

QUnit.test("basic rendering", async () => {
    const { openDiscuss } = await start();
    openDiscuss();
    await contains(".o-mail-DiscussSidebar");
    await contains(".o-mail-Discuss-content");
    await contains(".o-mail-Discuss-content .o-mail-Thread");
});

QUnit.test("basic rendering: sidebar", async () => {
    const { openDiscuss } = await start();
    openDiscuss();
    await contains(".o-mail-DiscussSidebar button", { text: "Inbox" });
    await contains(".o-mail-DiscussSidebar button", { text: "Starred" });
    await contains(".o-mail-DiscussSidebar button", { text: "History" });
    await contains(".o-mail-DiscussSidebarCategory", { count: 2 });
    await contains(".o-mail-DiscussSidebarCategory-channel", { text: "Channels" });
    await contains(".o-mail-DiscussSidebarCategory-chat", { text: "Direct messages" });
});

QUnit.test("sidebar: Inbox should have icon", async () => {
    const { openDiscuss } = await start();
    openDiscuss();
    await contains("button", { text: "Inbox", contains: [".fa-inbox"] });
});

QUnit.test("sidebar: default active inbox", async () => {
    const { openDiscuss } = await start();
    openDiscuss();
    await contains("button.o-active", { text: "Inbox" });
});

QUnit.test("sidebar: change active", async () => {
    const { openDiscuss } = await start();
    openDiscuss();
    await contains("button.o-active", { text: "Inbox" });
    await contains("button:not(.o-active)", { text: "Starred" });
    await click("button", { text: "Starred" });
    await contains("button:not(.o-active)", { text: "Inbox" });
    await contains("button.o-active", { text: "Starred" });
});

QUnit.test("sidebar: basic channel rendering", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { text: "General" });
    await contains(".o-mail-DiscussSidebarChannel img[data-alt='Thread Image']");
    await contains(".o-mail-DiscussSidebarChannel .o-mail-DiscussSidebarChannel-commands.d-none");
    await contains(
        ".o-mail-DiscussSidebarChannel .o-mail-DiscussSidebarChannel-commands i[title='Channel settings']"
    );
    await contains(
        ".o-mail-DiscussSidebarChannel .o-mail-DiscussSidebarChannel-commands div[title='Leave this channel']"
    );
});

QUnit.test("channel become active", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel");
    await contains(".o-mail-DiscussSidebarChannel.o-active", { count: 0 });
    await click(".o-mail-DiscussSidebarChannel");
    await contains(".o-mail-DiscussSidebarChannel.o-active");
});

QUnit.test("channel become active - show composer in discuss content", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    openDiscuss();
    await click(".o-mail-DiscussSidebarChannel");
    await contains(".o-mail-Thread");
    await contains(".o-mail-Composer");
});

QUnit.test("sidebar: channel rendering with needaction counter", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", {
        contains: [
            ["span", { text: "general" }],
            [".badge", { text: "1" }],
        ],
    });
});

QUnit.test("sidebar: chat rendering with unread counter", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 100, partner_id: pyEnv.currentPartnerId }), // weak test, relies on hardcoded value for message_unread_counter but the messages do not actually exist
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", {
        contains: [
            [".badge", { text: "100" }],
            [".o-mail-DiscussSidebarChannel-commands", { text: "Unpin Conversation", count: 0 }], // weak test, no guarantee this selector is valid in the first place
        ],
    });
});

QUnit.test("initially load messages from inbox", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "comment",
        model: "discuss.channel",
        needaction_partner_ids: [pyEnv.currentPartnerId],
        needaction: true,
        res_id: channelId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/inbox/messages") {
                step("/discuss/inbox/messages");
                assert.strictEqual(args.limit, 30);
            }
        },
    });
    openDiscuss();
    await contains(".o-mail-Message");
    await assertSteps(["/discuss/inbox/messages"]);
});

QUnit.test("default active id on mailbox", async () => {
    const { openDiscuss } = await start();
    openDiscuss("mail.box_starred");
    await contains("button.o-active", { text: "Starred" });
});

QUnit.test("basic top bar rendering", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    openDiscuss();
    await contains("button:disabled", { text: "Mark all read" });
    await contains(".o-mail-Discuss-threadName", { value: "Inbox" });

    await click("button", { text: "Starred" });
    await contains("button:disabled", { text: "Unstar all" });
    await contains(".o-mail-Discuss-threadName", { value: "Starred" });

    await click(".o-mail-DiscussSidebarChannel", { text: "General" });
    await contains(".o-mail-Discuss-header button[title='Add Users']");
    await contains(".o-mail-Discuss-threadName", { value: "General" });
});

QUnit.test("rendering of inbox message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Refactoring" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    openDiscuss();
    await contains(".o-mail-Message");
    await contains(".o-mail-Message-header small", { text: "on Refactoring" });
    await contains(".o-mail-Message-actions i", { count: 4 });
    await contains("[title='Add a Reaction']");
    await contains("[title='Mark as Todo']");
    await contains("[title='Mark as Read']");
    await click("[title='Expand']");
    await contains(".o-mail-Message-actions i", { count: 5 });
    await contains("[title='Reply']");
    await contains("[title='Mark as Todo']");
    await contains("[title='Mark as Read']");
    await contains("[title='Expand']");
});

QUnit.test("Unfollow message", async function () {
    const pyEnv = await startServer();
    const currentPartnerId = pyEnv.currentPartnerId;
    const [threadFollowedId, threadNotFollowedId] = pyEnv["res.partner"].create([
        {
            name: "Thread followed",
        },
        {
            name: "Thread not followed",
        },
    ]);
    pyEnv["mail.followers"].create({
        partner_id: currentPartnerId,
        res_id: threadFollowedId,
        res_model: "res.partner",
    });
    for (const threadId of [threadFollowedId, threadFollowedId, threadNotFollowedId]) {
        const messageId = pyEnv["mail.message"].create({
            body: "not empty",
            model: "res.partner",
            needaction: true,
            needaction_partner_ids: [currentPartnerId],
            res_id: threadId,
        });
        pyEnv["mail.notification"].create({
            mail_message_id: messageId,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: currentPartnerId,
        });
    }
    const { openDiscuss } = await start();
    openDiscuss();
    await contains(".o-mail-Message", { count: 3 });
    await click(":nth-child(1 of .o-mail-Message) button[title='Expand']");
    await contains(":nth-child(1 of .o-mail-Message)", {
        contains: [
            [".o-mail-Message-header small", { text: "on Thread followed" }],
            [".o-mail-Message-moreMenu"],
            ["span[title='Unfollow']"],
        ],
    });
    await click(":nth-child(2 of .o-mail-Message) button[title='Expand']");
    await contains(":nth-child(2 of .o-mail-Message)", {
        contains: [
            [".o-mail-Message-header small", { text: "on Thread followed" }],
            [".o-mail-Message-moreMenu"],
            ["span[title='Unfollow']"],
        ],
    });
    await click(":nth-child(3 of .o-mail-Message) button[title='Expand']");
    await contains(":nth-child(3 of .o-mail-Message)", {
        contains: [
            [".o-mail-Message-header small", { text: "on Thread not followed" }],
            [".o-mail-Message-moreMenu"],
            ["span[title='Unfollow']", { count: 0 }],
        ],
    });
    await click(":nth-child(1 of .o-mail-Message) button[title='Expand']");
    await click(":nth-child(1 of .o-mail-Message) span[title='Unfollow']");
    await contains(".o-mail-Message", { count: 2 }); // Unfollowing message 0 marks it as read -> Message removed
    await click(":nth-child(1 of .o-mail-Message) button[title='Expand']");
    await contains(":nth-child(1 of .o-mail-Message)", {
        contains: [
            [".o-mail-Message-header small", { text: "on Thread followed" }],
            [".o-mail-Message-moreMenu"],
            ["span[title='Unfollow']", { count: 0 }],
        ],
    });
    await click(":nth-child(2 of .o-mail-Message) button[title='Expand']");
    await contains(":nth-child(2 of .o-mail-Message)", {
        contains: [
            [".o-mail-Message-header small", { text: "on Thread not followed" }],
            [".o-mail-Message-moreMenu"],
            ["span[title='Unfollow']", { count: 0 }],
        ],
    });
});

QUnit.test('messages marked as read move to "History" mailbox', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "other-disco" });
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            body: "not empty",
            model: "discuss.channel",
            needaction: true,
            res_id: channelId,
        },
        {
            body: "not empty",
            model: "discuss.channel",
            needaction: true,
            res_id: channelId,
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId_1,
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        },
        {
            mail_message_id: messageId_2,
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        },
    ]);
    const { openDiscuss } = await start();
    openDiscuss("mail.box_history");
    await contains("button.o-active", { text: "History" });
    await contains(".o-mail-Thread h4", { text: "No history messages" });

    await click("button", { text: "Inbox" });
    await contains("button.o-active", { text: "Inbox" });
    await contains(".o-mail-Thread h4", { count: 0, text: "Congratulations, your inbox is empty" });

    await contains(".o-mail-Thread .o-mail-Message", { count: 2 });

    await click("button", { text: "Mark all read" });
    await contains("button.o-active", { text: "Inbox" });
    await contains(".o-mail-Thread h4", { text: "Congratulations, your inbox is empty" });

    await click("button", { text: "History" });
    await contains("button.o-active", { text: "History" });
    await contains(".o-mail-Thread h4", { count: 0, text: "No history messages" });

    await contains(".o-mail-Thread .o-mail-Message", { count: 2 });
});

QUnit.test(
    'mark a single message as read should only move this message to "History" mailbox',
    async () => {
        const pyEnv = await startServer();
        const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
            {
                body: "not empty 1",
                needaction: true,
                needaction_partner_ids: [pyEnv.currentPartnerId],
            },
            {
                body: "not empty 2",
                needaction: true,
                needaction_partner_ids: [pyEnv.currentPartnerId],
            },
        ]);
        pyEnv["mail.notification"].create([
            {
                mail_message_id: messageId_1,
                notification_type: "inbox",
                res_partner_id: pyEnv.currentPartnerId,
            },
            {
                mail_message_id: messageId_2,
                notification_type: "inbox",
                res_partner_id: pyEnv.currentPartnerId,
            },
        ]);
        const { openDiscuss } = await start();
        openDiscuss("mail.box_history");
        await contains("button.o-active", { text: "History" });
        await contains(".o-mail-Thread h4", { text: "No history messages" });
        await click("button", { text: "Inbox" });
        await contains("button.o-active", { text: "Inbox" });
        await contains(".o-mail-Message", { count: 2 });
        await click("[title='Mark as Read']", {
            parent: [".o-mail-Message", { text: "not empty 1" }],
        });
        await contains(".o-mail-Message");
        await contains(".o-mail-Message-content", { text: "not empty 2" });
        await click("button", { text: "History" });
        await contains("button.o-active", { text: "History" });
        await contains(".o-mail-Message");
        await contains(".o-mail-Message-content", { text: "not empty 1" });
    }
);

QUnit.test('all messages in "Inbox" in "History" after marked all as read', async () => {
    const pyEnv = await startServer();
    for (let i = 0; i < 40; i++) {
        const messageId = pyEnv["mail.message"].create({
            body: "not empty",
            needaction: true,
        });
        pyEnv["mail.notification"].create({
            mail_message_id: messageId,
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        });
    }
    const { openDiscuss } = await start();
    openDiscuss();
    await contains(".o-mail-Message", { count: 30 });
    await click("button", { text: "Mark all read" });
    await contains(".o-mail-Message", { count: 0 });
    await click("button", { text: "History" });
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await scroll(".o-mail-Thread", 0);
    await contains(".o-mail-Message", { count: 40 });
});

QUnit.test("post a simple message", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/message/post") {
                step("message_post");
                assert.strictEqual(args.thread_model, "discuss.channel");
                assert.strictEqual(args.thread_id, channelId);
                assert.strictEqual(args.post_data.body, "Test");
                assert.strictEqual(args.post_data.message_type, "comment");
                assert.strictEqual(args.post_data.subtype_xmlid, "mail.mt_comment");
            }
        },
    });
    openDiscuss(channelId);
    await contains(".o-mail-Thread", { text: "There are no messages in this conversation." });
    await contains(".o-mail-Message", { count: 0 });
    await insertText(".o-mail-Composer-input", "Test");
    await click(".o-mail-Composer-send:enabled");
    await assertSteps(["message_post"]);
    await contains(".o-mail-Composer-input", { value: "" });
    await contains(".o-mail-Message-author", { text: "Mitchell Admin" });
    await contains(".o-mail-Message-content", { text: "Test" });
});

QUnit.test("starred: unstar all", async () => {
    const pyEnv = await startServer();
    pyEnv["mail.message"].create([
        { body: "not empty", starred_partner_ids: [pyEnv.currentPartnerId] },
        { body: "not empty", starred_partner_ids: [pyEnv.currentPartnerId] },
    ]);
    const { openDiscuss } = await start();
    openDiscuss("mail.box_starred");
    await contains(".o-mail-Message", { count: 2 });
    await contains("button", { text: "Starred", contains: [".badge", { text: "2" }] });
    await click("button:enabled", { text: "Unstar all" });
    await contains("button", { text: "Starred", contains: [".badge", { count: 0 }] });
    await contains(".o-mail-Message", { count: 0 });
    await contains("button:disabled", { text: "Unstar all" });
});

QUnit.test("auto-focus composer on opening thread [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo User" });
    pyEnv["discuss.channel"].create([
        { name: "General" },
        {
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "chat",
        },
    ]);
    const { openDiscuss } = await start();
    openDiscuss();
    await contains("button.o-active", { text: "Inbox" });
    await contains(".o-mail-DiscussSidebarChannel:not(.o-active)", { text: "General" });
    await contains(".o-mail-DiscussSidebarChannel:not(.o-active)", { text: "Demo User" });
    await contains(".o-mail-Composer", { count: 0 });

    await click(".o-mail-DiscussSidebarChannel", { text: "General" });
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "General" });
    await contains(".o-mail-Composer-input:focus");
    await click(".o-mail-DiscussSidebarChannel", { text: "Demo User" });
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "Demo User" });
    await contains(".o-mail-Composer-input:focus");
});

QUnit.test(
    "receive new chat message: out of odoo focus (notification, channel)",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
        const { env, openDiscuss } = await start({
            services: {
                presence: makeFakePresenceService({ isOdooFocused: () => false }),
            },
        });
        openDiscuss();
        patchWithCleanup(env.services["title"], {
            setParts(parts) {
                if (parts._chat) {
                    step("set_title_part");
                    assert.strictEqual(parts._chat, "1 Message");
                }
            },
        });
        const channel = pyEnv["discuss.channel"].searchRead([["id", "=", channelId]])[0];
        // simulate receiving a new message with odoo out-of-focused
        pyEnv["bus.bus"]._sendone(channel, "discuss.channel/new_message", {
            id: channelId,
            message: {
                id: 126,
                model: "discuss.channel",
                res_id: channelId,
            },
        });
        await assertSteps(["set_title_part"]);
    }
);

QUnit.test("receive new chat message: out of odoo focus (notification, chat)", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    const { env, openDiscuss } = await start({
        services: {
            presence: makeFakePresenceService({ isOdooFocused: () => false }),
        },
    });
    openDiscuss();
    patchWithCleanup(env.services["title"], {
        setParts(parts) {
            if (parts._chat) {
                step("set_title_part");
                assert.strictEqual(parts._chat, "1 Message");
            }
        },
    });
    const channel = pyEnv["discuss.channel"].searchRead([["id", "=", channelId]])[0];
    // simulate receiving a new message with odoo out-of-focused
    pyEnv["bus.bus"]._sendone(channel, "discuss.channel/new_message", {
        id: channelId,
        message: {
            id: 126,
            model: "discuss.channel",
            res_id: channelId,
        },
    });
    await assertSteps(["set_title_part"]);
});

QUnit.test("no out-of-focus notification on receiving self messages in chat", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    const { env, openDiscuss } = await start({
        services: {
            presence: makeFakePresenceService({ isOdooFocused: () => false }),
        },
    });
    openDiscuss();
    patchWithCleanup(env.services["title"], {
        setParts(parts) {
            if (parts._chat) {
                step("set_title_part");
            }
        },
    });
    const channel = pyEnv["discuss.channel"].searchRead([["id", "=", channelId]])[0];
    // simulate receiving a new message of self with odoo out-of-focused
    pyEnv["bus.bus"]._sendone(channel, "discuss.channel/new_message", {
        id: channelId,
        message: {
            author: { id: pyEnv.currentPartnerId, type: "partner" },
            id: 126,
            model: "discuss.channel",
            res_id: channelId,
        },
    });
    await waitNotifications([env, "discuss.channel/new_message"]);
    // weak test, no guarantee to wait long enough for the potential step to trigger
    await nextTick();
    assertSteps([]);
});

QUnit.test("receive new chat messages: out of odoo focus (tab title)", async (assert) => {
    let stepCount = 0;
    const pyEnv = await startServer();
    const [channelId_1, channelId_2] = pyEnv["discuss.channel"].create([
        { channel_type: "chat" },
        { channel_type: "chat" },
    ]);
    const { env, openDiscuss } = await start({
        services: {
            presence: makeFakePresenceService({ isOdooFocused: () => false }),
        },
    });
    openDiscuss();
    patchWithCleanup(env.services["title"], {
        setParts(parts) {
            if (!parts._chat) {
                return;
            }
            stepCount++;
            step("set_title_part");
            if (stepCount === 1) {
                assert.strictEqual(parts._chat, "1 Message");
            }
            if (stepCount === 2) {
                assert.strictEqual(parts._chat, "2 Messages");
            }
            if (stepCount === 3) {
                assert.strictEqual(parts._chat, "3 Messages");
            }
        },
    });
    const channel_1 = pyEnv["discuss.channel"].searchRead([["id", "=", channelId_1]])[0];
    // simulate receiving a new message in chat 1 with odoo out-of-focused
    pyEnv["bus.bus"]._sendone(channel_1, "discuss.channel/new_message", {
        id: channelId_1,
        message: {
            id: 126,
            model: "discuss.channel",
            res_id: channelId_1,
        },
    });
    await assertSteps(["set_title_part"]);

    const channel_2 = pyEnv["discuss.channel"].searchRead([["id", "=", channelId_2]])[0];
    // simulate receiving a new message in chat 2 with odoo out-of-focused
    pyEnv["bus.bus"]._sendone(channel_2, "discuss.channel/new_message", {
        id: channelId_2,
        message: {
            id: 127,
            model: "discuss.channel",
            res_id: channelId_2,
        },
    });
    await assertSteps(["set_title_part"]);

    // simulate receiving another new message in chat 2 with odoo focused
    pyEnv["bus.bus"]._sendone(channel_2, "discuss.channel/new_message", {
        id: channelId_2,
        message: {
            id: 128,
            model: "discuss.channel",
            res_id: channelId_2,
        },
    });
    await assertSteps(["set_title_part"]);
});

QUnit.test("should auto-pin chat when receiving a new DM", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ is_pinned: false, partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { env, openDiscuss } = await start();
    openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory-chat");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0, text: "Demo" });

    // simulate receiving the first message on channel 11
    pyEnv.withUser(userId, () =>
        env.services.rpc("/mail/message/post", {
            post_data: { body: "new message", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-DiscussSidebarChannel", { text: "Demo" });
});

QUnit.test("'Add Users' button should be displayed in the topbar of channels", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains("button[title='Add Users']");
});

QUnit.test("'Add Users' button should be displayed in the topbar of chats", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Marc Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains("button[title='Add Users']");
});

QUnit.test("'Add Users' button should be displayed in the topbar of groups", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "group",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains("button[title='Add Users']");
});

QUnit.test("'Add Users' button should not be displayed in the topbar of mailboxes", async () => {
    const { openDiscuss } = await start();
    openDiscuss("mail.box_starred");
    await contains("button", { text: "Unstar all" });
    await contains("button[title='Add Users']", { count: 0 });
});

QUnit.test(
    "Thread avatar image is displayed in top bar of channels of type 'channel' limited to a group",
    async () => {
        const pyEnv = await startServer();
        const groupId = pyEnv["res.groups"].create({ name: "testGroup" });
        const channelId = pyEnv["discuss.channel"].create({
            channel_type: "channel",
            name: "string",
            group_public_id: groupId,
        });
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await contains(".o-mail-Discuss-header .o-mail-Discuss-threadAvatar");
    }
);

QUnit.test(
    "Thread avatar image is displayed in top bar of channels of type 'channel' not limited to any group",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            channel_type: "channel",
            name: "string",
            group_public_id: false,
        });
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await contains(".o-mail-Discuss-header .o-mail-Discuss-threadAvatar");
    }
);

QUnit.test(
    "Partner IM status is displayed as thread icon in top bar of channels of type 'chat'",
    async () => {
        const pyEnv = await startServer();
        const [partnerId_1, partnerId_2, partnerId_3, partnerId_4] = pyEnv["res.partner"].create([
            { im_status: "online", name: "Michel Online" },
            { im_status: "offline", name: "Jacqueline Offline" },
            { im_status: "away", name: "Nabuchodonosor Idle" },
            { im_status: "im_partner", name: "Robert Fired" },
        ]);
        pyEnv["discuss.channel"].create([
            {
                channel_member_ids: [
                    Command.create({ partner_id: pyEnv.currentPartnerId }),
                    Command.create({ partner_id: partnerId_1 }),
                ],
                channel_type: "chat",
            },
            {
                channel_member_ids: [
                    Command.create({ partner_id: pyEnv.currentPartnerId }),
                    Command.create({ partner_id: partnerId_2 }),
                ],
                channel_type: "chat",
            },
            {
                channel_member_ids: [
                    Command.create({ partner_id: pyEnv.currentPartnerId }),
                    Command.create({ partner_id: partnerId_3 }),
                ],
                channel_type: "chat",
            },
            {
                channel_member_ids: [
                    Command.create({ partner_id: pyEnv.currentPartnerId }),
                    Command.create({ partner_id: partnerId_4 }),
                ],
                channel_type: "chat",
            },
            {
                channel_member_ids: [
                    Command.create({ partner_id: pyEnv.currentPartnerId }),
                    Command.create({ partner_id: TEST_USER_IDS.odoobotId }),
                ],
                channel_type: "chat",
            },
        ]);
        const { openDiscuss } = await start();
        openDiscuss();
        await click(".o-mail-DiscussSidebarChannel", { text: "Michel Online" });
        await contains(".o-mail-Discuss-header .o-mail-ImStatus [title='Online']");
        await click(".o-mail-DiscussSidebarChannel", { text: "Jacqueline Offline" });
        await contains(".o-mail-Discuss-header .o-mail-ImStatus [title='Offline']");
        await click(".o-mail-DiscussSidebarChannel", { text: "Nabuchodonosor Idle" });
        await contains(".o-mail-Discuss-header .o-mail-ImStatus [title='Idle']");
        await click(".o-mail-DiscussSidebarChannel", { text: "Robert Fired" });
        await contains(".o-mail-Discuss-header .o-mail-ImStatus [title='No IM status available']");
        await click(".o-mail-DiscussSidebarChannel", { text: "OdooBot" });
        await contains(".o-mail-Discuss-header .o-mail-ImStatus [title='Bot']");
    }
);

QUnit.test("Thread avatar image is displayed in top bar of channels of type 'group'", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "group" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Discuss-header .o-mail-Discuss-threadAvatar");
});

QUnit.test("Do not trigger chat name server update when it is unchanged", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    const { openDiscuss } = await start({
        mockRPC(route, args, originalRPC) {
            if (args.method === "channel_set_custom_name") {
                step(args.method);
            }
            return originalRPC(route, args);
        },
    });
    openDiscuss(channelId);
    await insertText("input.o-mail-Discuss-threadName:enabled", "Mitchell Admin", {
        replace: true,
    });
    triggerHotkey("Enter");
    assertSteps([]);
});

QUnit.test(
    "Do not trigger channel description server update when channel has no description and editing to empty description",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            create_uid: pyEnv.currentUserId,
            name: "General",
        });
        const { openDiscuss } = await start({
            mockRPC(route, args, originalRPC) {
                if (args.method === "channel_change_description") {
                    step(args.method);
                }
                return originalRPC(route, args);
            },
        });
        openDiscuss(channelId);
        await insertText("input.o-mail-Discuss-threadDescription", "");
        triggerHotkey("Enter");
        assertSteps([]);
    }
);

QUnit.test("Channel is added to discuss after invitation", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Harry" });
    const partnerId = pyEnv["res.partner"].create({ name: "Harry", user_ids: [userId] });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [Command.create({ partner_id: partnerId })],
    });
    const { env, openDiscuss } = await start();
    openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory-channel");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0, text: "General" });

    pyEnv.withUser(userId, () =>
        env.services.orm.call("discuss.channel", "add_members", [[channelId]], {
            partner_ids: [pyEnv.adminPartnerId],
        })
    );
    await contains(".o-mail-DiscussSidebarChannel", { text: "General" });
    await contains(".o_notification.border-info", { text: "You have been invited to #General" });
});

QUnit.test("select another mailbox", async () => {
    patchUiSize({ height: 360, width: 640 });
    const { openDiscuss } = await start();
    openDiscuss();
    await contains(".o-mail-Discuss");
    await contains(".o-mail-Discuss-threadName", { value: "Inbox" });
    await click("button", { text: "Starred" });
    await contains("button:disabled", { text: "Unstar all" });
    await contains(".o-mail-Discuss-threadName", { value: "Starred" });
});

QUnit.test('auto-select "Inbox nav bar" when discuss had inbox as active thread', async () => {
    patchUiSize({ height: 360, width: 640 });
    const { openDiscuss } = await start();
    openDiscuss();
    await contains(".o-mail-Discuss-threadName", { value: "Inbox" });
    await contains(".o-mail-MessagingMenu-navbar button.fw-bolder", { text: "Mailboxes" });
    await contains("button.active.o-active", { text: "Inbox" });
    await contains("h4", { text: "Congratulations, your inbox is empty" });
});

QUnit.test(
    "composer should be focused automatically after clicking on the send button [REQUIRE FOCUS]",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "test" });
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await insertText(".o-mail-Composer-input", "Dummy Message");
        await click(".o-mail-Composer-send:enabled");
        assert.strictEqual(document.activeElement, $(".o-mail-Composer-input")[0]);
    }
);

QUnit.test(
    "mark channel as seen if last message is visible when switching channels when the previous channel had a more recent last message than the current channel [REQUIRE FOCUS]",
    async () => {
        const pyEnv = await startServer();
        const [channelId_1, channelId_2] = pyEnv["discuss.channel"].create([
            {
                channel_member_ids: [
                    [
                        0,
                        0,
                        {
                            message_unread_counter: 1,
                            partner_id: pyEnv.currentPartnerId,
                        },
                    ],
                ],
                name: "Bla",
            },
            {
                channel_member_ids: [
                    [
                        0,
                        0,
                        {
                            message_unread_counter: 1,
                            partner_id: pyEnv.currentPartnerId,
                        },
                    ],
                ],
                name: "Blu",
            },
        ]);
        pyEnv["mail.message"].create([
            {
                body: "oldest message",
                model: "discuss.channel",
                res_id: channelId_1,
            },
            {
                body: "newest message",
                model: "discuss.channel",
                res_id: channelId_2,
            },
        ]);
        const { openDiscuss } = await start();
        openDiscuss(channelId_2);
        await click("button", { text: "Bla" });
        await contains(".o-unread", { count: 0 });
    }
);

QUnit.test(
    "warning on send with shortcut when attempting to post message with still-uploading attachments",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "test" });
        const { openDiscuss } = await start({
            async mockRPC(route) {
                if (route === "/mail/attachment/upload") {
                    // simulates attachment is never finished uploading
                    await new Promise(() => {});
                }
            },
        });
        openDiscuss(channelId);
        await contains(".o-mail-Composer input[type=file]");
        const file = await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        });
        await editInput(document.body, ".o-mail-Composer input[type=file]", [file]);
        await contains(".o-mail-AttachmentCard");
        await contains(".o-mail-AttachmentCard.o-isUploading");
        await contains(".o-mail-Composer-send:disabled");
        // Try to send message
        triggerHotkey("Enter");
        await contains(".o_notification.border-warning", {
            text: "Please wait while the file is uploading.",
        });
    }
);

QUnit.test("new messages separator [REQUIRE FOCUS]", async () => {
    // this test requires several messages so that the last message is not
    // visible. This is necessary in order to display 'new messages' and not
    // remove from DOM right away from seeing last message.
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Foreigner partner" });
    const userId = pyEnv["res.users"].create({
        name: "Foreigner user",
        partner_id: partnerId,
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: partnerId }),
            Command.create({ partner_id: pyEnv.currentPartnerId }),
        ],
    });
    let lastMessageId;
    for (let i = 1; i <= 25; i++) {
        lastMessageId = pyEnv["mail.message"].create({
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", pyEnv.currentPartnerId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], { seen_message_id: lastMessageId });
    const { env, openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 25 });
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });
    await contains(".o-mail-Discuss-content .o-mail-Thread", { scroll: "bottom" });
    await scroll(".o-mail-Discuss-content .o-mail-Thread", 0);
    // composer is focused by default, we remove that focus
    $(".o-mail-Composer-input")[0].blur();
    // simulate receiving a message
    pyEnv.withUser(userId, () =>
        env.services.rpc("/mail/message/post", {
            post_data: { body: "hu", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message", { count: 26 });
    await contains(".o-mail-Thread-newMessage hr + span", { text: "New messages" });
    await scroll(".o-mail-Discuss-content .o-mail-Thread", "bottom");
    await contains(".o-mail-Thread-newMessage hr + span", { text: "New messages" });
    await focus(".o-mail-Composer-input");
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });
});

QUnit.test("failure on loading messages should display error", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/discuss/channel/messages") {
                return Promise.reject();
            }
        },
    });
    openDiscuss(channelId);
    await contains(".o-mail-Thread", { text: "An error occurred while fetching messages." });
});

QUnit.test("failure on loading messages should prompt retry button", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/discuss/channel/messages") {
                return Promise.reject();
            }
        },
    });
    openDiscuss(channelId);
    await contains("button", { text: "Click here to retry" });
});

QUnit.test(
    "failure on loading more messages should display error and prompt retry button",
    async () => {
        // first call needs to be successful as it is the initial loading of messages
        // second call comes from load more and needs to fail in order to show the error alert
        // any later call should work so that retry button and load more clicks would now work
        let messageFetchShouldFail = false;
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            channel_type: "channel",
            name: "General",
        });
        pyEnv["mail.message"].create(
            [...Array(60).keys()].map(() => {
                return {
                    body: "coucou",
                    model: "discuss.channel",
                    res_id: channelId,
                };
            })
        );
        const { openDiscuss } = await start({
            async mockRPC(route, args) {
                if (route === "/discuss/channel/messages" && messageFetchShouldFail) {
                    return Promise.reject();
                }
            },
        });
        openDiscuss(channelId);
        await contains(".o-mail-Message", { count: 30 });
        messageFetchShouldFail = true;
        await click("button", { text: "Load More" });
        await contains(".o-mail-Thread", { text: "An error occurred while fetching messages." });
        await contains("button", { text: "Click here to retry" });
        await contains("button", { count: 0, text: "Load More" });
    }
);

QUnit.test(
    "Retry loading more messages on failed load more messages should load more messages",
    async () => {
        // first call needs to be successful as it is the initial loading of messages
        // second call comes from load more and needs to fail in order to show the error alert
        // any later call should work so that retry button and load more clicks would now work
        let messageFetchShouldFail = false;
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            channel_type: "channel",
            name: "General",
        });
        pyEnv["mail.message"].create(
            [...Array(90).keys()].map(() => {
                return {
                    body: "coucou",
                    model: "discuss.channel",
                    res_id: channelId,
                };
            })
        );
        const { openDiscuss } = await start({
            async mockRPC(route, args) {
                if (route === "/discuss/channel/messages") {
                    if (messageFetchShouldFail) {
                        return Promise.reject();
                    }
                }
            },
        });
        openDiscuss(channelId);
        await contains(".o-mail-Message", { count: 30 });
        messageFetchShouldFail = true;
        await click("button", { text: "Load More" });
        messageFetchShouldFail = false;
        await click("button", { text: "Click here to retry" });
        await contains(".o-mail-Message", { count: 60 });
    }
);

QUnit.test("composer state: attachments save and restore", async () => {
    const pyEnv = await startServer();
    const [channelId] = pyEnv["discuss.channel"].create([{ name: "General" }, { name: "Special" }]);
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(
        ".o-mail-Composer:has(textarea[placeholder='Message #General…']) input[type=file]"
    );
    // Add attachment in a message for #general
    const file = await createFile({
        content: "hello, world",
        contentType: "text/plain",
        name: "text.txt",
    });
    await editInput(
        document.body,
        ".o-mail-Composer:has(textarea[placeholder='Message #General…']) input[type=file]",
        [file]
    );
    await contains(".o-mail-Composer .o-mail-AttachmentCard:not(.o-isUploading)");
    // Switch to #special
    await click("button", { text: "Special" });
    // Attach files in a message for #special
    const files = await Promise.all([
        createFile({
            content: "hello2, world",
            contentType: "text/plain",
            name: "text2.txt",
        }),
        createFile({
            content: "hello3, world",
            contentType: "text/plain",
            name: "text3.txt",
        }),
        createFile({
            content: "hello4, world",
            contentType: "text/plain",
            name: "text4.txt",
        }),
    ]);
    await contains(
        ".o-mail-Composer:has(textarea[placeholder='Message #Special…']) input[type=file]"
    );
    await editInput(
        document.body,
        ".o-mail-Composer:has(textarea[placeholder='Message #Special…']) input[type=file]",
        files
    );
    await contains(".o-mail-Composer .o-mail-AttachmentCard:not(.o-isUploading)", { count: 3 });
    // Switch back to #general
    await click("button", { text: "General" });
    await contains(".o-mail-Composer .o-mail-AttachmentCard");
    await contains(".o-mail-AttachmentCard", { text: "text.txt" });
    // Switch back to #special
    await click("button", { text: "Special" });
    await contains(".o-mail-Composer .o-mail-AttachmentCard", { count: 3 });
    await contains(".o-mail-AttachmentCard", { text: "text2.txt" });
    await contains(".o-mail-AttachmentCard", { text: "text3.txt" });
    await contains(".o-mail-AttachmentCard", { text: "text4.txt" });
});

QUnit.test(
    "sidebar: cannot unpin channel group_based_subscription: mandatorily pinned",
    async () => {
        const pyEnv = await startServer();
        pyEnv["discuss.channel"].create({
            name: "General",
            channel_member_ids: [
                Command.create({ is_pinned: false, partner_id: pyEnv.currentPartnerId }),
            ],
            group_based_subscription: true,
        });
        const { openDiscuss } = await start();
        openDiscuss();
        await contains("button", { text: "General" });
        await contains("div[title='Leave this channel']", { count: 0 });
    }
);

QUnit.test("restore thread scroll position", async () => {
    const pyEnv = await startServer();
    const [channelId_1, channelId_2] = pyEnv["discuss.channel"].create([
        { name: "Channel1" },
        { name: "Channel2" },
    ]);
    for (let i = 1; i <= 25; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId_1,
        });
    }
    for (let i = 1; i <= 24; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId_2,
        });
    }
    const { openDiscuss } = await start();
    openDiscuss(channelId_1);
    await contains(".o-mail-Message", { count: 25 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await scroll(".o-mail-Thread", 0);
    await click("button", { text: "Channel2" });
    await contains(".o-mail-Message", { count: 24 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await click("button", { text: "Channel1" });
    await contains(".o-mail-Message", { count: 25 });
    await contains(".o-mail-Thread", { scroll: 0 });
    await click("button", { text: "Channel2" });
    await contains(".o-mail-Message", { count: 24 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
});

QUnit.test("Message shows up even if channel data is incomplete", async () => {
    const { env, openDiscuss, pyEnv } = await start();
    openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory-chat");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
    const correspondentUserId = pyEnv["res.users"].create({ name: "Albert" });
    const correspondentPartnerId = pyEnv["res.partner"].create({
        name: "Albert",
        user_ids: [correspondentUserId],
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            [
                0,
                0,
                {
                    is_pinned: true,
                    partner_id: pyEnv.currentPartnerId,
                },
            ],
            Command.create({ partner_id: correspondentPartnerId }),
        ],
        channel_type: "chat",
    });
    await pyEnv.withUser(correspondentUserId, () =>
        env.services.rpc("/discuss/channel/notify_typing", {
            is_typing: true,
            channel_id: channelId,
        })
    );
    await pyEnv.withUser(correspondentUserId, () =>
        env.services.rpc("/mail/message/post", {
            post_data: { body: "hello world", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await click(".o-mail-DiscussSidebarChannel", { text: "Albert" });
    await contains(".o-mail-Message-content", { text: "hello world" });
});

QUnit.test("Correct breadcrumb when open discuss from chat window then see settings", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await click(".o_main_navbar i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "General" });
    await click("[title='Open Actions Menu']");
    await click("[title='Open in Discuss']");
    await click("[title='Channel settings']", {
        parent: [".o-mail-DiscussSidebarChannel", { text: "General" }],
    });
    await contains(".o_breadcrumb", { text: "DiscussGeneral" });
});

QUnit.test(
    "Chatter notification in messaging menu should open the form view even when discuss app is open",
    async () => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "TestPartner" });
        const messageId = pyEnv["mail.message"].create({
            model: "res.partner",
            body: "A needaction message to have it in messaging menu",
            author_id: pyEnv.odoobotId,
            needaction: true,
            needaction_partner_ids: [pyEnv.currentPartnerId],
            res_id: partnerId,
        });
        pyEnv["mail.notification"].create({
            mail_message_id: messageId,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        });
        const { openDiscuss } = await start();
        openDiscuss();
        await click(".o_main_navbar i[aria-label='Messages']");
        await click(".o-mail-NotificationItem");
        await contains(".o-mail-Discuss", { count: 0 });
        await contains(".o_form_view .o-mail-Chatter");
        await contains(".o_form_view .o_last_breadcrumb_item", { text: "TestPartner" });
        await contains(".o-mail-Chatter .o-mail-Message", {
            text: "A needaction message to have it in messaging menu",
        });
    }
);

QUnit.test(
    "Chats input should wait until the previous RPC is done before starting a new one",
    async () => {
        const pyEnv = await startServer();
        const [partnerId1, partnerId2] = pyEnv["res.partner"].create([
            { name: "Mario" },
            { name: "Mama" },
        ]);
        pyEnv["res.users"].create([{ partner_id: partnerId1 }, { partner_id: partnerId2 }]);
        const deferred1 = makeDeferred();
        const deferred2 = makeDeferred();
        const { openDiscuss } = await start({
            async mockRPC(route, params) {
                if (route === "/web/dataset/call_kw/res.partner/im_search") {
                    const { args } = params;
                    if (args[0] === "m") {
                        await deferred1;
                        step("First RPC");
                    } else if (args[0] === "mar") {
                        await deferred2;
                        step("Second RPC");
                    } else {
                        throw Error(`Unexpected search term: ${args[0]}`);
                    }
                }
            },
        });
        openDiscuss();
        await click(".o-mail-DiscussSidebarCategory-add[title='Start a conversation']");
        await insertText(".o-discuss-ChannelSelector input", "m");
        await contains(".o-mail-NavigableList-item", { text: "Loading" });
        await insertText(".o-discuss-ChannelSelector input", "a");
        await insertText(".o-discuss-ChannelSelector input", "r");
        deferred1.resolve();
        await Promise.resolve();
        await assertSteps(["First RPC"]);
        deferred2.resolve();
        await contains(".o-discuss-ChannelSelector-suggestion", { text: "Mario" });
        await contains(".o-discuss-ChannelSelector-suggestion", { count: 0, text: "Mama" });
        await assertSteps(["Second RPC"]);
    }
);

QUnit.test("Escape key should close the channel selector and focus the composer", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("i[title='Add or join a channel']");
    await contains(".o-discuss-ChannelSelector");
    triggerHotkey("escape");
    await contains(".o-discuss-ChannelSelector", { count: 0 });
    await contains(".o-mail-Composer-input:focus");
});

QUnit.test("Escape key should focus the composer if it's not focused", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("button[title='Pinned Messages']");
    triggerHotkey("escape");
    await contains(".o-mail-Composer-input:focus");
});

QUnit.test("Notification settings: basic rendering", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "Mario Party",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("[title='Notification Settings']");
    await contains("button", { text: "All Messages" });
    await contains("button", { text: "Mentions Only" });
    await contains("button", { text: "Nothing" });
    await click("[title='Mute Channel']");
    await contains("[title='For 15 minutes']");
    await contains("[title='For 1 hour']");
    await contains("[title='For 3 hours']");
    await contains("[title='For 8 hours']");
    await contains("[title='For 24 hours']");
    await contains("[title='Until I turn it back on']");
});

QUnit.test("Notification settings: mute channel will change the style of sidebar", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "Mario Party",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-DiscussSidebar-item", { text: "Mario Party" });
    await contains(".o-mail-DiscussSidebar-item[class*='opacity-50']", {
        text: "Mario Party",
        count: 0,
    });
    await click("[title='Notification Settings']");
    await click("[title='Mute Channel']");
    await click("[title='For 15 minutes']");
    await contains(".o-mail-DiscussSidebar-item", { text: "Mario Party" });
    await contains(".o-mail-DiscussSidebar-item[class*='opacity-50']", { text: "Mario Party" });
});

QUnit.test("Notification settings: mute/unmute channel works correctly", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "Mario Party",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("[title='Notification Settings']");
    await click("[title='Mute Channel']");
    await click("[title='For 15 minutes']");
    await click("[title='Notification Settings']");
    await contains("span", { text: "Unmute Channel" });
    await click("button", { text: "Unmute Channel" });
    await click("[title='Notification Settings']");
    await contains("span", { text: "Unmute Channel" });
});

QUnit.test("Newly created chat should be at the top of the direct message list", async () => {
    const pyEnv = await startServer();
    const [userId1, userId2] = pyEnv["res.users"].create([
        { name: "Jerry Golay" },
        { name: "Albert" },
    ]);
    const [partnerId1] = pyEnv["res.partner"].create([
        {
            name: "Albert",
            user_ids: [userId2],
        },
        {
            name: "Jerry Golay",
            user_ids: [userId1],
        },
    ]);
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                is_pinned: true,
                last_interest_dt: "2021-01-01 10:00:00",
                partner_id: pyEnv.currentPartnerId,
            }),
            Command.create({ partner_id: partnerId1 }),
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebarCategory-add[title='Start a conversation']");
    await insertText(".o-discuss-ChannelSelector input", "Jer");
    await click(".o-discuss-ChannelSelector-suggestion");
    await triggerHotkey("Enter");
    await contains(".o-mail-DiscussSidebar-item", {
        text: "Jerry Golay",
        before: [".o-mail-DiscussSidebar-item", { text: "Albert" }],
    });
});
