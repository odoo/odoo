import {
    SIZES,
    assertSteps,
    click,
    contains,
    defineMailModels,
    focus,
    hover,
    inputFiles,
    insertText,
    onRpcBefore,
    openDiscuss,
    openFormView,
    openListView,
    patchUiSize,
    scroll,
    start,
    startServer,
    step,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { queryFirst } from "@odoo/hoot-dom";
import { mockDate, tick } from "@odoo/hoot-mock";
import { Command, getService, serverState, withUser } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";

import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineMailModels();

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
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ fold_state: "open", partner_id: serverState.partnerId }),
        ],
    });
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
        contains: [".o-mail-Message-bubble.border"], // bordered bubble = "Send message" mode
    });
    await contains(".o-mail-Composer [placeholder='Log an internal note…']");
    await insertText(".o-mail-ChatWindow .o-mail-Composer-input", "Test");
    triggerHotkey("control+Enter");
    await contains(".o-mail-Message", {
        text: "Test",
        contains: [".o-mail-Message-bubble:not(.border)"], // non-bordered bubble = "Log note" mode
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
    await contains(".o-mail-ChatWindow-command", { count: 4 });
    await contains("[title='Start a Call']");
    await contains("[title='Open Actions Menu']");
    await contains("[title='Fold']");
    await contains("[title*='Close Chat Window']");
    await contains(".o-mail-ChatWindow .o-mail-Thread", { text: "The conversation is empty." });
    await click("[title='Open Actions Menu']");
    await contains(".o-mail-ChatWindow-command", { count: 14 });
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

test("Mobile: opening a chat window should not update channel state on the server", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ fold_state: "closed", partner_id: serverState.partnerId }),
        ],
    });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-ChatWindow");
    const [member] = pyEnv["discuss.channel.member"].search_read([
        ["channel_id", "=", channelId],
        ["partner_id", "=", serverState.partnerId],
    ]);
    expect(member.fold_state).toBe("closed");
});

test("chat window: fold", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({});
    onRpcBefore("/discuss/channel/fold", (args) => step(`channel_fold/${args.state}`));
    await start();
    // Open Thread
    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow .o-mail-Thread");
    await assertSteps(["channel_fold/open"]);
    // Fold chat window
    await click(".o-mail-ChatWindow-command[title='Fold']");
    await contains(".o-mail-ChatWindow .o-mail-Thread", { count: 0 });
    await assertSteps(["channel_fold/folded"]);
    // Unfold chat window
    await click(".o-mail-ChatBubble");
    await contains(".o-mail-ChatWindow .o-mail-Thread");
    await assertSteps(["channel_fold/open"]);
});

test("chat window: open / close", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({});
    onRpcBefore("/discuss/channel/fold", (args) => step(`channel_fold/${args.state}`));
    await start();
    await click("button i[aria-label='Messages']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
    await assertSteps(["channel_fold/open"]);
    await click(".o-mail-ChatWindow-command[title*='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await assertSteps(["channel_fold/closed"]);
    // Reopen chat window
    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
    await assertSteps(["channel_fold/open"]);
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

test("Mobile: closing a chat window should not update channel state on the server", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ fold_state: "open", partner_id: serverState.partnerId }),
        ],
    });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    await click("[title*='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    const [member] = pyEnv["discuss.channel.member"].search_read([
        ["channel_id", "=", channelId],
        ["partner_id", "=", serverState.partnerId],
    ]);
    expect(member.fold_state).toBe("open");
});

test("chat window: close on ESCAPE", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ fold_state: "open", partner_id: serverState.partnerId }),
        ],
    });
    onRpcBefore("/discuss/channel/fold", (args) => step(`channel_fold/${args.state}`));
    await start();
    await contains(".o-mail-ChatWindow");
    await focus(".o-mail-Composer-input");
    triggerHotkey("Escape");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await assertSteps(["channel_fold/closed"]);
});

test("chat window: close on ESCAPE (multi)", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create(
        Array(4)
            .keys()
            .map((i) => ({
                name: `channel_${i}`,
                channel_member_ids: [
                    Command.create({ fold_state: "open", partner_id: serverState.partnerId }),
                ],
            }))
    );
    patchUiSize({ width: 1920 });
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
});

test("Close composer suggestions in chat window with ESCAPE does not also close the chat window", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["discuss.channel"].create({
        name: "general",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, fold_state: "open" }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await insertText(".o-mail-Composer-input", "@");
    triggerHotkey("Escape");
    await contains(".o-mail-ChatWindow");
});

test("Close emoji picker in chat window with ESCAPE does not also close the chat window", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "general",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, fold_state: "open" }),
        ],
    });
    await start();
    await click("button[aria-label='Emojis']");
    triggerHotkey("Escape");
    await contains(".o-EmojiPicker", { count: 0 });
    await contains(".o-mail-ChatWindow");
});

