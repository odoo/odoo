import {
    assertChatHub,
    click,
    contains,
    defineMailModels,
    focus,
    inputFiles,
    insertText,
    isInViewportOf,
    onRpcBefore,
    openDiscuss,
    openFormView,
    openListView,
    patchUiSize,
    scroll,
    setupChatHub,
    SIZES,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { mockDate, tick } from "@odoo/hoot-mock";
import { EventBus } from "@odoo/owl";
import {
    asyncStep,
    Command,
    getService,
    patchWithCleanup,
    preloadBundle,
    serverState,
    waitForSteps,
    withUser,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";

import { rpc } from "@web/core/network/rpc";

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
    await contains(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu-counter", { count: 0 });
    // simulate receiving a message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hu", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-MessagingMenu-counter", { text: "1" });
    await contains(".o-mail-ChatWindow", { count: 0 });
});

test('chat window: post message on channel with "CTRL-Enter" keyboard shortcut for small screen size', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-ChatWindow .o-mail-Composer-input", "Test");
    triggerHotkey("control+Enter");
    await contains(".o-mail-Message");
});

test("Message post in chat window of chatter should log a note", async () => {
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
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
    await contains(".o-mail-Message", {
        text: "A needaction message to have it in messaging menu",
        contains: [".o-mail-Message-bubble"], // bubble = "Send message" mode
    });
    await contains(".o-mail-Composer [placeholder='Log an internal note…']");
    await insertText(".o-mail-ChatWindow .o-mail-Composer-input", "Test");
    triggerHotkey("control+Enter");
    await contains(".o-mail-Message", {
        text: "Test",
        contains: [".o-mail-Message-bubble", { count: 0 }], // no bubble = "Log note" mode
    });
});

test("Chatter in chat window should scroll to most recent message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "TestPartner" });
    // Fill both channels with random messages in order for the scrollbar to
    // appear.
    pyEnv["mail.message"].create(
        Array(50)
            .fill(0)
            .map((_, index) => ({
                model: "res.partner",
                body: "Non Empty Body ".repeat(25),
                author_id: serverState.odoobotId,
                needaction: true,
                res_id: partnerId,
            }))
    );
    const lastMessageId = pyEnv["mail.message"].create({
        model: "res.partner",
        body: "A needaction message to have it in messaging menu",
        author_id: serverState.odoobotId,
        needaction: true,
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: lastMessageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
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
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-Message", { count: 21 });
});

test("chat window: basic rendering", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
    await contains(".o-mail-ChatWindow-header", { text: "General" });
    await contains(".o-mail-ChatWindow-header .o-mail-ChatWindow-threadAvatar");
    await contains(".o-mail-ChatWindow-command", { count: 5 });
    await contains("[title='Start a Call']");
    await contains("[title='Start a Video Call']");
    await contains("[title='Open Actions Menu']");
    await contains("[title='Fold']");
    await contains("[title*='Close Chat Window']");
    await contains(".o-mail-ChatWindow .o-mail-Thread", { text: "The conversation is empty." });
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await contains(".o-mail-ChatWindow-command", { count: 15 });
    await contains(".o-dropdown-item", { text: "Attachments" });
    await contains(".o-dropdown-item", { text: "Pinned Messages" });
    await contains(".o-dropdown-item", { text: "Members" });
    await contains(".o-dropdown-item", { text: "Threads" });
    await contains(".o-dropdown-item", { text: "Invite People" });
    await contains(".o-dropdown-item", { text: "Search Messages" });
    await contains(".o-dropdown-item", { text: "Rename Thread" });
    await contains(".o-dropdown-item", { text: "Open in Discuss" });
    await contains(".o-dropdown-item", { text: "Notification Settings" });
    await contains(".o-dropdown-item", { text: "Call Settings" });
});

