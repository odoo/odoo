import { waitNotifications, waitUntilSubscribe } from "@bus/../tests/bus_test_helpers";

import {
    click,
    contains,
    defineMailModels,
    editInput,
    insertText,
    listenStoreFetch,
    onRpcBefore,
    openDiscuss,
    openFormView,
    patchUiSize,
    scroll,
    SIZES,
    start,
    startServer,
    STORE_FETCH_ROUTES,
    triggerHotkey,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred, press, runAllTimers, tick, waitFor } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import {
    asyncStep,
    Command,
    getService,
    makeKwArgs,
    mockService,
    onRpc,
    patchWithCleanup,
    serverState,
    waitForSteps,
    withUser,
} from "@web/../tests/web_test_helpers";

import { OutOfFocusService } from "@mail/core/common/out_of_focus_service";
import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineMailModels();

test("sanity check", async () => {
    await startServer();
    onRpcBefore((route, args) => {
        if (
            (route.startsWith("/mail") || route.startsWith("/discuss")) &&
            !STORE_FETCH_ROUTES.includes(route)
        ) {
            asyncStep(`${route} - ${JSON.stringify(args)}`);
        }
    });
    listenStoreFetch();
    await start();
    await waitStoreFetch(["failures", "systray_get_activities", "init_messaging"]);
    await openDiscuss();
    await waitStoreFetch(["channels_as_member"], {
        stepsAfter: ['/mail/inbox/messages - {"fetch_params":{"limit":30}}'],
    });
    await contains(".o-mail-DiscussSidebar");
    await contains("h4:contains(Your inbox is empty)");
});

test.tags("focus required");
test("can change the thread name of #general", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
        create_uid: serverState.userId,
    });

    onRpc("discuss.channel", "channel_rename", ({ route }) => asyncStep(route));

    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input:focus");
    await contains("input.o-mail-DiscussContent-threadName:value(general)");
    await insertText("input.o-mail-DiscussContent-threadName:enabled", "special", {
        replace: true,
    });
    triggerHotkey("Enter");
    await waitForSteps(["/web/dataset/call_kw/discuss.channel/channel_rename"]);
    await contains(".o-mail-DiscussSidebarChannel:contains(special)");
    await contains("input.o-mail-DiscussContent-threadName:value(special)");
});

test.tags("focus required");
test("should log notification when channel/thread is renamed", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        create_uid: serverState.userId,
    });
    pyEnv["discuss.channel"].create({
        name: "test",
        parent_channel_id: channelId,
        create_uid: serverState.userId,
    });
    onRpc("discuss.channel", "channel_rename", ({ route }) => expect.step(route));
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-DiscussContent-threadName:value(general)");
    await insertText(".o-mail-DiscussContent-threadName:enabled", "special", { replace: true });
    triggerHotkey("Enter");
    await expect.waitForSteps(["/web/dataset/call_kw/discuss.channel/channel_rename"]);
    await contains(".o-mail-DiscussContent-threadName:value(special)");
    await contains(".o-mail-NotificationMessage", {
        text: `${serverState.partnerName} changed the channel name to special`,
    });

    await click(".o-mail-DiscussSidebarChannel-subChannel", { text: "test" });
    await click(".o-mail-DiscussContent-threadName:value(test)");
    await insertText(".o-mail-DiscussContent-threadName:enabled", "specialThread", {
        replace: true,
    });
    triggerHotkey("Enter");
    await expect.waitForSteps(["/web/dataset/call_kw/discuss.channel/channel_rename"]);
    await contains(".o-mail-DiscussContent-threadName:value(specialThread)");
    await contains(".o-mail-NotificationMessage", {
        text: `${serverState.partnerName} changed the thread name to specialThread`,
    });
});

test("can active change thread from messaging menu", async () => {
    const pyEnv = await startServer();
    const [, teamId] = pyEnv["discuss.channel"].create([
        { name: "general", channel_type: "channel" },
        { name: "team", channel_type: "channel" },
    ]);
    await start();
    await openDiscuss(teamId);
    await contains(".o-mail-DiscussSidebar-item:contains(general)");
    await contains(".o-mail-DiscussSidebar-item.o-active:contains(team)");
    await click(".o_main_navbar i[aria-label='Messages']");
    await click(".o-mail-DiscussSidebar-item:contains(general)");
    await contains(".o-mail-DiscussSidebar-item.o-active:contains(general)");
    await contains(".o-mail-DiscussSidebar-item:contains(team)");
});

test.tags("focus required");
test("can change the thread description of #general", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
        description: "General announcements...",
        create_uid: serverState.userId,
    });

    onRpc("discuss.channel", "channel_change_description", ({ route }) => asyncStep(route));

    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input:focus");
    await contains("input.o-mail-DiscussContent-threadDescription:value(General announcements...)");
    await insertText(
        "input.o-mail-DiscussContent-threadDescription:enabled",
        "I want a burger today!",
        {
            replace: true,
        }
    );
    triggerHotkey("Enter");
    await waitForSteps(["/web/dataset/call_kw/discuss.channel/channel_change_description"]);
    await contains("input.o-mail-DiscussContent-threadDescription:value(I want a burger today!)");
});

test("Message following a notification should not be squashed", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: '<div class="o_mail_notification">created <a href="#" class="o_channel_redirect">#general</a></div>',
        model: "discuss.channel",
        res_id: channelId,
        message_type: "notification",
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Hello world!");
    await press("Enter");
    await contains(".o-mail-Message-sidebar .o-mail-Message-avatarContainer");
});

test("Posting message should transform links.", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "test https://www.odoo.com/");
    await press("Enter");
    await contains("a[href='https://www.odoo.com/']");
});

test("Posting message should transform relevant data to emoji.", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "test :P :laughing:");
    await press("Enter");
    await contains(".o-mail-Message-body", { text: "test 😛 😆" });
});

test("posting a message immediately after another one is displayed in 'simple' mode (squashed)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "abc");
    await press("Enter");
    await contains(".o-mail-Message", { count: 1 });
    await insertText(".o-mail-Composer-input", "def");
    await press("Enter");
    await contains(".o-mail-Message", { count: 2 });
    await contains(".o-mail-Message-header"); // just 1, because 2nd message is squashed
});

test("Message of type notification in chatter should not have inline display", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "testPartner" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "<p>Line 1</p><p>Line 2</p>",
        model: "res.partner",
        res_id: partnerId,
        message_type: "notification",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Message-body");
    expect(".o-mail-Message-body").not.toHaveStyle({ display: /inline/ });
});

test("Click on avatar opens its partner chat window", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "testPartner",
        email: "test@partner.com",
        phone: "+45687468",
    });
    pyEnv["res.users"].create({
        partner_id: partnerId,
        name: "testPartner",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "Test",
        attachment_ids: [],
        model: "res.partner",
        res_id: partnerId,
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Message-sidebar .o-mail-Message-avatarContainer img");
    await click(".o-mail-Message-sidebar .o-mail-Message-avatarContainer img");
    await contains(".o_avatar_card");
    await contains(".o_card_user_infos > span", { text: "testPartner" });
    await contains(".o_card_user_infos > a", { text: "test@partner.com" });
    await contains(".o_card_user_infos > a", { text: "+45687468" });
});

