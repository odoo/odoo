import {
    assertChatBubbleAndWindowImStatus,
    assertChatHub,
    contains as mailContains,
    defineMailModels,
    focus,
    hover,
    inputFiles,
    insertText,
    isInViewportOf,
    listenStoreFetch,
    openDiscuss,
    openFormView,
    openListView,
    openMessagingMenu,
    patchUiSize,
    scroll,
    setupChatHub,
    SIZES,
    start,
    startServer,
    triggerHotkey,
    waitStoreFetch,
    MENU_ACTIVE_IDS,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test, waitFor, waitForNone } from "@odoo/hoot";
import { mockDate, tick } from "@odoo/hoot-mock";
import {
    Command,
    contains,
    getService,
    preloadBundle,
    serverState,
    withUser,
} from "@web/../tests/web_test_helpers";

import { rpc } from "@web/core/network/rpc";
import { range } from "@web/core/utils/numbers";

describe.current.tags("desktop");
defineMailModels();
preloadBundle("web.assets_emoji");

test("Mobile: chat window shouldn't open automatically after receiving a new message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    patchUiSize({ size: SIZES.SM });
    await start();
    await waitFor(".o_menu_systray i[aria-label='Messages']:count(1)");
    await waitForNone(".o-mail-MessagingMenuInDropdown-counter");
    // simulate receiving a message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hu", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await waitFor(".o-mail-MessagingMenuInDropdown-counter:text('1'):count(1)");
    await waitForNone(".o-mail-ChatWindow");
});

test('chat window: post message on channel with "CTRL-Enter" keyboard shortcut for small screen size', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-ChatWindow .o-mail-Composer-input", "Test");
    triggerHotkey("control+Enter");
    await waitFor(".o-mail-Message:count(1)");
});

test("load messages from opening chat window from messaging menu", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        group_public_id: false,
        name: "General",
    });
    for (let i = 0; i <= 20; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem:count(1)").click();
    await waitFor(".o-mail-Message:count(21)");
});

test("chat window: basic rendering", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem:count(1)").click();
    await waitFor(".o-mail-ChatWindow:count(1)");
    await waitFor(".o-mail-ChatWindow-header:text('General'):count(1)");
    await waitFor(".o-mail-ChatWindow-header .o-mail-ChatWindow-threadAvatar:count(1)");
    await waitFor(".o-mail-ChatWindow-header button:count(5)");
    await waitFor("[title='Start Call']:count(1)");
    await waitFor("[title='Start Video Call']:count(1)");
    await waitFor("[title='Open Actions Menu']:count(1)");
    await waitFor("[title='Fold']:count(1)");
    await waitFor("[title*='Close Chat Window']:count(1)");
    await waitFor(".o-mail-ChatWindow .o-mail-Thread:has(:text('Welcome to #General!')):count(1)");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor("[title='Open Actions Menu']:count(1)");
    await contains("[title='Open Actions Menu']:count(1)").click();
    await waitFor(".o-dropdown-item:count(14)");
    await waitFor(".o-dropdown-item:text('Open in Discuss'):count(1)");
    await waitFor(".o-dropdown-item:text('Attachments'):count(1)");
    await waitFor(".o-dropdown-item:text('Pinned Messages'):count(1)");
    await waitFor(".o-dropdown-item:text('Members'):count(1)");
    await waitFor(".o-dropdown-item:text('Threads'):count(1)");
    await waitFor(".o-dropdown-item:text('Invite People'):count(1)");
    await waitFor(".o-dropdown-item:text('Search Messages'):count(1)");
    await waitFor(".o-dropdown-item:text('Rename Thread'):count(1)");
    await waitFor(".o-dropdown-item:text('Notification Settings'):count(1)");
    await waitFor(".o-dropdown-item:text('Add to Favorites'):count(1)");
    await waitFor(".o-dropdown-item:text('Voice & Video Settings'):count(1)");
    await waitFor(".o-dropdown-item:text('View Recordings'):count(1)");
    await waitFor(".o-dropdown-item:text('Hide Until New Message'):count(1)");
    await waitFor(".o-dropdown-item:text('Leave Conversation'):count(1)");
});

test("chat window: clicking chat correspondent avatars in start message opens avatar card", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "mario@example.com",
        name: "Mario",
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    setupChatHub({ opened: [channelId] });
    await start();
    await waitFor(".o-mail-ChatWindow .o-mail-Thread:count(1)");
    await waitFor(
        ".o-mail-Thread:has(:text('This is the start of your direct chat with Mario')):count(1)"
    );
    await contains(".o-mail-Thread-avatarChatWindow:count(1)").click();
    await waitFor(".o_avatar_card:count(1)");
    await waitFor(".o-mail-avatar-card-name:text('Mario'):count(1)");
});

