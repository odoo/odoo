import { waitUntilSubscribe } from "@bus/../tests/bus_test_helpers";

import { OutOfFocusService } from "@mail/core/common/out_of_focus_service";
import { DiscussApp } from "@mail/core/public_web/discuss_app/discuss_app_model";
import {
    click,
    contains,
    defineMailModels,
    editInput,
    focus,
    hover,
    insertText,
    listenStoreFetch,
    onRpcBefore,
    openDiscuss,
    openFormView,
    openMessagingMenu,
    patchUiSize,
    scroll,
    SIZES,
    start,
    startServer,
    STORE_FETCH_ROUTES,
    triggerHotkey,
    waitStoreFetch,
    getChannelCommandsForThread,
    MENU_ACTIVE_IDS,
} from "@mail/../tests/mail_test_helpers";
import {
    containsTextInComposer,
    insertTextInComposer,
} from "@mail/../tests/mail_test_helpers_composer";
import { htmlInsertText } from "@mail/../tests/mail_test_helpers_html";
import { Store } from "@mail/../tests/mock_server/store";

import { describe, expect, test } from "@odoo/hoot";
import {
    animationFrame,
    press,
    queryRect,
    rightClick,
    tick,
    waitFor,
    waitForNone,
} from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";

import { rpc } from "@web/core/network/rpc";
import {
    Command,
    getService,
    makeServerError,
    mockService,
    onRpc,
    serverState,
    withUser,
} from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";
import { makeRecordFieldLocalId } from "@mail/model/misc";
import { Settings } from "@mail/core/common/settings_model";
import { toRawValue } from "@mail/utils/common/local_storage";
import { range } from "@web/core/utils/numbers";
import { Message } from "@mail/core/common/message";

describe.current.tags("desktop");
defineMailModels();

test("sanity check", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    onRpcBefore((route, args) => {
        if (
            (route.startsWith("/mail") || route.startsWith("/discuss")) &&
            !STORE_FETCH_ROUTES.includes(route)
        ) {
            expect.step(`${route} - ${JSON.stringify(args)}`);
        }
    });
    listenStoreFetch();
    await start();
    await waitStoreFetch([
        "init_messaging",
        "failures",
        "systray_get_activities",
        "/mail/messaging_menu/initialize_counters",
    ]);
    await openDiscuss(channelId);
    await waitStoreFetch(
        [
            "discuss.channel",
            "/mail/messaging_menu/discuss.channel/load_more",
            "/discuss/channel/messages",
            "/discuss/channel/members",
        ],
        { ignoreOrder: true }
    );
});

test.tags("focus required");
test("can change the thread name of #general", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
        create_uid: serverState.userId,
    });

    onRpc("discuss.channel", "channel_rename", ({ route }) => expect.step(route));

    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer-input:focus:count(1)");
    await waitFor("input.o-mail-DiscussContent-threadName:value(general):count(1)");
    await insertText("input.o-mail-DiscussContent-threadName:enabled", "special", {
        replace: true,
    });
    triggerHotkey("Enter");
    await expect.waitForSteps(["/web/dataset/call_kw/discuss.channel/channel_rename"]);
    await waitFor(".o-mail-NotificationItem:has(:text('special')):count(1)");
    await waitFor("input.o-mail-DiscussContent-threadName:value(special):count(1)");
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
    await waitFor(".o-mail-DiscussContent-threadName:value(special):count(1)");
    await waitFor(
        ".o-mail-NotificationMessage:has(:text('" +
            `${serverState.partnerName} changed the channel name to special` +
            "')):count(1)"
    );

    await click(".o-mail-NotificationItem:has(:text('test'))");
    await click(".o-mail-DiscussContent-threadName:value(test)");
    await insertText(".o-mail-DiscussContent-threadName:enabled", "specialThread", {
        replace: true,
    });
    triggerHotkey("Enter");
    await expect.waitForSteps(["/web/dataset/call_kw/discuss.channel/channel_rename"]);
    await waitFor(".o-mail-DiscussContent-threadName:value(specialThread):count(1)");
    await waitFor(
        ".o-mail-NotificationMessage:has(:text('" +
            `${serverState.partnerName} changed the thread name to specialThread` +
            "')):count(1)"
    );
});

test("can active change thread from messaging menu", async () => {
    const pyEnv = await startServer();
    const [, teamId] = pyEnv["discuss.channel"].create([
        { name: "general", channel_type: "channel" },
        { name: "team", channel_type: "channel" },
    ]);
    await start();
    await openDiscuss(teamId);
    await waitFor(".o-mail-NotificationItem:has(:text('general')):count(1)");
    await waitFor(".o-mail-NotificationItem.o-active:has(:text('team')):count(1)");
    await click(".o_main_navbar i[aria-label='Messages']");
    await click(".o-mail-NotificationItem:has(:text('general'))");
    await waitFor(".o-mail-NotificationItem.o-active:has(:text('general')):count(1)");
    await waitFor(".o-mail-NotificationItem:has(:text('team')):count(1)");
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

    onRpc("discuss.channel", "channel_change_description", ({ route }) => expect.step(route));

    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer-input:focus:count(1)");
    await waitFor(
        "input.o-mail-DiscussContent-threadDescription:value(General announcements...):count(1)"
    );
    await insertText(
        "input.o-mail-DiscussContent-threadDescription:enabled",
        "I want a burger today!",
        { replace: true }
    );
    triggerHotkey("Enter");
    await expect.waitForSteps(["/web/dataset/call_kw/discuss.channel/channel_change_description"]);
    await waitFor(
        "input.o-mail-DiscussContent-threadDescription:value(I want a burger today!):count(1)"
    );
});

test("header card resizes to fit the thread description after switching channels", async () => {
    const pyEnv = await startServer();
    const longDescription =
        "A place to connect and exchange news with colleagues across the company. ".repeat(5);
    const [shortChannelId] = pyEnv["discuss.channel"].create([
        { name: "Short", channel_type: "channel", description: "Hi" },
        { name: "Long", channel_type: "channel", description: longDescription },
    ]);
    await start();
    await openDiscuss(shortChannelId);
    await waitFor("input.o-mail-DiscussContent-threadDescription:value(Hi):count(1)");
    const shortCardWidth = queryRect(".o-mail-DiscussContent-headerBox").width;
    // The box hugs the short description instead of spanning the whole header.
    expect(shortCardWidth).toBeLessThan(queryRect(".o-mail-DiscussContent-headerInfo").width);

    await click(".o-mail-NotificationItem:has(:text('Long'))");
    await waitFor(
        `input.o-mail-DiscussContent-threadDescription:value(${longDescription}):count(1)`
    );
    const longCardWidth = queryRect(".o-mail-DiscussContent-headerBox").width;
    expect(longCardWidth).toBeGreaterThan(shortCardWidth);
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
    await insertTextInComposer(".o-mail-Composer", "Hello world!");
    await press("Enter");
    await waitFor(".o-mail-Message-sidebar .o-mail-Message-avatarContainer:count(1)");
});

test("Posting message should transform links.", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "test https://www.odoo.com/");
    await press("Enter");
    await waitFor(".o-mail-Message a[href='https://www.odoo.com/']:count(1)");
});

test("[text composer] Posting message should transform relevant data to emoji.", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    // Type a trailing space to close the emoji suggestion, which Enter would pick.
    await insertTextInComposer(".o-mail-Composer", "test :P :laughing: ");
    await press("Enter");
    await waitFor(".o-mail-Message-body:text('test 😛 😆'):count(1)");
});

test.tags("html composer");
test("Posting message should transform relevant data to emoji.", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    await start();
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html.odoo-editor-editable");
    const editor = {
        document,
        editable: document.querySelector(".o-mail-Composer-html.odoo-editor-editable"),
    };
    await htmlInsertText(editor, "test :P :laughing:");
    await press("Enter");
    await waitFor(".o-mail-Message-body:text('test 😛 😆'):count(1)");
});

test("posting a message immediately after another one is displayed in 'simple' mode (squashed)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "abc");
    await press("Enter");
    await waitFor(".o-mail-Message:count(1)");
    await insertTextInComposer(".o-mail-Composer", "def");
    await press("Enter");
    await waitFor(".o-mail-Message:count(2)");
    await waitFor(".o-mail-Message-header:count(1)"); // just 1, because 2nd message is squashed
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
    await waitFor(".o-mail-Message-body:count(1)");
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
    await waitFor(".o-mail-Message-sidebar .o-mail-Message-avatarContainer img:count(1)");
    await click(".o-mail-Message-sidebar .o-mail-Message-avatarContainer img");
    await waitFor(".o_avatar_card:count(1)");
    await waitFor(".o-mail-avatar-card-name:text('testPartner'):count(1)");
    await waitFor(".o_card_user_infos > a:text('test@partner.com'):count(1)");
    await waitFor(".o_card_user_infos > a:text('+45687468'):count(1)");
});

test("guests are not allowed to use commands", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    await start({ authenticateAs: false });
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "/who");
    expect(getChannelCommandsForThread(channelId)).toHaveLength(0);
});

