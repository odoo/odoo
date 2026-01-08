/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import {
    CHAT_WINDOW_END_GAP_WIDTH,
    CHAT_WINDOW_INBETWEEN_WIDTH,
    CHAT_WINDOW_WIDTH,
} from "@mail/core/common/chat_window_service";
import { Command } from "@mail/../tests/helpers/command";
import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { start } from "@mail/../tests/helpers/test_utils";

import { triggerHotkey } from "@web/../tests/helpers/utils";
import {
    click,
    contains,
    createFile,
    focus,
    inputFiles,
    insertText,
    scroll,
} from "@web/../tests/utils";

QUnit.module("chat window");

QUnit.test(
    "Mobile: chat window shouldn't open automatically after receiving a new message",
    async () => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
        const userId = pyEnv["res.users"].create({ partner_id: partnerId });
        const channelId = pyEnv["discuss.channel"].create({
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "chat",
        });
        patchUiSize({ size: SIZES.SM });
        const { env } = await start();
        await contains(".o_menu_systray i[aria-label='Messages']");
        await contains(".o-mail-MessagingMenu-counter", { count: 0 });
        // simulate receiving a message
        pyEnv.withUser(userId, () =>
            env.services.rpc("/mail/message/post", {
                post_data: { body: "hu", message_type: "comment" },
                thread_id: channelId,
                thread_model: "discuss.channel",
            })
        );
        await contains(".o-mail-MessagingMenu-counter", { text: "1" });
        await contains(".o-mail-ChatWindow", { count: 0 });
    }
);

QUnit.test(
    'chat window: post message on channel with "CTRL-Enter" keyboard shortcut for small screen size',
    async () => {
        const pyEnv = await startServer();
        pyEnv["discuss.channel"].create({
            channel_member_ids: [
                Command.create({ is_minimized: true, partner_id: pyEnv.currentPartnerId }),
            ],
        });
        patchUiSize({ size: SIZES.SM });
        await start();
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-NotificationItem");
        await insertText(".o-mail-ChatWindow .o-mail-Composer-input", "Test");
        triggerHotkey("control+Enter");
        await contains(".o-mail-Message");
    }
);

QUnit.test("Message post in chat window of chatter should log a note", async () => {
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

QUnit.test("Chatter in chat window should scroll to most recent message", async () => {
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
                author_id: pyEnv.odoobotId,
                needaction: true,
                needaction_partner_ids: [pyEnv.currentPartnerId],
                res_id: partnerId,
            }))
    );
    const lastMessageId = pyEnv["mail.message"].create({
        model: "res.partner",
        body: "A needaction message to have it in messaging menu",
        author_id: pyEnv.odoobotId,
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: lastMessageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
});

QUnit.test("load messages from opening chat window from messaging menu", async () => {
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

QUnit.test("chat window: basic rendering", async () => {
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
    await contains(".o-mail-ChatWindow-command", { count: 11 });
    await contains("[title='Search Messages']");
    await contains("[title='Pinned Messages']");
    await contains("[title='Show Attachments']");
    await contains("[title='Add Users']");
    await contains("[title='Show Member List']");
    await contains("[title='Show Call Settings']");
    await contains("[title='Open in Discuss']");
});

QUnit.test("Fold state of chat window is sync among browser tabs", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    await click(".o_menu_systray i[aria-label='Messages']", { target: tab1.target });
    await click(".o-mail-NotificationItem", { target: tab1.target });
    await click(".o-mail-ChatWindow-header", { target: tab1.target }); // Fold
    await contains(".o-mail-Thread", { count: 0, target: tab1.target });
    await contains(".o-mail-Thread", { count: 0, target: tab2.target });
    await click(".o-mail-ChatWindow-header", { target: tab2.target }); // Unfold
    await contains(".o-mail-ChatWindow .o-mail-Thread", { target: tab1.target });
    await contains(".o-mail-ChatWindow .o-mail-Thread", { target: tab2.target });
    await click("[title='Close Chat Window']", { target: tab1.target });
    await contains(".o-mail-ChatWindow", { count: 0, target: tab1.target });
    await contains(".o-mail-ChatWindow", { count: 0, target: tab2.target });
});

QUnit.test(
    "Mobile: opening a chat window should not update channel state on the server",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            channel_member_ids: [
                Command.create({ fold_state: "closed", partner_id: pyEnv.currentPartnerId }),
            ],
        });
        patchUiSize({ size: SIZES.SM });
        await start();
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-NotificationItem");
        await click(".o-mail-ChatWindow");
        const [member] = pyEnv["discuss.channel.member"].searchRead([
            ["channel_id", "=", channelId],
            ["partner_id", "=", pyEnv.currentPartnerId],
        ]);
        assert.strictEqual(member.fold_state, "closed");
    }
);

