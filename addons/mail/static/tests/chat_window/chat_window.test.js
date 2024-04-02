import { describe, expect, test } from "@odoo/hoot";

/** @type {ReturnType<import("@mail/utils/common/misc").rpcWithEnv>} */
let rpc;

import {
    CHAT_WINDOW_END_GAP_WIDTH,
    CHAT_WINDOW_INBETWEEN_WIDTH,
    CHAT_WINDOW_WIDTH,
} from "@mail/core/common/chat_window_service";
import {
    SIZES,
    assertSteps,
    click,
    contains,
    createFile,
    defineMailModels,
    focus,
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
} from "../mail_test_helpers";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { withUser } from "@web/../tests/_framework/mock_server/mock_server";
import { rpcWithEnv } from "@mail/utils/common/misc";
import { mockDate } from "@odoo/hoot-mock";

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
    const env = await start();
    rpc = rpcWithEnv(env);
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
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ fold_state: "open", partner_id: serverState.partnerId }),
        ],
    });
    patchUiSize({ size: SIZES.SM });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
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
        needaction_partner_ids: [serverState.partnerId],
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
    await contains("[title='Close Chat Window']");
    await contains(".o-mail-ChatWindow .o-mail-Thread", {
        text: "There are no messages in this conversation.",
    });
    await click("[title='Open Actions Menu']");
    await contains(".o-mail-ChatWindow-command", { count: 12 });
    await contains("[title='Search Messages']");
    await contains("[title='Rename']");
    await contains("[title='Pinned Messages']");
    await contains("[title='Show Attachments']");
    await contains("[title='Add Users']");
    await contains("[title='Show Member List']");
    await contains("[title='Show Call Settings']");
    await contains("[title='Open in Discuss']");
});

test("Fold state of chat window is sync among browser tabs", async () => {
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
    await click(".o-mail-ChatWindow-header", { target: env2 }); // Unfold
    await contains(".o-mail-ChatWindow .o-mail-Thread", { target: env1 });
    await contains(".o-mail-ChatWindow .o-mail-Thread", { target: env2 });
    await click("[title='Close Chat Window']", { target: env1 });
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
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
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
    await click(".o-mail-ChatWindow-command[title='Open']");
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
    await click(".o-mail-ChatWindow-command[title='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await assertSteps(["channel_fold/closed"]);
    // Reopen chat window
    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
    await assertSteps(["channel_fold/open"]);
});

test("open chat on very narrow device should work", async () => {
    const pyEnv = await startServer();
    patchUiSize({ width: 200 });
    pyEnv["discuss.channel"].create({});
    await start();
    expect(CHAT_WINDOW_WIDTH).toBeGreaterThan(200, {
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
    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
    await click("[title='Close Chat Window']");
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
    expect(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 2 + CHAT_WINDOW_INBETWEEN_WIDTH
    ).toBeLessThan(1920, {
        message: "should have enough space to open 2 chat windows simultaneously",
    });
    await start();
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

test("open 3 different chat windows: not enough screen width", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        { name: "Channel_1" },
        { name: "Channel_2" },
        { name: "Channel_3" },
    ]);
    patchUiSize({ width: 900 });
    expect(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 2 + CHAT_WINDOW_INBETWEEN_WIDTH
    ).toBeLessThan(900, {
        message: "should have enough space to open 2 chat windows simultaneously",
    });
    expect(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 3 + CHAT_WINDOW_INBETWEEN_WIDTH * 2
    ).toBeGreaterThan(900, {
        message: "should not have enough space to open 3 chat windows simultaneously",
    });
    await start();
    // open, from systray menu, chat windows of channels with Id 1, 2, then 3
    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Channel_1" });
    await contains(".o-mail-ChatWindow");
    await contains(".o-mail-ChatWindowHiddenToggler", { count: 0 });
    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Channel_2" });
    await contains(".o-mail-ChatWindow", { count: 2 });
    await contains(".o-mail-ChatWindowHiddenToggler", { count: 0 });
    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Channel_3" });
    await contains(".o-mail-ChatWindow", { count: 2 });
    await contains(".o-mail-ChatWindowHiddenToggler");
    await contains(".o-mail-ChatWindow", { text: "Channel_1" });
    await contains(".o-mail-ChatWindow", {
        text: "Channel_3",
        contains: [".o-mail-Composer-input:focus"],
    });
});

test("closing hidden chat window", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        { name: "Ch_1" },
        { name: "Ch_2" },
        { name: "Ch_3" },
        { name: "Ch_4" },
    ]);
    patchUiSize({ width: 900 });
    expect(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 2 + CHAT_WINDOW_INBETWEEN_WIDTH
    ).toBeLessThan(900, {
        message: "should have enough space to open 2 chat windows simultaneously",
    });
    expect(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 3 + CHAT_WINDOW_INBETWEEN_WIDTH * 2
    ).toBeGreaterThan(900, {
        message: "should not have enough space to open 3 chat windows simultaneously",
    });
    await start();
    await click("i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Ch_1" });
    await contains(".o-mail-ChatWindow");
    await click("i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Ch_2" });
    await contains(".o-mail-ChatWindow", { count: 2 });
    await click("i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Ch_3" });
    await contains(".o-mail-ChatWindowHiddenToggler", { text: "1" });
    await click("i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Ch_4" });
    await contains(".o-mail-ChatWindowHiddenToggler", { text: "2" });
    await click(".o-mail-ChatWindowHiddenToggler");
    await contains(":not(.o-mail-ChatWindowHiddenMenu) .o-mail-ChatWindow", { text: "Ch_1" });
    await contains(".o-mail-ChatWindowHiddenMenu .o-mail-ChatWindow", { text: "Ch_2" });
    await contains(".o-mail-ChatWindowHiddenMenu .o-mail-ChatWindow", { text: "Ch_3" });
    await contains(":not(.o-mail-ChatWindowHiddenMenu) .o-mail-ChatWindow", { text: "Ch_4" });
    await click(".o-mail-ChatWindow-command[title='Close Chat Window']", {
        parent: [".o-mail-ChatWindow-header", { text: "Ch_2" }],
    });
    await contains(":not(.o-mail-ChatWindowHiddenMenu) .o-mail-ChatWindow", { text: "Ch_1" });
    await contains(".o-mail-ChatWindow", { count: 0, text: "Ch_2" });
    await contains(".o-mail-ChatWindowHiddenMenu .o-mail-ChatWindow", { text: "Ch_3" });
    await contains(":not(.o-mail-ChatWindowHiddenMenu) .o-mail-ChatWindow", { text: "Ch_4" });
});