test("sidebar: chat im_status rendering", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2, partnerId_3] = pyEnv["res.partner"].create([
        { im_status: "offline", name: "Partner1" },
        { im_status: "online", name: "Partner2" },
        { im_status: "away", name: "Partner3" },
    ]);
    pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partnerId_1 }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partnerId_2 }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partnerId_3 }),
            ],
            channel_type: "chat",
        },
    ]);
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel-threadIcon", { count: 3 });
    await contains(".o-mail-DiscussSidebarChannel", {
        text: "Partner1",
        contains: [".o-mail-ThreadIcon [title='Offline']"],
    });
    await contains(".o-mail-DiscussSidebarChannel", {
        text: "Partner2",
        contains: [".fa-circle.text-success"],
    });
    await contains(".o-mail-DiscussSidebarChannel", {
        text: "Partner3",
        contains: [".o-mail-ThreadIcon [title='Idle']"],
    });
});

test("No load more when fetch below fetch limit of 60", async () => {
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
    onRpcBefore("/discuss/channel/messages", (args) => {
        asyncStep("/discuss/channel/messages");
        expect(args.fetch_params.limit).toBe(60);
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 29 });
    await contains("button", { count: 0, text: "Load More" });
    await waitForSteps(["/discuss/channel/messages"]);
});

test("show date separator above mesages of similar date", async () => {
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", {
        count: 29,
        after: [".o-mail-DateSection", { text: "Apr 20, 2019" }],
    });
});

test("sidebar: chat custom name", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Marc Demo" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ custom_channel_name: "Marc", partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { text: "Marc" });
});

test.tags("focus required");
test("reply to message from inbox (message linked to document)", async () => {
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
        res_partner_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-Message");
    await contains(".o-mail-Message-header small", { text: "on Refactoring" });
    await click("[title='Expand']");
    await click(".o-dropdown-item:contains('Reply')");
    await contains(".o-mail-Message.o-selected");
    await contains(".o-mail-Composer");
    await contains(".o-mail-Composer-coreHeader", { text: "on: Refactoring" });
    await insertText(".o-mail-Composer-input:focus", "Hello");
    await press("Enter");
    await contains(".o-mail-Composer", { count: 0 });
    await contains(".o-mail-Message:not(.o-selected)");
    await contains(".o_notification:has(.o_notification_bar.bg-info)", {
        text: 'Message posted on "Refactoring"',
    });
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Message", { count: 2 });
    await contains(".o-mail-Message-content", { text: "Hello" });
});

test("Can reply to starred message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "RandomName" });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        starred_partner_ids: [serverState.partnerId],
        res_id: channelId,
    });
    await start();
    await openDiscuss("mail.box_starred");
    await click("[title='Reply']");
    await contains(".o-mail-Composer-coreHeader", { text: "RandomName" });
    await insertText(".o-mail-Composer-input", "abc");
    await press("Enter");
    await contains(".o_notification", { text: 'Message posted on "RandomName"' });
    await click(".o-mail-DiscussSidebarChannel", { text: "RandomName" });
    await contains(".o-mail-Message-content", { text: "abc" });
});

test("Can reply to history message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "RandomName" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
        is_read: true,
    });
    await start();
    await openDiscuss("mail.box_history");
    await click("[title='Reply']");
    await contains(".o-mail-Composer-coreHeader", { text: "RandomName" });
    await insertText(".o-mail-Composer-input", "abc");
    await press("Enter");
    await contains(".o_notification", { text: 'Message posted on "RandomName"' });
    await click(".o-mail-DiscussSidebarChannel", { text: "RandomName" });
    await contains(".o-mail-Message-content", { text: "abc" });
});

test("receive new needaction messages", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Frodo Baggins" });
    await start();
    await openDiscuss();
    await contains("button.o-active", { text: "Inbox", contains: [".badge", { count: 0 }] });
    await contains(".o-mail-Thread .o-mail-Message", { count: 0 });
    // simulate receiving a new needaction message
    const messageId_1 = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "not empty 1",
        needaction: true,
        model: "res.partner",
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId_1,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    const [partner] = pyEnv["res.partner"].read(serverState.partnerId);
    pyEnv["bus.bus"]._sendone(
        partner,
        "mail.message/inbox",
        new mailDataHelpers.Store(
            pyEnv["mail.message"].browse(messageId_1),
            makeKwArgs({ for_current_user: true, add_followers: true })
        ).get_result()
    );
    await contains("button", { text: "Inbox", contains: [".badge", { text: "1" }] });
    await contains(".o-mail-Message");
    await contains(".o-mail-Message-content", { text: "not empty 1" });
    // simulate receiving a new needaction message
    const messageId_2 = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "not empty 2",
        needaction: true,
        model: "res.partner",
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId_2,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    pyEnv["bus.bus"]._sendone(
        partner,
        "mail.message/inbox",
        new mailDataHelpers.Store(
            pyEnv["mail.message"].browse(messageId_2),
            makeKwArgs({ for_current_user: true, add_followers: true })
        ).get_result()
    );
    await contains("button", { text: "Inbox", contains: [".badge", { text: "2" }] });
    await contains(".o-mail-Message", { count: 2 });
    await contains(".o-mail-Message-content", { text: "not empty 1" });
    await contains(".o-mail-Message-content", { text: "not empty 2" });
});

test("receive a message that is not linked to thread", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Frodo Baggins" });
    await start();
    await openDiscuss();
    await contains("button.o-active", { text: "Inbox", contains: [".badge", { count: 0 }] });
    await contains(".o-mail-Thread .o-mail-Message", { count: 0 });
    // simulate receiving a new needaction message that is not linked to thread
    const messageId_1 = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "needaction message",
        needaction: true,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId_1,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    const [partner] = pyEnv["res.partner"].read(serverState.partnerId);
    pyEnv["bus.bus"]._sendone(
        partner,
        "mail.message/inbox",
        new mailDataHelpers.Store(
            pyEnv["mail.message"].browse(messageId_1),
            makeKwArgs({ for_current_user: true, add_followers: true })
        ).get_result()
    );
    await contains("button", { text: "Inbox", contains: [".badge", { text: "1" }] });
    await contains(".o-mail-Message");
    await contains(".o-mail-Message-content", { text: "needaction message" });
});

test("basic rendering", async () => {
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebar");
    await contains(".o-mail-DiscussContent");
    await contains(".o-mail-DiscussContent .o-mail-Thread");
});

test("basic rendering: sidebar", async () => {
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebar button", { text: "Inbox" });
    await contains(".o-mail-DiscussSidebar button", { text: "Starred messages" });
    await contains(".o-mail-DiscussSidebar button", { text: "History" });
    await contains(".o-mail-DiscussSidebarCategory", { count: 2 });
    await contains(".o-mail-DiscussSidebarCategory-channel", { text: "Channels" });
    await contains(".o-mail-DiscussSidebarCategory-chat", { text: "Direct messages" });
});

test("sidebar: Inbox should have icon", async () => {
    await start();
    await openDiscuss();
    await contains("button", { text: "Inbox", contains: [".fa-inbox"] });
});

test("sidebar: default active inbox", async () => {
    await start();
    await openDiscuss();
    await contains("button.o-active", { text: "Inbox" });
});