test.skip("Fold state of chat window is sync among browser tabs", async () => {
    // AKU TODO: fix crosstab
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true });
    await click(".o_menu_systray i[aria-label='Messages']", { target: env1 });
    await click(".o-mail-NotificationItem", { target: env1 });
    await contains(".o-mail-ChatWindow-header", { target: env2 });
    await click(".o-mail-ChatWindow-header", { target: env1 }); // Fold
    await contains(".o-mail-Thread", { count: 0, target: env1 });
    await contains(".o-mail-Thread", { count: 0, target: env2 });
    await click(".o-mail-ChatBubble", { target: env2 }); // Unfold
    await contains(".o-mail-ChatWindow .o-mail-Thread", { target: env1 });
    await contains(".o-mail-ChatWindow .o-mail-Thread", { target: env2 });
    await click("[title*='Close Chat Window']", { target: env1 });
    await contains(".o-mail-ChatWindow", { count: 0, target: env1 });
    await contains(".o-mail-ChatWindow", { count: 0, target: env2 });
});

test("chat window: fold", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    await start();
    // Open Thread
    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow .o-mail-Thread");
    assertChatHub({ opened: [channelId] });
    // Fold chat window
    await click(".o-mail-ChatWindow-command[title='Fold']");
    await contains(".o-mail-ChatWindow .o-mail-Thread", { count: 0 });
    assertChatHub({ folded: [channelId] });
    // Unfold chat window
    await click(".o-mail-ChatBubble");
    await contains(".o-mail-ChatWindow .o-mail-Thread");
    assertChatHub({ opened: [channelId] });
});

test("chat window: open / close", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    await start();
    await click("button i[aria-label='Messages']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
    assertChatHub({ opened: [channelId] });
    await click(".o-mail-ChatWindow-command[title*='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    assertChatHub({});
    // Reopen chat window
    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
    assertChatHub({ opened: [channelId] });
});

test("Open chatwindow as a non member", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [],
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
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
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
    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
});

test("chat window: close on ESCAPE", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    setupChatHub({ opened: [channelId] });
    await start();
    await contains(".o-mail-ChatWindow");
    await focus(".o-mail-Composer-input");
    triggerHotkey("Escape");
    await contains(".o-mail-ChatWindow", { count: 0 });
    assertChatHub({});
});

test("chat window: close on ESCAPE (multi)", async () => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create(
        Array(4)
            .keys()
            .map((i) => ({ name: `channel_${i}` }))
    );
    patchUiSize({ width: 1920 });
    setupChatHub({ opened: channelIds.reverse() });
    await start();
    await contains(".o-mail-ChatWindow", { count: 4 }); // expected order: 3, 2, 1, 0
    await contains(".o-mail-ChatWindow:eq(0)", { text: "channel_3" });
    await contains(".o-mail-ChatWindow:eq(1)", { text: "channel_2" });
    await contains(".o-mail-ChatWindow:eq(2)", { text: "channel_1" });
    await contains(".o-mail-ChatWindow:eq(3)", { text: "channel_0" });
    await focus(".o-mail-Composer-input:eq(3)");
    triggerHotkey("Escape");
    await contains(".o-mail-ChatWindow", { count: 3 });
    await contains(".o-mail-ChatWindow:eq(0)", { text: "channel_3" });
    await contains(".o-mail-ChatWindow:eq(1)", { text: "channel_2" });
    await contains(".o-mail-ChatWindow:eq(2)", { text: "channel_1" });
    await contains(".o-mail-ChatWindow:eq(2) .o-mail-Composer.o-focused");
    await focus(".o-mail-Composer-input:eq(0)");
    triggerHotkey("Escape");
    await contains(".o-mail-ChatWindow", { count: 2 });
    await contains(".o-mail-ChatWindow:eq(0)", { text: "channel_2" });
    await contains(".o-mail-ChatWindow:eq(1)", { text: "channel_1" });
    await contains(".o-mail-ChatWindow:eq(0) .o-mail-Composer.o-focused");
    triggerHotkey("Escape");
    await contains(".o-mail-ChatWindow", { count: 1 });
    await contains(".o-mail-ChatWindow", { text: "channel_1" });
    triggerHotkey("Escape");
    await contains(".o-mail-ChatWindow", { count: 0 });
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
    await contains(".o-mail-ChatWindow");
});