QUnit.test("chat window: fold", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({});
    await start({
        mockRPC(route, args) {
            if (args.method === "channel_fold") {
                assert.step(`rpc:${args.method}/${args.kwargs.state}`);
            }
        },
    });
    // Open Thread
    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow .o-mail-Thread");
    assert.verifySteps(["rpc:channel_fold/open"]);

    // Fold chat window
    await click(".o-mail-ChatWindow-command[title='Fold']");
    await contains(".o-mail-ChatWindow .o-mail-Thread", { count: 0 });
    assert.verifySteps(["rpc:channel_fold/folded"]);

    // Unfold chat window
    await click(".o-mail-ChatWindow-command[title='Open']");
    await contains(".o-mail-ChatWindow .o-mail-Thread");
    assert.verifySteps(["rpc:channel_fold/open"]);
});

QUnit.test("chat window: open / close", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({});
    await start({
        mockRPC(route, args) {
            if (args.method === "channel_fold") {
                assert.step(`rpc:channel_fold/${args.kwargs.state}`);
            }
        },
    });
    await click("button i[aria-label='Messages']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
    assert.verifySteps(["rpc:channel_fold/open"]);

    await click(".o-mail-ChatWindow-command[title='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    assert.verifySteps(["rpc:channel_fold/closed"]);

    // Reopen chat window
    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
    assert.verifySteps(["rpc:channel_fold/open"]);
});

QUnit.test("open chat on very narrow device should work", async (assert) => {
    const pyEnv = await startServer();
    patchUiSize({ width: 200 });
    pyEnv["discuss.channel"].create({});
    await start();
    assert.ok(CHAT_WINDOW_WIDTH > 200, "Device is narrower than usual chat window width"); // scenario where this might fail
    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
});

QUnit.test(
    "Mobile: closing a chat window should not update channel state on the server",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            channel_member_ids: [
                Command.create({ fold_state: "open", partner_id: pyEnv.currentPartnerId }),
            ],
        });
        patchUiSize({ size: SIZES.SM });
        await start();
        await click("button i[aria-label='Messages']");
        await click(".o-mail-NotificationItem");
        await contains(".o-mail-ChatWindow");
        await click("[title='Close Chat Window']");
        await contains(".o-mail-ChatWindow", { count: 0 });
        const [member] = pyEnv["discuss.channel.member"].searchRead([
            ["channel_id", "=", channelId],
            ["partner_id", "=", pyEnv.currentPartnerId],
        ]);
        assert.strictEqual(member.fold_state, "open");
    }
);

QUnit.test("chat window: close on ESCAPE", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ is_minimized: true, partner_id: pyEnv.currentPartnerId }),
        ],
    });
    await start({
        mockRPC(route, args) {
            if (args.method === "channel_fold") {
                assert.step(`rpc:channel_fold/${args.kwargs.state}`);
            }
        },
    });
    await contains(".o-mail-ChatWindow");
    await focus(".o-mail-Composer-input");
    triggerHotkey("Escape");
    await contains(".o-mail-ChatWindow", { count: 0 });
    assert.verifySteps(["rpc:channel_fold/closed"]);
});

QUnit.test(
    "Close composer suggestions in chat window with ESCAPE does not also close the chat window",
    async () => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({
            email: "testpartner@odoo.com",
            name: "TestPartner",
        });
        pyEnv["res.users"].create({ partner_id: partnerId });
        pyEnv["discuss.channel"].create({
            name: "general",
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId, is_minimized: true }),
                Command.create({ partner_id: partnerId }),
            ],
        });
        await start();
        await insertText(".o-mail-Composer-input", "@");

        triggerHotkey("Escape");
        await contains(".o-mail-ChatWindow");
    }
);

QUnit.test(
    "Close emoji picker in chat window with ESCAPE does not also close the chat window",
    async () => {
        const pyEnv = await startServer();
        pyEnv["discuss.channel"].create({
            name: "general",
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId, is_minimized: true }),
            ],
        });
        await start();
        await click("button[aria-label='Emojis']");
        triggerHotkey("Escape");
        await contains(".o-EmojiPicker", { count: 0 });
        await contains(".o-mail-ChatWindow");
    }
);

