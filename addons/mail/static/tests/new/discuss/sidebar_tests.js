/** @odoo-module **/

import {
    afterNextRender,
    click,
    insertText,
    nextAnimationFrame,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";
import { makeDeferred } from "@mail/utils/deferred";
import { editInput, getFixture } from "@web/../tests/helpers/utils";
import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";

let target;

QUnit.module("discuss sidebar", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("toggling category button hide category items", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(target, "button.o-active:contains('Inbox')");
    assert.containsOnce(target, ".o-mail-category-item");

    await click(".o-mail-category-icon");
    assert.containsNone(target, ".o-mail-category-item");
});

QUnit.test("toggling category button does not hide active category items", async (assert) => {
    const pyEnv = await startServer();
    const [channelId] = pyEnv["mail.channel"].create([
        { name: "abc", channel_type: "channel" },
        { name: "def", channel_type: "channel" },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsN(target, ".o-mail-category-item", 2);
    assert.containsOnce(target, ".o-mail-category-item.o-active");

    await click(".o-mail-category-icon");
    assert.containsOnce(target, ".o-mail-category-item");
    assert.containsOnce(target, ".o-mail-category-item.o-active");
});

QUnit.test(
    "Closing a category sends the updated user setting to the server.",
    async function (assert) {
        const { openDiscuss } = await start({
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/res.users.settings/set_res_users_settings") {
                    assert.step(route);
                    assert.strictEqual(
                        args.kwargs.new_settings.is_discuss_sidebar_category_channel_open,
                        false
                    );
                }
            },
        });
        await openDiscuss();
        await click(".o-mail-category-icon");
        assert.verifySteps(["/web/dataset/call_kw/res.users.settings/set_res_users_settings"]);
    }
);

QUnit.test(
    "Opening a category sends the updated user setting to the server.",
    async function (assert) {
        const pyEnv = await startServer();
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_channel_open: false,
        });
        const { openDiscuss } = await start({
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/res.users.settings/set_res_users_settings") {
                    assert.step(route);
                    assert.strictEqual(
                        args.kwargs.new_settings.is_discuss_sidebar_category_channel_open,
                        true
                    );
                }
            },
        });
        await openDiscuss();
        await click(".o-mail-category-icon");
        assert.verifySteps(["/web/dataset/call_kw/res.users.settings/set_res_users_settings"]);
    }
);

QUnit.test(
    "channel - command: should have view command when category is unfolded",
    async function (assert) {
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsOnce(target, "i[title='View or join channels']");
    }
);

QUnit.test(
    "channel - command: should have view command when category is folded",
    async function (assert) {
        const pyEnv = await startServer();
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_channel_open: false,
        });
        const { openDiscuss } = await start();
        await openDiscuss();
        await click(".o-mail-category-channel span:contains(Channels)");
        assert.containsOnce(target, "i[title='View or join channels']");
    }
);

QUnit.test(
    "channel - command: should have add command when category is unfolded",
    async function (assert) {
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsOnce(target, "i[title='Add or join a channel']");
    }
);

QUnit.test(
    "channel - command: should not have add command when category is folded",
    async function (assert) {
        const pyEnv = await startServer();
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_channel_open: false,
        });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsNone(target, "i[title='Add or join a channel']");
    }
);

QUnit.test("channel - states: close manually by clicking the title", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({ name: "general" });
    pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_channel_open: true,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(target, ".o-mail-category-item:contains(general)");
    await click(".o-mail-category-channel span:contains(Channels)");
    assert.containsNone(target, ".o-mail-category-item:contains(general)");
});

QUnit.test("channel - states: open manually by clicking the title", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({ name: "general" });
    pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_channel_open: false,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsNone(target, ".o-mail-category-item:contains(general)");
    await click(".o-mail-category-channel span:contains(Channels)");
    assert.containsOnce(target, ".o-mail-category-item:contains(general)");
});

QUnit.test("sidebar: inbox with counter", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.notification"].create({
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(target, "button:contains(Inbox) .badge:contains(1)");
});