test("Close emoji picker in chat window with ESCAPE does not also close the chat window", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    setupChatHub({ opened: [channelId] });
    await start();
    await click("button[title='Add Emojis']");
    triggerHotkey("Escape");
    await contains(".o-EmojiPicker", { count: 0 });
    await contains(".o-mail-ChatWindow");
});

test("Close active thread action in chatwindow on ESCAPE", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    setupChatHub({ opened: [channelId] });
    await start();
    await contains(".o-mail-ChatWindow");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains(".o-mail-ChatWindow-command", { text: "General" });
    await click(".o-mail-ChatWindow-command", { text: "General" });
    await click(".o-dropdown-item", { text: "Invite People" });
    await contains(".o-discuss-ChannelInvitation");
    triggerHotkey("Escape");
    await contains(".o-discuss-ChannelInvitation", { count: 0 });
    await contains(".o-mail-ChatWindow");
});

test("ESC cancels thread rename", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    setupChatHub({ opened: [channelId] });
    await start();
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains(".o-mail-ChatWindow-command", { text: "General" });
    await click(".o-mail-ChatWindow-command", { text: "General" });
    await click(".o-dropdown-item", { text: "Rename Thread" });
    await contains(".o-mail-AutoresizeInput.o-focused[title='General']");
    await insertText(".o-mail-AutoresizeInput", "New", { replace: true });
    triggerHotkey("Escape");
    await contains(".o-mail-AutoresizeInput.o-focused", { count: 0 });
    await contains(".o-mail-ChatWindow-command", { text: "General" });
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
    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Channel_1" });
    await contains(".o-mail-ChatWindow", {
        text: "Channel_1",
        contains: [".o-mail-Composer-input:focus"],
    });
    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Channel_2" });
    await contains(".o-mail-ChatWindow", { count: 2 });
    await contains(".o-mail-ChatWindow", { text: "Channel_1" });
    await contains(".o-mail-ChatWindow", {
        text: "Channel_2",
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
    await contains(".o-mail-ChatWindow .o-mail-Composer-input", { count: 2 });
    await focus(".o-mail-Composer-input", {
        parent: [".o-mail-ChatWindow", { text: "MyTeam" }],
    });
    triggerHotkey("Escape");
    await contains(".o-mail-ChatWindow");
    await contains(".o-mail-ChatWindow", {
        text: "General",
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
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "channel1" });
    await contains(".o-mail-ChatWindow", { count: 1 });
    await contains(".o-mail-ChatWindow", {
        text: "channel1",
        contains: [".o-mail-Composer-input:focus"],
    });
    triggerHotkey("Tab");
    await contains(".o-mail-ChatWindow", {
        text: "channel1",
        contains: [".o-mail-Composer-input:focus"],
    });
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "channel2" });
    await contains(".o-mail-ChatWindow", { count: 2 });
    await contains(".o-mail-ChatWindow", {
        text: "channel2",
        contains: [".o-mail-Composer-input:focus"],
    });
    triggerHotkey("Tab");
    await contains(".o-mail-ChatWindow", {
        text: "channel1",
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
    await contains(".o-mail-ChatWindow .o-mail-Composer-input", { count: 3 });
    await focus(".o-mail-Composer-input", {
        parent: [".o-mail-ChatWindow", { text: "MyProject" }],
    });
    triggerHotkey("Tab");
    await contains(".o-mail-ChatWindow", {
        text: "MyTeam",
        contains: [".o-mail-Composer-input:focus"],
    });
    triggerHotkey("Tab");
    await contains(".o-mail-ChatWindow", {
        text: "General",
        contains: [".o-mail-Composer-input:focus"],
    });
    triggerHotkey("Tab");
    await contains(".o-mail-ChatWindow", {
        text: "MyProject",
        contains: [".o-mail-Composer-input:focus"],
    });
});

test("chat window should open when receiving a new DM", async () => {
    mockDate("2023-01-03 12:00:00"); // so that it's after last interest (mock server is in 2019 by default!)
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
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
    onRpcBefore("/mail/data", async (args) => {
        if (args.fetch_params.includes("init_messaging")) {
            asyncStep("init_messaging");
        }
    });
    await start();
    await waitForSteps(["init_messaging"]);
    await contains(".o-mail-ChatHub");
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hi, are you here?", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatBubble");
    await contains(".o-mail-ChatBubble-counter", { text: "1" });
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
    await contains(".o-mail-ChatHub");
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello, I'm new", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatWindow", { count: 0 });
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
    await contains(".o-mail-Message", { count: 10 });
    await insertText(".o-mail-Composer-input", "WOLOLO");
    triggerHotkey("Enter");
    await contains(".o-mail-Message", { count: 11 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
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
    await contains(".o-mail-ChatBubble");
    await contains(".o-mail-ChatBubble-counter", { count: 0 });
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "New Message", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatBubble-counter", { text: "1" });
    await contains(".o-mail-ChatBubble");
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
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    // Set content of the composer of the chat window
    await insertText(".o-mail-Composer-input", "XDU for the win !");
    await contains(".o-mail-Composer-footer .o-mail-AttachmentList .o-mail-AttachmentCard", {
        count: 0,
    });
    // Set attachments of the composer
    await inputFiles(".o-mail-Composer .o_input_file", [textFile1, textFile2]);
    await contains(".o-mail-AttachmentCard .fa-check", { count: 2 });
    await openDiscuss();
    await contains(".o-mail-ChatWindow", { count: 0 });
    await openFormView("discuss.channel", channelId);
    await contains(
        ".o-mail-Composer-footer .o-mail-AttachmentList .o-mail-AttachmentCard:not(.o-isUploading)",
        { count: 2 }
    );
    await contains(".o-mail-Composer-input", { value: "XDU for the win !" });
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
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-ChatWindow .o-mail-Thread", { scroll: 0 });
    await tick(); // wait for the scroll to first unread to complete
    await scroll(".o-mail-ChatWindow .o-mail-Thread", 142);
    await openDiscuss();
    await contains(".o-mail-ChatWindow", { count: 0 });
    await openListView("discuss.channel", { res_id: channelId });
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-ChatWindow .o-mail-Thread", { scroll: 142 });
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
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-ChatWindow .o-mail-Thread", { scroll: 0 });
    await tick(); // wait for the scroll to first unread to complete
    await scroll(".o-mail-ChatWindow .o-mail-Thread", 142);
    // fold chat window
    await click(".o-mail-ChatWindow-command[title='Fold']");
    await contains(".o-mail-Message", { count: 0 });
    await contains(".o-mail-ChatWindow .o-mail-Thread", { count: 0 });
    // unfold chat window
    await click(".o-mail-ChatBubble");
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-ChatWindow .o-mail-Thread", { scroll: 142 });
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
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-ChatWindow .o-mail-Thread", { scroll: 0 });
    await tick(); // wait for the scroll to first unread to complete
    await scroll(".o-mail-ChatWindow .o-mail-Thread", 142);
    // fold chat window
    await click(".o-mail-ChatWindow-command[title='Fold']");
    await openDiscuss();
    await contains(".o-mail-ChatWindow", { count: 0 });
    await openListView("discuss.channel", { res_id: channelId });
    // unfold chat window
    await click(".o-mail-ChatBubble");
    await contains(".o-mail-ChatWindow .o-mail-Message", { count: 30 });
    await contains(".o-mail-ChatWindow .o-mail-Thread", { scroll: 142 });
});

test("folded chat window should hide member-list and settings buttons", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({});
    await start();
    // Open Thread
    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await contains(".o-dropdown-item", { text: "Members" });
    await contains(".o-dropdown-item", { text: "Call Settings" });
    await click(".o-mail-ChatWindow-header"); // click away to close the more menu
    await contains(".o-dropdown-item", { text: "Members", count: 0 });
    // Fold chat window
    await click(".o-mail-ChatWindow-command[title='Fold']");
    await contains("[title='Open Actions Menu']", { count: 0 });
    await contains(".o-dropdown-item", { text: "Members", count: 0 });
    await contains(".o-dropdown-item", { text: "Call Settings", count: 0 });
    // Unfold chat window
    await click(".o-mail-ChatBubble");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await contains(".o-dropdown-item", { text: "Members" });
    await contains(".o-dropdown-item", { text: "Call Settings" });
});

test("Chat window in mobile are not foldable", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    patchUiSize({ size: SIZES.SM });
    setupChatHub({ opened: [channelId] });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-ChatWindow");
    await contains(".o-mail-ChatWindow-header.cursor-pointer", { count: 0 });
    await click(".o-mail-ChatWindow-header");
    await contains(".o-mail-Thread"); // content => non-folded
});