test("Opening hidden chat window from messaging menu", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([{ name: "Ch_1" }, { name: "Ch_2" }, { name: "Ch_3" }]);
    patchUiSize({ width: 900 });
    expect(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 2 + CHAT_WINDOW_INBETWEEN_WIDTH
    ).toBeLessThan(900, {
        message: "should have enough space to open 2 chat windows simultaneously",
    });
    expect(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 3 + CHAT_WINDOW_INBETWEEN_WIDTH * 2
    ).toBeGreaterThan(900, {
        message: "should not have enough space to open 3 chat windows simultaneously",
    });
    await start();
    await click("i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Ch_1" });
    await click("i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Ch_2" });
    await click("i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Ch_3" });
    await click(".o-mail-ChatWindowHiddenToggler");
    await contains(":not(.o-mail-ChatWindowHiddenMenu) .o-mail-ChatWindow", { text: "Ch_1" });
    await contains(".o-mail-ChatWindowHiddenMenu .o-mail-ChatWindow", { text: "Ch_2" });
    await contains(":not(.o-mail-ChatWindowHiddenMenu) .o-mail-ChatWindow", { text: "Ch_3" });
    await click("i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Ch_2" });
    await click(".o-mail-ChatWindowHiddenToggler");
    await contains(":not(.o-mail-ChatWindowHiddenMenu) .o-mail-ChatWindow", { text: "Ch_1" });
    await contains(":not(.o-mail-ChatWindowHiddenMenu) .o-mail-ChatWindow", { text: "Ch_2" });
    await contains(".o-mail-ChatWindowHiddenMenu .o-mail-ChatWindow", { text: "Ch_3" });
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
    expect(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 2 + CHAT_WINDOW_INBETWEEN_WIDTH
    ).toBeLessThan(1920, {
        message: "should have enough space to open 2 chat windows simultaneously",
    });
    await start();
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
    expect(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 2 + CHAT_WINDOW_INBETWEEN_WIDTH
    ).toBeLessThan(1920, {
        message: "should have enough space to open 2 chat windows simultaneously",
    });
    await start();
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
    expect(
        CHAT_WINDOW_END_GAP_WIDTH * 3 + CHAT_WINDOW_WIDTH * 3 + CHAT_WINDOW_INBETWEEN_WIDTH * 2
    ).toBeLessThan(1920, {
        message: "should have enough space to open 3 chat windows simultaneously",
    });
    await start();
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