test("open 2 different chat windows: enough screen width [REQUIRE FOCUS]", async () => {
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

test("focus next visible chat window when closing current chat window with ESCAPE [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        {
            name: "General",
            channel_member_ids: [
                Command.create({
                    fold_state: "open",
                    partner_id: serverState.partnerId,
                }),
            ],
        },
        {
            name: "MyTeam",
            channel_member_ids: [
                Command.create({
                    fold_state: "open",
                    partner_id: serverState.partnerId,
                }),
            ],
        },
    ]);
    patchUiSize({ width: 1920 });
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

test("chat window: switch on TAB [REQUIRE FOCUS]", async () => {
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

test("chat window: TAB cycle with 3 open chat windows [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        {
            name: "General",
            channel_member_ids: [
                Command.create({
                    fold_state: "open",
                    partner_id: serverState.partnerId,
                }),
            ],
        },
        {
            name: "MyTeam",
            channel_member_ids: [
                Command.create({
                    fold_state: "open",
                    partner_id: serverState.partnerId,
                }),
            ],
        },
        {
            name: "MyProject",
            channel_member_ids: [
                Command.create({
                    fold_state: "open",
                    partner_id: serverState.partnerId,
                }),
            ],
        },
    ]);
    patchUiSize({ width: 1920 });
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
    onRpcBefore("/mail/action", async (args) => {
        if (args.init_messaging) {
            step("init_messaging");
        }
    });
    await start();
    await assertSteps(["init_messaging"]);
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
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                fold_state: "open",
                partner_id: serverState.partnerId,
            }),
        ],
    });
    for (let i = 0; i < 10; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
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
            Command.create({
                fold_state: "folded",
                partner_id: serverState.partnerId,
            }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
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
    await inputFiles(".o-mail-Composer-coreMain .o_input_file", [textFile1, textFile2]);
    await contains(".o-mail-AttachmentCard .fa-check", { count: 2 });
    await openDiscuss();
    await contains(".o-mail-ChatWindow", { count: 0 });
    await openFormView("discuss.channel", channelId);
    await contains(".o-mail-Composer-footer .o-mail-AttachmentList .o-mail-AttachmentCard", {
        count: 2,
    });
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
    await click("[title='Open Actions Menu']");
    await contains(".o-dropdown-item", { text: "Members" });
    await contains(".o-dropdown-item", { text: "Call Settings" });
});

test("Chat window in mobile are not foldable", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ fold_state: "open", partner_id: serverState.partnerId }),
        ],
    });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-ChatWindow");
    await contains(".o-mail-ChatWindow-header.cursor-pointer", { count: 0 });
    await click(".o-mail-ChatWindow-header");
    await contains(".o-mail-Thread"); // content => non-folded
});

test("Server-synced chat windows should not open at page load on mobile", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                fold_state: "open",
                partner_id: serverState.partnerId,
            }),
        ],
    });
    patchUiSize({ size: SIZES.SM });
    await start();
    await contains(".o-mail-ChatHub");
    await contains(".o-mail-ChatWindow", { count: 0 });
});

test("chat window of channels should not have 'Open in Discuss' (mobile)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
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

test("keyboard navigation ArrowUp/ArrowDown on message action dropdown in chat window [REQUIRE FOCUS]", async () => {
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
    pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "general" });
    await contains(".o-mail-ChatWindow", { count: 1 });
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Notification Settings" });
    await contains("button", { text: "All Messages" });
    await contains("button", { text: "Mentions Only", count: 2 }); // the extra is in the Use Default as subtitle
    await contains("button", { text: "Nothing" });
    await click("button", { text: "Mute Conversation" });
    await contains("button", { text: "For 15 minutes" });
    await contains("button", { text: "For 1 hour" });
    await contains("button", { text: "For 3 hours" });
    await contains("button", { text: "For 8 hours" });
    await contains("button", { text: "For 24 hours" });
    await contains("button", { text: "Until I turn it back on" });
});

test("Can make chat windows bigger", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "general", channel_type: "channel" });
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
    const normalWidth = queryFirst(".o-mail-ChatWindow").getBoundingClientRect().width;
    await hover(".o-mail-ChatHub-bubbles");
    await click("button[title='Chat Options']");
    await contains("button:contains(Large windows)");
    await contains("button:contains(Large windows) input");
    await contains("button:contains(Large windows) input:not(:checked)");
    await click("button:contains(Large windows)");
    await contains("button:contains(Large windows) input:checked");
    await contains(".o-mail-ChatWindow.o-large");
    const largeWidth = queryFirst(".o-mail-ChatWindow").getBoundingClientRect().width;
    expect(largeWidth).toBeGreaterThan(normalWidth);
});

test("Bigger chat windows is locally persistent (saved in local storage)", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "general", channel_type: "channel" });
    browser.localStorage.setItem("mail.user_setting.chat_window_big", true);
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow.o-large");
    expect(browser.localStorage.getItem("mail.user_setting.chat_window_big")).toBe("true");
    await hover(".o-mail-ChatHub-bubbles");
    await click("button[title='Chat Options']");
    await click("button:contains(Large windows)");
    await contains(".o-mail-ChatWindow.o-large");
    expect(browser.localStorage.getItem("mail.user_setting.chat_window_big")).toBe(null);
});
