/** @odoo-module **/

import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import {
    afterNextRender,
    click,
    createFile,
    insertText,
    isScrolledToBottom,
    nextAnimationFrame,
    start,
    startServer,
    waitUntil,
} from "@mail/../tests/helpers/test_utils";
import { Command } from "@mail/../tests/helpers/command";

import {
    CHAT_WINDOW_END_GAP_WIDTH,
    CHAT_WINDOW_INBETWEEN_WIDTH,
    CHAT_WINDOW_WIDTH,
} from "@mail/web/chat_window/chat_window_service";
import { nextTick, triggerEvent, triggerHotkey } from "@web/../tests/helpers/utils";
import { file } from "web.test_utils";
const { inputFiles } = file;

QUnit.module("chat window");

QUnit.test(
    "Mobile: chat window shouldn't open automatically after receiving a new message",
    async (assert) => {
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

        // simulate receiving a message
        env.services.rpc("/mail/message/post", {
            context: { mockedUserId: userId },
            post_data: { body: "hu", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        });
        await nextAnimationFrame();
        assert.containsNone($, ".o-mail-ChatWindow");
    }
);

QUnit.test(
    'chat window: post message on channel with "CTRL-Enter" keyboard shortcut for small screen size',
    async (assert) => {
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
        await afterNextRender(() => triggerHotkey("control+Enter"));
        assert.containsOnce($, ".o-mail-Message");
    }
);

QUnit.test("Message post in chat window of chatter should log a note", async (assert) => {
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
    assert.containsOnce($, ".o-mail-ChatWindow");
    assert.containsOnce(
        $,
        ".o-mail-Message:contains(A needaction message to have it in messaging menu)"
    );
    assert.containsOnce(
        $(".o-mail-Message:contains(A needaction message to have it in messaging menu)"),
        ".o-mail-Message-bubble.border" // bordered bubble = "Send message" mode
    );
    assert.containsOnce($, ".o-mail-Composer [placeholder='Log an internal note...']");
    await insertText(".o-mail-ChatWindow .o-mail-Composer-input", "Test");
    await afterNextRender(() => triggerHotkey("control+Enter"));
    assert.containsOnce($, ".o-mail-Message:contains(Test)");
    assert.containsNone(
        $(".o-mail-Message:contains(Test)"),
        ".o-mail-Message-bubble.border" // non-bordered bubble = "Log note" mode
    );
});

QUnit.test("load messages from opening chat window from messaging menu", async (assert) => {
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
    assert.containsN($, ".o-mail-Message", 21);
});

QUnit.test("chat window: basic rendering", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    assert.containsOnce($, ".o-mail-ChatWindow");
    assert.containsOnce($, ".o-mail-ChatWindow-header");
    assert.containsOnce($(".o-mail-ChatWindow-header"), ".o-mail-ChatWindow-threadAvatar");
    assert.containsOnce($, ".o-mail-ChatWindow-name:contains(General)");
    assert.containsN($, ".o-mail-ChatWindow-command", 3);
    assert.containsOnce($, "[title='Start a Call']");
    assert.containsOnce($, "[title='More actions']");
    assert.containsOnce($, "[title='Close Chat Window']");
    assert.containsOnce($, ".o-mail-ChatWindow-content .o-mail-Thread");
    assert.strictEqual(
        $(".o-mail-ChatWindow-content .o-mail-Thread").text().trim(),
        "There are no messages in this conversation."
    );
    await click("[title='More actions']");
    assert.containsN($, ".o-mail-ChatWindow-command", 8);
    assert.containsOnce($, "[title='Pinned Messages']");
    assert.containsOnce($, "[title='Add Users']");
    assert.containsOnce($, "[title='Show Member List']");
    assert.containsOnce($, "[title='Show Call Settings']");
    assert.containsOnce($, "[title='Open in Discuss']");
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
    assert.containsOnce($, ".o-mail-ChatWindow .o-mail-Thread");
    assert.verifySteps(["rpc:channel_fold/open"]);

    // Fold chat window
    await click(".o-mail-ChatWindow-header");
    assert.verifySteps(["rpc:channel_fold/folded"]);
    assert.containsNone($, ".o-mail-ChatWindow .o-mail-Thread");

    // Unfold chat window
    await click(".o-mail-ChatWindow-header");
    assert.verifySteps(["rpc:channel_fold/open"]);
    assert.containsOnce($, ".o-mail-ChatWindow .o-mail-Thread");
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
    assert.containsNone($, ".o-mail-ChatWindow");
    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    assert.containsOnce($, ".o-mail-ChatWindow");
    assert.verifySteps(["rpc:channel_fold/open"]);

    await click(".o-mail-ChatWindow-command[title='Close Chat Window']");
    assert.containsNone($, ".o-mail-ChatWindow");
    assert.verifySteps(["rpc:channel_fold/closed"]);

    // Reopen chat window
    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    assert.containsOnce($, ".o-mail-ChatWindow");
    assert.verifySteps(["rpc:channel_fold/open"]);
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
        assert.containsOnce($, ".o-mail-ChatWindow");
        await click("[title='Close Chat Window']");
        assert.containsNone($, ".o-mail-ChatWindow");
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
    assert.containsOnce($, ".o-mail-ChatWindow");

    $(".o-mail-Composer-input")[0].focus();
    await afterNextRender(() => triggerHotkey("Escape"));
    assert.containsNone($, ".o-mail-ChatWindow");
    assert.verifySteps(["rpc:channel_fold/closed"]);
});