test("sidebar: change active", async () => {
    await start();
    await openDiscuss();
    await contains("button.o-active", { text: "Inbox" });
    await contains("button:not(.o-active)", { text: "Starred messages" });
    await click("button", { text: "Starred messages" });
    await contains("button:not(.o-active)", { text: "Inbox" });
    await contains("button.o-active", { text: "Starred messages" });
});

test("sidebar: basic channel rendering", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { text: "General" });
    await contains(".o-mail-DiscussSidebarChannel img[alt='Thread Image']");
    await contains(".o-mail-DiscussSidebarChannel .o-mail-DiscussSidebarChannel-actions.d-none");
    await click("[title='Channel Actions']");
    await contains(".o-dropdown-item:contains('Leave Channel')");
});

test("channel become active", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel");
    await contains(".o-mail-DiscussSidebarChannel.o-active", { count: 0 });
    await click(".o-mail-DiscussSidebarChannel");
    await contains(".o-mail-DiscussSidebarChannel.o-active");
});

test("channel become active - show composer in discuss content", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebarChannel");
    await contains(".o-mail-Thread");
    await contains(".o-mail-Composer");
});

test("sidebar: channel rendering with needaction counter", async () => {
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
        res_partner_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", {
        contains: [
            ["span", { text: "general" }],
            [".badge", { text: "1" }],
        ],
    });
});

test("initially load messages from inbox", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "comment",
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
    onRpcBefore("/mail/inbox/messages", (args) => {
        asyncStep("/discuss/inbox/messages");
        expect(args.fetch_params.limit).toBe(30);
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-Message");
    await waitForSteps(["/discuss/inbox/messages"]);
});

test("default active id on mailbox", async () => {
    await start();
    await openDiscuss("mail.box_starred");
    await contains("button.o-active", { text: "Starred messages" });
});

test("basic top bar rendering", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss();
    await contains("button:disabled", { text: "Mark all read" });
    await contains(".o-mail-DiscussContent-threadName", { value: "Inbox" });
    await click("button", { text: "Starred messages" });
    await contains("button:disabled", { text: "Unstar all" });
    await contains(".o-mail-DiscussContent-threadName", { value: "Starred messages" });
    await click(".o-mail-DiscussSidebarChannel", { text: "General" });
    await contains(".o-mail-DiscussContent-threadName", { value: "General" });
    await contains(".o-mail-DiscussContent-header button", { count: 9 });
    await contains(".o-mail-DiscussContent-header button[title='Start Video Call']");
    await contains(".o-mail-DiscussContent-header button[title='Start Call']");
    await contains(".o-mail-DiscussContent-header button[title='Notification Settings']");
    await contains(".o-mail-DiscussContent-header button[title='Invite People']");
    await contains(".o-mail-DiscussContent-header button[title='Search Messages']");
    await contains(".o-mail-DiscussContent-header button[title='Threads']");
    await contains(".o-mail-DiscussContent-header button[title='Attachments']");
    await contains(".o-mail-DiscussContent-header button[title='Pinned Messages']");
    await contains(".o-mail-DiscussContent-header button[title='Members']");
});

test("rendering of inbox message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Refactoring" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
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
    await openDiscuss();
    await contains(".o-mail-Message");
    await contains(".o-mail-Message-header small", { text: "on Refactoring" });
    await contains(".o-mail-Message-actions i", { count: 4 });
    await contains("[title='Add a Reaction']");
    await contains("[title='Mark as Todo']");
    await contains("[title='Mark as Read']");
    await contains("[title='Reply']");
});

test("Unfollow message", async function () {
    const pyEnv = await startServer();
    const [threadFollowedId, threadNotFollowedId] = pyEnv["res.partner"].create([
        { name: "Thread followed" },
        { name: "Thread not followed" },
    ]);
    pyEnv["mail.followers"].create({
        partner_id: serverState.partnerId,
        res_id: threadFollowedId,
        res_model: "res.partner",
    });
    for (const threadId of [threadFollowedId, threadFollowedId, threadNotFollowedId]) {
        const messageId = pyEnv["mail.message"].create({
            body: "not empty",
            model: "res.partner",
            needaction: true,
            res_id: threadId,
        });
        pyEnv["mail.notification"].create({
            mail_message_id: messageId,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        });
    }
    await start();
    await openDiscuss();
    await contains(".o-mail-Message", { count: 3 });
    await click(".o-mail-Message:eq(0) [title='Expand']");
    await contains(".o-mail-Message:eq(0)", {
        contains: [[".o-mail-Message-header small", { text: "on Thread followed" }]],
    });
    await contains(".o-mail-Message-moreMenu");
    await contains(".o-dropdown-item:contains('Unfollow')");
    await click(".o-mail-Message:eq(1) [title='Expand']");
    await contains(".o-mail-Message:eq(1)", {
        contains: [[".o-mail-Message-header small", { text: "on Thread followed" }]],
    });
    await contains(".o-dropdown-item:contains('Unfollow')");
    await contains(".o-mail-Message:eq(2) [title='Expand']", { count: 0 });
    await contains(".o-mail-Message:eq(2)", {
        contains: [[".o-mail-Message-header small", { text: "on Thread not followed" }]],
    });
    await contains(".o-mail-Message:eq(2) [title='Unfollow']", { count: 0 });
    await click(".o-mail-Message:eq(0) [title='Expand']");
    await click(".o-dropdown-item:contains('Unfollow')");
    await contains(".o-mail-Message", { count: 2 }); // Unfollowing message 0 marks it as read -> Message removed
    await contains(".o-mail-Message:eq(0)", {
        contains: [[".o-mail-Message-header small", { text: "on Thread followed" }]],
    });
    await contains(".o-mail-Message:eq(0) [title='Expand']", { count: 0 });
    await contains(".o-mail-Message:eq(0) [title='Unfollow']", { count: 0 });
    await contains(".o-mail-Message:eq(1)", {
        contains: [[".o-mail-Message-header small", { text: "on Thread not followed" }]],
    });
    await contains(".o-mail-Message:eq(1) [title='Expand']", { count: 0 });
    await contains(".o-mail-Message:eq(1) [title='Unfollow']", { count: 0 });
});

test('messages marked as read move to "History" mailbox', async () => {
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
            res_partner_id: serverState.partnerId,
        },
        {
            mail_message_id: messageId_2,
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
    ]);
    await start();
    await openDiscuss("mail.box_history");
    await contains("button.o-active", { text: "History" });
    await contains(".o-mail-Thread h4", { text: "No history messages" });
    await click("button", { text: "Inbox" });
    await contains("button.o-active", { text: "Inbox" });
    await contains(".o-mail-Thread h4", { count: 0, text: "Your inbox is empty" });
    await contains(".o-mail-Thread .o-mail-Message", { count: 2 });
    await click("button", { text: "Mark all read" });
    await contains("button.o-active", { text: "Inbox" });
    await contains(".o-mail-Thread h4", { text: "Your inbox is empty" });
    await click("button", { text: "History" });
    await contains("button.o-active", { text: "History" });
    await contains(".o-mail-Thread h4", { count: 0, text: "No history messages" });
    await contains(".o-mail-Thread .o-mail-Message", { count: 2 });
});

test('mark a single message as read should only move this message to "History" mailbox', async () => {
    const pyEnv = await startServer();
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            body: "not empty 1",
            needaction: true,
        },
        {
            body: "not empty 2",
            needaction: true,
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
    await openDiscuss("mail.box_history");
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
});