QUnit.test("Close active thread action in chatwindow on ESCAPE", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId, is_minimized: true }),
        ],
    });
    await start();
    await contains(".o-mail-ChatWindow");
    await click(".o-mail-ChatWindow-command", { text: "General" });
    await click(".dropdown-item", { text: "Add Users" });
    await contains(".o-discuss-ChannelInvitation");
    triggerHotkey("Escape");
    await contains(".o-discuss-ChannelInvitation", { count: 0 });
    await contains(".o-mail-ChatWindow");
});

QUnit.test("ESC cancels thread rename", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId, is_minimized: true }),
        ],
        create_uid: pyEnv.currentUserId,
    });
    await start();
    await click(".o-mail-ChatWindow-command", { text: "General" });
    await click(".dropdown-item", { text: "Rename" });
    await contains(".o-mail-AutoresizeInput.o-focused[title='General']");
    await insertText(".o-mail-AutoresizeInput", "New", { replace: true });
    triggerHotkey("Escape");
    await contains(".o-mail-AutoresizeInput.o-focused", { count: 0 });
    await contains(".o-mail-ChatWindow-command", { text: "General" });
});

QUnit.test("open 2 different chat windows: enough screen width [REQUIRE FOCUS]", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([{ name: "Channel_1" }, { name: "Channel_2" }]);
    patchUiSize({ width: 1920 });
    assert.ok(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 2 + CHAT_WINDOW_INBETWEEN_WIDTH < 1920,
        "should have enough space to open 2 chat windows simultaneously"
    );
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

QUnit.test("open 3 different chat windows: not enough screen width", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        { name: "Channel_1" },
        { name: "Channel_2" },
        { name: "Channel_3" },
    ]);
    patchUiSize({ width: 900 });
    assert.ok(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 2 + CHAT_WINDOW_INBETWEEN_WIDTH < 900,
        "should have enough space to open 2 chat windows simultaneously"
    );
    assert.ok(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 3 + CHAT_WINDOW_INBETWEEN_WIDTH * 2 >
            900,
        "should not have enough space to open 3 chat windows simultaneously"
    );
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

QUnit.test("closing hidden chat window", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        { name: "Ch_1" },
        { name: "Ch_2" },
        { name: "Ch_3" },
        { name: "Ch_4" },
    ]);
    patchUiSize({ width: 900 });
    assert.ok(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 2 + CHAT_WINDOW_INBETWEEN_WIDTH < 900,
        "should have enough space to open 2 chat windows simultaneously"
    );
    assert.ok(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 3 + CHAT_WINDOW_INBETWEEN_WIDTH * 2 >
            900,
        "should not have enough space to open 3 chat windows simultaneously"
    );
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

QUnit.test("Opening hidden chat window from messaging menu", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([{ name: "Ch_1" }, { name: "Ch_2" }, { name: "Ch_3" }]);
    patchUiSize({ width: 900 });
    assert.ok(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 2 + CHAT_WINDOW_INBETWEEN_WIDTH < 900,
        "should have enough space to open 2 chat windows simultaneously"
    );
    assert.ok(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 3 + CHAT_WINDOW_INBETWEEN_WIDTH * 2 >
            900,
        "should not have enough space to open 3 chat windows simultaneously"
    );
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

QUnit.test(
    "focus next visible chat window when closing current chat window with ESCAPE [REQUIRE FOCUS]",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["discuss.channel"].create([
            {
                name: "General",
                channel_member_ids: [
                    [
                        0,
                        0,
                        {
                            fold_state: "open",
                            is_minimized: true,
                            partner_id: pyEnv.currentPartnerId,
                        },
                    ],
                ],
            },
            {
                name: "MyTeam",
                channel_member_ids: [
                    [
                        0,
                        0,
                        {
                            fold_state: "open",
                            is_minimized: true,
                            partner_id: pyEnv.currentPartnerId,
                        },
                    ],
                ],
            },
        ]);
        patchUiSize({ width: 1920 });
        assert.ok(
            CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 2 + CHAT_WINDOW_INBETWEEN_WIDTH <
                1920,
            "should have enough space to open 2 chat windows simultaneously"
        );
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
    }
);