test("sidebar: chat im_status rendering", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2, partnerId_3] = pyEnv["res.partner"].create([
        { name: "Partner1" },
        { name: "Partner2" },
        { name: "Partner3" },
    ]);
    pyEnv["res.users"].create([
        { partner_id: partnerId_1, im_status: "offline" },
        { partner_id: partnerId_2, im_status: "online" },
        { partner_id: partnerId_3, im_status: "away" },
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
    await waitFor(".o-mail-MessagingMenuItem .o-mail-ThreadIcon:count(3)");
    await contains(".o-mail-MessagingMenuItem:has(:text('Partner1'))", {
        contains: [".o-mail-ThreadIcon[title='User is offline']"],
    });
    await contains(".o-mail-MessagingMenuItem:has(:text('Partner2'))", {
        contains: ["[data-icon='circle'].text-success"],
    });
    await contains(".o-mail-MessagingMenuItem:has(:text('Partner3'))", {
        contains: [".o-mail-ThreadIcon[title='User is idle']"],
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
    listenStoreFetch("/discuss/channel/messages", { logParams: ["/discuss/channel/messages"] });
    await start();
    await openDiscuss(channelId);
    await waitStoreFetch([
        [
            "/discuss/channel/messages",
            { channel_id: channelId, fetch_params: { limit: 60, around: 0 } },
        ],
    ]);
    await waitFor(".o-mail-Message:count(29)");
    await waitForNone("button:text('Load More')");
    await waitStoreFetch([]);
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
        after: [".o-mail-DateSection:text('Apr 20, 2019')"],
    });
});

test("receive new needaction messages", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    const partnerId = pyEnv["res.partner"].create({ name: "Frodo Baggins" });
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.NOTIFICATION);
    await waitFor(
        ".o-mail-MessagingMenu-tab:has(:text('Notifications')):not(:has(.badge)):count(1)"
    );
    await waitForNone(".o-mail-MessagingMenuItem");
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
    pyEnv["bus.bus"]._sendone(partner, "mail.message/notification", {
        message_id: messageId_1,
        store_data: new Store()
            .add(pyEnv["mail.message"].browse(messageId_1), "_store_message_fields", {
                fields_params: { inbox_fields: true },
            })
            .as_dict(),
    });
    await waitFor(
        ".o-mail-MessagingMenu-tab:has(:text('Notifications')):has(.badge:text(1)):count(1)"
    );
    await waitFor(".o-mail-MessagingMenuItem:count(1)");
    await waitFor(".o-mail-MessagingMenuItem:has(:text('Frodo Baggins: not empty 1')):count(1)");
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
    pyEnv["bus.bus"]._sendone(partner, "mail.message/notification", {
        message_id: messageId_2,
        store_data: new Store()
            .add(pyEnv["mail.message"].browse(messageId_2), "_store_message_fields", {
                fields_params: { inbox_fields: true },
            })
            .as_dict(),
    });
    await waitFor(
        ".o-mail-MessagingMenu-tab:has(:text('Notifications')):has(.badge:text(2)):count(1)"
    );
    await waitFor(".o-mail-MessagingMenuItem:count(2)");
    await waitFor(".o-mail-MessagingMenuItem:has(:text('Frodo Baggins: not empty 1')):count(1)");
    await waitFor(".o-mail-MessagingMenuItem:has(:text('Frodo Baggins: not empty 2')):count(1)");
});

test("receive a message that is not linked to thread", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    const partnerId = pyEnv["res.partner"].create({ name: "Frodo Baggins" });
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.NOTIFICATION);
    await waitForNone(".o-mail-MessagingMenuItem");
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
    pyEnv["bus.bus"]._sendone(partner, "mail.message/notification", {
        message_id: messageId_1,
        store_data: new Store()
            .add(pyEnv["mail.message"].browse(messageId_1), "_store_message_fields", {
                fields_params: { inbox_fields: true },
            })
            .as_dict(),
    });
    await contains("button:has(:text('Notifications'))", { contains: [".badge:text('1')"] });
    await waitFor(".o-mail-MessagingMenuItem:count(1)");
    await waitFor(".o-mail-MessagingMenuItem:has(:text('needaction message')):count(1)");
});

test("basic rendering: sidebar", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        bookmarked_partner_ids: [serverState.partnerId],
        res_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await waitFor(".o-mail-MessagingMenu-tab:has(:text('Notifications')):count(1)");
    await waitFor(".o-mail-MessagingMenu-tab:has(:text('Bookmarks')):count(1)");
    await waitFor(".o-mail-MessagingMenu-tab:has(:text('Channels')):count(1)");
    await waitFor(".o-mail-MessagingMenu-tab:has(:text('Chats')):count(1)");
});

test("last discuss conversation is remembered", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const LAST_DISCUSS_ACTIVE_ID_LS = makeRecordFieldLocalId(DiscussApp.localId(), "lastActiveId");
    window.localStorage.setItem(
        LAST_DISCUSS_ACTIVE_ID_LS,
        toRawValue(`${"discuss.channel_" + channelId}`)
    );
    await start();
    await openDiscuss();
    await waitFor('[role="heading"]:text("Welcome to #General!"):count(1)');
});

test("sidebar: default no conversation selected", async () => {
    await start();
    await openDiscuss();
    await waitFor("h4:text('No conversation selected.'):count(1)");
});

test("channel deletion fallbacks to no conversation selected", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Thread:has(:text('Welcome to #General!')):count(1)");
    pyEnv["discuss.channel"].unlink([channelId]);
    await waitFor("h4:text('No conversation selected.'):count(1)");
});

test("sidebar: change active", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        bookmarked_partner_ids: [serverState.partnerId],
        res_id: serverState.partnerId,
    });
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.NOTIFICATION);
    await waitFor("button.active:text('Notifications'):count(1)");
    await waitFor("button:not(.active):has(:text('Bookmarks')):count(1)");
    await click("button:has(:text('Bookmarks'))");
    await waitFor("button:not(.active):text('Notifications'):count(1)");
    await waitFor("button.active:has(:text('Bookmarks')):count(1)");
});

test("sidebar: basic channel rendering", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.CHANNEL);
    await waitFor(".o-mail-NotificationItem:has(:text('General')):count(1)");
    await waitFor(".o-mail-MessagingMenuItem img[alt='Thread Image']:count(1)");
    await click("[title='Channel Actions']");
    await waitFor(".o-dropdown-item:contains('Leave Conversation'):count(1)");
});

test("channel become active", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.CHANNEL);
    await waitFor(".o-mail-NotificationItem:count(1)");
    await waitForNone(".o-mail-NotificationItem.o-active");
    await click(".o-mail-NotificationItem");
    await waitFor(".o-mail-NotificationItem.o-active:count(1)");
});

test("channel become active - show composer in discuss content", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.CHANNEL);
    await click(".o-mail-NotificationItem");
    await waitFor(".o-mail-Thread:count(1)");
    await waitFor(".o-mail-Composer:count(1)");
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
    await openDiscuss(MENU_ACTIVE_IDS.CHANNEL);
    await waitFor(".o-mail-MessagingMenuItem:has(:text('general')) .badge:text(1):count(1)");
});

test("basic top bar rendering", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        bookmarked_partner_ids: [serverState.partnerId],
        res_id: channelId,
    });
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.CHANNEL);
    await click(".o-mail-NotificationItem:has(:text('General'))");
    await contains(".o-mail-DiscussContent-threadName", { value: "General" });
    await waitFor(".o-mail-DiscussContent-header button:count(8)");
    await waitFor(".o-mail-DiscussContent-header button[title='Start Video Call']:count(1)");
    await waitFor(".o-mail-DiscussContent-header button[title='Start Call']:count(1)");
    await waitFor(".o-mail-DiscussContent-header button[title='Notification Settings']:count(1)");
    await waitFor(".o-mail-DiscussContent-header button[title='Search Messages']:count(1)");
    await waitFor(".o-mail-DiscussContent-header button[title='Threads']:count(1)");
    await waitFor(".o-mail-DiscussContent-header button[title='Attachments']:count(1)");
    await waitFor(".o-mail-DiscussContent-header button[title='Pinned Messages']:count(1)");
    await waitFor(".o-mail-DiscussContent-header button[title='Members']:count(1)");
});

