/* @odoo-module */

import { Command } from "@mail/../tests/helpers/command";
import {
    afterNextRender,
    click,
    insertText,
    start,
    startServer,
    waitUntil,
} from "@mail/../tests/helpers/test_utils";

import { getOrigin } from "@web/core/utils/urls";
import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import { editInput, nextTick } from "@web/../tests/helpers/utils";

QUnit.module("discuss sidebar");

QUnit.test("toggling category button hide category items", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, "button.o-active:contains('Inbox')");
    assert.containsOnce($, ".o-mail-DiscussCategoryItem");

    await click(".o-mail-DiscussCategory-icon");
    assert.containsNone($, ".o-mail-DiscussCategoryItem");
});

QUnit.test("toggling category button does not hide active category items", async (assert) => {
    const pyEnv = await startServer();
    const [channelId] = pyEnv["discuss.channel"].create([
        { name: "abc", channel_type: "channel" },
        { name: "def", channel_type: "channel" },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsN($, ".o-mail-DiscussCategoryItem", 2);
    assert.containsOnce($, ".o-mail-DiscussCategoryItem.o-active");

    await click(".o-mail-DiscussCategory-icon");
    assert.containsOnce($, ".o-mail-DiscussCategoryItem");
    assert.containsOnce($, ".o-mail-DiscussCategoryItem.o-active");
});

QUnit.test("Closing a category sends the updated user setting to the server.", async (assert) => {
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
    await click(".o-mail-DiscussCategory-icon");
    assert.verifySteps(["/web/dataset/call_kw/res.users.settings/set_res_users_settings"]);
});

QUnit.test("Opening a category sends the updated user setting to the server.", async (assert) => {
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
    await click(".o-mail-DiscussCategory-icon");
    assert.verifySteps(["/web/dataset/call_kw/res.users.settings/set_res_users_settings"]);
});

QUnit.test(
    "channel - command: should have view command when category is unfolded",
    async (assert) => {
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsOnce($, "i[title='View or join channels']");
    }
);

QUnit.test(
    "channel - command: should have view command when category is folded",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_channel_open: false,
        });
        const { openDiscuss } = await start();
        await openDiscuss();
        await click(".o-mail-DiscussCategory-channel span:contains(Channels)");
        assert.containsOnce($, "i[title='View or join channels']");
    }
);

QUnit.test(
    "channel - command: should have add command when category is unfolded",
    async (assert) => {
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsOnce($, "i[title='Add or join a channel']");
    }
);

QUnit.test(
    "channel - command: should not have add command when category is folded",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_channel_open: false,
        });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsNone($, "i[title='Add or join a channel']");
    }
);

QUnit.test("channel - states: close manually by clicking the title", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "general" });
    pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_channel_open: true,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussCategoryItem:contains(general)");
    await click(".o-mail-DiscussCategory-channel span:contains(Channels)");
    assert.containsNone($, ".o-mail-DiscussCategoryItem:contains(general)");
});

QUnit.test("channel - states: open manually by clicking the title", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "general" });
    pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_channel_open: false,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsNone($, ".o-mail-DiscussCategoryItem:contains(general)");
    await click(".o-mail-DiscussCategory-channel span:contains(Channels)");
    assert.containsOnce($, ".o-mail-DiscussCategoryItem:contains(general)");
});

QUnit.test("sidebar: inbox with counter", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["mail.notification"].create({
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, "button:contains(Inbox) .badge:contains(1)");
});