QUnit.test("chat window: switch on TAB [REQUIRE FOCUS]", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([{ name: "channel1" }, { name: "channel2" }]);
    patchUiSize({ width: 1920 });
    assert.ok(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 2 + CHAT_WINDOW_INBETWEEN_WIDTH < 1920,
        "should have enough space to open 2 chat windows simultaneously"
    );
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

QUnit.test("chat window: TAB cycle with 3 open chat windows [REQUIRE FOCUS]", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        {
            name: "General",
            channel_member_ids: [
                [
                    0,
                    0,
                    {
                        fold_state: "open",
                        is_minimized: true,
                        partner_id: pyEnv.currentPartnerId,
                    },
                ],
            ],
        },
        {
            name: "MyTeam",
            channel_member_ids: [
                [
                    0,
                    0,
                    {
                        fold_state: "open",
                        is_minimized: true,
                        partner_id: pyEnv.currentPartnerId,
                    },
                ],
            ],
        },
        {
            name: "MyProject",
            channel_member_ids: [
                [
                    0,
                    0,
                    {
                        fold_state: "open",
                        is_minimized: true,
                        partner_id: pyEnv.currentPartnerId,
                    },
                ],
            ],
        },
    ]);
    patchUiSize({ width: 1920 });
    assert.ok(
        CHAT_WINDOW_END_GAP_WIDTH * 3 + CHAT_WINDOW_WIDTH * 3 + CHAT_WINDOW_INBETWEEN_WIDTH * 2 <
            1920,
        "should have enough space to open 3 chat windows simultaneously"
    );
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

QUnit.test(
    "new message separator is shown in a chat window of a chat on receiving new message if there is a history of conversation",
    async () => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
        const userId = pyEnv["res.users"].create({ name: "Foreigner user", partner_id: partnerId });
        const channelId = pyEnv["discuss.channel"].create({
            channel_member_ids: [
                [
                    0,
                    0,
                    {
                        is_minimized: true,
                        is_pinned: false,
                        partner_id: pyEnv.currentPartnerId,
                    },
                ],
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
            ["partner_id", "=", pyEnv.currentPartnerId],
        ]);
        pyEnv["discuss.channel.member"].write([memberId], { seen_message_id: messageId });
        const { env } = await start();
        // simulate receiving a message
        pyEnv.withUser(userId, () =>
            env.services.rpc("/mail/message/post", {
                post_data: { body: "hu", message_type: "comment" },
                thread_id: channelId,
                thread_model: "discuss.channel",
            })
        );
        await contains(".o-mail-ChatWindow");
        await contains(".o-mail-Message", { count: 2 });
        await contains(".o-mail-Thread-newMessage hr + span", { text: "New messages" });
    }
);

QUnit.test(
    "new message separator is shown in chat window of chat on receiving new message when there was no history",
    async () => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
        const userId = pyEnv["res.users"].create({
            name: "Foreigner user",
            partner_id: partnerId,
        });
        const channelId = pyEnv["discuss.channel"].create({
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "chat",
        });
        const { env } = await start();
        // simulate receiving a message
        pyEnv.withUser(userId, () =>
            env.services.rpc("/mail/message/post", {
                post_data: { body: "hu", message_type: "comment" },
                thread_id: channelId,
                thread_model: "discuss.channel",
            })
        );
        await contains(".o-mail-Thread-newMessage hr + span", { text: "New messages" });
    }
);