test("Can right-click on message to opens message actions dropdown", async () => {
    const pyEnv = await startServer();
    const [channelId, testChannelId] = pyEnv["discuss.channel"].create([
        { name: "General" },
        { name: "test" },
    ]);
    let lastOnContextMenuEv;
    patch(Message.prototype, {
        onContextMenu(ev) {
            lastOnContextMenuEv = ev;
            expect.step("Message.onContextMenu");
            super.onContextMenu(...arguments);
        },
        onOpenRightClickMenu() {
            expect.step("Message.onOpenRightClickMenu");
            super.onOpenRightClickMenu(...arguments);
        },
    });
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            body: "message-body-1",
            model: "discuss.channel",
            needaction: true,
            res_id: testChannelId,
        },
        {
            body: "msg-body-2 <a href='#'>Test link</a><a href='#'><font>Test link 2</font></a>",
            model: "discuss.channel",
            needaction: true,
            res_id: testChannelId,
        },
        {
            body: "msg-body-3 <a href='#'>Test link</a><a href='#'><font>Test link 2</font></a>",
            message_type: "email",
            model: "discuss.channel",
            needaction: true,
            res_id: testChannelId,
        },
        {
            body: "message-body-4",
            model: "discuss.channel",
            pinned_at: "2023-03-30 11:27:11",
            res_id: channelId,
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId_1,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
        {
            mail_message_id: messageId_2,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
    ]);
    await start();
    await openDiscuss(testChannelId);
    await waitFor(".o-mail-Message:count(3)");
    await rightClick(".o-mail-Message:eq(0)");
    await animationFrame();
    await expect.waitForSteps(["Message.onContextMenu", "Message.onOpenRightClickMenu"]);
    expect(lastOnContextMenuEv.defaultPrevented).toBe(true);
    await waitFor(".o-dropdown-item:count(7)");
    await waitFor(".o-dropdown-item:contains('Add a Reaction'):count(1)");
    await waitFor(".o-dropdown-item:contains('Bookmark'):count(1)");
    await waitFor(".o-dropdown-item:contains('Mark as Unread'):count(1)");
    await waitFor(".o-dropdown-item:contains('Reply'):count(1)");
    await waitFor(".o-dropdown-item:contains('Reply'):count(1)");
    await waitFor(".o-dropdown-item:contains('Copy Text'):count(1)");
    await waitFor(".o-dropdown-item:contains('Pin'):count(1)");
    await waitFor(".o-mail-Message:eq(0).o-selected:count(1)");
    await waitFor(".o-mail-Message:eq(1):not(.o-selected):count(1)");
    // Test right-click again doesn't show the menu (shows browser context menu instead)
    await rightClick(".o-mail-Message:eq(0)");
    await waitForNone(".o-dropdown-item");
    await animationFrame();
    expect.verifySteps(["Message.onContextMenu"]);
    expect(lastOnContextMenuEv.defaultPrevented).toBe(false);
    // Test inner-link in body of message doesn't trigger showing of message actions
    await click(".o-mail-Thread");
    await waitForNone(".o-dropdown-item");
    await rightClick(".o-mail-Message-body:eq(1) a:eq(0)");
    await expect.waitForSteps(["Message.onContextMenu"]);
    await animationFrame();
    expect.verifySteps([]);
    await rightClick(".o-mail-Message-body:eq(1) a:eq(1) font");
    await expect.waitForSteps(["Message.onContextMenu"]);
    await animationFrame();
    expect.verifySteps([]);
    // ...also inside shadow DOM (messages of type 'email')
    await click(".o-mail-Thread");
    await waitForNone(".o-dropdown-item");
    await rightClick(".o-mail-Message-body:eq(2) .o-mail-Message-shadowBody:shadow a:eq(0)");
    await expect.waitForSteps(["Message.onContextMenu"]);
    await animationFrame();
    expect.verifySteps([]);
    await rightClick(".o-mail-Message-body:eq(2) .o-mail-Message-shadowBody:shadow a:eq(1) font");
    await expect.waitForSteps(["Message.onContextMenu"]);
    await animationFrame();
    expect.verifySteps([]);
    expect(lastOnContextMenuEv.defaultPrevented).toBe(false);
    // Test Pinned Panel right-click doesn't show message actions
    await click(".o-mail-MessagingMenu-tab[data-id='channel']");
    await click(".o-mail-NotificationItem:has(:text('General'))");
    await waitFor(".o-mail-DiscussContent-threadName:value('General'):count(1)");
    await click("button[title='Pinned Messages']");
    await waitFor(".o-discuss-PinnedMessagesPanel .o-mail-Message:count(1)");
    await rightClick(".o-discuss-PinnedMessagesPanel .o-mail-Message");
    await expect.waitForSteps(["Message.onContextMenu"]);
    await animationFrame();
    expect.verifySteps([]);
    expect(lastOnContextMenuEv.defaultPrevented).toBe(false);
});

test("Can add reaction from right-click on message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    pyEnv["mail.message"].create({
        body: "message-body-1",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Message:count(1)");
    await rightClick(".o-mail-Message");
    await click(".o-dropdown-item:contains('Add a Reaction')");
    await click(".o-Emoji:contains(😊)");
    await waitFor(".o-mail-MessageReaction:contains(😊):count(1)");
});

test("Unfollow message", async function () {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    const [threadFollowedId, threadNotFollowedId] = pyEnv["res.partner"].create([
        { name: "Thread followed" },
        { name: "Thread not followed" },
    ]);
    pyEnv["mail.followers"].create({
        partner_id: serverState.partnerId,
        res_id: threadFollowedId,
        res_model: "res.partner",
    });
    const threadIds = [threadFollowedId, threadFollowedId, threadNotFollowedId];
    const messageIds = pyEnv["mail.message"].create(
        threadIds.map((threadId) => ({
            body: "not empty",
            model: "res.partner",
            needaction: true,
            res_id: threadId,
        }))
    );
    pyEnv["mail.notification"].create(
        messageIds.map((messageId) => ({
            mail_message_id: messageId,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        }))
    );
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.NOTIFICATION);
    await waitFor(".o-mail-MessagingMenuItem:count(3)");
    await click(
        ".o-mail-MessagingMenuItem:has(:text('Thread followed')):eq(0) [title='Message Actions']"
    );
    await waitFor(".o-dropdown-item:contains('Unfollow'):count(1)");
    await click(
        ".o-mail-MessagingMenuItem:has(:text('Thread followed')):eq(1) [title='Message Actions']"
    );
    await waitFor(".o-dropdown-item:contains('Unfollow'):count(1)");
    await click(
        ".o-mail-MessagingMenuItem:has(:text('Thread not followed')) [title='Message Actions']"
    );
    await waitForNone(".o-dropdown-item:contains('Unfollow')");
    await click(
        ".o-mail-MessagingMenuItem:has(:text('Thread followed')):eq(0) [title='Message Actions']"
    );
    await click(".o-dropdown-item:contains('Unfollow')");
    // Unfollowing message 0 marks all messages of the thread as read -> All messages on 'Thread followed' removed
    await waitFor(".o-mail-MessagingMenuItem:count(1)");
    await click(
        ".o-mail-MessagingMenuItem:has(:text('Thread not followed')) [title='Message Actions']"
    );
    await waitForNone(".o-dropdown-item:contains('Unfollow')");
});

test("messages marked as read leave the unread filter but remain in the full inbox", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            body: "not empty",
            model: "res.partner",
            needaction: true,
            res_id: serverState.partnerId,
        },
        {
            body: "not empty",
            model: "res.partner",
            needaction: true,
            res_id: serverState.partnerId,
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
    await openDiscuss(MENU_ACTIVE_IDS.NOTIFICATION);
    await waitFor("button.active:has(:text('Notifications')):count(1)");
    await waitFor("button.o-active:text('Unread'):count(1)");
    await waitFor(".o-mail-MessagingMenuItem:count(2)");
    await click("button:text('Mark all read')");
    await waitFor("button.active:has(:text('Notifications')):count(1)");
    await waitFor(`.o-mail-MessagingMenuEmpty:has(:text("You're all caught up!")):count(1)`);
    await click("button:text('All')");
    await waitFor(".o-mail-MessagingMenuItem:count(2)");
});

test("mark a single message as read removes it from the unread filter but keeps it in the full inbox", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
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
    await openDiscuss(MENU_ACTIVE_IDS.NOTIFICATION);
    await waitFor("button.active:has(:text('Notifications')):count(1)");
    await waitFor(".o-mail-MessagingMenuItem:count(2)");
    await click(
        ".o-mail-MessagingMenuItem:has(:text('You: not empty 1')) [title='Message Actions']"
    );
    await click("button:text('Mark as Read')");
    await waitFor(".o-mail-MessagingMenuItem:count(1)");
    await waitFor(".o-mail-MessagingMenuItem:has(:text('You: not empty 2')):count(1)");
    await click("button:text('All')");
    await waitFor(".o-mail-MessagingMenuItem:count(2)");
    await waitFor(".o-mail-MessagingMenuItem:has(:text('You: not empty 1')):count(1)");
    await waitFor(".o-mail-MessagingMenuItem:has(:text('You: not empty 2')):count(1)");
});

test("full inbox shows all messages after marking all as read and clearing the unread filter", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    for (let i = 0; i < 40; i++) {
        const messageId = pyEnv["mail.message"].create({
            body: i + "",
            needaction: true,
        });
        pyEnv["mail.notification"].create({
            mail_message_id: messageId,
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        });
    }
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.NOTIFICATION);
    await waitFor(".o-mail-MessagingMenuItem:count(20)");
    await click("button:text('Mark all read')");
    await waitFor(`.o-mail-MessagingMenuEmpty:has(:text("You're all caught up!")):count(1)`);
    await click("button:text('All')");
    await scroll(".o-mail-MessagingMenu-tabContent", "bottom");
    await waitFor(".o-mail-MessagingMenuItem:count(40)");
});