QUnit.test(
    "Close composer suggestions in chat window with ESCAPE does not also close the chat window",
    async (assert) => {
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
        await afterNextRender(() => triggerHotkey("Escape"));
        assert.containsOnce($, ".o-mail-ChatWindow");
    }
);

QUnit.test(
    "Close emoji picker in chat window with ESCAPE does not also close the chat window",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["discuss.channel"].create({
            name: "general",
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId, is_minimized: true }),
            ],
        });
        await start();
        await click("button[aria-label='Emojis']");
        await afterNextRender(() => triggerHotkey("Escape"));
        assert.containsNone($, ".o-mail-EmojiPicker");
        assert.containsOnce($, ".o-mail-ChatWindow");
    }
);

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
    await click(".o-mail-NotificationItem:contains(Channel_1)");
    assert.containsOnce($, ".o-mail-ChatWindow");
    assert.containsOnce($, ".o-mail-ChatWindow-header:contains(Channel_1)");
    assert.strictEqual(
        document.activeElement,
        $(".o-mail-ChatWindow-header:contains(Channel_1)")
            .closest(".o-mail-ChatWindow")
            .find(".o-mail-Composer-input")[0]
    );

    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem:contains(Channel_2)");
    assert.containsN($, ".o-mail-ChatWindow", 2);
    assert.containsOnce($, ".o-mail-ChatWindow-header:contains(Channel_2)");
    assert.containsOnce($, ".o-mail-ChatWindow-header:contains(Channel_1)");
    assert.strictEqual(
        document.activeElement,
        $(".o-mail-ChatWindow-header:contains(Channel_2)")
            .closest(".o-mail-ChatWindow")
            .find(".o-mail-Composer-input")[0]
    );
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
    await click(".o-mail-NotificationItem:contains(Channel_1)");
    assert.containsOnce($, ".o-mail-ChatWindow");
    assert.containsNone($, ".o-mail-ChatWindowHiddenToggler");

    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem:contains(Channel_2)");
    assert.containsN($, ".o-mail-ChatWindow", 2);
    assert.containsNone($, ".o-mail-ChatWindowHiddenToggler");

    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem:contains(Channel_3)");
    assert.containsN($, ".o-mail-ChatWindow", 2);
    assert.containsOnce($, ".o-mail-ChatWindowHiddenToggler");
    assert.containsOnce($, ".o-mail-ChatWindow-header:contains(Channel_1)");
    assert.containsOnce($, ".o-mail-ChatWindow-header:contains(Channel_3)");
    assert.strictEqual(
        document.activeElement,
        $(".o-mail-ChatWindow-header:contains(Channel_3)")
            .closest(".o-mail-ChatWindow")
            .find(".o-mail-Composer-input")[0]
    );
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
        assert.containsN($, ".o-mail-ChatWindow .o-mail-Composer-input", 2);

        $(".o-mail-ChatWindow-name:contains(MyTeam)")
            .closest(".o-mail-ChatWindow")
            .find(".o-mail-Composer-input")[0]
            .focus();
        await afterNextRender(() => triggerHotkey("Escape"));
        assert.containsOnce($, ".o-mail-ChatWindow");
        assert.strictEqual(
            document.activeElement,
            $(".o-mail-ChatWindow-name:contains(General)")
                .closest(".o-mail-ChatWindow")
                .find(".o-mail-Composer-input")[0]
        );
    }
);