QUnit.test("chat window should open when receiving a new DM", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ is_pinned: false, partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { env } = await start();
    await contains(".o-mail-ChatWindowContainer");
    pyEnv.withUser(userId, () =>
        env.services.rpc("/mail/message/post", {
            post_data: { body: "new message", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatWindow");
});

QUnit.test("chat window should not open when receiving a new DM from odoobot", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ partner_id: pyEnv.odoobotId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ is_pinned: false, partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: pyEnv.odoobotId }),
        ],
        channel_type: "chat",
    });
    const { env } = await start();
    await contains(".o-mail-ChatWindowContainer");
    pyEnv.withUser(userId, () =>
        env.services.rpc("/mail/message/post", {
            post_data: { body: "new message", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatWindow", { count: 0 });
});

QUnit.test(
    "chat window should scroll to the newly posted message just after posting it",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            channel_member_ids: [
                [
                    0,
                    0,
                    {
                        fold_state: "open",
                        is_minimized: true,
                        partner_id: pyEnv.currentPartnerId,
                    },
                ],
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
    }
);

QUnit.test("chat window should remain folded when new message is received", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({
        name: "Foreigner user",
        partner_id: partnerId,
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            [
                0,
                0,
                {
                    fold_state: "folded",
                    is_minimized: true,
                    partner_id: pyEnv.currentPartnerId,
                },
            ],
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { env } = await start();
    await contains(".o-mail-ChatWindow.o-folded");
    await contains(".o-mail-ChatWindow-counter", { count: 0 });
    pyEnv.withUser(userId, () =>
        env.services.rpc("/mail/message/post", {
            post_data: { body: "New Message", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatWindow-counter", { text: "1" });
    await contains(".o-mail-ChatWindow.o-folded");
});

QUnit.test(
    "should not have chat window hidden menu in mobile (transition from 3 chat windows in desktop to mobile)",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["discuss.channel"].create([
            { name: "Channel-1" },
            { name: "Channel-2" },
            { name: "Channel-3" },
        ]);
        patchUiSize({ width: 900 });
        assert.ok(
            CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 2 + CHAT_WINDOW_INBETWEEN_WIDTH <
                900,
            "should have enough space to open 2 chat windows simultaneously"
        );
        assert.ok(
            CHAT_WINDOW_END_GAP_WIDTH * 2 +
                CHAT_WINDOW_WIDTH * 3 +
                CHAT_WINDOW_INBETWEEN_WIDTH * 2 >
                900,
            "should not have enough space to open 3 chat windows simultaneously"
        );
        const { openDiscuss } = await start();
        openDiscuss();
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
    }
);

QUnit.test("chat window: composer state conservation on toggle discuss", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    const { openDiscuss, openView } = await start();
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
    openDiscuss();
    await contains(".o-mail-ChatWindow", { count: 0 });
    openView({
        res_id: channelId,
        res_model: "discuss.channel",
        views: [[false, "form"]],
    });
    await contains(".o-mail-Composer-footer .o-mail-AttachmentList .o-mail-AttachmentCard", {
        count: 2,
    });
    await contains(".o-mail-Composer-input", { value: "XDU for the win !" });
});

QUnit.test(
    "focusing a chat window of a chat should make new message separator disappear [REQUIRE FOCUS]",
    async () => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
        const userId = pyEnv["res.users"].create({
            name: "Foreigner user",
            partner_id: partnerId,
        });
        const channelId = pyEnv["discuss.channel"].create({
            name: "test",
            channel_member_ids: [
                [
                    0,
                    0,
                    {
                        fold_state: "open",
                        is_minimized: true,
                        partner_id: pyEnv.currentPartnerId,
                    },
                ],
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "chat",
        });
        const messageId = pyEnv["mail.message"].create([
            {
                body: "not empty",
                model: "discuss.channel",
                res_id: channelId,
            },
        ]);
        const [memberId] = pyEnv["discuss.channel.member"].search([
            ["channel_id", "=", channelId],
            ["partner_id", "=", pyEnv.currentPartnerId],
        ]);
        pyEnv["discuss.channel.member"].write([memberId], { seen_message_id: messageId });
        const { env } = await start();
        $(".o-mail-Composer-input")[0].blur();
        // simulate receiving a message
        pyEnv.withUser(userId, () =>
            env.services.rpc("/mail/message/post", {
                post_data: { body: "hu", message_type: "comment" },
                thread_id: channelId,
                thread_model: "discuss.channel",
            })
        );
        await contains(".o-mail-Thread-newMessage hr + span", { text: "New messages" });
        await focus(".o-mail-Composer-input");
        await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });
    }
);

QUnit.test("chat window: scroll conservation on toggle discuss", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    for (let i = 0; i < 100; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const { openDiscuss, openView } = await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-ChatWindow .o-mail-Thread", { scroll: "bottom" });
    await scroll(".o-mail-ChatWindow .o-mail-Thread", 142);
    openDiscuss(null);
    await contains(".o-mail-ChatWindow", { count: 0 });
    openView({
        res_id: channelId,
        res_model: "discuss.channel",
        views: [[false, "list"]],
    });
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-ChatWindow .o-mail-Thread", { scroll: 142 });
});

QUnit.test(
    "chat window with a thread: keep scroll position in message list on folded",
    async () => {
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
    }
);

QUnit.test(
    "chat window with a thread: keep scroll position in message list on toggle discuss when folded",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({});
        for (let i = 0; i < 100; i++) {
            pyEnv["mail.message"].create({
                body: "not empty",
                model: "discuss.channel",
                res_id: channelId,
            });
        }
        const { openDiscuss, openView } = await start();
        await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
        await click(".o-mail-NotificationItem");
        await contains(".o-mail-Message", { count: 30 });
        await contains(".o-mail-ChatWindow .o-mail-Thread", { scroll: "bottom" });
        await scroll(".o-mail-ChatWindow .o-mail-Thread", 142);
        // fold chat window
        await click(".o-mail-ChatWindow-command[title='Fold']");
        openDiscuss(null);
        await contains(".o-mail-ChatWindow", { count: 0 });
        openView({
            res_id: channelId,
            res_model: "discuss.channel",
            views: [[false, "list"]],
        });
        // unfold chat window
        await click(".o-mail-ChatWindow-command[title='Open']");
        await contains(".o-mail-ChatWindow .o-mail-Message", { count: 30 });
        await contains(".o-mail-ChatWindow .o-mail-Thread", { scroll: 142 });
    }
);

QUnit.test("folded chat window should hide member-list and settings buttons", async () => {
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

QUnit.test("Chat window in mobile are not foldable", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ fold_state: "open", partner_id: pyEnv.currentPartnerId }),
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

QUnit.test("Server-synced chat windows should not open at page load on mobile", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                fold_state: "open",
                is_minimized: true,
                partner_id: pyEnv.currentPartnerId,
            }),
        ],
    });
    patchUiSize({ size: SIZES.SM });
    await start();
    await contains(".o-mail-ChatWindowContainer");
    await contains(".o-mail-ChatWindow", { count: 0 });
});