test("post a simple message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const { promise: messagePostPromise, resolve: resolveMessagePost } = Promise.withResolvers();
    onRpcBefore("/mail/message/post", async (args) => {
        expect.step("message_post");
        expect(args.thread_model).toBe("discuss.channel");
        expect(args.thread_id).toBe(channelId);
        expect(args.post_data.body).toBe("Test");
        expect(args.post_data.message_type).toBe("comment");
        expect(args.post_data.subtype_xmlid).toBe("mail.mt_comment");
        await messagePostPromise;
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Thread:has(:text('Welcome to #general!')):count(1)");
    await waitForNone(".o-mail-Message");
    await insertTextInComposer(".o-mail-Composer", "Test");
    await press("Enter");
    await expect.waitForSteps(["message_post"]);
    // optimistically show posted message
    await containsTextInComposer(".o-mail-Composer", "");
    await waitFor(".o-mail-Message-author:text('Mitchell Admin'):count(1)");
    await waitFor(".o-mail-Message-content:text('Test'):count(1)");
    expect(".o-mail-Message-content").toHaveStyle({ opacity: "0.5" });
    await waitFor(".o-mail-Message-pendingProgress:count(1)"); // visible after 0.5 sec. elapsed
    // simulate message genuinely posted
    resolveMessagePost();
    await waitForNone(".o-mail-Message-pendingProgress");
    await waitFor(".o-mail-Message-content:text('Test'):count(1)");
    expect(".o-mail-Message-content").toHaveStyle({ opacity: "1" });
});

test("post several messages with failures", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    /** awaiting deferreds of message_post of msg 0, 1, 2 respectively  */
    const messagePostPromWithResolvers = [
        Promise.withResolvers(),
        Promise.withResolvers(),
        Promise.withResolvers(),
    ];
    onRpcBefore("/mail/message/post", async (args) => {
        await messagePostPromWithResolvers[parseInt(args.post_data.body)].promise;
    });
    await start();
    await openDiscuss(channelId);
    // post 3 messages
    await waitFor(".o-mail-Thread:has(:text('Welcome to #general!')):count(1)");
    await waitForNone(".o-mail-Message");
    await insertTextInComposer(".o-mail-Composer", "0");
    await press("Enter");
    await containsTextInComposer(".o-mail-Composer", "");
    await insertTextInComposer(".o-mail-Composer", "1");
    await press("Enter");
    await containsTextInComposer(".o-mail-Composer", "");
    await insertTextInComposer(".o-mail-Composer", "2");
    await press("Enter");
    await containsTextInComposer(".o-mail-Composer", "");
    await waitFor(".o-mail-Message-author:text('Mitchell Admin'):count(1)");
    await contains(".o-mail-Thread", {
        contains: [
            [".o-mail-Message-content:text('0')"],
            [".o-mail-Message-content:text('1')"],
            [".o-mail-Message-content:text('2')"],
        ],
    });
    // all are pending
    expect(".o-mail-Message-content:eq(0)").toHaveStyle({ opacity: "0.5" });
    expect(".o-mail-Message-content:eq(1)").toHaveStyle({ opacity: "0.5" });
    expect(".o-mail-Message-content:eq(2)").toHaveStyle({ opacity: "0.5" });
    await waitFor(".o-mail-Message-pendingProgress:count(3)"); // visible after 0.5 sec. elapsed
    // simulate OK for 1, NOT-OK for 0, 2
    messagePostPromWithResolvers[0].reject();
    messagePostPromWithResolvers[1].resolve();
    messagePostPromWithResolvers[2].reject();
    await waitForNone(".o-mail-Message-pendingProgress");
    expect(".o-mail-Message-content:eq(0)").toHaveStyle({ opacity: "0.5" });
    expect(".o-mail-Message-content:eq(1)").toHaveStyle({ opacity: "1" });
    expect(".o-mail-Message-content:eq(2)").toHaveStyle({ opacity: "0.5" });
    // re-try failed posted messages
    messagePostPromWithResolvers[0] = true;
    messagePostPromWithResolvers[2] = true;
    await click(
        ".o-mail-Message:contains(0) button[title='Failed to post the message. Click to retry']"
    );
    await click(
        ".o-mail-Message:contains(2) button[title='Failed to post the message. Click to retry']"
    );
    // check all genuinely posted
    await contains(".o-mail-Thread", {
        contains: [
            [".o-mail-Message-content:not(.opacity-50):text('1')"], // was ok before
            [".o-mail-Message-content:not(.opacity-50):text('0')"],
            [".o-mail-Message-content:not(.opacity-50):text('2')"],
        ],
    });
    expect(".o-mail-Message-content:eq(0)").toHaveStyle({ opacity: "1" });
    expect(".o-mail-Message-content:eq(1)").toHaveStyle({ opacity: "1" });
    expect(".o-mail-Message-content:eq(2)").toHaveStyle({ opacity: "1" });
});

test("failed message tooltip includes the server error", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    onRpcBefore("/mail/message/post", () => {
        throw makeServerError({ message: "Error message" });
    });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "Test");
    await press("Enter");
    await waitFor(
        ".o-mail-Message button[title='Failed to post the message (Error message). Click to retry']:count(1)"
    );
});

test("bookmarked: unbookmark all", async () => {
    const pyEnv = await startServer();
    pyEnv["mail.message"].create([
        { body: "not empty", bookmarked_partner_ids: [serverState.partnerId] },
        { body: "not empty", bookmarked_partner_ids: [serverState.partnerId] },
    ]);
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.BOOKMARK);
    await waitFor(".o-mail-MessagingMenuItem:count(2)");
    await contains("button:has(:text('Bookmarks'))", { contains: [".badge:text('2')"] });
    await click("button:enabled:text('Remove all')");
    await waitForNone(".o-mail-MessagingMenu-tab:has(:text('Bookmarks'))");
    await waitForNone(".o-mail-MessagingMenuItem");
});

test.tags("focus required");
test("auto-focus composer on opening thread", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
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
    await openDiscuss(MENU_ACTIVE_IDS.CHANNEL);
    await waitFor(".o-mail-Discuss:has(:text('No conversation selected.')):count(1)");
    await click(".o-mail-NotificationItem:has(:text('General'))");
    await waitFor(".o-mail-NotificationItem.o-active:has(:text('General')):count(1)");
    await waitFor(".o-mail-Composer-input:focus:count(1)");
    await click(".o-mail-MessagingMenu-tab[data-id='chat']");
    await click(".o-mail-NotificationItem:has(:text('Demo User'))");
    await waitFor(".o-mail-NotificationItem.o-active:has(:text('Demo User')):count(1)");
    await waitFor(".o-mail-Composer-input:focus:count(1)");
});

test("no out-of-focus notification on receiving self messages in chat", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    patch(document, {
        set title(value) {
            const match = value.match(/^\((\d+)\) .*/);
            if (match) {
                expect.step(`set_counters:discuss:${match[1]}`);
            }
        },
    });
    await start();
    await waitFor(".o_menu_systray i[aria-label='Messages']:count(1)");
    await waitForNone(".o-mail-ChatWindow");
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
    await openMessagingMenu();
    await waitFor(".o-mail-NotificationItem-text:text('You: New message'):count(1)");
    await waitForNone(".o-mail-ChatWindow");
    await expect.waitForSteps([]);
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
    patch(document, {
        set title(value) {
            const match = value.match(/^\((\d+)\) .*/);
            if (match) {
                expect.step(`set_counters:discuss:${match[1]}`);
            }
        },
    });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    await waitFor(".o_menu_systray i[aria-label='Messages']:count(1)");
    await waitForNone(".o-mail-ChatWindow");
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
    await waitFor(".o-mail-ChatBubble:count(1)");
    await expect.waitForSteps(["set_counters:discuss:1"]);
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
    patch(document, {
        set title(value) {
            const match = value.match(/^\((\d+)\) .*/);
            if (match) {
                expect.step(`set_counters:discuss:${match[1]}`);
            }
        },
    });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    await waitFor(".o_menu_systray i[aria-label='Messages']:count(1)");
    await waitForNone(".o-mail-ChatWindow");
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
    await waitFor(".o-mail-ChatBubble:count(1)");
    await expect.waitForSteps(["set_counters:discuss:1"]);
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
    patch(document, {
        set title(value) {
            const match = value.match(/^\((\d+)\) .*/);
            if (match) {
                expect.step(`set_counters:discuss:${match[1]}`);
            }
        },
    });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await waitForNone(".o-mail-ChatWindow");
    // simulate receving new message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "New message", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await openMessagingMenu();
    await waitFor(".o-mail-NotificationItem-text:text('Dumbledore: New message'):count(1)");
    await waitForNone(".o-mail-ChatWindow");
    await expect.waitForSteps([]);
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
    patch(document, {
        set title(value) {
            const match = value.match(/^\((\d+)\) .*/);
            if (match) {
                stepCount++;
                const count = parseInt(match[1]);
                expect.step(`set_counters:discuss`);
                if (stepCount === 1) {
                    expect(count).toBe(1);
                }
                if (stepCount === 2) {
                    expect(count).toBe(2);
                }
                if (stepCount === 3) {
                    expect(count).toBe(3);
                }
            }
        },
    });
    await start();
    await openDiscuss();
    await waitFor(".o-mail-MessagingMenuItem:count(2)");
    // simulate receiving a new message in chat 1 with odoo out-of-focused
    await withUser(bobUserId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello world!", message_type: "comment" },
            thread_id: channelId_1,
            thread_model: "discuss.channel",
        })
    );
    await expect.waitForSteps(["set_counters:discuss"]);
    // simulate receiving a new message in chat 2 with odoo out-of-focused
    await withUser(bobUserId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello world!", message_type: "comment" },
            thread_id: channelId_2,
            thread_model: "discuss.channel",
        })
    );
    await expect.waitForSteps(["set_counters:discuss"]);
    // simulate receiving another new message in chat 2 with odoo focused
    await withUser(bobUserId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello world!", message_type: "comment" },
            thread_id: channelId_2,
            thread_model: "discuss.channel",
        })
    );
    await expect.waitForSteps(["set_counters:discuss"]);
});