test.skip("Fold state of chat window is sync among browser tabs", async () => {
    // AKU TODO: fix crosstab
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true, waitUntilSubscribe: false });
    await contains(`${env1.selector} .o_menu_systray i[aria-label='Messages']:count(1)`).click();
    await contains(`${env1.selector} .o-mail-NotificationItem:count(1)`).click();
    await waitFor(`${env2.selector} .o-mail-ChatWindow-header:count(1)`);
    await contains(`${env1.selector} .o-mail-ChatWindow-header:count(1)`).click(); // Fold
    await waitForNone(`${env1.selector} .o-mail-Thread`);
    await waitForNone(`${env2.selector} .o-mail-Thread`);
    await contains(`${env2.selector} .o-mail-ChatBubble:count(1)`).click(); // Unfold
    await waitFor(`${env1.selector} .o-mail-ChatWindow .o-mail-Thread:count(1)`);
    await waitFor(`${env2.selector} .o-mail-ChatWindow .o-mail-Thread:count(1)`);
    await contains(`${env1.selector} [title*='Close Chat Window']:count(1)`).click();
    await waitForNone(`${env1.selector} .o-mail-ChatWindow`);
    await waitForNone(`${env2.selector} .o-mail-ChatWindow`);
});

test("chat window: fold", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    await start();
    // Open Thread
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem:count(1)").click();
    await waitFor(".o-mail-ChatWindow .o-mail-Thread:count(1)");
    assertChatHub({ opened: [channelId] });
    // Fold chat window
    await contains(".o-mail-ChatWindow-header [title='Fold']:count(1)").click();
    await waitForNone(".o-mail-ChatWindow .o-mail-Thread");
    assertChatHub({ folded: [channelId] });
    // Unfold chat window
    await contains(".o-mail-ChatBubble:count(1)").click();
    await waitFor(".o-mail-ChatWindow .o-mail-Thread:count(1)");
    assertChatHub({ opened: [channelId] });
});

test("chat window: open / close", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await waitForNone(".o-mail-ChatWindow");
    await contains(".o-mail-NotificationItem:count(1)").click();
    await waitFor(".o-mail-ChatWindow:count(1)");
    assertChatHub({ opened: [channelId] });
    await contains(".o-mail-ChatWindow-header [title*='Close Chat Window']:count(1)").click();
    await waitForNone(".o-mail-ChatWindow");
    assertChatHub({});
    // Reopen chat window
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem:count(1)").click();
    await waitFor(".o-mail-ChatWindow:count(1)");
    assertChatHub({ opened: [channelId] });
});

test("Open chatwindow as a non member", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [],
        name: "General",
        message_needaction: true,
    });
    const messageId = pyEnv["mail.message"].create({
        model: "discuss.channel",
        body: "A needaction message to have it in messaging menu",
        author_id: serverState.odoobotId,
        needaction: true,
        res_id: channelId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem:count(1)").click();
    await waitFor(".o-mail-ChatWindow:count(1)");
});

test("open chat on very narrow device should work", async () => {
    const pyEnv = await startServer();
    patchUiSize({ width: 200 });
    pyEnv["discuss.channel"].create({});
    await start();
    const store = getService("mail.store");
    expect(store.chatHub.WINDOW).toBeGreaterThan(200, {
        message: "Device is narrower than usual chat window width",
    }); // scenario where this might fail
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem:count(1)").click();
    await waitFor(".o-mail-ChatWindow:count(1)");
});

test("chat window: close on ESCAPE", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    setupChatHub({ opened: [channelId] });
    await start();
    await waitFor(".o-mail-ChatWindow:count(1)");
    await focus(".o-mail-Composer-input");
    triggerHotkey("Escape");
    await waitForNone(".o-mail-ChatWindow");
    assertChatHub({});
});

test("chat window: close on ESCAPE (multi)", async () => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create(
        range(4).map((i) => ({ name: `channel_${i}` }))
    );
    patchUiSize({ width: 1920 });
    setupChatHub({ opened: channelIds.reverse() });
    await start();
    await waitFor(".o-mail-ChatWindow:count(4)"); // expected order: 3, 2, 1, 0
    await waitFor(".o-mail-ChatWindow-header:eq(0):has(:text('channel_3')):count(1)");
    await waitFor(".o-mail-ChatWindow-header:eq(1):has(:text('channel_2')):count(1)");
    await waitFor(".o-mail-ChatWindow-header:eq(2):has(:text('channel_1')):count(1)");
    await waitFor(".o-mail-ChatWindow-header:eq(3):has(:text('channel_0')):count(1)");
    await focus(".o-mail-Composer-input:eq(3)");
    triggerHotkey("Escape");
    await waitFor(".o-mail-ChatWindow:count(3)");
    await waitFor(".o-mail-ChatWindow-header:eq(0):has(:text('channel_3')):count(1)");
    await waitFor(".o-mail-ChatWindow-header:eq(1):has(:text('channel_2')):count(1)");
    await waitFor(".o-mail-ChatWindow-header:eq(2):has(:text('channel_1')):count(1)");
    await waitFor(".o-mail-ChatWindow:eq(2) .o-mail-Composer.o-focused:count(1)");
    await focus(".o-mail-Composer-input:eq(0)");
    triggerHotkey("Escape");
    await waitFor(".o-mail-ChatWindow:count(2)");
    await waitFor(".o-mail-ChatWindow-header:eq(0):has(:text('channel_2')):count(1)");
    await waitFor(".o-mail-ChatWindow-header:eq(1):has(:text('channel_1')):count(1)");
    await waitFor(".o-mail-ChatWindow:eq(0) .o-mail-Composer.o-focused:count(1)");
    triggerHotkey("Escape");
    await waitFor(".o-mail-ChatWindow:count(1)");
    await waitFor(".o-mail-ChatWindow-header:eq(0):has(:text('channel_1')):count(1)");
    triggerHotkey("Escape");
    await waitForNone(".o-mail-ChatWindow");
    assertChatHub({});
});