QUnit.test("default thread rendering", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(target, "button:contains(Inbox)");
    assert.containsOnce(target, "button:contains(Starred)");
    assert.containsOnce(target, "button:contains(History)");
    assert.containsOnce(target, ".o-mail-category-item:contains(General)");
    assert.hasClass($(target).find("button:contains(Inbox)"), "o-active");
    assert.containsOnce(
        target,
        ".o-mail-thread:contains(Congratulations, your inbox is empty  New messages appear here.)"
    );

    await click("button:contains(Starred)");
    assert.hasClass($(target).find("button:contains(Starred)"), "o-active");
    assert.containsOnce(
        target,
        ".o-mail-thread:contains(No starred messages  You can mark any message as 'starred', and it shows up in this mailbox.)"
    );

    await click("button:contains(History)");
    assert.hasClass($(target).find("button:contains(History)"), "o-active");
    assert.containsOnce(
        target,
        ".o-mail-thread:contains(No history messages  Messages marked as read will appear in the history.)"
    );

    await click(".o-mail-category-item:contains(General)");
    assert.hasClass($(target).find(".o-mail-category-item:contains(General)"), "o-active");
    assert.containsOnce(
        target,
        ".o-mail-thread:contains(There are no messages in this conversation.)"
    );
});

QUnit.test("sidebar quick search at 20 or more pinned channels", async function (assert) {
    const pyEnv = await startServer();
    for (let id = 1; id <= 20; id++) {
        pyEnv["mail.channel"].create({ name: `channel${id}` });
    }
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsN(target, ".o-mail-category-item", 20);
    assert.containsOnce(target, ".o-mail-discuss-sidebar input[placeholder='Quick search...']");

    await editInput(target, ".o-mail-discuss-sidebar input[placeholder='Quick search...']", "1");
    assert.containsN(target, ".o-mail-category-item", 11);

    await editInput(target, ".o-mail-discuss-sidebar input[placeholder='Quick search...']", "12");
    assert.containsOnce(target, ".o-mail-category-item");
    assert.containsOnce(target, ".o-mail-category-item:contains(channel12)");

    await editInput(target, ".o-mail-discuss-sidebar input[placeholder='Quick search...']", "123");
    assert.containsNone(target, ".o-mail-category-item");
});

QUnit.test("sidebar: basic chat rendering", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["mail.channel"].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(target, ".o-mail-category-item:contains(Demo)");
    const $chat = $(target).find(".o-mail-category-item:contains(Demo)");
    assert.containsOnce($chat, "img[data-alt='Thread Image']");
    assert.containsOnce($chat, "span:contains(Demo)");
    assert.containsOnce($chat, ".o-mail-commands");
    assert.containsOnce($chat, ".o-mail-commands div[title='Unpin Conversation']");
    assert.containsNone($chat, ".badge");
});

QUnit.test("sidebar: show pinned channel", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(target, ".o-mail-category-item:contains(General)");
});

QUnit.test("sidebar: open pinned channel", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss();
    await click(".o-mail-category-item:contains(General)");
    assert.strictEqual($(target).find(".o-mail-discuss-thread-name").val(), "General");
    assert.containsOnce(target, ".o-mail-composer-textarea[placeholder='Message #General…']");
});

QUnit.test("sidebar: open channel and leave it", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "General",
        channel_member_ids: [
            [0, 0, { fold_state: "open", is_minimized: true, partner_id: pyEnv.currentPartnerId }],
        ],
    });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (args.method === "action_unfollow") {
                assert.step("action_unfollow");
                assert.deepEqual(args.args[0], channelId);
            }
        },
    });
    await openDiscuss();
    await click(".o-mail-category-item:contains(General)");
    assert.verifySteps([]);

    await click(".o-mail-category-item:contains(General) .btn[title='Leave this channel']");
    assert.verifySteps(["action_unfollow"]);
    assert.containsNone(target, ".o-mail-category-item:contains(General)");
    assert.notOk($(target).find(".o-mail-discuss-thread-name")?.val() === "General");
});