test("new message separator is shown in a chat window of a chat on receiving new message if there is a history of conversation", async () => {
    mockDate("2023-01-03 12:00:00"); // so that it's after last interest (mock server is in 2019 by default!)
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({ name: "Foreigner user", partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                fold_state: "open",
                unpin_dt: "2021-01-01 12:00:00",
                last_interest_dt: "2021-01-01 10:00:00",
                partner_id: serverState.partnerId,
            }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", serverState.partnerId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], { seen_message_id: messageId });
    const env = await start();
    rpc = rpcWithEnv(env);
    // simulate receiving a message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hu", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatWindow");
    await contains(".o-mail-Message", { count: 2 });
    await contains(".o-mail-Thread-newMessage hr + span", { text: "New messages" });
});

test("new message separator is shown in chat window of chat on receiving new message when there was no history", async () => {
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
    onRpcBefore("/mail/action", (args) => {
        if (args.init_messaging) {
            step(`/mail/action - ${JSON.stringify(args)}`);
        }
    });
    const env = await start();
    rpc = rpcWithEnv(env);
    await assertSteps([
        `/mail/action - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: serverState.userId, allowed_company_ids: [1] },
        })}`,
    ]);
    // send after init_messaging because bus subscription is done after init_messaging
    // simulate receiving a message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hu", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Thread-newMessage hr + span", { text: "New messages" });
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
    const env = await start();
    rpc = rpcWithEnv(env);
    await contains(".o-mail-ChatWindowContainer");
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "new message", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatWindow");
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
    const env = await start();
    rpc = rpcWithEnv(env);
    await contains(".o-mail-ChatWindowContainer");
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "new message", message_type: "comment" },
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
    const env = await start();
    rpc = rpcWithEnv(env);
    await contains(".o-mail-ChatWindow.o-folded");
    await contains(".o-mail-ChatWindow-counter", { count: 0 });
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "New Message", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatWindow-counter", { text: "1" });
    await contains(".o-mail-ChatWindow.o-folded");
});

test("should not have chat window hidden menu in mobile (transition from 3 chat windows in desktop to mobile)", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        { name: "Channel-1" },
        { name: "Channel-2" },
        { name: "Channel-3" },
    ]);
    patchUiSize({ width: 900 });
    expect(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 2 + CHAT_WINDOW_INBETWEEN_WIDTH
    ).toBeLessThan(900, {
        message: "should have enough space to open 2 chat windows simultaneously",
    });
    expect(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 3 + CHAT_WINDOW_INBETWEEN_WIDTH * 2
    ).toBeGreaterThan(900, {
        message: "should not have enough space to open 3 chat windows simultaneously",
    });
    await start();
    await openDiscuss();
    // open, from systray menu, chat windows of channels with id 1, 2, 3
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Channel-1" });
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Channel-2" });
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Channel-3" });
    // simulate resize to go into mobile
    patchUiSize({ size: SIZES.SM });
    window.dispatchEvent(new UIEvent("resize"));
    await contains(".o-mail-ChatWindowHiddenToggler", { count: 0 });
});

test("chat window: composer state conservation on toggle discuss", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    // Set content of the composer of the chat window
    await insertText(".o-mail-Composer-input", "XDU for the win !");
    await contains(".o-mail-Composer-footer .o-mail-AttachmentList .o-mail-AttachmentCard", {
        count: 0,
    });
    // Set attachments of the composer
    await inputFiles(".o-mail-Composer-coreMain .o_input_file", [
        await createFile({
            name: "text state conservation on toggle home menu.txt",
            content: "hello, world",
            contentType: "text/plain",
        }),
        await createFile({
            name: "text2 state conservation on toggle home menu.txt",
            content: "hello, xdu is da best man",
            contentType: "text/plain",
        }),
    ]);
    await contains(".o-mail-AttachmentCard .fa-check", { count: 2 });
    await openDiscuss();
    await contains(".o-mail-ChatWindow", { count: 0 });
    await openFormView("discuss.channel", channelId);
    await contains(".o-mail-Composer-footer .o-mail-AttachmentList .o-mail-AttachmentCard", {
        count: 2,
    });
    await contains(".o-mail-Composer-input", { value: "XDU for the win !" });
});