QUnit.test("chat window: switch on TAB", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([{ name: "channel1" }, { name: "channel2" }]);
    patchUiSize({ width: 1920 });
    assert.ok(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 2 + CHAT_WINDOW_INBETWEEN_WIDTH < 1920,
        "should have enough space to open 2 chat windows simultaneously"
    );
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem:contains(channel1)");
    assert.containsOnce($, ".o-mail-ChatWindow");
    assert.containsOnce($, ".o-mail-ChatWindow-name:contains(channel1)");
    assert.strictEqual(
        document.activeElement,
        $(".o-mail-ChatWindow-name:contains(channel1)")
            .closest(".o-mail-ChatWindow")
            .find(".o-mail-Composer-input")[0]
    );

    await afterNextRender(() => triggerHotkey("Tab"));
    assert.strictEqual(
        document.activeElement,
        $(".o-mail-ChatWindow-name:contains(channel1)")
            .closest(".o-mail-ChatWindow")
            .find(".o-mail-Composer-input")[0]
    );

    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem:contains(channel2)");
    assert.containsN($, ".o-mail-ChatWindow", 2);
    assert.containsOnce($, ".o-mail-ChatWindow-name:contains(channel1)");
    assert.containsOnce($, ".o-mail-ChatWindow-name:contains(channel2)");
    assert.strictEqual(
        document.activeElement,
        $(".o-mail-ChatWindow-name:contains(channel2)")
            .closest(".o-mail-ChatWindow")
            .find(".o-mail-Composer-input")[0]
    );

    await afterNextRender(() => triggerHotkey("Tab"));
    assert.containsN($, ".o-mail-ChatWindow", 2);
    assert.strictEqual(
        document.activeElement,
        $(".o-mail-ChatWindow-name:contains(channel1)")
            .closest(".o-mail-ChatWindow")
            .find(".o-mail-Composer-input")[0]
    );
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
    assert.containsN($, ".o-mail-ChatWindow .o-mail-Composer-input", 3);

    $(".o-mail-ChatWindow-name:contains(MyProject)")
        .closest(".o-mail-ChatWindow")
        .find(".o-mail-Composer-input")[0]
        .focus();
    await afterNextRender(() => triggerHotkey("Tab"));
    assert.strictEqual(
        document.activeElement,
        $(".o-mail-ChatWindow-name:contains(MyTeam)")
            .closest(".o-mail-ChatWindow")
            .find(".o-mail-Composer-input")[0]
    );

    await afterNextRender(() => triggerHotkey("Tab"));
    assert.strictEqual(
        document.activeElement,
        $(".o-mail-ChatWindow-name:contains(General)")
            .closest(".o-mail-ChatWindow")
            .find(".o-mail-Composer-input")[0]
    );

    await afterNextRender(() => triggerHotkey("Tab"));
    assert.strictEqual(
        document.activeElement,
        $(".o-mail-ChatWindow-name:contains(MyProject)")
            .closest(".o-mail-ChatWindow")
            .find(".o-mail-Composer-input")[0]
    );
});

QUnit.test(
    "new message separator is shown in a chat window of a chat on receiving new message if there is a history of conversation",
    async (assert) => {
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
        await afterNextRender(async () =>
            env.services.rpc("/mail/message/post", {
                context: { mockedUserId: userId },
                post_data: { body: "hu", message_type: "comment" },
                thread_id: channelId,
                thread_model: "discuss.channel",
            })
        );
        assert.containsOnce($, ".o-mail-ChatWindow");
        assert.containsN($, ".o-mail-Message", 2);
        assert.containsOnce($, "hr + span:contains(New messages)");
    }
);

QUnit.test(
    "new message separator is shown in chat window of chat on receiving new message when there was no history",
    async (assert) => {
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
        await afterNextRender(async () =>
            env.services.rpc("/mail/message/post", {
                context: { mockedUserId: userId },
                post_data: { body: "hu", message_type: "comment" },
                thread_id: channelId,
                thread_model: "discuss.channel",
            })
        );
        assert.containsOnce($, "hr + span:contains(New messages)");
    }
);