QUnit.test("sidebar: unpin channel from bus", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(target, ".o-mail-category-item:contains(General)");

    await click(".o-mail-category-item:contains(General)");
    assert.strictEqual($(target).find(".o-mail-discuss-thread-name").val(), "General");

    // Simulate receiving a leave channel notification
    // (e.g. from user interaction from another device or browser tab)
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.channel/unpin", { id: channelId });
    });
    assert.containsNone(target, ".o-mail-category-item:contains(General)");
    assert.notOk($(target).find(".o-mail-discuss-thread-name")?.val() === "General");
});

QUnit.test("chat - channel should count unread message [REQUIRE FOCUS]", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Demo",
        im_status: "offline",
    });
    const channelId = pyEnv["mail.channel"].create({
        channel_member_ids: [
            [0, 0, { message_unread_counter: 1, partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
        channel_type: "chat",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "<p>Test</p>",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(target, ".o-mail-discuss-sidebar-counter");
    assert.strictEqual(target.querySelector(".o-mail-discuss-sidebar-counter").textContent, "1");

    await click(".o-mail-category-item:contains(Demo)");
    assert.containsNone(target, ".o-mail-discuss-sidebar-counter");
});

QUnit.test("mark channel as seen on last message visible [REQUIRE FOCUS]", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { message_unread_counter: 1, partner_id: pyEnv.currentPartnerId }],
        ],
    });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(target, ".o-mail-category-item:contains(test)");
    assert.hasClass($(".o-mail-category-item:contains(test)"), "o-unread");

    await click(".o-mail-category-item:contains(test)");
    assert.doesNotHaveClass($(".o-mail-category-item:contains(test)"), "o-unread");
});

QUnit.test(
    "channel - counter: should not have a counter if the category is unfolded and without needaction messages",
    async function (assert) {
        const pyEnv = await startServer();
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_channel_open: true,
        });
        pyEnv["mail.channel"].create({ name: "general" });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsNone(target, ".o-mail-category:contains(Channels) .badge");
    }
);

QUnit.test(
    "channel - counter: should not have a counter if the category is unfolded and with needaction messages",
    async function (assert) {
        const pyEnv = await startServer();
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_channel_open: true,
        });
        const [channelId_1, channelId_2] = pyEnv["mail.channel"].create([
            { name: "channel1" },
            { name: "channel2" },
        ]);
        const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
            {
                body: "message 1",
                model: "mail.channel",
                res_id: channelId_1,
            },
            {
                body: "message_2",
                model: "mail.channel",
                res_id: channelId_2,
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
        await openDiscuss();
        assert.containsNone(target, ".o-mail-category:contains(Channels) .badge");
    }
);

QUnit.test(
    "channel - counter: should not have a counter if category is folded and without needaction messages",
    async function (assert) {
        const pyEnv = await startServer();
        pyEnv["mail.channel"].create({});
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_channel_open: false,
        });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsNone(target, ".o-mail-category:contains(Channels) .badge");
    }
);

QUnit.test(
    "channel - counter: should have correct value of needaction threads if category is folded and with needaction messages",
    async function (assert) {
        const pyEnv = await startServer();
        const [channelId_1, channelId_2] = pyEnv["mail.channel"].create([
            { name: "Channel_1" },
            { name: "Channel_2" },
        ]);
        const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
            {
                body: "message 1",
                model: "mail.channel",
                res_id: channelId_1,
            },
            {
                body: "message_2",
                model: "mail.channel",
                res_id: channelId_2,
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
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_channel_open: false,
        });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsOnce(target, ".o-mail-category:contains(Channels) .badge:contains(2)");
    }
);

QUnit.test(
    "chat - counter: should not have a counter if the category is unfolded and without unread messages",
    async function (assert) {
        const pyEnv = await startServer();
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_chat_open: true,
        });
        pyEnv["mail.channel"].create({
            channel_member_ids: [
                [0, 0, { message_unread_counter: 0, partner_id: pyEnv.currentPartnerId }],
            ],
            channel_type: "chat",
        });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsNone(target, ".o-mail-category:contains(Direct messages) .badge");
    }
);