QUnit.test("chat window of channels should not have 'Open in Discuss' (mobile)", async () => {
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

QUnit.test("Open chat window of new inviter", async () => {
    const pyEnv = await startServer();
    await start();
    const partnerId = pyEnv["res.partner"].create({ name: "Newbie" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    // simulate receiving notification of new connection of inviting user
    pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "res.users/connection", {
        username: "Newbie",
        partnerId,
    });
    await contains(".o-mail-ChatWindow", { text: "Newbie" });
    await contains(".o_notification", {
        text: "Newbie connected. This is their first connection. Wish them luck.",
    });
});

QUnit.test(
    "keyboard navigation ArrowUp/ArrowDown on message action dropdown in chat window",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "General" });
        pyEnv["mail.message"].create({
            author_id: pyEnv.currentPartnerId,
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
    }
);

QUnit.test(
    "Close dropdown in chat window with ESCAPE does not also close the chat window",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "General" });
        pyEnv["mail.message"].create({
            author_id: pyEnv.currentPartnerId,
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
    }
);

QUnit.test("hiding/swapping hidden chat windows does not update server state", async (assert) => {
    patchUiSize({ size: SIZES.MD }); // only 2 chat window can be opened at a time
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([{ name: "General" }, { name: "Sales" }, { name: "D&D" }]);
    await start({
        mockRPC(route, args) {
            if (args.method === "channel_fold") {
                const [channel] = pyEnv["discuss.channel"].searchRead([
                    ["id", "=", args.args[0][0]],
                ]);
                assert.step(`${channel.name} - ${args.kwargs.state}`);
            }
        },
    });
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "General" });
    await contains(".o-mail-ChatWindow", { text: "General" });
    assert.verifySteps(["General - open"]);
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Sales" });
    await contains(".o-mail-ChatWindow", { text: "Sales" });
    assert.verifySteps(["Sales - open"]);
    // Sales chat window will be hidden since there is not enough space for the
    // D&D one but Sales fold state should not be updated.
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "D&D" });
    await contains(".o-mail-ChatWindow", { text: "D&D" });
    assert.verifySteps(["D&D - open"]);
    // D&D chat window will be hidden since there is not enough space for the
    // Sales one, the server should not be notified as the state is up to date.
    await click(".o-mail-ChatWindowHiddenToggler");
    await click(".o-mail-ChatWindowHiddenMenu-item .o-mail-ChatWindow-header", {
        text: "Sales",
        visible: true,
    });
    await contains(".o-mail-ChatWindow", { text: "Sales" });
    assert.verifySteps([]);
});