test("Close composer suggestions in chat window with ESCAPE does not also close the chat window", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    setupChatHub({ opened: [channelId] });
    await start();
    await insertText(".o-mail-Composer-input", "@");
    triggerHotkey("Escape");
    await waitFor(".o-mail-ChatWindow:count(1)");
});

test("Close emoji picker in chat window with ESCAPE does not also close the chat window", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    setupChatHub({ opened: [channelId] });
    await start();
    await contains("button[title='Add Emojis']:count(1)").click();
    triggerHotkey("Escape");
    await waitForNone(".o-EmojiPicker");
    await waitFor(".o-mail-ChatWindow:count(1)");
});

test.tags("focus required");
test("Closing seen-by dialog on ESCAPE should not close the chat window", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo User" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Hello",
        model: "discuss.channel",
        res_id: channelId,
    });
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", partnerId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], {
        seen_message_id: messageId,
    });
    setupChatHub({ opened: [channelId] });
    await start();
    await waitFor(".o-mail-ChatWindow:count(1)");
    await contains(".o-mail-MessageSeenIndicator:count(1)").click();
    await waitFor(".o-mail-MessageSeenIndicatorDialog :focus:count(1)");
    triggerHotkey("Escape");
    await waitForNone(".o-mail-MessageSeenIndicatorDialog");
    await waitFor(".o-mail-ChatWindow:count(1)");
});

test("Close active thread action in chatwindow on ESCAPE", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    setupChatHub({ opened: [channelId] });
    await start();
    await waitFor(".o-mail-ChatWindow:count(1)");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor(".o-mail-ChatWindow-moreActions:text('General'):count(1)");
    await contains(".o-mail-ChatWindow-moreActions:text('General'):count(1)").click();
    await contains(".o-dropdown-item:text('Invite People'):count(1)").click();
    await waitFor(".o-discuss-ChannelInvitation:count(1)");
    triggerHotkey("Escape");
    await waitForNone(".o-discuss-ChannelInvitation");
    await waitFor(".o-mail-ChatWindow:count(1)");
});

test("ESC cancels thread rename", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    setupChatHub({ opened: [channelId] });
    await start();
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor(".o-mail-ChatWindow-moreActions:text('General'):count(1)");
    await contains(".o-mail-ChatWindow-moreActions:text('General'):count(1)").click();
    await contains(".o-dropdown-item:text('Rename Thread'):count(1)").click();
    await waitFor(".o-mail-AutoresizeInput.o-focused[title='General']:count(1)");
    await insertText(".o-mail-AutoresizeInput", "New", { replace: true });
    triggerHotkey("Escape");
    await waitForNone(".o-mail-AutoresizeInput.o-focused");
    await waitFor(".o-mail-ChatWindow-moreActions:text('General'):count(1)");
});

test.tags("focus required");
test("open 2 different chat windows: enough screen width", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([{ name: "Channel_1" }, { name: "Channel_2" }]);
    patchUiSize({ width: 1920 });
    await start();
    const store = getService("mail.store");
    expect(
        store.chatHub.WINDOW_GAP * 2 + store.chatHub.WINDOW * 2 + store.chatHub.WINDOW_INBETWEEN
    ).toBeLessThan(1920, {
        message: "should have enough space to open 2 chat windows simultaneously",
    });
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem-name:text('Channel_1'):count(1)").click();
    await mailContains(".o-mail-ChatWindow:has(:text('Channel_1'))", {
        contains: [".o-mail-Composer-input:focus"],
    });
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem-name:text('Channel_2'):count(1)").click();
    await waitFor(".o-mail-ChatWindow:count(2)");
    await waitFor(".o-mail-ChatWindow:has(:text('Channel_1')):count(1)");
    await mailContains(".o-mail-ChatWindow:has(:text('Channel_2'))", {
        contains: [".o-mail-Composer-input:focus"],
    });
});