test('all messages in "Inbox" in "History" after marked all as read', async () => {
    const pyEnv = await startServer();
    for (let i = 0; i < 40; i++) {
        const messageId = pyEnv["mail.message"].create({
            body: "not empty",
            needaction: true,
        });
        pyEnv["mail.notification"].create({
            mail_message_id: messageId,
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        });
    }
    await start();
    await openDiscuss();
    await contains(".o-mail-Message", { count: 30 });
    await click("button", { text: "Mark all read" });
    await contains(".o-mail-Message", { count: 0 });
    await click("button", { text: "History" });
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await scroll(".o-mail-Thread", 0);
    await contains(".o-mail-Message", { count: 40 });
});

test("post a simple message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messagePostDef = new Deferred();
    onRpcBefore("/mail/message/post", async (args) => {
        asyncStep("message_post");
        expect(args.thread_model).toBe("discuss.channel");
        expect(args.thread_id).toBe(channelId);
        expect(args.post_data.body).toBe("Test");
        expect(args.post_data.message_type).toBe("comment");
        expect(args.post_data.subtype_xmlid).toBe("mail.mt_comment");
        await messagePostDef;
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread", { text: "Welcome to #general!" });
    await contains(".o-mail-Message", { count: 0 });
    await insertText(".o-mail-Composer-input", "Test");
    await press("Enter");
    await waitForSteps(["message_post"]);
    // optimistically show posted message
    await contains(".o-mail-Composer-input", { value: "" });
    await contains(".o-mail-Message-author", { text: "Mitchell Admin" });
    await contains(".o-mail-Message-content", { text: "Test" });
    expect(".o-mail-Message-content").toHaveStyle({ opacity: "0.5" });
    await contains(".o-mail-Message-pendingProgress"); // visible after 0.5 sec. elapsed
    // simulate message genuinely posted
    messagePostDef.resolve();
    await contains(".o-mail-Message-pendingProgress", { count: 0 });
    await contains(".o-mail-Message-content", { text: "Test" });
    expect(".o-mail-Message-content").toHaveStyle({ opacity: "1" });
});

test("post several messages with failures", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    /** awaiting deferreds of message_post of msg 0, 1, 2 respectively  */
    const messagePostDefs = [new Deferred(), new Deferred(), new Deferred()];
    onRpcBefore("/mail/message/post", async (args) => {
        await messagePostDefs[parseInt(args.post_data.body)];
    });
    await start();
    await openDiscuss(channelId);
    // post 3 messages
    await contains(".o-mail-Thread", { text: "Welcome to #general!" });
    await contains(".o-mail-Message", { count: 0 });
    await insertText(".o-mail-Composer-input", "0");
    await press("Enter");
    await contains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", "1");
    await press("Enter");
    await contains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", "2");
    await press("Enter");
    await contains(".o-mail-Composer-input", { value: "" });
    await contains(".o-mail-Message-author", { text: "Mitchell Admin" });
    await contains(".o-mail-Thread", {
        contains: [
            [".o-mail-Message-content", { text: "0" }],
            [".o-mail-Message-content", { text: "1" }],
            [".o-mail-Message-content", { text: "2" }],
        ],
    });
    // all are pending
    expect(".o-mail-Message-content:eq(0)").toHaveStyle({ opacity: "0.5" });
    expect(".o-mail-Message-content:eq(1)").toHaveStyle({ opacity: "0.5" });
    expect(".o-mail-Message-content:eq(2)").toHaveStyle({ opacity: "0.5" });
    await contains(".o-mail-Message-pendingProgress", { count: 3 }); // visible after 0.5 sec. elapsed
    // simulate OK for 1, NOT-OK for 0, 2
    messagePostDefs[0].reject();
    messagePostDefs[1].resolve();
    messagePostDefs[2].reject();
    await contains(".o-mail-Message-pendingProgress", { count: 0 });
    expect(".o-mail-Message-content:eq(0)").toHaveStyle({ opacity: "0.5" });
    expect(".o-mail-Message-content:eq(1)").toHaveStyle({ opacity: "1" });
    expect(".o-mail-Message-content:eq(2)").toHaveStyle({ opacity: "0.5" });
    // re-try failed posted messages
    messagePostDefs[0] = true;
    messagePostDefs[2] = true;
    await click(
        ".o-mail-Message:contains(0) button[title='Failed to post the message. Click to retry']"
    );
    await click(
        ".o-mail-Message:contains(2) button[title='Failed to post the message. Click to retry']"
    );
    // check all genuinely posted
    await contains(".o-mail-Thread", {
        contains: [
            [".o-mail-Message-content:not(.opacity-50)", { text: "1" }], // was ok before
            [".o-mail-Message-content:not(.opacity-50)", { text: "0" }],
            [".o-mail-Message-content:not(.opacity-50)", { text: "2" }],
        ],
    });
    expect(".o-mail-Message-content:eq(0)").toHaveStyle({ opacity: "1" });
    expect(".o-mail-Message-content:eq(1)").toHaveStyle({ opacity: "1" });
    expect(".o-mail-Message-content:eq(2)").toHaveStyle({ opacity: "1" });
});

test("starred: unstar all", async () => {
    const pyEnv = await startServer();
    pyEnv["mail.message"].create([
        { body: "not empty", starred_partner_ids: [serverState.partnerId] },
        { body: "not empty", starred_partner_ids: [serverState.partnerId] },
    ]);
    await start();
    await openDiscuss("mail.box_starred");
    await contains(".o-mail-Message", { count: 2 });
    await contains("button", { text: "Starred messages", contains: [".badge", { text: "2" }] });
    await click("button:enabled", { text: "Unstar all" });
    await contains("button", { text: "Starred messages", contains: [".badge", { count: 0 }] });
    await contains(".o-mail-Message", { count: 0 });
    await contains("button:disabled", { text: "Unstar all" });
});

test.tags("focus required");
test("auto-focus composer on opening thread", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo User" });
    pyEnv["discuss.channel"].create([
        { name: "General" },
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

test("no out-of-focus notification on receiving self messages in chat", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    mockService("title", {
        setCounters(counters) {
            if (counters.discuss) {
                asyncStep("set_counters:discuss");
            }
        },
    });
    await start();
    await contains(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    // simulate receiving a new message of self with odoo out-of-focused
    withUser(serverState.userId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "New message",
                message_type: "comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { text: "You: New message" });
    await contains(".o-mail-ChatWindow", { count: 0 });
    await waitForSteps([]);
});

test("out-of-focus notif on needaction message in channel", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "channel",
    });
    mockService("title", {
        setCounters(counters) {
            if (counters.discuss) {
                asyncStep(`set_counters:discuss:${counters.discuss}`);
            }
        },
    });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    await contains(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    // simulate receiving a new needaction message with odoo out-of-focused
    const adminId = serverState.partnerId;
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "@Michell Admin",
                partner_ids: [adminId],
                message_type: "comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatBubble");
    await waitForSteps(["set_counters:discuss:1"]);
});

test("receive new chat message: out of odoo focus (notification, chat)", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    mockService("title", {
        setCounters(counters) {
            if (counters.discuss) {
                asyncStep(`set_counters:discuss:${counters.discuss}`);
            }
        },
    });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    await contains(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    // simulate receiving a new message with odoo out-of-focused
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "New message",
                message_type: "comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatBubble");
    await waitForSteps(["set_counters:discuss:1"]);
});