test("new message in tab title has precedence over action name", async () => {
    const pyEnv = await startServer();
    patch(document, {
        set title(newTitle) {
            if (newTitle?.includes("General")) {
                expect.step(newTitle);
            }
        },
    });
    const bobUserId = pyEnv["res.users"].create({ name: "bob" });
    const bobPartnerId = pyEnv["res.partner"].create({ name: "bob", user_ids: [bobUserId] });
    const [channelId, initialChannelId] = pyEnv["discuss.channel"].create([
        {
            channel_type: "chat",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: bobPartnerId }),
            ],
        },
        { name: "General" },
    ]);
    await start();
    await openDiscuss(initialChannelId);
    await contains(".o-mail-DiscussContent-threadName", { value: "General" }); // wait for action name being Inbox
    await expect.waitForSteps(["General"]);
    // simulate receiving a new message in chat 1 with odoo out-of-focused
    await withUser(bobUserId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello world!", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await expect.waitForSteps(["(1) General"]);
});

test("out-of-focus notif takes new inbox messages into account", async () => {
    const pyEnv = await startServer();
    patch(document, {
        set title(newTitle) {
            if (newTitle === "(1) Odoo") {
                expect.step(newTitle);
            }
        },
    });
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    await openDiscuss();
    await openMessagingMenu(MENU_ACTIVE_IDS.NOTIFICATION);
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
    await expect.waitForSteps(["(1) Odoo"]);
});

test("out-of-focus notif respects push subscription eligibility", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    const partnerId = pyEnv["res.partner"].create({ name: "Hagrid" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    patch(OutOfFocusService.prototype, {
        async notify() {
            expect.step("notification handled");
            await super.notify(...arguments);
        },
        async hasServiceWorkInstalledAndPushSubscriptionActive() {
            return true;
        },
        sendNotification() {
            expect.step("send_notification");
        },
    });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    await openDiscuss();
    const adminId = serverState.partnerId;
    const post = (author, message_type) =>
        withUser(author, () =>
            rpc("/mail/message/post", {
                post_data: { body: "hello", partner_ids: [adminId], message_type },
                thread_id: partnerId,
                thread_model: "res.partner",
            })
        );
    // pushed type, not self-authored → JS bails, push handles it
    await post(userId, "comment");
    await expect.waitForSteps(["notification handled"]);
    // non-pushed type → whitelist rejects → JS fires
    await post(userId, "auto_comment");
    await expect.waitForSteps(["notification handled", "send_notification"]);
    // self-authored → author excluded from push → JS fires
    await post(serverState.userId, "comment");
    await expect.waitForSteps(["notification handled", "send_notification"]);
});

test("out-of-focus notif body shows attachment symbol for attachment-only message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Norris" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "group",
    });
    const attachmentId = pyEnv["ir.attachment"].create({
        mimetype: "image/png",
        name: "picture.png",
        res_id: false,
        res_model: "mail.compose.message",
    });
    patch(OutOfFocusService.prototype, {
        sendNotification({ message }) {
            expect.step(message);
        },
    });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    await openDiscuss();
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: {
                attachment_ids: [attachmentId],
                body: "",
                message_type: "comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await expect.waitForSteps(["Norris: 📷\u00A0\u00A0picture.png"]);
});

test("out-of-focus notif on needaction message in group chat contributes only once", async () => {
    const pyEnv = await startServer();
    patch(document, {
        set title(newTitle) {
            if (newTitle === "(1) Odoo") {
                expect.step(newTitle);
            }
        },
    });
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
    await waitFor(".o-mail-MessagingMenu-tab:has(:text('Chats')) .badge:text(1):count(1)");
    await expect.waitForSteps(["(1) Odoo"]);
});

test("inbox notifs shouldn't play sound nor open chat bubble", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["discuss.channel"].create({ name: "general", channel_type: "channel" });
    patch(OutOfFocusService.prototype, {
        _playSound() {
            expect.step("play_sound");
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
                needaction: true,
            },
            thread_id: partnerId,
            thread_model: "res.partner",
        })
    );
    await waitFor(".o-mail-MessagingMenuInDropdown-counter:text('1'):count(1)");
    // check no chat window nor chat bubble spawn: can be delayed, hence opening and folding chat by hand
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await click(".o-mail-MessagingMenu button:contains(general)");
    await waitFor(".o-mail-ChatWindow:contains(general):count(1)");
    await waitFor(".o-mail-ChatWindow:count(1)");
    await click(".o-mail-ChatWindow button[title='Fold']");
    await waitFor(".o-mail-ChatBubble:count(1)"); // no other chat bubble other than manually folded one
    await expect.waitForSteps([]); // no sound alert whatsoever
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
            expect.step(`sound:${soundEffectName}`);
            return super.play(soundEffectName, ...args);
        },
    });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    await waitFor(".o_menu_systray i[aria-label='Messages']:count(1)");
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
    await expect.waitForSteps(["sound:new-message"]);
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
            expect.step(`sound:${soundEffectName}`);
            return super.play(soundEffectName, ...args);
        },
    });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    await waitFor(".o_menu_systray i[aria-label='Messages']:count(1)");
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
    await expect.waitForSteps(["sound:new-message"]);
    // simulate message sound settings turned off
    const MESSAGE_SOUND_LS = makeRecordFieldLocalId(Settings.localId(), "messageSound");
    window.localStorage.setItem(MESSAGE_SOUND_LS, toRawValue(false));
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
    window.localStorage.removeItem(MESSAGE_SOUND_LS);
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
    await expect.waitForSteps(["sound:new-message"]);
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
    await waitFor(".o-mail-MessagingMenu-tab:has(:text('Chats')):count(1)");
    await waitForNone(".o-mail-MessagingMenuItem:has(:text('Demo'))");
    // simulate receiving the first message on channel 11
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "What do you want?", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await waitFor(".o-mail-MessagingMenuItem:has(:text('Demo')):count(1)");
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
    await waitFor("button[title='Invite People']:count(1)");
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
    await waitFor(".o-mail-DiscussContent-header .o-mail-DiscussContent-threadAvatar:count(1)");
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
    await waitFor(".o-mail-DiscussContent-header .o-mail-DiscussContent-threadAvatar:count(1)");
});

test("Partner IM status is displayed as thread icon in top bar of channels of type 'chat'", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2, partnerId_3, partnerId_4] = pyEnv["res.partner"].create([
        { name: "Michel Online" },
        { name: "Jacqueline Offline" },
        { name: "Nabuchodonosor Idle" },
        { name: "Robert Fired" },
    ]);
    pyEnv["res.users"].create([
        { partner_id: partnerId_1, im_status: "online" },
        { partner_id: partnerId_2, im_status: "offline" },
        { partner_id: partnerId_3, im_status: "away" },
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
    await click(".o-mail-NotificationItem:has(:text('Michel Online'))");
    await waitFor(
        ".o-mail-DiscussContent-header .o-mail-ImStatus[title='User is online']:count(1)"
    );
    await click(".o-mail-NotificationItem:has(:text('Jacqueline Offline'))");
    await waitFor(
        ".o-mail-DiscussContent-header .o-mail-ImStatus[title='User is offline']:count(1)"
    );
    await click(".o-mail-NotificationItem:has(:text('Nabuchodonosor Idle'))");
    await waitFor(".o-mail-DiscussContent-header .o-mail-ImStatus[title='User is idle']:count(1)");
    await click(".o-mail-NotificationItem:has(:text('Robert Fired'))");
    await waitForNone(".o-mail-DiscussContent-header .o-mail-ImStatus");
    await click(".o-mail-NotificationItem:has(:text('OdooBot'))");
    await waitFor(".o-mail-DiscussContent-header .o-mail-ImStatus[title='User is a bot']:count(1)");
});

test("Thread avatar image is displayed in top bar of channels of type 'group'", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "group" });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-DiscussContent-header .o-mail-DiscussContent-threadAvatar:count(1)");
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
    await waitFor(".o-mail-DiscussContent-threadName[title='GroupChat']:count(1)");
    await waitFor(".o-mail-DiscussContent-threadAvatar [data-icon='edit']:count(1)");
    await click(".o-mail-NotificationItem:has(:text('Demo'))");
    await waitFor(".o-mail-DiscussContent-threadName[title='Demo']:count(1)");
    await waitForNone(".o-mail-DiscussContent-threadAvatar [data-icon='edit']");
});

test("Do not trigger channel name server update when it is unchanged", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });

    onRpc("discuss.channel", "channel_rename", ({ method }) => expect.step(method));

    await start();
    await openDiscuss(channelId);
    await insertText("input.o-mail-DiscussContent-threadName:enabled", "General", {
        replace: true,
    });
    triggerHotkey("Enter");
    await expect.waitForSteps([]);
});

test("Do not trigger channel description server update when channel has no description and editing to empty description", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        create_uid: serverState.userId,
        name: "General",
    });

    onRpc("discuss.channel", "channel_change_description", ({ method }) => expect.step(method));

    await start();
    await openDiscuss(channelId);
    await insertText("input.o-mail-DiscussContent-threadDescription", "");
    triggerHotkey("Enter");
    await expect.waitForSteps([]);
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
    await openDiscuss(MENU_ACTIVE_IDS.CHANNEL);
    await waitFor(".o-mail-MessagingMenuItem:has(:text('my channel')):count(1)");
    await waitForNone(".o-mail-MessagingMenuItem:has(:text('General'))");
    const adminUserId = serverState.userId;
    await withUser(userId, () =>
        getService("mail.store").fetchStoreData("/discuss/channel/add_members", {
            channel_id: channelId,
            user_ids: [adminUserId],
        })
    );
    await waitFor(".o-mail-MessagingMenuItem:has(:text('General')):count(1)");
});