test("Synced chat windows should open at page load on mobile", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    patchUiSize({ size: SIZES.SM });
    setupChatHub({ opened: [channelId] });
    await start();
    await contains(".o-mail-ChatHub");
    await contains(".o-mail-ChatWindow");
});

test("chat window of channels should not have 'Open in Discuss' (mobile)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await contains(".o-dropdown-item", { text: "Open in Discuss", count: 0 });
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
    await contains(".o-mail-ChatWindow", { text: "Newbie" });
    await contains(".o_notification", {
        text: "Newbie connected. This is their first connection. Wish them luck.",
    });
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
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow .o-mail-Composer-input:focus");
    await click(".o-mail-Message [title='Expand']");
    await contains(".o-mail-Message-moreMenu.dropdown-menu");
    await focus(".o-mail-Message [title='Expand']"); // necessary otherwise focus is in composer input
    triggerHotkey("ArrowDown");
    await contains(".o-mail-Message-moreMenu :nth-child(1 of .dropdown-item).focus");
    triggerHotkey("ArrowDown");
    await contains(".o-mail-Message-moreMenu :nth-child(2 of .dropdown-item).focus");
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
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await click(".o-mail-Message [title='Expand']");
    await contains(".o-mail-Message-moreMenu.dropdown-menu");
    await focus(".o-mail-Message [title='Expand']"); // necessary otherwise focus is in composer input
    triggerHotkey("Escape");
    await contains(".o-mail-Message-moreMenu.dropdown-menu", { count: 0 });
    await contains(".o-mail-ChatWindow");
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
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "bob" });
    await contains(".o-mail-ChatWindow .o-mail-ChatWindow-header", { text: "bob" });
    // composer is focused by default, we remove that focus
    await contains(".o-mail-Composer-input:focus");
    document.querySelector(".o-mail-Composer-input").blur();
    await contains(".o-mail-Composer-input:not(:focus");
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
    await contains(".o-mail-ChatWindow-counter", { text: "1" });
    await click(".o-mail-ChatWindow-command[title*='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "bob" });
    await contains(".o-mail-ChatWindow .o-mail-ChatWindow-header", { text: "bob" });
    await contains(".o-mail-ChatWindow-counter", { count: 0 });
});