test.tags("focus required");
test("focus next visible chat window when closing current chat window with ESCAPE", async () => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create([{ name: "General" }, { name: "MyTeam" }]);
    patchUiSize({ width: 1920 });
    setupChatHub({ opened: channelIds });
    await start();
    const store = getService("mail.store");
    expect(
        store.chatHub.WINDOW_GAP * 2 + store.chatHub.WINDOW * 2 + store.chatHub.WINDOW_INBETWEEN
    ).toBeLessThan(1920, {
        message: "should have enough space to open 2 chat windows simultaneously",
    });
    await waitFor(".o-mail-ChatWindow .o-mail-Composer-input:count(2)");
    await focus(".o-mail-Composer-input", {
        parent: [".o-mail-ChatWindow:has(:text('MyTeam'))"],
    });
    triggerHotkey("Escape");
    await waitFor(".o-mail-ChatWindow:count(1)");
    await mailContains(".o-mail-ChatWindow:has(:text('General'))", {
        contains: [".o-mail-Composer-input:focus"],
    });
});

test.tags("focus required");
test("chat window: switch on TAB", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([{ name: "channel1" }, { name: "channel2" }]);
    patchUiSize({ width: 1920 });
    await start();
    const store = getService("mail.store");
    expect(
        store.chatHub.WINDOW_GAP * 2 + store.chatHub.WINDOW * 2 + store.chatHub.WINDOW_INBETWEEN
    ).toBeLessThan(1920, {
        message: "should have enough space to open 2 chat windows simultaneously",
    });
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem-name:text('channel1'):count(1)").click();
    await waitFor(".o-mail-ChatWindow:count(1)");
    await mailContains(".o-mail-ChatWindow:has(:text('channel1'))", {
        contains: [".o-mail-Composer-input:focus"],
    });
    triggerHotkey("Tab");
    await mailContains(".o-mail-ChatWindow:has(:text('channel1'))", {
        contains: [".o-mail-Composer-input:focus"],
    });
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem-name:text('channel2'):count(1)").click();
    await waitFor(".o-mail-ChatWindow:count(2)");
    await mailContains(".o-mail-ChatWindow:has(:text('channel2'))", {
        contains: [".o-mail-Composer-input:focus"],
    });
    triggerHotkey("Tab");
    await mailContains(".o-mail-ChatWindow:has(:text('channel1'))", {
        contains: [".o-mail-Composer-input:focus"],
    });
});

test.tags("focus required");
test("chat window: TAB cycle with 3 open chat windows", async () => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create([
        { name: "General" },
        { name: "MyTeam" },
        { name: "MyProject" },
    ]);
    patchUiSize({ width: 1920 });
    setupChatHub({ opened: channelIds.reverse() });
    await start();
    const store = getService("mail.store");
    expect(
        store.chatHub.WINDOW_GAP * 3 + store.chatHub.WINDOW * 3 + store.chatHub.WINDOW_INBETWEEN * 2
    ).toBeLessThan(1920, {
        message: "should have enough space to open 3 chat windows simultaneously",
    });
    // FIXME: assumes ordering: MyProject, MyTeam, General
    await waitFor(".o-mail-ChatWindow .o-mail-Composer-input:count(3)");
    await focus(".o-mail-Composer-input", {
        parent: [".o-mail-ChatWindow:has(:text('MyProject'))"],
    });
    triggerHotkey("Tab");
    await mailContains(".o-mail-ChatWindow:has(:text('MyTeam'))", {
        contains: [".o-mail-Composer-input:focus"],
    });
    triggerHotkey("Tab");
    await mailContains(".o-mail-ChatWindow:has(:text('General'))", {
        contains: [".o-mail-Composer-input:focus"],
    });
    triggerHotkey("Tab");
    await mailContains(".o-mail-ChatWindow:has(:text('MyProject'))", {
        contains: [".o-mail-Composer-input:focus"],
    });
});

test("chat window should open when receiving a new DM", async () => {
    mockDate("2023-01-03 12:00:00"); // so that it's after last interest (mock server is in 2019 by default!)
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "DemoUser" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId, im_status: "online" });
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
    await waitStoreFetch("init_messaging");
    await waitFor(".o-mail-ChatHub:count(1)");
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "Hi, are you here?",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await waitFor(".o-mail-ChatBubble:count(1)");
    await waitFor(".o-mail-ChatBubble-counter:text('1'):count(1)");
    await waitFor(".o-mail-ChatBubble .o-mail-ImStatus[title='User is online']:count(1)");
    await assertChatBubbleAndWindowImStatus("DemoUser", 1);
});

test("chat window should not open when receiving a new DM from odoobot", async () => {
    mockDate("2023-01-03 12:00:00"); // so that it's after last interest (mock server is in 2019 by default!)
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ partner_id: serverState.odoobotId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                unpin_dt: "2021-01-01 12:00:00",
                last_interest_dt: "2021-01-01 10:00:00",
                partner_id: serverState.partnerId,
            }),
            Command.create({ partner_id: serverState.odoobotId }),
        ],
        channel_type: "chat",
    });
    await start();
    await waitFor(".o-mail-ChatHub:count(1)");
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello, I'm new", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await waitForNone(".o-mail-ChatWindow");
});

test("chat window should scroll to the newly posted message just after posting it", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    for (let i = 0; i < 10; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    setupChatHub({ opened: [channelId] });
    await start();
    await waitFor(".o-mail-Message:count(10)");
    await insertText(".o-mail-Composer-input", "WOLOLO");
    triggerHotkey("Enter");
    await waitFor(".o-mail-Message:count(11)");
    await mailContains(".o-mail-Thread", { scroll: "bottom" });
});