test("select another mailbox", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.NOTIFICATION);
    await waitFor(".o-mail-Discuss:count(1)");
    await waitFor(`.o-mail-MessagingMenuEmpty:has(:text("You're all caught up!")):count(1)`);
    await click("button:text('Unread')");
    await waitFor(`.o-mail-MessagingMenuEmpty:has(:text("You're all caught up!")):count(1)`);
});

test("composer should be focused automatically after clicking on the send button", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "Dummy Message");
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
        expect.step(`rpc:mark_as_read - ${args.channel_id}`);
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
    await expect.waitForSteps([`rpc:mark_as_read - ${channelId_2}`]);
    await click(".o-mail-NotificationItem:has(:text('Bla'))");
    await expect.waitForSteps([`rpc:mark_as_read - ${channelId_1}`]);
});

test("warning on send with shortcut when attempting to post message with still-uploading attachments", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    onRpcBefore("/mail/attachment/upload", () => new Promise(() => {})); // simulates an attachment upload that never completes
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer input[type=file]:count(1)");
    const file = new File(["hello, world"], "text.txt", { type: "text/plain" });
    await insertTextInComposer(".o-mail-Composer", "Dummy Message");
    await editInput(document.body, ".o-mail-Composer input[type=file]", [file]);
    await waitFor(
        ".o-mail-AttachmentContainer.o-isUploading:contains(text.txt) [data-icon='autorenew']:count(1)"
    );
    await waitFor(".o-mail-Composer button[title='Send']:disabled:count(1)");
    await press("Enter"); // Try to send message
    await waitFor(".o_notification:text('Please wait while the file is uploading.'):count(1)");
});

test("[text composer] Can post message with only attachment", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    onRpcBefore("/mail/message/post", () => new Promise(() => {}));
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer input[type=file]:count(1)");
    const file = new File(["hello, world"], "text.txt", { type: "text/plain" });
    await editInput(document.body, ".o-mail-Composer input[type=file]", [file]);
    await waitFor(
        ".o-mail-AttachmentContainer:not(.o-isUploading):contains('text.txt'):not(:has([data-icon='autorenew'])):count(1)"
    );
    await press("Enter");
    await waitFor(".o-mail-Message:count(1)");
    await waitFor(".o-mail-Message .o-mail-AttachmentContainer:contains('text.txt'):count(1)");
    await waitForNone(".o-mail-Message .o-mail-Message-bubble");
});

test.tags("html composer");
test("Can post message with only attachment", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    onRpcBefore("/mail/message/post", () => new Promise(() => {}));
    await start();
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer input[type=file]:count(1)");
    const file = new File(["hello, world"], "text.txt", { type: "text/plain" });
    await editInput(document.body, ".o-mail-Composer input[type=file]", [file]);
    await waitFor(
        ".o-mail-AttachmentContainer:not(.o-isUploading):contains('text.txt'):not(:has([data-icon='autorenew'])):count(1)"
    );
    await press("Enter");
    await waitFor(".o-mail-Message:count(1)");
    await waitFor(".o-mail-Message .o-mail-AttachmentContainer:contains('text.txt'):count(1)");
    await waitForNone(".o-mail-Message .o-mail-Message-bubble");
});

test("failure on loading messages should display error", async () => {
    let messageFetchShouldFail = false;
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Target" });
    // Chat channel_type: no member panel, so fetchChannelMembers won't race with the failing messages fetch.
    const chatId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    listenStoreFetch(
        ["/discuss/channel/messages", "/mail/messaging_menu/discuss.channel/load_more"],
        {
            onRpc() {
                if (messageFetchShouldFail) {
                    return Promise.reject();
                }
            },
        }
    );
    await start();
    // Let all init RPCs settle so they are not in the same batch as the failing messages fetch.
    await openDiscuss();
    await waitStoreFetch("/mail/messaging_menu/discuss.channel/load_more");
    messageFetchShouldFail = true;
    await openDiscuss(chatId);
    await waitFor(
        ".o-mail-Thread:has(:text('An error occurred while loading messages.')):count(1)"
    );
});

test("failure on loading messages should prompt retry button", async () => {
    let messageFetchShouldFail = false;
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Target" });
    // Chat channel_type: no member panel, so fetchChannelMembers won't race with the failing messages fetch.
    const chatId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    listenStoreFetch(
        ["/discuss/channel/messages", "/mail/messaging_menu/discuss.channel/load_more"],
        {
            onRpc() {
                if (messageFetchShouldFail) {
                    return Promise.reject();
                }
            },
        }
    );
    await start();
    // Let all init RPCs settle so they are not in the same batch as the failing messages fetch.
    await openDiscuss();
    await waitStoreFetch("/mail/messaging_menu/discuss.channel/load_more");
    messageFetchShouldFail = true;
    await openDiscuss(chatId);
    await waitFor("button:text('Try again'):count(1)");
});

test("Retry on failed initial load should load messages", async () => {
    let messageFetchShouldFail = false;
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Target" });
    // Chat channel_type: no member panel, so fetchChannelMembers won't race with the failing messages fetch.
    const chatId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const messageIds = pyEnv["mail.message"].create(
        range(60).map((i) => ({
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: chatId,
        }))
    );
    const [selfMember] = pyEnv["discuss.channel.member"].search_read([
        ["partner_id", "=", serverState.partnerId],
        ["channel_id", "=", chatId],
    ]);
    pyEnv["discuss.channel.member"].write([selfMember.id], {
        new_message_separator: messageIds[29],
    });
    listenStoreFetch(
        ["/discuss/channel/messages", "/mail/messaging_menu/discuss.channel/load_more"],
        {
            onRpc() {
                if (messageFetchShouldFail) {
                    return Promise.reject();
                }
            },
        }
    );
    await start();
    // Let all init RPCs settle so they are not in the same batch as the failing messages fetch.
    await openDiscuss();
    await waitStoreFetch("/mail/messaging_menu/discuss.channel/load_more");
    messageFetchShouldFail = true;
    await openDiscuss(chatId);
    await waitFor("button:text('Try again'):count(1)");
    messageFetchShouldFail = false;
    await click("button:text('Try again')");
    await waitStoreFetch("/discuss/channel/messages");
    await waitFor(".o-mail-Message:count(60)");
    await waitFor(".o-mail-Thread-newMessage:count(1)");
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
        range(60).map(() => ({
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
    listenStoreFetch("/discuss/channel/messages", {
        onRpc() {
            if (messageFetchShouldFail) {
                return Promise.reject();
            }
        },
    });
    await start();
    await openDiscuss(channelId);
    await waitStoreFetch("/discuss/channel/messages");
    await waitFor(".o-mail-Message:count(30)");
    messageFetchShouldFail = true;
    await click("button:text('Load More')");
    await waitFor(
        ".o-mail-Thread:has(:text('An error occurred while loading messages.')):count(1)"
    );
    await waitFor("button:text('Try again'):count(1)");
    await waitForNone("button:text('Load More')");
});

test("Retry loading more messages on failed load more messages should load more messages", async () => {
    // The initial load and the retry/success loads use the real handler; only the
    // "load more" that must fail goes through messageFetchDeferred. It is rejected
    // only once the fetch is in flight (waitForSteps), so that while it is pending a
    // duplicate IntersectionObserver fire no-ops on status "loading" and cannot leave
    // an orphaned fetch racing the retry click.
    let messageFetchDeferred;
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    const messageIds = pyEnv["mail.message"].create(
        range(90).map(() => ({
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
    listenStoreFetch("/discuss/channel/messages", {
        async onRpc() {
            if (messageFetchDeferred) {
                expect.step("load more messages");
                await messageFetchDeferred.promise;
            }
        },
    });
    await start();
    await openDiscuss(channelId);
    await waitStoreFetch("/discuss/channel/messages");
    await waitFor(".o-mail-Message:count(30)");
    messageFetchDeferred = Promise.withResolvers();
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await scroll(".o-mail-Thread", 0);
    await expect.waitForSteps(["load more messages"]);
    messageFetchDeferred.reject(new Error("Simulated load more failure"));
    await waitFor("button:text('Try again'):count(1)");
    messageFetchDeferred = undefined;
    await click("button:text('Try again')");
    await waitStoreFetch("/discuss/channel/messages");
    await waitFor(".o-mail-Message:count(60)");
    await scroll(".o-mail-Thread", 0);
    await waitStoreFetch("/discuss/channel/messages");
    await waitFor(".o-mail-Message:count(90)");
});

test("composer state: attachments save and restore", async () => {
    const pyEnv = await startServer();
    const [channelId] = pyEnv["discuss.channel"].create([{ name: "General" }, { name: "Special" }]);
    await start();
    await openDiscuss(channelId);
    await waitFor(
        ".o-mail-Composer:has(textarea[placeholder='Message #General…']) input[type=file]:count(1)"
    );
    // Add attachment in a message for #general
    const file = new File(["hello, world"], "text.txt", { type: "text/plain" });
    await editInput(
        document.body,
        ".o-mail-Composer:has(textarea[placeholder='Message #General…']) input[type=file]",
        [file]
    );
    await waitFor(
        ".o-mail-Composer .o-mail-AttachmentContainer:not(.o-isUploading):contains(text.txt):count(1)"
    );
    await waitFor(".o-mail-Composer .o-mail-AttachmentContainer:count(1)");
    // Switch to #special
    await click(".o-mail-NotificationItem:has(:text('Special'))");
    // Attach files in a message for #special
    const files = [
        new File(["hello2, world"], "text2.txt", { type: "text/plain" }),
        new File(["hello3, world"], "text3.txt", { type: "text/plain" }),
        new File(["hello4, world"], "text4.txt", { type: "text/plain" }),
    ];
    await waitFor(
        ".o-mail-Composer:has(textarea[placeholder='Message #Special…']) input[type=file]:count(1)"
    );
    await editInput(
        document.body,
        ".o-mail-Composer:has(textarea[placeholder='Message #Special…']) input[type=file]",
        files
    );
    await waitFor(".o-mail-Composer .o-mail-AttachmentContainer:not(.o-isUploading):count(3)");
    await waitFor(".o-mail-Composer .o-mail-AttachmentContainer:count(3)");
    // Switch back to #general
    await click(".o-mail-NotificationItem:has(:text('General'))");
    await waitFor(".o-mail-Composer .o-mail-AttachmentContainer:count(1)");
    await waitFor(".o-mail-Composer .o-mail-AttachmentContainer:contains(text.txt):count(1)");
    // Switch back to #special
    await click(".o-mail-NotificationItem:has(:text('Special'))");
    await waitFor(".o-mail-Composer .o-mail-AttachmentContainer:count(3)");
    await waitFor(".o-mail-AttachmentCard-info:text('text2.txt'):count(1)");
    await waitFor(".o-mail-AttachmentCard-info:text('text3.txt'):count(1)");
    await waitFor(".o-mail-AttachmentCard-info:text('text4.txt'):count(1)");
});

test("sidebar: cannot leave channel with group_ids", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        {
            name: "General",
            group_ids: [Command.create({ name: "test" })],
        },
        {
            name: "Special",
        },
    ]);
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.CHANNEL);
    await click(".o-mail-NotificationItem:has(:text('General')) [title='Channel Actions']");
    await waitFor(".dropdown-item:text(Notification Settings)"); // check anything else in the dropdown
    await waitForNone(".dropdown-item:text('Leave Conversation')");
    await click(".o-mail-NotificationItem:has(:text('Special')) [title='Channel Actions']");
    await waitFor(".dropdown-item:text('Leave Conversation')");
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
    await waitFor(".o-mail-Message:count(25)");
    await contains(".o-mail-Thread", { scroll: 0 });
    await tick(); // wait for the scroll to first unread to complete
    await scroll(".o-mail-Thread", "bottom");
    await click(".o-mail-NotificationItem:has(:text('Channel2'))");
    await waitFor(".o-mail-Message:count(24)");
    await contains(".o-mail-Thread", { scroll: 0 });
    await click(".o-mail-NotificationItem:has(:text('Channel1'))");
    await waitFor(".o-mail-Message:count(25)");
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await click(".o-mail-NotificationItem:has(:text('Channel2'))");
    await waitFor(".o-mail-Message:count(24)");
    await contains(".o-mail-Thread", { scroll: 0 });
});

test("Message shows up even if channel data is incomplete", async () => {
    const pyEnv = await startServer();
    await start();
    await openDiscuss();
    await waitFor(".o-mail-MessagingMenuEmpty:count(1)");
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
    const subscribePromise = waitUntilSubscribe();
    getService("bus_service").forceUpdateChannels();
    await subscribePromise;
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
    await click(".o-mail-NotificationItem:has(:text('Albert'))");
    await waitFor(".o-mail-Message-content:text('hello world'):count(1)");
});

test("Correct breadcrumb when open discuss from chat window then see settings as channel owner", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, channel_role: "owner" }),
        ],
    });
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await click(".o-mail-NotificationItem:has(:text('General'))");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor("[title='Open Actions Menu']:count(1)");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item:text('Open in Discuss')");
    await waitFor(".o-mail-MessagingMenuItem:has(:text('General')):count(1)");
    await click("[title='Channel Actions']", {
        parent: [".o-mail-MessagingMenuItem:has(:text('General'))"],
    });
    await click(".o-dropdown-item:text('Advanced Settings')");
    await waitFor(".o_breadcrumb:text('General General'):count(1)");
});