test("Notification settings rendering in chatwindow", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "general", channel_type: "channel" });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "general" });
    await contains(".o-mail-ChatWindow", { count: 1 });
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Notification Settings" });
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

test("open channel in chat window from push notification", async () => {
    patchWithCleanup(window.navigator, {
        serviceWorker: Object.assign(new EventBus(), { register: () => Promise.resolve() }),
    });
    const pyEnv = await startServer();
    const [channelId, salesId] = pyEnv["discuss.channel"].create([
        { name: "General" },
        { name: "Sales" },
    ]);
    setupChatHub({ opened: [salesId] });
    await start();
    await contains(".o-mail-ChatWindow", { text: "Sales" });
    await contains(".o-mail-ChatWindow", { text: "General", count: 0 });
    browser.navigator.serviceWorker.dispatchEvent(
        new MessageEvent("message", {
            data: { action: "OPEN_CHANNEL", data: { id: channelId } },
        })
    );
    await contains(".o-mail-ChatWindow", { text: "General" });
});

test("Chat window should be closed when leaving the channel", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "general" });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow", { text: "general" });
    await insertText(".o-mail-Composer-input", "/leave");
    await contains(".o-mail-NavigableList-active strong", { text: "leave" });
    triggerHotkey("Enter");
    await contains(".o-mail-Composer-input", { value: "/leave " });
    triggerHotkey("Enter");
    await contains(".o-mail-ChatWindow", { text: "general", count: 0 });
});