QUnit.test("default thread rendering", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, "button:contains(Inbox)");
    assert.containsOnce($, "button:contains(Starred)");
    assert.containsOnce($, "button:contains(History)");
    assert.containsOnce($, ".o-mail-DiscussCategoryItem:contains(General)");
    assert.hasClass($("button:contains(Inbox)"), "o-active");
    assert.containsOnce(
        $,
        ".o-mail-Thread:contains(Congratulations, your inbox is empty  New messages appear here.)"
    );

    await click("button:contains(Starred)");
    assert.hasClass($("button:contains(Starred)"), "o-active");
    assert.containsOnce(
        $,
        ".o-mail-Thread:contains(No starred messages  You can mark any message as 'starred', and it shows up in this mailbox.)"
    );

    await click("button:contains(History)");
    assert.hasClass($("button:contains(History)"), "o-active");
    assert.containsOnce(
        $,
        ".o-mail-Thread:contains(No history messages  Messages marked as read will appear in the history.)"
    );

    await click(".o-mail-DiscussCategoryItem:contains(General)");
    assert.hasClass($(".o-mail-DiscussCategoryItem:contains(General)"), "o-active");
    assert.containsOnce($, ".o-mail-Thread:contains(There are no messages in this conversation.)");
});

QUnit.test("sidebar quick search at 20 or more pinned channels", async (assert) => {
    const pyEnv = await startServer();
    for (let id = 1; id <= 20; id++) {
        pyEnv["discuss.channel"].create({ name: `channel${id}` });
    }
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsN($, ".o-mail-DiscussCategoryItem", 20);
    assert.containsOnce($, ".o-mail-DiscussSidebar input[placeholder='Quick search...']");

    await editInput(
        document.body,
        ".o-mail-DiscussSidebar input[placeholder='Quick search...']",
        "1"
    );
    assert.containsN($, ".o-mail-DiscussCategoryItem", 11);

    await editInput(
        document.body,
        ".o-mail-DiscussSidebar input[placeholder='Quick search...']",
        "12"
    );
    assert.containsOnce($, ".o-mail-DiscussCategoryItem");
    assert.containsOnce($, ".o-mail-DiscussCategoryItem:contains(channel12)");

    await editInput(
        document.body,
        ".o-mail-DiscussSidebar input[placeholder='Quick search...']",
        "123"
    );
    assert.containsNone($, ".o-mail-DiscussCategoryItem");
});

QUnit.test("sidebar: basic chat rendering", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussCategoryItem:contains(Demo)");
    const $chat = $(".o-mail-DiscussCategoryItem:contains(Demo)");
    assert.containsOnce($chat, "img[data-alt='Thread Image']");
    assert.containsOnce($chat, "span:contains(Demo)");
    assert.containsOnce($chat, ".o-mail-DiscussCategoryItem-commands");
    assert.containsOnce(
        $chat,
        ".o-mail-DiscussCategoryItem-commands div[title='Unpin Conversation']"
    );
    assert.containsNone($chat, ".badge");
});

QUnit.test("sidebar: show pinned channel", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussCategoryItem:contains(General)");
});

QUnit.test("sidebar: open pinned channel", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss();
    await click(".o-mail-DiscussCategoryItem:contains(General)");
    assert.strictEqual($(".o-mail-Discuss-threadName").val(), "General");
    assert.containsOnce($, ".o-mail-Composer-input[placeholder='Message #General…']");
});

QUnit.test("sidebar: open channel and leave it", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            Command.create({
                fold_state: "open",
                is_minimized: true,
                partner_id: pyEnv.currentPartnerId,
            }),
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
    await click(".o-mail-DiscussCategoryItem:contains(General)");
    assert.verifySteps([]);

    await click(".o-mail-DiscussCategoryItem:contains(General) .btn[title='Leave this channel']");
    assert.verifySteps(["action_unfollow"]);
    assert.containsNone($, ".o-mail-DiscussCategoryItem:contains(General)");
    assert.notOk($(".o-mail-Discuss-threadName")?.val() === "General");
});

QUnit.test("sidebar: unpin channel from bus", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussCategoryItem:contains(General)");

    await click(".o-mail-DiscussCategoryItem:contains(General)");
    assert.strictEqual($(".o-mail-Discuss-threadName").val(), "General");

    // Simulate receiving a leave channel notification
    // (e.g. from user interaction from another device or browser tab)
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "discuss.channel/unpin", { id: channelId });
    });
    assert.containsNone($, ".o-mail-DiscussCategoryItem:contains(General)");
    assert.notOk($(".o-mail-Discuss-threadName")?.val() === "General");
});