test("chat window should remain folded when new message is received", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({
        name: "Foreigner user",
        partner_id: partnerId,
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    setupChatHub({ folded: [channelId] });
    await start();
    await waitFor(".o-mail-ChatBubble:count(1)");
    await waitForNone(".o-mail-ChatBubble-counter");
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "New Message", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await waitFor(".o-mail-ChatBubble-counter:text('1'):count(1)");
    await waitFor(".o-mail-ChatBubble:count(1)");
});

test("chat window: composer state conservation on toggle discuss", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    const textFile1 = new File(
        ["hello, world"],
        "text state conversation on toggle home menu.txt",
        { type: "text/plain" }
    );
    const textFile2 = new File(
        ["hello, xdu is da best man"],
        "text2 state conversation on toggle home menu.txt",
        { type: "text/plain" }
    );
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem:count(1)").click();
    // Set content of the composer of the chat window
    await insertText(".o-mail-Composer-input", "XDU for the win !");
    await waitForNone(".o-mail-Composer-footer .o-mail-AttachmentList .o-mail-AttachmentContainer");
    // Set attachments of the composer
    await inputFiles(".o-mail-Composer .o_input_file", [textFile1, textFile2]);
    await waitFor(".o-mail-AttachmentContainer:not(.o-isUploading):count(2)");
    await openDiscuss();
    await waitForNone(".o-mail-ChatWindow");
    await openFormView("discuss.channel", channelId);
    await waitFor(
        ".o-mail-Composer-footer .o-mail-AttachmentList .o-mail-AttachmentContainer:not(.o-isUploading):count(2)"
    );
    await mailContains(".o-mail-Composer-input", { value: "XDU for the win !" });
});

test("don't show chat hub options when discuss is open", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({});
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem:count(1)").click();
    await waitFor(".o-mail-ChatWindow:count(1)");
    await waitFor(".o-mail-ChatHub [title='Chat Options']:count(1)");
    await openDiscuss();
    await waitForNone(".o-mail-ChatWindow");
    await waitForNone(".o-mail-ChatHub [title='Chat Options']");
});

test("chat window: scroll conservation on toggle discuss", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    for (let i = 0; i < 100; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem:count(1)").click();
    await waitFor(".o-mail-Message:count(30)");
    await mailContains(".o-mail-ChatWindow .o-mail-Thread", { scroll: 0 });
    await tick(); // wait for the scroll to first unread to complete
    await scroll(".o-mail-ChatWindow .o-mail-Thread", 142);
    await openDiscuss();
    await waitForNone(".o-mail-ChatWindow");
    await openListView("discuss.channel", { res_id: channelId });
    await waitFor(".o-mail-Message:count(30)");
    await mailContains(".o-mail-ChatWindow .o-mail-Thread", { scroll: 142 });
});

test("chat window with a thread: keep scroll position in message list on folded", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    for (let i = 0; i < 100; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem:count(1)").click();
    await waitFor(".o-mail-Message:count(30)");
    await mailContains(".o-mail-ChatWindow .o-mail-Thread", { scroll: 0 });
    await tick(); // wait for the scroll to first unread to complete
    await scroll(".o-mail-ChatWindow .o-mail-Thread", 142);
    // fold chat window
    await contains(".o-mail-ChatWindow-header [title='Fold']:count(1)").click();
    await waitForNone(".o-mail-Message");
    await waitForNone(".o-mail-ChatWindow .o-mail-Thread");
    // unfold chat window
    await contains(".o-mail-ChatBubble:count(1)").click();
    await waitFor(".o-mail-Message:count(30)");
    await mailContains(".o-mail-ChatWindow .o-mail-Thread", { scroll: 142 });
});

test("chat window with a thread: keep scroll position in message list on toggle discuss when folded", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    for (let i = 0; i < 100; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem:count(1)").click();
    await waitFor(".o-mail-Message:count(30)");
    await mailContains(".o-mail-ChatWindow .o-mail-Thread", { scroll: 0 });
    await tick(); // wait for the scroll to first unread to complete
    await scroll(".o-mail-ChatWindow .o-mail-Thread", 142);
    // fold chat window
    await contains(".o-mail-ChatWindow-header [title='Fold']:count(1)").click();
    await openDiscuss();
    await waitForNone(".o-mail-ChatWindow");
    await openListView("discuss.channel", { res_id: channelId });
    // unfold chat window
    await contains(".o-mail-ChatBubble:count(1)").click();
    await waitFor(".o-mail-ChatWindow .o-mail-Message:count(30)");
    await mailContains(".o-mail-ChatWindow .o-mail-Thread", { scroll: 142 });
});