test("no out-of-focus notif on non-needaction message in channel", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "channel",
    });
    mockService("title", {
        setCounters(counters) {
            if (counters.discuss) {
                asyncStep("set_counters:discuss");
            }
        },
    });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    await contains(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    // simulate receving new message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "New message", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", { text: "Dumbledore: New message" });
    await contains(".o-mail-ChatWindow", { count: 0 });
    await waitForSteps([]);
});

test("receive new chat messages: out of odoo focus (tab title)", async () => {
    let stepCount = 0;
    const pyEnv = await startServer();
    const bobUserId = pyEnv["res.users"].create({ name: "bob" });
    const bobPartnerId = pyEnv["res.partner"].create({ name: "bob", user_ids: [bobUserId] });
    const [channelId_1, channelId_2] = pyEnv["discuss.channel"].create([
        {
            channel_type: "chat",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: bobPartnerId }),
            ],
        },
        {
            channel_type: "chat",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: bobPartnerId }),
            ],
        },
    ]);
    mockService("title", {
        setCounters(counters) {
            if (!counters.discuss) {
                return;
            }
            stepCount++;
            asyncStep("set_counters:discuss");
            if (stepCount === 1) {
                expect(counters.discuss).toBe(1);
            }
            if (stepCount === 2) {
                expect(counters.discuss).toBe(2);
            }
            if (stepCount === 3) {
                expect(counters.discuss).toBe(3);
            }
        },
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { count: 2 });
    // simulate receiving a new message in chat 1 with odoo out-of-focused
    await withUser(bobUserId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello world!", message_type: "comment" },
            thread_id: channelId_1,
            thread_model: "discuss.channel",
        })
    );
    await waitForSteps(["set_counters:discuss"]);
    // simulate receiving a new message in chat 2 with odoo out-of-focused
    await withUser(bobUserId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello world!", message_type: "comment" },
            thread_id: channelId_2,
            thread_model: "discuss.channel",
        })
    );
    await waitForSteps(["set_counters:discuss"]);
    // simulate receiving another new message in chat 2 with odoo focused
    await withUser(bobUserId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello world!", message_type: "comment" },
            thread_id: channelId_2,
            thread_model: "discuss.channel",
        })
    );
    await waitForSteps(["set_counters:discuss"]);
});

test("new message in tab title has precedence over action name", async () => {
    const pyEnv = await startServer();
    const bobUserId = pyEnv["res.users"].create({ name: "bob" });
    const bobPartnerId = pyEnv["res.partner"].create({ name: "bob", user_ids: [bobUserId] });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: bobPartnerId }),
        ],
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussContent-threadName", { value: "Inbox" }); // wait for action name being Inbox
    const titleService = getService("title");
    expect(titleService.current).toBe("Inbox");
    // simulate receiving a new message in chat 1 with odoo out-of-focused
    await withUser(bobUserId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello world!", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await waitNotifications(["discuss.channel.member/fetched"]);
    expect(titleService.current).toBe("(1) Inbox");
});

test("out-of-focus notif takes new inbox messages into account", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    await openDiscuss();
    const titleService = getService("title");
    // simulate receiving a new needaction message with odoo out-of-focused
    const adminId = serverState.partnerId;
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "@Michell Admin",
                partner_ids: [adminId],
                message_type: "comment",
            },
            thread_id: partnerId,
            thread_model: "res.partner",
        })
    );
    await contains(".o-mail-DiscussSidebar-item:has(.badge:contains(1))", { text: "Inbox" });
    expect(titleService.current).toBe("(1) Inbox");
});

test("out-of-focus notif on needaction message in group chat contributes only once", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "group",
    });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    await openDiscuss();
    const titleService = getService("title");
    // simulate receiving a new needaction message with odoo out-of-focused
    const adminId = serverState.partnerId;
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "@Michell Admin",
                partner_ids: [adminId],
                message_type: "comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-DiscussSidebar-item:has(.badge:contains(1))", { text: "Inbox" });
    await contains(".o-mail-DiscussSidebar-item:has(.badge:contains(1))", {
        text: "Mitchell Admin and Dumbledore",
    });
    expect(titleService.current).toBe("(1) Inbox");
});

test("inbox notifs shouldn't play sound nor open chat bubble", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["discuss.channel"].create({ name: "general", channel_type: "channel" });
    patchWithCleanup(OutOfFocusService.prototype, {
        _playSound() {
            asyncStep("play_sound");
        },
    });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    // simulate receiving a new needaction message with odoo out-of-focused
    const adminId = serverState.partnerId;
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "@Michell Admin",
                partner_ids: [adminId],
                message_type: "comment",
            },
            thread_id: partnerId,
            thread_model: "res.partner",
        })
    );
    await contains(".o-mail-MessagingMenu-counter", { text: "1" });
    // check no chat window nor chat bubble spawn: can be delayed, hence opening and folding chat by hand
    await click("button.dropdown i[aria-label='Messages']");
    await click(".o-mail-MessagingMenu button:contains(general)");
    await contains(".o-mail-ChatWindow:contains(general)");
    await contains(".o-mail-ChatWindow", { count: 1 });
    await click(".o-mail-ChatWindow button[title='Fold']");
    await contains(".o-mail-ChatBubble", { count: 1 }); // no other chat bubble other than manually folded one
    await waitForSteps([]); // no sound alert whatsoever
});

test("receive new message plays sound", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    mockService("mail.sound_effects", {
        play(soundEffectName, ...args) {
            asyncStep(`sound:${soundEffectName}`);
            return super.play(soundEffectName, ...args);
        },
    });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    await contains(".o_menu_systray i[aria-label='Messages']");
    // simulate receiving a new message
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "New message",
                message_type: "comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await waitForSteps(["sound:new-message"]);
});

test("message sound on receiving new message based on user preferences", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    mockService("mail.sound_effects", {
        play(soundEffectName, ...args) {
            asyncStep(`sound:${soundEffectName}`);
            return super.play(soundEffectName, ...args);
        },
    });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    await contains(".o_menu_systray i[aria-label='Messages']");
    // simulate receiving a new message
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "New message",
                message_type: "comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await waitFor(".o-mail-ChatBubble .badge:contains(1)", { timeout: 3000 });
    await waitForSteps(["sound:new-message"]);
    // simulate message sound settings turned off
    browser.localStorage.setItem("mail.user_setting.message_sound", false);
    await animationFrame();
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "New message2",
                message_type: "comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await waitFor(".o-mail-ChatBubble .badge:contains(2)", { timeout: 3000 });
    expect.verifySteps([]);
    // simulate message sound settings turned on
    browser.localStorage.setItem("mail.user_setting.message_sound", null);
    browser.localStorage.removeItem("mail.user_setting.message_sound");
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "New message",
                message_type: "comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await waitFor(".o-mail-ChatBubble .badge:contains(3)", { timeout: 3000 });
    await waitForSteps(["sound:new-message"]);
});