test("focusing a chat window of a chat should make new message separator disappear [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({
        name: "Foreigner user",
        partner_id: partnerId,
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({
                fold_state: "open",
                partner_id: serverState.partnerId,
            }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", serverState.partnerId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], { seen_message_id: messageId });
    const env = await start();
    rpc = rpcWithEnv(env);
    await contains(".o-mail-Composer-input:not(:focus)");
    // simulate receiving a message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hu", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Thread-newMessage hr + span", { text: "New messages" });
    await focus(".o-mail-Composer-input");
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });
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
    await contains(".o-mail-ChatWindow .o-mail-Thread", { scroll: "bottom" });
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
    await contains(".o-mail-ChatWindow .o-mail-Thread", { scroll: "bottom" });
    await scroll(".o-mail-ChatWindow .o-mail-Thread", 142);
    // fold chat window
    await click(".o-mail-ChatWindow-command[title='Fold']");
    await contains(".o-mail-Message", { count: 0 });
    await contains(".o-mail-ChatWindow .o-mail-Thread", { count: 0 });
    // unfold chat window
    await click(".o-mail-ChatWindow-command[title='Open']");
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
    await contains(".o-mail-ChatWindow .o-mail-Thread", { scroll: "bottom" });
    await scroll(".o-mail-ChatWindow .o-mail-Thread", 142);
    // fold chat window
    await click(".o-mail-ChatWindow-command[title='Fold']");
    await openDiscuss();
    await contains(".o-mail-ChatWindow", { count: 0 });
    await openListView("discuss.channel", { res_id: channelId });
    // unfold chat window
    await click(".o-mail-ChatWindow-command[title='Open']");
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
    await contains("[title='Show Member List']");
    await contains("[title='Show Call Settings']");
    await click(".o-mail-ChatWindow-header"); // click away to close the more menu
    await contains("[title='Show Member List']", { count: 0 });
    // Fold chat window
    await click(".o-mail-ChatWindow-command[title='Fold']");
    await contains("[title='Open Actions Menu']", { count: 0 });
    await contains("[title='Show Member List']", { count: 0 });
    await contains("[title='Show Call Settings']", { count: 0 });
    // Unfold chat window
    await click(".o-mail-ChatWindow-command[title='Open']");
    await click("[title='Open Actions Menu']");
    await contains("[title='Show Member List']");
    await contains("[title='Show Call Settings']");
});

test("Chat window in mobile are not foldable", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ fold_state: "open", partner_id: serverState.partnerId }),
        ],
    });
    patchUiSize({ size: SIZES.SM });
    await start();
    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
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
    await contains(".o-mail-ChatWindowContainer");
    await contains(".o-mail-ChatWindow", { count: 0 });
});

test("chat window of channels should not have 'Open in Discuss' (mobile)", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await contains("[title='Open in Discuss']", { count: 0 });
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

test("hiding/swapping hidden chat windows does not update server state", async () => {
    patchUiSize({ size: SIZES.MD }); // only 2 chat window can be opened at a time
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([{ name: "General" }, { name: "Sales" }, { name: "D&D" }]);
    onRpcBefore("/discuss/channel/fold", (args) => {
        const [channel] = pyEnv["discuss.channel"].search_read([["id", "=", args.channel_id]]);
        step(`${channel.name} - ${args.state}`);
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "General" });
    await contains(".o-mail-ChatWindow", { text: "General" });
    await assertSteps(["General - open"]);
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Sales" });
    await contains(".o-mail-ChatWindow", { text: "Sales" });
    await assertSteps(["Sales - open"]);
    // Sales chat window will be hidden since there is not enough space for the
    // D&D one but Sales fold state should not be updated.
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "D&D" });
    await contains(".o-mail-ChatWindow", { text: "D&D" });
    await assertSteps(["D&D - open"]);
    // D&D chat window will be hidden since there is not enough space for the
    // Sales one, the server should not be notified as the state is up to date.
    await click(".o-mail-ChatWindowHiddenToggler");
    await click(".o-mail-ChatWindowHiddenMenu-item .o-mail-ChatWindow-header", {
        text: "Sales",
        visible: true,
    });
    await contains(".o-mail-ChatWindow", { text: "Sales" });
    await assertSteps([]);
});