test("folded chat window should hide member-list and settings buttons", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({});
    await start();
    // Open Thread
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem:count(1)").click();
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor("[title='Open Actions Menu']:count(1)");
    await contains("[title='Open Actions Menu']:count(1)").click();
    await waitFor(".o-dropdown-item:text('Members'):count(1)");
    await waitFor(".o-dropdown-item:text('Voice & Video Settings'):count(1)");
    await contains(".o-mail-ChatWindow-header:count(1)").click(); // click away to close the more menu
    await waitForNone(".o-dropdown-item:text('Members')");
    // Fold chat window
    await contains(".o-mail-ChatWindow-header [title='Fold']:count(1)").click();
    await waitForNone("[title='Open Actions Menu']");
    await waitForNone(".o-dropdown-item:text('Members')");
    await waitForNone(".o-dropdown-item:text('Voice & Video Settings')");
    // Unfold chat window
    await contains(".o-mail-ChatBubble:count(1)").click();
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor("[title='Open Actions Menu']:count(1)");
    await contains("[title='Open Actions Menu']:count(1)").click();
    await waitFor(".o-dropdown-item:text('Members'):count(1)");
    await waitFor(".o-dropdown-item:text('Voice & Video Settings'):count(1)");
});

test("chat window: fold (mobile)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-ChatWindow:count(1)");
    await contains(".o-mail-ChatWindow-header [title='Fold']:count(1)").click();
    await waitForNone(".o-mail-ChatWindow");
    await waitForNone(".o-mail-ChatBubble");
    await openListView("discuss.channel", { res_id: channelId });
    await waitFor(".o-mail-ChatBubble:count(1)");
    assertChatHub({ folded: [channelId] });
});

test("Synced chat windows should open at page load on mobile", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    patchUiSize({ size: SIZES.SM });
    setupChatHub({ opened: [channelId] });
    await start();
    await waitFor(".o-mail-ChatHub:count(1)");
    await waitFor(".o-mail-ChatWindow:count(1)");
});

test("Should not auto-open direct chat window without self", async () => {
    // Chat hub state is saved locally on device. If logging out then loggin in with another user,
    // this shouldn't open direct chat from previous user that the new user not have access.
    // Normally this is prevented with being unable to fetch the channel, but admin can still fetch.
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelIds = pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.odoobotId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "chat",
        },
    ]);
    setupChatHub({ opened: channelIds }); // simulate having both conversations open when logged in as "Demo User"
    await start();
    await waitFor(".o-mail-ChatHub:count(1)");
    await waitFor(".o-mail-ChatWindow:count(1)");
    await waitFor(".o-mail-ChatWindow-displayName:text(Demo):count(1)");
});

test("chat window of channels should not have 'Open in Discuss' (mobile)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor("[title='Open Actions Menu']:count(1)");
    await contains("[title='Open Actions Menu']:count(1)").click();
    await waitForNone(".o-dropdown-item:text('Open in Discuss')");
});

test("Open chat window of new inviter", async () => {
    const pyEnv = await startServer();
    await start();
    const partnerId = pyEnv["res.partner"].create({ name: "Newbie" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    // simulate receiving notification of new connection of inviting user
    const [partner] = pyEnv["res.partner"].read(serverState.partnerId);
    pyEnv["bus.bus"]._sendone(partner, "res.users/connection", {
        username: "Newbie",
        partnerId,
    });
    await waitFor(".o-mail-ChatWindow-displayName:text('Newbie'):count(1)");
    await waitFor(
        ".o_notification:text('Newbie just connected for the first time. Wish them luck!'):count(1)"
    );
});

test.tags("focus required");
test("keyboard navigation ArrowUp/ArrowDown on message action dropdown in chat window", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem:count(1)").click();
    await waitFor(".o-mail-ChatWindow .o-mail-Composer-input:focus:count(1)");
    await contains(".o-mail-Message").hover();
    await contains(".o-mail-Message [title='Expand']").click();
    await waitFor(".o-mail-Message-moreMenu.dropdown-menu:count(1)");
    triggerHotkey("ArrowDown");
    await waitFor(".o-mail-Message-moreMenu .dropdown-item:eq(0).focus:count(1)");
    triggerHotkey("ArrowDown");
    await waitFor(".o-mail-Message-moreMenu .dropdown-item:eq(1).focus:count(1)");
});

test("Close dropdown in chat window with ESCAPE does not also close the chat window", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem:count(1)").click();
    await contains(".o-mail-Message").hover();
    await contains(".o-mail-Message [title='Expand']").click();
    await waitFor(".o-mail-Message-moreMenu.dropdown-menu:count(1)");
    triggerHotkey("Escape");
    await waitForNone(".o-mail-Message-moreMenu.dropdown-menu");
    await waitFor(".o-mail-ChatWindow:count(1)");
});