test("should auto-pin chat when receiving a new DM", async () => {
    mockDate("2023-01-03 12:00:00"); // so that it's after last interest (mock server is in 2019 by default!)
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                unpin_dt: "2021-01-01 12:00:00",
                last_interest_dt: "2021-01-01 10:00:00",
                partner_id: serverState.partnerId,
            }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    listenStoreFetch("init_messaging");
    await start();
    await openDiscuss();
    await waitStoreFetch("init_messaging");
    await contains(".o-mail-DiscussSidebarCategory-chat");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0, text: "Demo" });
    // simulate receiving the first message on channel 11
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "What do you want?", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-DiscussSidebarChannel", { text: "Demo" });
});

test("'Invite People' button should be displayed in the topbar of channels", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains("button[title='Invite People']");
});

test("'Invite People' button should be displayed in the topbar of chats", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Marc Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains("button[title='Invite People']");
});

test("'Invite People' button should be displayed in the topbar of groups", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "group",
    });
    await start();
    await openDiscuss(channelId);
    await contains("button[title='Invite People']");
});

test("'Invite People' button should not be displayed in the topbar of mailboxes", async () => {
    await start();
    await openDiscuss("mail.box_starred");
    await contains("button", { text: "Unstar all" });
    await contains("button[title='Invite People']", { count: 0 });
});

test("Thread avatar image is displayed in top bar of channels of type 'channel' limited to a group", async () => {
    const pyEnv = await startServer();
    const groupId = pyEnv["res.groups"].create({ name: "testGroup" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "string",
        group_public_id: groupId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussContent-header .o-mail-DiscussContent-threadAvatar");
});

test("Thread avatar image is displayed in top bar of channels of type 'channel' not limited to any group", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "string",
        group_public_id: false,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussContent-header .o-mail-DiscussContent-threadAvatar");
});

test("Partner IM status is displayed as thread icon in top bar of channels of type 'chat'", async () => {
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
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partnerId_1 }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partnerId_2 }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partnerId_3 }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partnerId_4 }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: serverState.odoobotId }),
            ],
            channel_type: "chat",
        },
    ]);
    await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebarChannel", { text: "Michel Online" });
    await contains(".o-mail-DiscussContent-header .o-mail-ImStatus [title='Online']");
    await click(".o-mail-DiscussSidebarChannel", { text: "Jacqueline Offline" });
    await contains(".o-mail-DiscussContent-header .o-mail-ImStatus [title='Offline']");
    await click(".o-mail-DiscussSidebarChannel", { text: "Nabuchodonosor Idle" });
    await contains(".o-mail-DiscussContent-header .o-mail-ImStatus [title='Idle']");
    await click(".o-mail-DiscussSidebarChannel", { text: "Robert Fired" });
    await contains(
        ".o-mail-DiscussContent-header .o-mail-ImStatus [title='No IM status available']"
    );
    await click(".o-mail-DiscussSidebarChannel", { text: "OdooBot" });
    await contains(".o-mail-DiscussContent-header .o-mail-ImStatus [title='Bot']");
});

test("Thread avatar image is displayed in top bar of channels of type 'group'", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "group" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussContent-header .o-mail-DiscussContent-threadAvatar");
});

test("Thread avatar is not editable in DM chat", async () => {
    const pyEnv = await startServer();
    const demoUid = pyEnv["res.users"].create({ name: "Demo" });
    const demoPid = pyEnv["res.partner"].create({ name: "Demo", user_ids: [demoUid] });
    const [groupChatId] = pyEnv["discuss.channel"].create([
        { channel_type: "group", name: "GroupChat" },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: demoPid }),
            ],
            channel_type: "chat",
        },
    ]);
    await start();
    await openDiscuss(groupChatId);
    await contains(".o-mail-DiscussContent-threadName[title='GroupChat']");
    await contains(".o-mail-DiscussContent-threadAvatar .fa-pencil");
    await click(".o-mail-DiscussSidebar-item:contains('Demo')");
    await contains(".o-mail-DiscussContent-threadName[title='Demo']");
    await contains(".o-mail-DiscussContent-threadAvatar .fa-pencil", { count: 0 });
});

test("Do not trigger chat name server update when it is unchanged", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });

    onRpc("discuss.channel", "channel_set_custom_name", ({ method }) => asyncStep(method));

    await start();
    await openDiscuss(channelId);
    await insertText("input.o-mail-DiscussContent-threadName:enabled", "Mitchell Admin", {
        replace: true,
    });
    triggerHotkey("Enter");
    await waitForSteps([]);
});

test("Do not trigger channel description server update when channel has no description and editing to empty description", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        create_uid: serverState.userId,
        name: "General",
    });

    onRpc("discuss.channel", "channel_change_description", ({ method }) => asyncStep(method));

    await start();
    await openDiscuss(channelId);
    await insertText("input.o-mail-DiscussContent-threadDescription", "");
    triggerHotkey("Enter");
    await waitForSteps([]);
});

test("Channel is added to discuss after invitation", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Harry" });
    const partnerId = pyEnv["res.partner"].create({ name: "Harry", user_ids: [userId] });
    const [, channelId] = pyEnv["discuss.channel"].create([
        { name: "my channel" },
        {
            name: "General",
            channel_member_ids: [Command.create({ partner_id: partnerId })],
        },
    ]);
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { text: "my channel" });
    await contains(".o-mail-DiscussSidebarChannel", { count: 0, text: "General" });
    const adminPartnerId = serverState.partnerId;
    withUser(userId, () =>
        getService("orm").call("discuss.channel", "add_members", [[channelId]], {
            partner_ids: [adminPartnerId],
        })
    );
    await contains(".o-mail-DiscussSidebarChannel", { text: "General" });
    await contains(".o_notification:has(.o_notification_bar.bg-info)", {
        text: "You have been invited to #General",
    });
});

test("select another mailbox", async () => {
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss();
    await contains(".o-mail-Discuss");
    await click("button:contains('Inbox')");
    await contains(".o-mail-DiscussContent-threadName", { value: "Inbox" });
    await click("button", { text: "Starred messages" });
    await contains("button:disabled", { text: "Unstar all" });
    await contains(".o-mail-DiscussContent-threadName", { value: "Starred messages" });
});

test('auto-select "Inbox nav bar" when discuss had inbox as active thread', async () => {
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss();
    await click("button:contains('Inbox')");
    await contains(".o-mail-DiscussContent-threadName", { value: "Inbox" });
    await contains(".o-mail-MessagingMenu-navbar button.o-active", { text: "Inbox" });
    await contains("button.active.o-active", { text: "Inbox" });
    await contains("h4", { text: "Your inbox is empty" });
});

test("composer should be focused automatically after clicking on the send button", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Dummy Message");
    await press("Enter");
    expect(".o-mail-Composer-input").toBeFocused();
});

test.tags("focus required");
test("mark channel as seen if last message is visible when switching channels when the previous channel had a more recent last message than the current channel", async () => {
    const pyEnv = await startServer();
    const [channelId_1, channelId_2] = pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [
                Command.create({
                    message_unread_counter: 1,
                    partner_id: serverState.partnerId,
                }),
            ],
            name: "Bla",
        },
        {
            channel_member_ids: [
                Command.create({
                    message_unread_counter: 1,
                    partner_id: serverState.partnerId,
                }),
            ],
            name: "Blu",
        },
    ]);
    onRpcBefore("/discuss/channel/mark_as_read", (args) => {
        asyncStep(`rpc:mark_as_read - ${args.channel_id}`);
    });
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
    await start();
    await openDiscuss(channelId_2);
    await waitForSteps([`rpc:mark_as_read - ${channelId_2}`]);
    await click("button", { text: "Bla" });
    await waitForSteps([`rpc:mark_as_read - ${channelId_1}`]);
});