QUnit.test(
    "chat - counter: should not have a counter if the category is unfolded and with unread messagens",
    async function (assert) {
        const pyEnv = await startServer();
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_chat_open: true,
        });
        pyEnv["mail.channel"].create({
            channel_member_ids: [
                [0, 0, { message_unread_counter: 10, partner_id: pyEnv.currentPartnerId }],
            ],
            channel_type: "chat",
        });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsNone(target, ".o-mail-category:contains(Direct messages) .badge");
    }
);

QUnit.test(
    "chat - counter: should not have a counter if category is folded and without unread messages",
    async function (assert) {
        const pyEnv = await startServer();
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_chat_open: false,
        });
        pyEnv["mail.channel"].create({
            channel_member_ids: [
                [0, 0, { message_unread_counter: 0, partner_id: pyEnv.currentPartnerId }],
            ],
            channel_type: "chat",
        });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsNone(target, ".o-mail-category:contains(Direct messages) .badge");
    }
);

QUnit.test(
    "chat - counter: should have correct value of unread threads if category is folded and with unread messages",
    async function (assert) {
        const pyEnv = await startServer();
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_chat_open: false,
        });
        pyEnv["mail.channel"].create([
            {
                channel_member_ids: [
                    [0, 0, { message_unread_counter: 10, partner_id: pyEnv.currentPartnerId }],
                ],
                channel_type: "chat",
            },
            {
                channel_member_ids: [
                    [0, 0, { message_unread_counter: 20, partner_id: pyEnv.currentPartnerId }],
                ],
                channel_type: "chat",
            },
        ]);
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsOnce(
            target,
            ".o-mail-category:contains(Direct messages) .badge:contains(2)"
        );
    }
);

QUnit.test(
    "chat - command: should have add command when category is unfolded",
    async function (assert) {
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsOnce(
            target,
            ".o-mail-category:contains(Direct messages) i[title='Start a conversation']"
        );
    }
);

QUnit.test(
    "chat - command: should not have add command when category is folded",
    async function (assert) {
        const pyEnv = await startServer();
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_chat_open: false,
        });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsNone(
            target,
            ".o-mail-category:contains(Direct messages) i[title='Start a conversation']"
        );
    }
);

QUnit.test("chat - states: close manually by clicking the title", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({ channel_type: "chat" });
    pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_chat_open: true,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(target, ".o-mail-category-item");
    await click(".o-mail-category:contains(Direct messages) div");
    assert.containsNone(target, ".o-mail-category-item");
});

QUnit.test("sidebar find shows channels matching search term", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({
        channel_member_ids: [],
        channel_type: "channel",
        group_public_id: false,
        name: "test",
    });
    const def = makeDeferred();
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (args.method === "search_read") {
                def.resolve();
            }
        },
    });
    await openDiscuss();
    await click(".o-mail-category-add-button");
    await insertText(".o-mail-channel-selector input", "test");
    await def;
    await nextAnimationFrame(); // ensures search_read rpc is rendered.
    // When searching for a single existing channel, the results list will have at least 2 lines:
    // One for the existing channel itself
    // One for creating a channel with the search term
    assert.containsN(target, ".o-navigable-list-dropdown-item", 2);
    assert.containsN(target, ".o-navigable-list-dropdown-item:contains(test)", 2);
});

QUnit.test(
    "sidebar find shows channels matching search term even when user is member",
    async function (assert) {
        const pyEnv = await startServer();
        pyEnv["mail.channel"].create({
            channel_member_ids: [[0, 0, { partner_id: pyEnv.currentPartnerId }]],
            channel_type: "channel",
            group_public_id: false,
            name: "test",
        });
        const def = makeDeferred();
        const { openDiscuss } = await start({
            async mockRPC(route, args) {
                if (args.method === "search_read") {
                    def.resolve();
                }
            },
        });
        await openDiscuss();
        await click(".o-mail-category-add-button");
        await insertText(".o-mail-channel-selector input", "test");
        await def;
        await nextAnimationFrame(); // ensures search_read rpc is rendered.
        // When searching for a single existing channel, the results list will have at least 2 lines:
        // One for the existing channel itself
        // One for creating a channel with the search term
        assert.containsN(target, ".o-navigable-list-dropdown-item", 2);
        assert.containsN(target, ".o-navigable-list-dropdown-item:contains(test)", 2);
    }
);