QUnit.test("chat window should open when receiving a new DM", async (assert) => {
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
    // simulate receiving the first message on chat
    await afterNextRender(() =>
        env.services.rpc("/mail/message/post", {
            context: {
                mockedUserId: userId,
            },
            post_data: { body: "new message", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    assert.containsOnce($, ".o-mail-ChatWindow");
});

QUnit.test("chat window should not open when receiving a new DM from odoobot", async (assert) => {
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
    // simulate receiving new message from odoobot
    await afterNextRender(() =>
        env.services.rpc("/mail/message/post", {
            context: { mockedUserId: userId },
            post_data: { body: "new message", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    assert.containsNone($, ".o-mail-ChatWindow");
});

QUnit.test(
    "chat window should scroll to the newly posted message just after posting it",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            channel_member_ids: [
                [
                    0,
                    0,
                    { fold_state: "open", is_minimized: true, partner_id: pyEnv.currentPartnerId },
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
        await insertText(".o-mail-Composer-input", "WOLOLO");
        await afterNextRender(() =>
            triggerEvent(document.body, ".o-mail-Composer-input", "keydown", {
                key: "Enter",
            })
        );
        assert.ok(isScrolledToBottom($(".o-mail-Thread")[0]));
    }
);

QUnit.test("chat window should remain folded when new message is received", async (assert) => {
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
    assert.hasClass($(".o-mail-ChatWindow"), "o-folded");

    env.services.rpc("/mail/message/post", {
        context: { mockedUserId: userId },
        post_data: { body: "New Message", message_type: "comment" },
        thread_id: channelId,
        thread_model: "discuss.channel",
    });
    await nextTick();
    assert.hasClass($(".o-mail-ChatWindow"), "o-folded");
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
        const { env, openDiscuss } = await start();
        await openDiscuss();
        // open, from systray menu, chat windows of channels with id 1, 2, 3
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-NotificationItem-name:contains(Channel-1)");
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-NotificationItem-name:contains(Channel-2)");
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-NotificationItem-name:contains(Channel-3)");
        // simulate resize to go into mobile
        await afterNextRender(() => (env.services["mail.store"].isSmall = true));
        assert.containsNone($, ".o-mail-ChatWindowHiddenToggler");
    }
);

QUnit.test("chat window: composer state conservation on toggle discuss", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    const { openDiscuss, openView } = await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    // Set content of the composer of the chat window
    await insertText(".o-mail-Composer-input", "XDU for the win !");
    assert.containsNone($, ".o-mail-Composer-footer .o-mail-AttachmentList .o-mail-AttachmentCard");
    // Set attachments of the composer
    const files = [
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
    ];
    inputFiles($(".o-mail-Composer-coreMain .o_input_file")[0], files);
    await waitUntil(".o-mail-AttachmentCard .fa-check", 2);
    assert.strictEqual($(".o-mail-Composer-input").val(), "XDU for the win !");

    await openDiscuss();
    assert.containsNone($, ".o-mail-ChatWindow");

    await openView({
        res_id: channelId,
        res_model: "discuss.channel",
        views: [[false, "form"]],
    });
    assert.strictEqual($(".o-mail-Composer-input").val(), "XDU for the win !");
    assert.containsN($, ".o-mail-Composer-footer .o-mail-AttachmentList .o-mail-AttachmentCard", 2);
});

QUnit.test(
    "focusing a chat window of a chat should make new message separator disappear [REQUIRE FOCUS]",
    async (assert) => {
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
        await afterNextRender(() =>
            env.services.rpc("/mail/message/post", {
                context: { mockedUserId: userId },
                post_data: { body: "hu", message_type: "comment" },
                thread_id: channelId,
                thread_model: "discuss.channel",
            })
        );
        assert.containsOnce($, "hr + span:contains(New messages)");
        await afterNextRender(() => $(".o-mail-Composer-input")[0].focus());
        assert.containsNone($, "hr + span:contains(New messages)");
    }
);

QUnit.test("chat window: scroll conservation on toggle discuss", async (assert) => {
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
    $(".o-mail-Thread")[0].scrollTop = 142;
    await openDiscuss(null, { waitUntilMessagesLoaded: false });
    assert.containsNone($, ".o-mail-ChatWindow");

    await openView({
        res_id: channelId,
        res_model: "discuss.channel",
        views: [[false, "list"]],
    });
    assert.strictEqual($(".o-mail-Thread")[0].scrollTop, 142);
});

QUnit.test(
    "chat window with a thread: keep scroll position in message list on folded",
    async (assert) => {
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
        // Set a scroll position to chat window
        $(".o-mail-Thread")[0].scrollTop = 142;
        assert.strictEqual($(".o-mail-Thread")[0].scrollTop, 142);

        // fold chat window
        await click(".o-mail-ChatWindow-header");
        assert.containsNone($, ".o-mail-Thread");
        // unfold chat window
        await click(".o-mail-ChatWindow-header");
        assert.strictEqual($(".o-mail-Thread")[0].scrollTop, 142);
    }
);

QUnit.test(
    "chat window with a thread: keep scroll position in message list on toggle discuss when folded",
    async (assert) => {
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

        // Set a scroll position to chat window
        $(".o-mail-Thread")[0].scrollTop = 142;
        // fold chat window
        await click(".o-mail-ChatWindow-header");
        await openDiscuss(null, { waitUntilMessagesLoaded: false });
        assert.containsNone($, ".o-mail-ChatWindow");

        await openView({
            res_id: channelId,
            res_model: "discuss.channel",
            views: [[false, "list"]],
        });
        // unfold chat window
        await click(".o-mail-ChatWindow-header");
        assert.strictEqual($(".o-mail-Thread")[0].scrollTop, 142);
    }
);

QUnit.test("folded chat window should hide member-list and settings buttons", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({});
    await start();
    // Open Thread
    await click("button i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await click("[title='More actions']");
    assert.containsOnce($, "[title='Show Member List']");
    assert.containsOnce($, "[title='Show Call Settings']");
    await click(".o-mail-ChatWindow-header"); // click away to close the more menu

    // Fold chat window
    await click(".o-mail-ChatWindow-header");
    assert.containsNone($, "[title='More actions']");
    assert.containsNone($, "[title='Show Member List']");
    assert.containsNone($, "[title='Show Call Settings']");

    // Unfold chat window
    await click(".o-mail-ChatWindow-header");
    await click("[title='More actions']");
    assert.containsOnce($, "[title='Show Member List']");
    assert.containsOnce($, "[title='Show Call Settings']");
});

QUnit.test("Chat window in mobile are not foldable", async (assert) => {
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
    assert.containsNone($, ".o-mail-ChatWindow-header.cursor-pointer");
    click(".o-mail-ChatWindow-header").catch(() => {});
    await nextAnimationFrame();
    assert.containsOnce($, ".o-mail-ChatWindow-content"); // content => non-folded
});

QUnit.test("Server-synced chat windows should not open at page load on mobile", async (assert) => {
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
    assert.containsNone($, ".o-mail-ChatWindow");
});

QUnit.test("chat window of channels should not have 'Open in Discuss' (mobile)", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    assert.containsOnce($, ".o-mail-ChatWindow");
    assert.containsOnce($, "[title='More actions']");
    await click("[title='More actions']");
    assert.containsNone($, "[title='Open in Discuss']");
});

QUnit.test("Open chat window of new inviter", async (assert) => {
    const pyEnv = await startServer();
    await start();
    const partnerId = pyEnv["res.partner"].create({ name: "Newbie" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    // simulate receiving notification of new connection of inviting user
    pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "res.users/connection", {
        username: "Newbie",
        partnerId,
    });
    await waitUntil(".o-mail-ChatWindow:contains(Newbie)");
    assert.containsOnce(
        $,
        ".o_notification:contains(Newbie connected. This is their first connection. Wish them luck.)"
    );
});

QUnit.test(
    "keyboard navigation ArrowUp/ArrowDown on message action dropdown in chat window",
    async (assert) => {
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
        await afterNextRender(() => {
            $(".o-mail-Message")[0].dispatchEvent(new window.MouseEvent("mouseenter"));
        });
        await click(".o-mail-Message [title='Expand']");
        $(".o-mail-Message [title='Expand']")[0].focus(); // necessary otherwise focus is in composer input
        assert.containsOnce($, ".o-mail-Message-moreMenu.dropdown-menu");
        await triggerHotkey("ArrowDown");
        assert.containsOnce($, ".o-mail-Message-moreMenu .dropdown-item:eq(0).focus");
        await triggerHotkey("ArrowDown");
        assert.containsOnce($, ".o-mail-Message-moreMenu .dropdown-item:eq(1).focus");
    }
);

QUnit.test(
    "Close dropdown in chat window with ESCAPE does not also close the chat window",
    async (assert) => {
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
        await afterNextRender(() => {
            $(".o-mail-Message")[0].dispatchEvent(new window.MouseEvent("mouseenter"));
        });
        await click(".o-mail-Message [title='Expand']");
        $(".o-mail-Message [title='Expand']")[0].focus(); // necessary otherwise focus is in composer input
        assert.containsOnce($, ".o-mail-Message-moreMenu.dropdown-menu");
        await triggerHotkey("Escape");
        assert.containsNone($, ".o-mail-Message-moreMenu.dropdown-menu");
        assert.containsOnce($, ".o-mail-ChatWindow");
    }
);