QUnit.test("chat - channel should count unread message [REQUIRE FOCUS]", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Demo",
        im_status: "offline",
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 1, partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-discuss-badge");
    assert.strictEqual($(".o-discuss-badge").text(), "1");

    await click(".o-mail-DiscussCategoryItem:contains(Demo)");
    assert.containsNone($, ".o-discuss-badge");
});

QUnit.test("mark channel as seen on last message visible [REQUIRE FOCUS]", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ message_unread_counter: 1, partner_id: pyEnv.currentPartnerId }),
        ],
    });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussCategoryItem:contains(test)");
    assert.hasClass($(".o-mail-DiscussCategoryItem:contains(test)"), "o-unread");

    await click(".o-mail-DiscussCategoryItem:contains(test)");
    assert.doesNotHaveClass($(".o-mail-DiscussCategoryItem:contains(test)"), "o-unread");
});

QUnit.test(
    "channel - counter: should not have a counter if the category is unfolded and without needaction messages",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_channel_open: true,
        });
        pyEnv["discuss.channel"].create({ name: "general" });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsNone($, ".o-mail-DiscussCategory:contains(Channels) .badge");
    }
);

QUnit.test(
    "channel - counter: should not have a counter if the category is unfolded and with needaction messages",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_channel_open: true,
        });
        const [channelId_1, channelId_2] = pyEnv["discuss.channel"].create([
            { name: "channel1" },
            { name: "channel2" },
        ]);
        const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
            {
                body: "message 1",
                model: "discuss.channel",
                res_id: channelId_1,
            },
            {
                body: "message_2",
                model: "discuss.channel",
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
        assert.containsNone($, ".o-mail-DiscussCategory:contains(Channels) .badge");
    }
);

QUnit.test(
    "channel - counter: should not have a counter if category is folded and without needaction messages",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["discuss.channel"].create({});
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_channel_open: false,
        });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsNone($, ".o-mail-DiscussCategory:contains(Channels) .badge");
    }
);

QUnit.test(
    "channel - counter: should have correct value of needaction threads if category is folded and with needaction messages",
    async (assert) => {
        const pyEnv = await startServer();
        const [channelId_1, channelId_2] = pyEnv["discuss.channel"].create([
            { name: "Channel_1" },
            { name: "Channel_2" },
        ]);
        const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
            {
                body: "message 1",
                model: "discuss.channel",
                res_id: channelId_1,
            },
            {
                body: "message_2",
                model: "discuss.channel",
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
        assert.containsOnce($, ".o-mail-DiscussCategory:contains(Channels) .badge:contains(2)");
    }
);

QUnit.test(
    "chat - counter: should not have a counter if the category is unfolded and without unread messages",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_chat_open: true,
        });
        pyEnv["discuss.channel"].create({
            channel_member_ids: [
                Command.create({ message_unread_counter: 0, partner_id: pyEnv.currentPartnerId }),
            ],
            channel_type: "chat",
        });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsNone($, ".o-mail-DiscussCategory:contains(Direct messages) .badge");
    }
);

QUnit.test(
    "chat - counter: should not have a counter if the category is unfolded and with unread messagens",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_chat_open: true,
        });
        pyEnv["discuss.channel"].create({
            channel_member_ids: [
                Command.create({ message_unread_counter: 10, partner_id: pyEnv.currentPartnerId }),
            ],
            channel_type: "chat",
        });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsNone($, ".o-mail-DiscussCategory:contains(Direct messages) .badge");
    }
);

QUnit.test(
    "chat - counter: should not have a counter if category is folded and without unread messages",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_chat_open: false,
        });
        pyEnv["discuss.channel"].create({
            channel_member_ids: [
                Command.create({ message_unread_counter: 0, partner_id: pyEnv.currentPartnerId }),
            ],
            channel_type: "chat",
        });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsNone($, ".o-mail-DiscussCategory:contains(Direct messages) .badge");
    }
);