QUnit.test(
    "sidebar channels should be ordered case insensitive alphabetically",
    async function (assert) {
        const pyEnv = await startServer();
        pyEnv["mail.channel"].create([
            { name: "Xyz" },
            { name: "abc" },
            { name: "Abc" },
            { name: "Xyz" },
        ]);
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.deepEqual(
            [
                $(".o-mail-category-item:eq(0)").text(),
                $(".o-mail-category-item:eq(1)").text(),
                $(".o-mail-category-item:eq(2)").text(),
                $(".o-mail-category-item:eq(3)").text(),
            ],
            ["abc", "Abc", "Xyz", "Xyz"]
        );
    }
);

QUnit.test("sidebar: public channel rendering", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create([
        { name: "channel1", channel_type: "channel", group_public_id: false },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(target, "button:contains(channel1)");
    assert.containsOnce(target, "button:contains(channel1) .fa-globe");
});

QUnit.test("channel - avatar: should have correct avatar", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "test",
        avatarCacheKey: "100111",
    });

    const { openDiscuss } = await start();
    await openDiscuss();

    assert.containsOnce(target, ".o-mail-category-item img");
    assert.containsOnce(
        target,
        `img[data-src='/web/image/mail.channel/${channelId}/avatar_128?unique=100111']`
    );
});

QUnit.test("channel - avatar: should update avatar url from bus", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ avatarCacheKey: "101010" });
    const { env, openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(
        target,
        `img[data-src='/web/image/mail.channel/${channelId}/avatar_128?unique=101010']`
    );
    await afterNextRender(() => {
        env.services.orm.call("mail.channel", "write", [
            [channelId],
            { image_128: "This field does not matter" },
        ]);
    });
    const result = pyEnv["mail.channel"].searchRead([["id", "=", channelId]]);
    const newCacheKey = result[0]["avatarCacheKey"];
    assert.containsOnce(
        target,
        `img[data-src='/web/image/mail.channel/${channelId}/avatar_128?unique=${newCacheKey}']`
    );
});

QUnit.test(
    "channel - states: close should update the value on the server",
    async function (assert) {
        const pyEnv = await startServer();
        pyEnv["mail.channel"].create({ name: "test" });
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_channel_open: true,
        });
        const currentUserId = pyEnv.currentUserId;
        const { openDiscuss, env } = await start();
        await openDiscuss();
        const initalSettings = await env.services.orm.call(
            "res.users.settings",
            "_find_or_create_for_user",
            [[currentUserId]]
        );
        assert.ok(initalSettings.is_discuss_sidebar_category_channel_open);
        await click(".o-mail-category span:contains(Channels)");
        const newSettings = await env.services.orm.call(
            "res.users.settings",
            "_find_or_create_for_user",
            [[currentUserId]]
        );
        assert.notOk(newSettings.is_discuss_sidebar_category_channel_open);
    }
);

QUnit.test("channel - states: open should update the value on the server", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({ name: "test" });
    pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_channel_open: false,
    });
    const currentUserId = pyEnv.currentUserId;
    const { openDiscuss, env } = await start();
    await openDiscuss();
    const initalSettings = await env.services.orm.call(
        "res.users.settings",
        "_find_or_create_for_user",
        [[currentUserId]]
    );
    assert.notOk(initalSettings.is_discuss_sidebar_category_channel_open);

    await click(".o-mail-category span:contains(Channels)");
    const newSettings = await env.services.orm.call(
        "res.users.settings",
        "_find_or_create_for_user",
        [[currentUserId]]
    );
    assert.ok(newSettings.is_discuss_sidebar_category_channel_open);
});