test("Chatter notification in messaging menu should open the form view even when discuss app is open", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
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
    await openMessagingMenu(MENU_ACTIVE_IDS.NOTIFICATION);
    await click(".o-mail-NotificationItem");
    await waitForNone(".o-mail-Discuss");
    await waitFor(".o_form_view .o-mail-Chatter:count(1)");
    await waitFor(".o_form_view .o_last_breadcrumb_item:text('TestPartner'):count(1)");
    await waitFor(
        ".o-mail-Chatter .o-mail-Message:has(:text('A needaction message to have it in messaging menu')):count(1)"
    );
});

test.tags("focus required");
test("Escape key should focus the composer if it's not focused", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Pinned Messages']");
    triggerHotkey("escape");
    await waitFor(".o-mail-Composer-input:focus:count(1)");
});

test("Notification settings: basic rendering", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "Mario Party",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-discuss-ChannelMemberList:count(1)"); // wait for auto-open of this panel
    await click("[title='Notification Settings']");
    await waitFor("button:text('All Messages'):count(1)");
    await waitFor("button:text('Mentions Only'):count(1)");
    await waitFor("button:text('Nothing'):count(1)");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor("button:text('Mute Conversation'):count(1)");
    await hover("button:has(:text('Mute Conversation'))");
    await waitFor(".o-dropdown-item:text('For 15 minutes'):count(1)");
    await waitFor(".o-dropdown-item:text('For 1 hour'):count(1)");
    await waitFor(".o-dropdown-item:text('For 3 hours'):count(1)");
    await waitFor(".o-dropdown-item:text('For 8 hours'):count(1)");
    await waitFor(".o-dropdown-item:text('For 24 hours'):count(1)");
    await waitFor(".o-dropdown-item:text('Until I turn it back on'):count(1)");
});

test("Notification settings: mute conversation will change the style of sidebar", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "Mario Party",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-NotificationItem:has(:text('Mario Party')):count(1)");
    await waitForNone(".o-mail-NotificationItem[class*='opacity-50']:text('Mario Party')");
    await click("[title='Notification Settings']");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor("button:text('Mute Conversation'):count(1)");
    await hover("button:has(:text('Mute Conversation'))");
    await click(".o-dropdown-item:text('For 15 minutes')");
    await waitFor(".o-mail-NotificationItem:has(:text('Mario Party')):count(1)");
    await waitFor(
        ".o-mail-NotificationItem[class*='opacity-50']:has(:text('Mario Party')):count(1)"
    );
});

test("Notification settings: change the mute duration of the conversation", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "Mario Party",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-MessagingMenuItem:has(:text('Mario Party')):count(1)");
    await waitForNone(".o-mail-MessagingMenuItem[class*='opacity-50']:has(:text('Mario Party'))");
    await click("[title='Notification Settings']");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor("button:text('Mute Conversation'):count(1)");
    await hover("button:has(:text('Mute Conversation'))");
    await click(".o-dropdown-item:text('For 15 minutes')");
    await click("[title='Notification Settings']");
    await click(".o-discuss-NotificationSettings span:text('Unmute Conversation')");
    await click("[title='Notification Settings']");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor("button:text('Mute Conversation'):count(1)");
    await hover("button:has(:text('Mute Conversation'))");
    await click(".o-dropdown-item:text('For 1 hour')");
});

test("Notification settings: mute/unmute conversation works correctly", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "Mario Party",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-discuss-ChannelMemberList:count(1)"); // wait for auto-open of this panel
    await click("[title='Notification Settings']");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor("button:text('Mute Conversation'):count(1)");
    await hover("button:has(:text('Mute Conversation'))");
    await click(".o-dropdown-item:text('For 15 minutes')");
    await click("[title='Notification Settings']");
    await waitFor("button:has(:text('Unmute Conversation')):count(1)");
    await click("button:has(:text('Unmute Conversation'))");
    await click("[title='Notification Settings']");
    await waitFor("button:has(:text('Unmute Conversation')):count(1)");
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
    await triggerHotkey("control+k");
    await waitFor(".o_command_name:count(3)");
    await insertText(".o_command_palette_search input[placeholder='Search conversations']", "Jer");
    await waitFor(".o_command_name:count(2)");
    await click(".o_command_name:text('Jerry Golay')");
    await contains(".o-mail-MessagingMenuItem:has(:text('Jerry Golay'))", {
        before: [".o-mail-MessagingMenuItem:has(:text('Albert'))"],
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
    await contains(".o-mail-MessagingMenuItem:has(:text('Marc Demo'))", {
        contains: [".badge:text('1')"],
    });
    // simulate deleted message
    rpc("/mail/message/update_content", {
        message_id: messageId,
        update_data: {
            body: "",
            attachment_ids: [],
        },
    });
    await click("button:has(:text('Marc Demo'))");
    await contains(".o-mail-MessagingMenuItem:has(:text('Marc Demo'))", {
        contains: [".badge", { count: 0 }],
    });
});

test("do not show control panel without breadcrumbs", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussContent-threadName", { value: "General" });
    await waitForNone(".o_control_panel");
    await openFormView("res.partner", serverState.partnerId);
    await openDiscuss();
    await waitFor(".o-mail-Discuss:count(1)");
    await contains(".o_control_panel .breadcrumb:has(:text('" + serverState.partnerName + "'))");
});