QUnit.test(
    "chat - counter: should have correct value of unread threads if category is folded and with unread messages",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_chat_open: false,
        });
        pyEnv["discuss.channel"].create([
            {
                channel_member_ids: [
                    Command.create({
                        message_unread_counter: 10,
                        partner_id: pyEnv.currentPartnerId,
                    }),
                ],
                channel_type: "chat",
            },
            {
                channel_member_ids: [
                    Command.create({
                        message_unread_counter: 20,
                        partner_id: pyEnv.currentPartnerId,
                    }),
                ],
                channel_type: "chat",
            },
        ]);
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsOnce(
            $,
            ".o-mail-DiscussCategory:contains(Direct messages) .badge:contains(2)"
        );
    }
);

QUnit.test("chat - command: should have add command when category is unfolded", async (assert) => {
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(
        $,
        ".o-mail-DiscussCategory:contains(Direct messages) i[title='Start a conversation']"
    );
});

QUnit.test(
    "chat - command: should not have add command when category is folded",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_chat_open: false,
        });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsNone(
            $,
            ".o-mail-DiscussCategory:contains(Direct messages) i[title='Start a conversation']"
        );
    }
);

QUnit.test("chat - states: close manually by clicking the title", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ channel_type: "chat" });
    pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_chat_open: true,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussCategoryItem");
    await click(".o-mail-DiscussCategory:contains(Direct messages) div");
    assert.containsNone($, ".o-mail-DiscussCategoryItem");
});

QUnit.test("sidebar channels should be ordered case insensitive alphabetically", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        { name: "Xyz" },
        { name: "abc" },
        { name: "Abc" },
        { name: "Xyz" },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.deepEqual(
        [
            $(".o-mail-DiscussCategoryItem:eq(0)").text(),
            $(".o-mail-DiscussCategoryItem:eq(1)").text(),
            $(".o-mail-DiscussCategoryItem:eq(2)").text(),
            $(".o-mail-DiscussCategoryItem:eq(3)").text(),
        ],
        ["abc", "Abc", "Xyz", "Xyz"]
    );
});

QUnit.test("sidebar: public channel rendering", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "channel1",
        channel_type: "channel",
        group_public_id: false,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, "button:contains(channel1)");
    assert.containsOnce($, "button:contains(channel1) .fa-globe");
});

QUnit.test("channel - avatar: should have correct avatar", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        avatarCacheKey: "100111",
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussCategoryItem img");
    assert.containsOnce(
        $,
        `img[data-src='${getOrigin()}/discuss/channel/${channelId}/avatar_128?unique=100111']`
    );
});

QUnit.test("channel - avatar: should update avatar url from bus", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ avatarCacheKey: "101010", name: "test" });
    const { env, openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsN(
        $,
        `img[data-src='${getOrigin()}/discuss/channel/${channelId}/avatar_128?unique=101010']`,
        2
    );
    await afterNextRender(() => {
        env.services.orm.call("discuss.channel", "write", [
            [channelId],
            { image_128: "This field does not matter" },
        ]);
    });
    const result = pyEnv["discuss.channel"].searchRead([["id", "=", channelId]]);
    const newCacheKey = result[0]["avatarCacheKey"];
    assert.containsN(
        $,
        `img[data-src='${getOrigin()}/discuss/channel/${channelId}/avatar_128?unique=${newCacheKey}']`,
        2
    );
});

QUnit.test("channel - states: close should update the value on the server", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "test" });
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
    await click(".o-mail-DiscussCategory span:contains(Channels)");
    const newSettings = await env.services.orm.call(
        "res.users.settings",
        "_find_or_create_for_user",
        [[currentUserId]]
    );
    assert.notOk(newSettings.is_discuss_sidebar_category_channel_open);
});

QUnit.test("channel - states: open should update the value on the server", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "test" });
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

    await click(".o-mail-DiscussCategory span:contains(Channels)");
    const newSettings = await env.services.orm.call(
        "res.users.settings",
        "_find_or_create_for_user",
        [[currentUserId]]
    );
    assert.ok(newSettings.is_discuss_sidebar_category_channel_open);
});