test("Chat window should be closed when leaving a chat", async () => {
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
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow", { text: "Demo" });
    await insertText(".o-mail-Composer-input", "/leave");
    await contains(".o-mail-NavigableList-active strong", { text: "leave" });
    triggerHotkey("Enter");
    await contains(".o-mail-Composer-input", { value: "/leave " });
    triggerHotkey("Enter");
    await contains(".o-mail-ChatWindow", { text: "Demo", count: 0 });
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
    await contains(".o-mail-ChatWindow", { count: 2 });
    await contains(".o-mail-ChatWindow:eq(0)", { text: "important channel" });
    await contains(".o-mail-ChatWindow:eq(1)", { text: "other channel" });
    await contains(".o-mail-ChatWindow:eq(0) .o-mail-Message", { count: 40 });
    await scroll(".o-mail-ChatWindow:eq(0) .o-mail-Thread", 0);
    await contains(".o-mail-ChatWindow:eq(0) .o-mail-Thread", { scroll: 0 });
    await focus(".o-mail-Composer-input:eq(1)");
    await contains(".o-mail-ChatWindow:eq(1) .o-mail-Composer.o-focused");
    triggerHotkey("Tab");
    await contains(".o-mail-ChatWindow:eq(0) .o-mail-Composer.o-focused");
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
    await focus(".o-mail-ChatWindow", { text: "General" });
    triggerHotkey("control+k");
    await contains(".o_command_palette_search", { text: "@" });
});

test("Do not squash logged notes", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "TestPartner" });
    const messageId = pyEnv["mail.message"].create([
        {
            model: "res.partner",
            body: "Test Message",
            author_id: partnerId,
            needaction: true,
            res_id: partnerId,
        },
        {
            model: "res.partner",
            body: "Message",
            author_id: serverState.partnerId,
            needaction: true,
            res_id: partnerId,
        },
        {
            model: "res.partner",
            body: "Message Squashed",
            author_id: serverState.partnerId,
            needaction: true,
            res_id: partnerId,
        },
        {
            model: "res.partner",
            body: "Hello",
            author_id: serverState.partnerId,
            needaction: true,
            res_id: partnerId,
            is_note: true,
        },
        {
            model: "res.partner",
            body: "World!",
            author_id: serverState.partnerId,
            needaction: true,
            res_id: partnerId,
            is_note: true,
        },
    ]);
    pyEnv["mail.notification"].create({
        mail_message_id: messageId[0],
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-Message.o-squashed", { text: "Message Squashed" });
    await contains(".o-mail-Message:not(.o-squashed)", { text: "Hello" });
    await contains(".o-mail-Message:not(.o-squashed)", { text: "World!" });
});