test("warning on send with shortcut when attempting to post message with still-uploading attachments", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    onRpcBefore("/mail/attachment/upload", async () => await new Deferred()); // simulates attachment is never finished uploading
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer input[type=file]");
    const file = new File(["hello, world"], "text.txt", { type: "text/plain" });
    await insertText(".o-mail-Composer-input", "Dummy Message");
    await editInput(document.body, ".o-mail-Composer input[type=file]", [file]);
    await contains(
        ".o-mail-AttachmentContainer.o-isUploading:contains(text.txt) .fa.fa-circle-o-notch"
    );
    await contains(".o-mail-Composer button[title='Send']:disabled");
    await press("Enter"); // Try to send message
    await contains(".o_notification", { text: "Please wait while the file is uploading." });
});

test("post attachment-only message shows optimistically the new message with attachment", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    onRpcBefore("/mail/message/post", async () => await new Deferred());
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer input[type=file]");
    const file = new File(["hello, world"], "text.txt", { type: "text/plain" });
    await editInput(document.body, ".o-mail-Composer input[type=file]", [file]);
    await contains(
        ".o-mail-AttachmentContainer:not(.o-isUploading):contains('text.txt'):not(:has(.fa.fa-circle-o-notch))"
    );
    await press("Enter");
    await contains(".o-mail-Message");
    await contains(".o-mail-Message .o-mail-AttachmentContainer:contains('text.txt')");
});

test("failure on loading messages should display error", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });

    onRpc("/discuss/channel/messages", () => Promise.reject());

    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread", { text: "An error occurred while fetching messages." });
});

test("failure on loading messages should prompt retry button", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });

    onRpc("/discuss/channel/messages", () => Promise.reject());

    await start();
    await openDiscuss(channelId);
    await contains("button", { text: "Click here to retry" });
});

test("failure on loading more messages should display error and prompt retry button", async () => {
    // first call needs to be successful as it is the initial loading of messages
    // second call comes from load more and needs to fail in order to show the error alert
    // any later call should work so that retry button and load more clicks would now work
    let messageFetchShouldFail = false;
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    const messageIds = pyEnv["mail.message"].create(
        [...Array(60).keys()].map(() => ({
            body: "coucou",
            model: "discuss.channel",
            res_id: channelId,
        }))
    );
    const [selfMember] = pyEnv["discuss.channel.member"].search_read([
        ["partner_id", "=", serverState.partnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.member"].write([selfMember.id], {
        new_message_separator: messageIds.at(-1) + 1,
    });
    onRpcBefore("/discuss/channel/messages", () => {
        if (messageFetchShouldFail) {
            return Promise.reject();
        }
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 30 });
    messageFetchShouldFail = true;
    await click("button", { text: "Load More" });
    await contains(".o-mail-Thread", { text: "An error occurred while fetching messages." });
    await contains("button", { text: "Click here to retry" });
    await contains("button", { count: 0, text: "Load More" });
});

test("Retry loading more messages on failed load more messages should load more messages", async () => {
    // first call needs to be successful as it is the initial loading of messages
    // second call comes from load more and needs to fail in order to show the error alert
    // any later call should work so that retry button and load more clicks would now work
    let messageFetchShouldFail = false;
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    const messageIds = pyEnv["mail.message"].create(
        [...Array(90).keys()].map(() => ({
            body: "coucou",
            model: "discuss.channel",
            res_id: channelId,
        }))
    );
    const [selfMember] = pyEnv["discuss.channel.member"].search_read([
        ["partner_id", "=", serverState.partnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.member"].write([selfMember.id], {
        new_message_separator: messageIds.at(-1) + 1,
    });
    onRpcBefore("/discuss/channel/messages", () => {
        if (messageFetchShouldFail) {
            return Promise.reject();
        }
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 30 });
    messageFetchShouldFail = true;
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await scroll(".o-mail-Thread", 0);
    await contains("button", { text: "Click here to retry" });
    messageFetchShouldFail = false;
    await click("button", { text: "Click here to retry" });
    await contains(".o-mail-Message", { count: 60 });
});

test("composer state: attachments save and restore", async () => {
    const pyEnv = await startServer();
    const [channelId] = pyEnv["discuss.channel"].create([{ name: "General" }, { name: "Special" }]);
    await start();
    await openDiscuss(channelId);
    await contains(
        ".o-mail-Composer:has(textarea[placeholder='Message #General…']) input[type=file]"
    );
    // Add attachment in a message for #general
    const file = new File(["hello, world"], "text.txt", { type: "text/plain" });
    await editInput(
        document.body,
        ".o-mail-Composer:has(textarea[placeholder='Message #General…']) input[type=file]",
        [file]
    );
    await contains(
        ".o-mail-Composer .o-mail-AttachmentContainer:not(.o-isUploading):contains(text.txt)"
    );
    await contains(".o-mail-Composer .o-mail-AttachmentContainer");
    // Switch to #special
    await click("button", { text: "Special" });
    // Attach files in a message for #special
    const files = [
        new File(["hello2, world"], "text2.txt", { type: "text/plain" }),
        new File(["hello3, world"], "text3.txt", { type: "text/plain" }),
        new File(["hello4, world"], "text4.txt", { type: "text/plain" }),
    ];
    await contains(
        ".o-mail-Composer:has(textarea[placeholder='Message #Special…']) input[type=file]"
    );
    await editInput(
        document.body,
        ".o-mail-Composer:has(textarea[placeholder='Message #Special…']) input[type=file]",
        files
    );
    await contains(".o-mail-Composer .o-mail-AttachmentContainer:not(.o-isUploading)", {
        count: 3,
    });
    await contains(".o-mail-Composer .o-mail-AttachmentContainer", { count: 3 });
    // Switch back to #general
    await click("button", { text: "General" });
    await contains(".o-mail-Composer .o-mail-AttachmentContainer");
    await contains(".o-mail-Composer .o-mail-AttachmentContainer:contains(text.txt)");
    // Switch back to #special
    await click("button", { text: "Special" });
    await contains(".o-mail-Composer .o-mail-AttachmentContainer", { count: 3 });
    await contains(".o-mail-AttachmentContainer", { text: "text2.txt" });
    await contains(".o-mail-AttachmentContainer", { text: "text3.txt" });
    await contains(".o-mail-AttachmentContainer", { text: "text4.txt" });
});

test("sidebar: cannot leave channel with group_ids", async () => {
    mockDate("2023-01-03 12:00:00"); // so that it's after last interest (mock server is in 2019 by default!)
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            Command.create({
                unpin_dt: "2021-01-01 12:00:00",
                last_interest_dt: "2021-01-01 10:00:00",
                partner_id: serverState.partnerId,
            }),
        ],
        group_ids: [Command.create({ name: "test" })],
    });
    await start();
    await openDiscuss();
    await contains("button", { text: "General" });
    await contains("[title='Leave Channel']", { count: 0 });
});