QUnit.test("channel - states: close from the bus", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({ name: "test" });
    const userSettingsId = pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_channel_open: true,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.record/insert", {
            "res.users.settings": {
                id: userSettingsId,
                is_discuss_sidebar_category_channel_open: false,
            },
        });
    });
    assert.containsOnce(target, ".o-mail-category-channel .fa-chevron-right");
    assert.containsNone(target, "button:contains(test)");
});

QUnit.test("channel - states: open from the bus", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({ name: "test" });
    const userSettingsId = pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_channel_open: false,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.record/insert", {
            "res.users.settings": {
                id: userSettingsId,
                is_discuss_sidebar_category_channel_open: true,
            },
        });
    });
    assert.containsOnce(target, ".o-mail-category-channel .fa-chevron-down");
    assert.containsOnce(target, "button:contains(test)");
});

QUnit.test(
    "channel - states: the active category item should be visible even if the category is closed",
    async function (assert) {
        const pyEnv = await startServer();
        pyEnv["mail.channel"].create({ name: "test" });
        const { openDiscuss } = await start();
        await openDiscuss();
        await click(".o-mail-category-item:contains(test)");
        assert.containsOnce(target, "button:contains(test).o-active");

        await click(".o-mail-category span:contains(Channels)");
        assert.containsOnce(target, ".o-mail-category-channel .fa-chevron-right");
        assert.containsOnce(target, "button:contains(test)");

        await click("button:contains(Inbox)");
        assert.containsNone(target, "button:contains(test)");
    }
);

QUnit.test("chat - states: open manually by clicking the title", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({
        channel_type: "chat",
    });
    pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_chat_open: false,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    await click(".o-mail-category-chat span:contains(Direct messages)");
    assert.containsOnce(target, "button:contains(Mitchell Admin)");
});

QUnit.test("chat - states: close should call update server data", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({ name: "test" });
    pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_chat_open: true,
    });
    const currentUserId = pyEnv.currentUserId;
    const { openDiscuss, env } = await start();
    await openDiscuss();
    const initalSettings = await env.services.orm.call(
        "res.users.settings",
        "_find_or_create_for_user",
        [[currentUserId]]
    );
    assert.ok(initalSettings.is_discuss_sidebar_category_chat_open);

    await click(".o-mail-category-chat span:contains(Direct messages)");
    const newSettings = await env.services.orm.call(
        "res.users.settings",
        "_find_or_create_for_user",
        [[currentUserId]]
    );
    assert.notOk(newSettings.is_discuss_sidebar_category_chat_open);
});

QUnit.test("chat - states: open should call update server data", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({ name: "test" });
    pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_chat_open: false,
    });
    const { openDiscuss, env } = await start();
    await openDiscuss();
    const currentUserId = pyEnv.currentUserId;
    const initalSettings = await env.services.orm.call(
        "res.users.settings",
        "_find_or_create_for_user",
        [[currentUserId]]
    );
    assert.notOk(initalSettings.is_discuss_sidebar_category_chat_open);

    await click(".o-mail-category-chat span:contains(Direct messages)");
    const newSettings = await env.services.orm.call(
        "res.users.settings",
        "_find_or_create_for_user",
        [[currentUserId]]
    );
    assert.ok(newSettings.is_discuss_sidebar_category_chat_open);
});

QUnit.test("chat - states: close from the bus", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({ channel_type: "chat" });
    const userSettingsId = pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_chat_open: true,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.record/insert", {
            "res.users.settings": {
                id: userSettingsId,
                is_discuss_sidebar_category_chat_open: false,
            },
        });
    });
    assert.containsOnce(target, ".o-mail-category-chat .fa-chevron-right");
    assert.containsNone(target, "button:contains(Mitchell Admin)");
});

QUnit.test("chat - states: open from the bus", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({ channel_type: "chat" });
    const userSettingsId = pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_chat_open: false,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.record/insert", {
            "res.users.settings": {
                id: userSettingsId,
                is_discuss_sidebar_category_chat_open: true,
            },
        });
    });
    assert.containsOnce(target, ".o-mail-category-chat .fa-chevron-down");
    assert.containsOnce(target, "button:contains(Mitchell Admin)");
});