QUnit.test("channel - states: close from the bus", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "test" });
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
    assert.containsOnce($, ".o-mail-DiscussCategory-channel .oi-chevron-right");
    assert.containsNone($, "button:contains(test)");
});

QUnit.test("channel - states: open from the bus", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "test" });
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
    assert.containsOnce($, ".o-mail-DiscussCategory-channel .oi-chevron-down");
    assert.containsOnce($, "button:contains(test)");
});

QUnit.test(
    "channel - states: the active category item should be visible even if the category is closed",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["discuss.channel"].create({ name: "test" });
        const { openDiscuss } = await start();
        await openDiscuss();
        await click(".o-mail-DiscussCategoryItem:contains(test)");
        assert.containsOnce($, "button:contains(test).o-active");

        await click(".o-mail-DiscussCategory span:contains(Channels)");
        assert.containsOnce($, ".o-mail-DiscussCategory-channel .oi-chevron-right");
        assert.containsOnce($, "button:contains(test)");

        await click("button:contains(Inbox)");
        assert.containsNone($, "button:contains(test)");
    }
);

QUnit.test("chat - states: open manually by clicking the title", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        channel_type: "chat",
    });
    pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_chat_open: false,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    await click(".o-mail-DiscussCategory-chat span:contains(Direct messages)");
    assert.containsOnce($, "button:contains(Mitchell Admin)");
});

QUnit.test("chat - states: close should call update server data", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "test" });
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

    await click(".o-mail-DiscussCategory-chat span:contains(Direct messages)");
    const newSettings = await env.services.orm.call(
        "res.users.settings",
        "_find_or_create_for_user",
        [[currentUserId]]
    );
    assert.notOk(newSettings.is_discuss_sidebar_category_chat_open);
});

QUnit.test("chat - states: open should call update server data", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "test" });
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

    await click(".o-mail-DiscussCategory-chat span:contains(Direct messages)");
    const newSettings = await env.services.orm.call(
        "res.users.settings",
        "_find_or_create_for_user",
        [[currentUserId]]
    );
    assert.ok(newSettings.is_discuss_sidebar_category_chat_open);
});

QUnit.test("chat - states: close from the bus", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ channel_type: "chat" });
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
    assert.containsOnce($, ".o-mail-DiscussCategory-chat .oi-chevron-right");
    assert.containsNone($, "button:contains(Mitchell Admin)");
});

QUnit.test("chat - states: open from the bus", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ channel_type: "chat" });
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
    assert.containsOnce($, ".o-mail-DiscussCategory-chat .oi-chevron-down");
    assert.containsOnce($, "button:contains(Mitchell Admin)");
});

QUnit.test(
    "chat - states: the active category item should be visible even if the category is closed",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["discuss.channel"].create({ channel_type: "chat" });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsOnce($, ".o-mail-DiscussCategory-chat .oi-chevron-down");
        assert.containsOnce($, "button:contains(Mitchell Admin)");

        await click("button:contains(Mitchell Admin)");
        assert.containsOnce($, "button:contains(Mitchell Admin).o-active");

        await click(".o-mail-DiscussCategory-chat span:contains(Direct messages)");
        assert.containsOnce($, ".o-mail-DiscussCategory-chat .oi-chevron-right");
        assert.containsOnce($, "button:contains(Mitchell Admin)");

        await click("button:contains(Inbox)");
        assert.containsOnce($, ".o-mail-DiscussCategory-chat .oi-chevron-right");
        assert.containsNone($, "button:contains(Mitchell Admin)");
    }
);

QUnit.test("chat - avatar: should have correct avatar", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Demo",
        im_status: "offline",
    });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    await openDiscuss();

    assert.containsOnce($, ".o-mail-DiscussCategoryItem img");
    assert.containsOnce($, `img[data-src='/web/image/res.partner/${partnerId}/avatar_128']`);
});