test("mark as read when opening chat window", async () => {
    const pyEnv = await startServer();
    const bobPartnerId = pyEnv["res.partner"].create({ name: "bob" });
    const bobUserId = pyEnv["res.users"].create({ name: "bob", partner_id: bobPartnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: bobPartnerId }),
        ],
    });
    listenStoreFetch("/discuss/channel/messages");
    await start();
    await openMessagingMenu();
    await contains(".o-mail-NotificationItem-name:text('bob'):count(1)").click();
    await waitStoreFetch("/discuss/channel/messages");
    await waitFor(".o-mail-ChatWindow .o-mail-ChatWindow-header:text('bob'):count(1)");
    // message list fully loaded
    await waitFor(
        ".o-mail-ChatWindow .o-mail-Thread-empty:has(:text('This is the start of your direct chat with bob')):count(1)"
    );
    // composer is focused by default, we remove that focus
    await waitFor(".o-mail-Composer-input:focus:count(1)");
    document.querySelector(".o-mail-Composer-input").blur();
    await waitFor(".o-mail-Composer-input:not(:focus):count(1)");
    await withUser(bobUserId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "Hello, how are you?",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await waitFor(".o-mail-ChatWindow-counter:text('1'):count(1)");
    await contains(".o-mail-ChatWindow-header [title*='Close Chat Window']:count(1)").click();
    await waitForNone(".o-mail-ChatWindow");
    await openMessagingMenu();
    await contains(".o-mail-NotificationItem-name:text('bob'):count(1)").click();
    await waitFor(".o-mail-ChatWindow .o-mail-ChatWindow-header:text('bob'):count(1)");
    await waitForNone(".o-mail-ChatWindow-counter");
});

test("Notification settings rendering in chatwindow", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "general", channel_type: "channel" });
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem-name:text('general'):count(1)").click();
    await waitFor(".o-mail-ChatWindow:count(1)");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor("[title='Open Actions Menu']:count(1)");
    await contains("[title='Open Actions Menu']:count(1)").click();
    await contains(".o-dropdown-item:text('Notification Settings'):count(1)").click();
    await waitFor("button:has(:text('All Messages')):count(1)");
    await waitFor("button:has(:text('Mentions Only')):count(2)"); // the extra is in the Use Default as subtitle
    await waitFor("button:has(:text('Nothing')):count(1)");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor("button:has(:text('Mute Conversation')):count(1)");
    await hover("button:has(:text('Mute Conversation'))");
    await waitFor(".o-dropdown-item:text('For 15 minutes'):count(1)");
    await waitFor(".o-dropdown-item:text('For 1 hour'):count(1)");
    await waitFor(".o-dropdown-item:text('For 3 hours'):count(1)");
    await waitFor(".o-dropdown-item:text('For 8 hours'):count(1)");
    await waitFor(".o-dropdown-item:text('For 24 hours'):count(1)");
    await waitFor(".o-dropdown-item:text('Until I turn it back on'):count(1)");
});

test("open channel in chat window from push notification", async () => {
    const pyEnv = await startServer();
    const [channelId, salesId] = pyEnv["discuss.channel"].create([
        { name: "General" },
        { name: "Sales" },
    ]);
    setupChatHub({ opened: [salesId] });
    await start();
    await waitFor(".o-mail-ChatWindow-header:text('Sales'):count(1)");
    await waitForNone(".o-mail-ChatWindow-header:text('General')");
    navigator.serviceWorker.dispatchEvent(
        new MessageEvent("message", {
            data: { action: "OPEN_CHANNEL", data: { id: channelId } },
        })
    );
    await waitFor(".o-mail-ChatWindow-header:text('General'):count(1)");
});

test("Chat window should be closed when leaving the channel", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "general" });
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem:count(1)").click();
    await waitFor(".o-mail-ChatWindow-displayName:text('general'):count(1)");
    await contains("[title='Open Actions Menu']:count(1)").click();
    await contains(".o-dropdown-item:text('Leave Conversation'):count(1)").click();
    await contains(".o_dialog button:text('Leave Conversation'):count(1)").click();
    await waitForNone(".o-mail-ChatWindow-displayName:text('general')");
});

test("Chat window should be closed when hiding a chat", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openMessagingMenu();
    await contains(".o-mail-NotificationItem:count(1)").click();
    await waitFor(".o-mail-ChatWindow-displayName:text('Demo'):count(1)");
    await contains("[title='Open Actions Menu']:count(1)").click();
    await contains(".o-dropdown-item:text('Hide Until New Message'):count(1)").click();
    await waitForNone(".o-mail-ChatWindow-displayName:text('Demo')");
});

test.tags("focus required");
test("getting focus of chat window through tab key should jump to new message separator", async () => {
    const pyEnv = await startServer();
    const channel_ids = pyEnv["discuss.channel"].create([
        {
            name: "important channel",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    new_message_separator: 21,
                }),
            ],
        },
        { name: "other channel" },
    ]);
    for (let i = 0; i < 40; i++) {
        pyEnv["mail.message"].create({
            body: `message_${i}`,
            model: "discuss.channel",
            res_id: channel_ids[0],
        });
    }
    patchUiSize({ width: 1920 });
    setupChatHub({ opened: channel_ids });
    await start();
    await waitFor(".o-mail-ChatWindow:count(2)");
    await waitFor(
        ".o-mail-ChatWindow:eq(0) .o-mail-ChatWindow-header:text('important channel'):count(1)"
    );
    await waitFor(
        ".o-mail-ChatWindow:eq(1) .o-mail-ChatWindow-header:text('other channel'):count(1)"
    );
    await waitFor(".o-mail-ChatWindow:eq(0) .o-mail-Message:count(40)");
    await scroll(".o-mail-ChatWindow:eq(0) .o-mail-Thread", 0);
    await mailContains(".o-mail-ChatWindow:eq(0) .o-mail-Thread", { scroll: 0 });
    await focus(".o-mail-Composer-input:eq(1)");
    await waitFor(".o-mail-ChatWindow:eq(1) .o-mail-Composer.o-focused:count(1)");
    triggerHotkey("Tab");
    await waitFor(".o-mail-ChatWindow:eq(0) .o-mail-Composer.o-focused:count(1)");
    await isInViewportOf(
        ".o-mail-Message:contains(message_20)",
        ".o-mail-ChatWindow:eq(0) .o-mail-Thread"
    );
});