test("Show typing icon on group chat in sidebar", async () => {
    const pyEnv = await startServer();
    const marcPid = pyEnv["res.partner"].create({ name: "Marc Demo" });
    const marcUid = pyEnv["res.users"].create({ partner_id: marcPid, name: "Marc Demo" });
    const groupChatId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: marcPid }),
        ],
        channel_type: "group",
    });
    await start();
    await openDiscuss(groupChatId);
    // simulate receive typing notification from Marc Demo "is typing"
    withUser(marcUid, () =>
        rpc("/discuss/channel/notify_typing", {
            is_typing: true,
            channel_id: groupChatId,
        })
    );
    await waitFor(
        ".o-mail-MessagingMenuItem .o-discuss-Typing-icon[title='Marc Demo is typing...']:count(1)"
    );
});

test("Read-only channel member has bottom banner instead of composer", async () => {
    const pyEnv = await startServer();
    const memberPartnerId = pyEnv["res.partner"].create({ name: "Member User" });
    pyEnv["res.users"].create({
        partner_id: memberPartnerId,
        login: "test_member",
        password: "test_member",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        is_readonly: true,
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, channel_role: "owner" }),
            Command.create({ partner_id: memberPartnerId }),
        ],
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Welcome to the read-only channel!",
        model: "discuss.channel",
        res_id: channelId,
    });

    await start({
        authenticateAs: { login: "test_member", password: "test_member" },
    });
    await openDiscuss(channelId);
    await waitFor(".o-mail-DiscussContent-core span:text('This channel is read-only.'):count(1)");
    await waitForNone(".o-mail-Composer");
    pyEnv["discuss.channel"].write([channelId], { is_readonly: false });
    await waitFor(".o-mail-Composer:count(1)");
    await waitForNone(".o-mail-DiscussContent-core span:text('This channel is read-only.')");
    // reply to message composer should disappear when channel becomes read-only again
    await hover(".o-mail-Message:has(:text('Welcome to the read-only channel!'))");
    await click(".o-mail-Message:has(:text('Welcome to the read-only channel!')) [title='Expand']");
    await click(".o-dropdown-item:text('Reply')");
    await waitFor(".o-mail-Composer:has(:text('Replying to Mitchell Admin')):count(1)");
    pyEnv["discuss.channel"].write([channelId], { is_readonly: true });
    await waitFor(".o-mail-DiscussContent-core span:text('This channel is read-only.'):count(1)");
    await waitForNone(".o-mail-Composer");
});

test("Read-only channel info is only editable by channel admins", async () => {
    const pyEnv = await startServer();
    const memberPartnerId = pyEnv["res.partner"].create({ name: "Member User" });
    pyEnv["res.users"].create({
        partner_id: memberPartnerId,
        login: "test_member",
        password: "test_member",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        description: "Read-only channel description",
        group_public_id: false,
        is_readonly: true,
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, channel_role: "owner" }),
            Command.create({ partner_id: memberPartnerId, channel_role: "admin" }),
        ],
    });
    await start({
        authenticateAs: { login: "test_member", password: "test_member" },
    });
    await openDiscuss(channelId);
    await waitFor(".o-mail-DiscussContent-threadName:enabled:count(1)");
    await waitFor(".o-mail-DiscussContent-threadDescription:enabled:count(1)");
    await waitFor(".o-mail-DiscussContent-header a[title='Change Picture']:count(1)");
    const memberId = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", memberPartnerId],
    ])[0];
    pyEnv["discuss.channel.member"].write([memberId], { channel_role: false });
    await waitFor(".o-mail-DiscussContent-threadName:disabled:count(1)");
    await waitFor(".o-mail-DiscussContent-threadDescription:disabled:count(1)");
    await waitForNone(".o-mail-DiscussContent-header a[title='Change Picture']");
});

test("Read-only channel admin has composer", async () => {
    const pyEnv = await startServer();
    const adminPartnerId = pyEnv["res.partner"].create({ name: "Admin User" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        is_readonly: true,
        channel_member_ids: [
            Command.create({ partner_id: adminPartnerId, channel_role: "owner" }),

            Command.create({ partner_id: serverState.partnerId, channel_role: "owner" }),
        ],
    });
    pyEnv["res.users"].create({
        partner_id: adminPartnerId,
        login: "test_member",
        password: "test_member",
    });
    await start({
        authenticateAs: { login: "test_member", password: "test_member" },
    });
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer:count(1)");
    const memberId = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", adminPartnerId],
    ])[0];
    pyEnv["discuss.channel.member"].write([memberId], { channel_role: false });
    await waitFor(".o-mail-DiscussContent-core span:text('This channel is read-only.'):count(1)");
    await waitForNone(".o-mail-Composer");
    pyEnv["discuss.channel.member"].write([memberId], { channel_role: "admin" });
    await waitFor(".o-mail-Composer:count(1)");
    await waitForNone(".o-mail-DiscussContent-core span:text('This channel is read-only.')");
});

test("Read-only channel member cannot respond or create subthread", async () => {
    const pyEnv = await startServer();
    const memberPartnerId = pyEnv["res.partner"].create({ name: "Member User" });
    pyEnv["res.users"].create({
        partner_id: memberPartnerId,
        login: "test_member",
        password: "test_member",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        is_readonly: true,
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, channel_role: "owner" }),
            Command.create({ partner_id: memberPartnerId }),
        ],
    });
    const memberId = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", serverState.partnerId],
    ])[0];
    pyEnv["mail.message"].create({
        body: "Welcome to the read-only channel!",
        model: "discuss.channel",
        res_id: channelId,
        author_id: memberId,
    });
    await start({
        authenticateAs: { login: "test_member", password: "test_member" },
    });
    await openDiscuss(channelId);
    await hover(".o-mail-Message");
    await waitFor(".o-mail-Message-actions button:count(2)");
    await waitFor(
        ".o-mail-Message .o-mail-QuickReactionMenu-toggler[title='Add a Reaction']:count(1)"
    );
    await click(".o-mail-Message .o-mail-ActionList-button[title='Expand']");
    await waitFor(".o-dropdown-item:count(3)");
    await waitFor(".o-dropdown-item:text('Mark as Unread'):count(1)");
    await waitFor(".o-dropdown-item:text('Bookmark'):count(1)");
    await waitFor(".o-dropdown-item:text('Copy Text'):count(1)");
});

test("Read-only channel have reactions for admin", async () => {
    const pyEnv = await startServer();
    const adminPartnerId = pyEnv["res.partner"].create({ name: "Admin User" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        is_readonly: true,
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, channel_role: "admin" }),
            Command.create({ partner_id: adminPartnerId, channel_role: "owner" }),
        ],
    });
    const memberId = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", serverState.partnerId],
    ])[0];
    pyEnv["mail.message"].create({
        body: "Welcome to the read-only channel!",
        model: "discuss.channel",
        res_id: channelId,
        author_id: memberId,
    });
    await start();
    await openDiscuss(channelId);
    await hover(".o-mail-Message");
    await waitFor(".o-mail-Message .o-mail-ActionList-button:count(1)");
    await waitFor(
        ".o-mail-Message .o-mail-QuickReactionMenu-toggler[title='Add a Reaction']:count(1)"
    );
    await click(".o-mail-Message .o-mail-ActionList-button[title='Expand']");
    await waitFor(".o-dropdown-item:count(6)");
    await waitFor(".o-dropdown-item:text('Reply'):count(1)");
    await waitFor(".o-dropdown-item:text('Bookmark'):count(1)");
    await waitFor(".o-dropdown-item:text('Copy Text'):count(1)");
    await waitFor(".o-dropdown-item:text('Create Thread'):count(1)");
    await waitFor(".o-dropdown-item:text('Mark as Unread'):count(1)");
    await waitFor(".o-dropdown-item:text('Pin'):count(1)");
});

test("Cannot call read-only channels", async () => {
    const pyEnv = await startServer();
    const adminPartnerId = pyEnv["res.partner"].create({ name: "Admin User" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        is_readonly: true,
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: adminPartnerId, channel_role: "owner" }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(
        ".o-mail-DiscussContent-header .o-mail-ActionList-button[title='Notification Settings']:count(1)"
    );
    await waitFor(
        ".o-mail-DiscussContent-header .o-mail-ActionList-button[title='Search Messages']:count(1)"
    );
    await waitFor(
        ".o-mail-DiscussContent-header .o-mail-ActionList-button[title='Pinned Messages']:count(1)"
    );
    await waitFor(
        ".o-mail-DiscussContent-header .o-mail-ActionList-button[title='Threads']:count(1)"
    );
    await waitFor(
        ".o-mail-DiscussContent-header .o-mail-ActionList-button[title='Attachments']:count(1)"
    );
    await waitFor(
        ".o-mail-DiscussContent-header .o-mail-ActionList-button[title='Members']:count(1)"
    );
    await waitFor(
        ".o-mail-DiscussContent-header .o-mail-ActionList .o-mail-ActionList-button:count(6)"
    );
});

test("Prevent link interactions in message preview", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Marc" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const messageId = pyEnv["mail.message"].create({
        body: "<a href='https://www.odoo.com'>https://www.odoo.com</a>",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", partnerId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], { seen_message_id: messageId });
    await start();
    await openDiscuss();
    await waitFor("h4:text('No conversation selected.'):count(1)");
    await click(".o-mail-NotificationItem-text a");
    expect(".o-mail-NotificationItem-text").toHaveStyle({ pointerEvents: "none" });
    await waitFor(".o-mail-Message:has(:text('https://www.odoo.com')):count(1)");
});