test("restore thread scroll position", async () => {
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
    await start();
    await openDiscuss(channelId_1);
    await contains(".o-mail-Message", { count: 25 });
    await contains(".o-mail-Thread", { scroll: 0 });
    await tick(); // wait for the scroll to first unread to complete
    await scroll(".o-mail-Thread", "bottom");
    await click("button", { text: "Channel2" });
    await contains(".o-mail-Message", { count: 24 });
    await contains(".o-mail-Thread", { scroll: 0 });
    await click("button", { text: "Channel1" });
    await contains(".o-mail-Message", { count: 25 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await click("button", { text: "Channel2" });
    await contains(".o-mail-Message", { count: 24 });
    await contains(".o-mail-Thread", { scroll: 0 });
});

test("Message shows up even if channel data is incomplete", async () => {
    // Pass in only but not when bulk running tests
    const pyEnv = await startServer();
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory-chat");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
    const correspondentUserId = pyEnv["res.users"].create({ name: "Albert" });
    const correspondentPartnerId = pyEnv["res.partner"].create({
        name: "Albert",
        user_ids: [correspondentUserId],
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                unpin_dt: false,
                partner_id: serverState.partnerId,
            }),
            Command.create({ partner_id: correspondentPartnerId }),
        ],
        channel_type: "chat",
    });
    getService("bus_service").forceUpdateChannels();
    await runAllTimers();
    await waitUntilSubscribe();
    await withUser(correspondentUserId, () =>
        rpc("/discuss/channel/notify_typing", {
            is_typing: true,
            channel_id: channelId,
        })
    );
    await withUser(correspondentUserId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hello world", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await click(".o-mail-DiscussSidebarChannel", { text: "Albert" });
    await contains(".o-mail-Message-content", { text: "hello world" });
});

test("Correct breadcrumb when open discuss from chat window then see settings", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await click(".o_main_navbar i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "General" });
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Open in Discuss" });
    await click("[title='Channel Actions']", {
        parent: [".o-mail-DiscussSidebarChannel", { text: "General" }],
    });
    await click(".o-dropdown-item:contains('Advanced Settings')");
    await contains(".o_breadcrumb", { text: "GeneralGeneral" });
});

test("Chatter notification in messaging menu should open the form view even when discuss app is open", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "TestPartner" });
    const messageId = pyEnv["mail.message"].create({
        model: "res.partner",
        body: "A needaction message to have it in messaging menu",
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
    await openDiscuss();
    await click(".o_main_navbar i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-Discuss", { count: 0 });
    await contains(".o_form_view .o-mail-Chatter");
    await contains(".o_form_view .o_last_breadcrumb_item", { text: "TestPartner" });
    await contains(".o-mail-Chatter .o-mail-Message", {
        text: "A needaction message to have it in messaging menu",
    });
});

test.tags("focus required");
test("Escape key should focus the composer if it's not focused", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Pinned Messages']");
    triggerHotkey("escape");
    await contains(".o-mail-Composer-input:focus");
});

test("Notification settings: basic rendering", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "Mario Party",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Notification Settings']");
    await contains("button", { text: "All Messages" });
    await contains("button", { text: "Mentions Only", count: 2 }); // the extra is in the Use Default as subtitle
    await contains("button", { text: "Nothing" });
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("button", { text: "Mute Conversation" });
    await click("button", { text: "Mute Conversation" });
    await contains("button", { text: "For 15 minutes" });
    await contains("button", { text: "For 1 hour" });
    await contains("button", { text: "For 3 hours" });
    await contains("button", { text: "For 8 hours" });
    await contains("button", { text: "For 24 hours" });
    await contains("button", { text: "Until I turn it back on" });
});

test("Notification settings: mute conversation will change the style of sidebar", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "Mario Party",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussSidebar-item", { text: "Mario Party" });
    await contains(".o-mail-DiscussSidebar-item[class*='opacity-50']", {
        text: "Mario Party",
        count: 0,
    });
    await click("[title='Notification Settings']");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("button", { text: "Mute Conversation" });
    await click("button", { text: "Mute Conversation" });
    await click("button", { text: "For 15 minutes" });
    await contains(".o-mail-DiscussSidebar-item", { text: "Mario Party" });
    await contains(".o-mail-DiscussSidebar-item[class*='opacity-50']", { text: "Mario Party" });
});

test("Notification settings: change the mute duration of the conversation", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "Mario Party",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussSidebar-item", { text: "Mario Party" });
    await contains(".o-mail-DiscussSidebar-item[class*='opacity-50']", {
        text: "Mario Party",
        count: 0,
    });
    await click("[title='Notification Settings']");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("button", { text: "Mute Conversation" });
    await click("button", { text: "Mute Conversation" });
    await click("button", { text: "For 15 minutes" });
    await click("[title='Notification Settings']");
    await click(".o-discuss-NotificationSettings span", { text: "Unmute Conversation" });
    await click("[title='Notification Settings']");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("button", { text: "Mute Conversation" });
    await click("button", { text: "Mute Conversation" });
    await click("button", { text: "For 1 hour" });
});

test("Notification settings: mute/unmute conversation works correctly", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "Mario Party",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Notification Settings']");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("button", { text: "Mute Conversation" });
    await click("button", { text: "Mute Conversation" });
    await click("button", { text: "For 15 minutes" });
    await click("[title='Notification Settings']");
    await contains("button", { text: "Unmute Conversation" });
    await click("button", { text: "Unmute Conversation" });
    await click("[title='Notification Settings']");
    await contains("button", { text: "Unmute Conversation" });
});

test("Newly created chat is at the top of the DM list", async () => {
    mockDate("2021-01-03 12:00:00"); // so that it's after last interest (mock server is in 2019 by default!)
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
                unpin_dt: false,
                last_interest_dt: "2021-01-01 10:00:00",
                partner_id: serverState.partnerId,
            }),
            Command.create({ partner_id: partnerId1 }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss();
    await click("input[placeholder='Search conversations']");
    await insertText("input[placeholder='Search a conversation']", "Jer");
    await click(".o_command_name", { text: "Jerry Golay" });
    await contains(".o-mail-DiscussSidebar-item", {
        text: "Jerry Golay",
        before: [".o-mail-DiscussSidebar-item", { text: "Albert" }],
    });
});

test.tags("focus required");
test("Read of unread chat where new message is deleted should mark as read", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Marc Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "Heyo",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", serverState.partnerId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], {
        seen_message_id: messageId,
        message_unread_counter: 1,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebar-item", {
        text: "Marc Demo",
        contains: [".badge", { text: "1" }],
    });
    // simulate deleted message
    rpc("/mail/message/update_content", {
        message_id: messageId,
        update_data: {
            body: "",
            attachment_ids: [],
        },
    });
    await click("button", { text: "Marc Demo" });
    await contains(".o-mail-DiscussSidebar-item", {
        text: "Marc Demo",
        contains: [".badge", { count: 0 }],
    });
});

test("do not show control panel without breadcrumbs", async () => {
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussContent-threadName", { value: "Inbox" });
    await contains(".o_control_panel", { count: 0 });
    await openFormView("res.partner", serverState.partnerId);
    await openDiscuss();
    await contains(".o-mail-Discuss");
    await contains(".o_control_panel .breadcrumb", { text: serverState.partnerName });
});