test("Ctrl+k opens the @ command palette", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create([
        {
            name: "General",
            channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        },
    ]);
    setupChatHub({ opened: channelId });
    await start();
    await focus(".o-mail-ChatWindow:has(.o-mail-ChatWindow-displayName:text('General'))");
    triggerHotkey("control+k");
    await waitFor(".o_command_palette_search:text('@'):count(1)");
});

test("Do not squash logged notes", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["discuss.channel"].create({ name: "test channel" });
    const messageId = pyEnv["mail.message"].create([
        {
            model: "discuss.channel",
            body: "Test Message",
            author_id: partnerId,
            needaction: true,
            res_id: partnerId,
        },
        {
            model: "discuss.channel",
            body: "Message",
            author_id: serverState.partnerId,
            needaction: true,
            res_id: partnerId,
        },
        {
            model: "discuss.channel",
            body: "Message Squashed",
            author_id: serverState.partnerId,
            needaction: true,
            res_id: partnerId,
        },
        {
            model: "discuss.channel",
            body: "Hello",
            author_id: serverState.partnerId,
            needaction: true,
            res_id: partnerId,
            subtype_id: pyEnv["mail.message.subtype"].search([
                ["subtype_xmlid", "=", "mail.mt_note"],
            ])[0],
        },
        {
            model: "discuss.channel",
            body: "World!",
            author_id: serverState.partnerId,
            needaction: true,
            res_id: partnerId,
            subtype_id: pyEnv["mail.message.subtype"].search([
                ["subtype_xmlid", "=", "mail.mt_note"],
            ])[0],
        },
    ]);
    pyEnv["mail.notification"].create({
        mail_message_id: messageId[0],
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem:count(1)").click();
    await waitFor(".o-mail-Message.o-squashed:text('Message Squashed'):count(1)");
    await waitFor(
        ".o-mail-Message:not(.o-squashed) .o-mail-Message-content:has(:text('Hello')):count(1)"
    );
    await waitFor(
        ".o-mail-Message:not(.o-squashed) .o-mail-Message-content:has(:text('World!')):count(1)"
    );
});

test("Readonly chat window as non-admin shows bottom banner", async () => {
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
    setupChatHub({ opened: [channelId] });
    await start({
        authenticateAs: { login: "test_member", password: "test_member" },
    });
    await waitFor(".o-mail-ChatWindow span:text('This channel is read-only.'):count(1)");
    await waitForNone(".o-mail-ChatWindow .o-mail-Composer-input");
});

test("Readonly chat window as admin shows composer", async () => {
    const pyEnv = await startServer();
    const adminPartnerId = pyEnv["res.partner"].create({ name: "Admin User" });
    pyEnv["res.users"].create({ partner_id: adminPartnerId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        is_readonly: true,
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, channel_role: "owner" }),
            Command.create({ partner_id: adminPartnerId }),
        ],
    });
    setupChatHub({ opened: [channelId] });
    await start();
    await waitFor(".o-mail-ChatWindow .o-mail-Composer-input:count(1)");
    await waitForNone(".o-mail-ChatWindow span:text('This channel is read-only.')");
});

test("preserve link formatting in chat bubble message preview", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        model: "discuss.channel",
        body: `<a href="https://odoo.com/">https://odoo.com</a>`,
        author_id: serverState.partnerId,
        res_id: channelId,
    });
    setupChatHub({ folded: [channelId] });
    await start();
    await hover(".o-mail-ChatBubble[name='General']");
    await waitFor(`.o-mail-ChatBubble-preview a[href="https://odoo.com/"]:count(1)`);
    expect(".o-mail-ChatBubble-preview a").toHaveStyle({ pointerEvents: "none" }); // links in preview should not be clickable
});

test("decorate emojis in chat bubble message preview", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        model: "discuss.channel",
        body: "Hello 😇",
        author_id: serverState.partnerId,
        res_id: channelId,
    });
    setupChatHub({ folded: [channelId] });
    await start();
    await hover(".o-mail-ChatBubble[name='General']");
    await waitFor(`.o-mail-ChatBubble-preview .o-mail-emoji[title=":innocent: :halo:"]:count(1)`);
});