QUnit.test(
    "chat - states: the active category item should be visible even if the category is closed",
    async function (assert) {
        const pyEnv = await startServer();
        pyEnv["mail.channel"].create({ channel_type: "chat" });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsOnce(target, ".o-mail-category-chat .fa-chevron-down");
        assert.containsOnce(target, "button:contains(Mitchell Admin)");

        await click("button:contains(Mitchell Admin)");
        assert.containsOnce(target, "button:contains(Mitchell Admin).o-active");

        await click(".o-mail-category-chat span:contains(Direct messages)");
        assert.containsOnce(target, ".o-mail-category-chat .fa-chevron-right");
        assert.containsOnce(target, "button:contains(Mitchell Admin)");

        await click("button:contains(Inbox)");
        assert.containsOnce(target, ".o-mail-category-chat .fa-chevron-right");
        assert.containsNone(target, "button:contains(Mitchell Admin)");
    }
);

QUnit.test("chat - avatar: should have correct avatar", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Demo",
        im_status: "offline",
    });
    const channelId = pyEnv["mail.channel"].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
        channel_type: "chat",
    });
    const channel = pyEnv["mail.channel"].searchRead([["id", "=", channelId]])[0];
    const { openDiscuss } = await start();
    await openDiscuss();

    assert.containsOnce(target, ".o-mail-category-item img");
    assert.containsOnce(
        target,
        `img[data-src='/web/image/res.partner/${partnerId}/avatar_128?unique=${channel.avatarCacheKey}']`
    );
});

QUnit.test("chat should be sorted by last activity time [REQUIRE FOCUS]", async function (assert) {
    const pyEnv = await startServer();
    const [demo_id, yoshi_id] = pyEnv["res.partner"].create([{ name: "Demo" }, { name: "Yoshi" }]);
    pyEnv["res.users"].create([{ partner_id: demo_id }, { partner_id: yoshi_id }]);
    pyEnv["mail.channel"].create([
        {
            channel_member_ids: [
                [
                    0,
                    0,
                    {
                        last_interest_dt: "2021-01-01 10:00:00",
                        partner_id: pyEnv.currentPartnerId,
                    },
                ],
                [0, 0, { partner_id: demo_id }],
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                [
                    0,
                    0,
                    {
                        last_interest_dt: "2021-02-01 10:00:00",
                        partner_id: pyEnv.currentPartnerId,
                    },
                ],
                [0, 0, { partner_id: yoshi_id }],
            ],
            channel_type: "chat",
        },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss();
    let $chats = $(".o-mail-category-chat ~ .o-mail-category-item");
    assert.strictEqual($chats.length, 2);
    assert.strictEqual($($chats[0]).text(), "Yoshi");
    assert.strictEqual($($chats[1]).text(), "Demo");

    // post a new message on the last channel
    await click($($chats[1]));
    await insertText(".o-mail-composer-textarea", "Blabla");
    await click(".o-mail-composer-send-button");
    $chats = $(".o-mail-category-chat ~ .o-mail-category-item");
    assert.strictEqual($chats.length, 2);
    assert.strictEqual($($chats[0]).text(), "Demo");
    assert.strictEqual($($chats[1]).text(), "Yoshi");
});

QUnit.test("Can unpin chat channel", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(target, ".o-mail-category-item:contains(Mitchell Admin)");
    await click(".o-mail-category-item .o-mail-commands *[title='Unpin Conversation']");
    assert.containsNone(target, ".o-mail-category-item:contains(Mitchell Admin)");
});

QUnit.test("Unpinning chat should display notification", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({
        channel_type: "chat",
    });
    const { openDiscuss } = await start({
        services: {
            notification: makeFakeNotificationService((message) => assert.step(message)),
        },
    });
    await openDiscuss();
    await click(".o-mail-category-item .o-mail-commands *[title='Unpin Conversation']");
    assert.verifySteps(["You unpinned your conversation with Mitchell Admin"]);
});