QUnit.test("chat should be sorted by last activity time [REQUIRE FOCUS]", async (assert) => {
    const pyEnv = await startServer();
    const [demo_id, yoshi_id] = pyEnv["res.partner"].create([{ name: "Demo" }, { name: "Yoshi" }]);
    pyEnv["res.users"].create([{ partner_id: demo_id }, { partner_id: yoshi_id }]);
    pyEnv["discuss.channel"].create([
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
                Command.create({ partner_id: demo_id }),
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
                Command.create({ partner_id: yoshi_id }),
            ],
            channel_type: "chat",
        },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss();
    let $chats = $(".o-mail-DiscussCategory-chat ~ .o-mail-DiscussCategoryItem");
    assert.strictEqual($chats.length, 2);
    assert.strictEqual($($chats[0]).text(), "Yoshi");
    assert.strictEqual($($chats[1]).text(), "Demo");

    // post a new message on the last channel
    await click($($chats[1]));
    await insertText(".o-mail-Composer-input", "Blabla");
    await click(".o-mail-Composer-send");
    $chats = $(".o-mail-DiscussCategory-chat ~ .o-mail-DiscussCategoryItem");
    assert.strictEqual($chats.length, 2);
    assert.strictEqual($($chats[0]).text(), "Demo");
    assert.strictEqual($($chats[1]).text(), "Yoshi");
});

QUnit.test("Can unpin chat channel", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ channel_type: "chat" });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussCategoryItem:contains(Mitchell Admin)");
    await click(".o-mail-DiscussCategoryItem [title='Unpin Conversation']");
    assert.containsNone($, ".o-mail-DiscussCategoryItem:contains(Mitchell Admin)");
});

QUnit.test("Unpinning chat should display notification", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ channel_type: "chat" });
    const { openDiscuss } = await start({
        services: {
            notification: makeFakeNotificationService((message) => assert.step(message)),
        },
    });
    await openDiscuss();
    await click(".o-mail-DiscussCategoryItem [title='Unpin Conversation']");
    assert.verifySteps(["You unpinned your conversation with Mitchell Admin"]);
});

QUnit.test("Can leave channel", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { env, openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-DiscussCategoryItem:contains(General)");
    const messageId = pyEnv["mail.message"].create({
        body: '<div class="o_mail_notification">Mitchell Admin left the channel</div>',
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const [message] = await env.services.orm.call("mail.message", "message_format", [[messageId]]);
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendmany([
            [channelId, "discuss.channel/leave", { id: channelId }],
            [channelId, "discuss.channel/new_message", { id: channelId, message }],
        ]);
    });
    assert.containsNone($, ".o-mail-DiscussCategoryItem:contains(General)");
});

QUnit.test("Do no channel_info after unpin", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General", channel_type: "chat" });
    const { env, openDiscuss } = await start({
        mockRPC(route, args, originalRPC) {
            if (route === "/discuss/channel/info") {
                assert.step("channel_info");
            }
            return originalRPC(route, args);
        },
    });
    await openDiscuss(channelId);
    await click(".o-mail-DiscussCategoryItem-commands [title='Unpin Conversation']");
    await afterNextRender(() => {
        env.services.rpc("/mail/message/post", {
            thread_id: channelId,
            thread_model: "discuss.channel",
            post_data: {
                body: "Hello world",
                message_type: "comment",
            },
        });
    });
    await nextTick();
    assert.verifySteps([]);
});

QUnit.test("Group unread counter up to date after mention is marked as seen", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Chuck" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "group",
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        model: "discuss.channel",
        res_id: channelId,
        body: "@Mitchell Admin",
        needaction: true,
    });
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId,
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussCategoryItem .o-discuss-badge");
    await click(".o-mail-DiscussCategoryItem");
    await waitUntil(".o-discuss-badge", 0);
});

QUnit.test("Unpinning channel closes its chat window", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "Sales" });
    const { openFormView, openDiscuss } = await start();
    await openFormView("discuss.channel");
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    assert.containsOnce($, ".o-mail-ChatWindow:contains(Sales)");
    await openDiscuss();
    await click(".o-mail-DiscussCategoryItem:contains(Sales) [title='Leave this channel']");
    await openFormView("discuss.channel");
    assert.containsNone($, ".o-mail-ChatWindow:contains(Sales)");
});
