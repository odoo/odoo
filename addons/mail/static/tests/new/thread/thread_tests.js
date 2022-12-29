/** @odoo-module **/

import { config as transitionConfig } from "@web/core/transition";
import {
    afterNextRender,
    click,
    dragenterFiles,
    insertText,
    isScrolledTo,
    isScrolledToBottom,
    nextAnimationFrame,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";

import { makeDeferred, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("thread");

QUnit.test("dragover files on thread with composer", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        channel_type: "channel",
        group_public_id: false,
        name: "General",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await afterNextRender(() => dragenterFiles($(".o-Thread")[0]));
    assert.containsOnce($, ".o-Dropzone");
});

QUnit.test("load more messages from channel (auto-load on scroll)", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        channel_type: "channel",
        group_public_id: false,
        name: "General",
    });
    for (let i = 0; i <= 60; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "mail.channel",
            res_id: channelId,
        });
    }
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsN($, "button:contains(Load More) ~ .o-Message", 30);

    await afterNextRender(() => ($(".o-Thread")[0].scrollTop = 0));
    assert.containsN($, ".o-Message", 60);
});

QUnit.test(
    "show message subject when subject is not the same as the thread name",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({
            channel_type: "channel",
            group_public_id: false,
            name: "General",
        });
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "mail.channel",
            res_id: channelId,
            subject: "Salutations, voyageur",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-Message");
        assert.containsOnce($, ".o-Message:contains(Subject: Salutations, voyageur)");
    }
);

QUnit.test(
    "do not show message subject when subject is the same as the thread name",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({
            channel_type: "channel",
            group_public_id: false,
            name: "Salutations, voyageur",
        });
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "mail.channel",
            res_id: channelId,
            subject: "Salutations, voyageur",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsNone($, ".o-Message:contains(Salutations, voyageur)");
    }
);

QUnit.test("auto-scroll to bottom of thread on load", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "general" });
    for (let i = 1; i <= 25; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "mail.channel",
            res_id: channelId,
        });
    }
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsN($, ".o-Message", 25);
    assert.ok(isScrolledToBottom($(".o-Thread")[0]));
});

QUnit.test("display day separator before first message of the day", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "" });
    pyEnv["mail.message"].create([
        {
            body: "not empty",
            model: "mail.channel",
            res_id: channelId,
        },
        {
            body: "not empty",
            model: "mail.channel",
            res_id: channelId,
        },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-Thread-date");
});

QUnit.test("do not display day separator if all messages of the day are empty", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "" });
    pyEnv["mail.message"].create({
        body: "",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-Thread-date");
});

QUnit.test(
    "scroll position is kept when navigating from one channel to another",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId_1 = pyEnv["mail.channel"].create({ name: "channel-1" });
        const channelId_2 = pyEnv["mail.channel"].create({ name: "channel-2" });
        // Fill both channels with random messages in order for the scrollbar to
        // appear.
        pyEnv["mail.message"].create(
            Array(40)
                .fill(0)
                .map((_, index) => ({
                    body: "Non Empty Body ".repeat(25),
                    message_type: "comment",
                    model: "mail.channel",
                    res_id: index & 1 ? channelId_1 : channelId_2,
                }))
        );
        const { openDiscuss } = await start();
        await openDiscuss(channelId_1);
        const scrolltop_1 = $(".o-Thread")[0].scrollHeight / 2;
        $(".o-Thread")[0].scrollTo({ top: scrolltop_1 });
        await click(".o-DiscussCategoryItem:contains(channel-2)");
        const scrolltop_2 = $(".o-Thread")[0].scrollHeight / 3;
        $(".o-Thread")[0].scrollTo({ top: scrolltop_2 });
        await click(".o-DiscussCategoryItem:contains(channel-1)");
        assert.ok(isScrolledTo($(".o-Thread")[0], scrolltop_1));
        await click(".o-DiscussCategoryItem:contains(channel-2)");
        assert.ok(isScrolledTo($(".o-Thread")[0], scrolltop_2));
    }
);

QUnit.test("thread is still scrolling after scrolling up then to bottom", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "channel-1" });
    pyEnv["mail.message"].create(
        Array(20)
            .fill(0)
            .map(() => ({
                body: "Non Empty Body ".repeat(25),
                message_type: "comment",
                model: "mail.channel",
                res_id: channelId,
            }))
    );
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    $(".o-Thread")[0].scrollTo({ top: $(".o-Thread")[0].scrollHeight / 2 });
    $(".o-Thread")[0].scrollTo({ top: $(".o-Thread")[0].scrollHeight });
    await insertText(".o-Composer-input", "123");
    await click(".o-Composer-send");
    assert.ok(isScrolledToBottom($(".o-Thread")[0]));
});

QUnit.test("mention a channel with space in the name", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General good boy" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-Composer-input", "#");
    await click(".o-composer-suggestion");
    await click(".o-Composer-send");
    assert.containsOnce($(".o-Message-body"), ".o_channel_redirect");
    assert.strictEqual($(".o_channel_redirect").text(), "#General good boy");
});

QUnit.test('mention a channel with "&" in the name', async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General & good" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-Composer-input", "#");
    await click(".o-composer-suggestion");
    await click(".o-Composer-send");
    assert.containsOnce($(".o-Message-body"), ".o_channel_redirect");
    assert.strictEqual($(".o_channel_redirect").text(), "#General & good");
});

QUnit.test(
    "mark channel as fetched when a new message is loaded and as seen when focusing composer [REQUIRE FOCUS]",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({
            email: "fred@example.com",
            name: "Fred",
        });
        const userId = pyEnv["res.users"].create({ partner_id: partnerId });
        const channelId = pyEnv["mail.channel"].create({
            name: "test",
            uuid: "uuid-uuid",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId }],
            ],
            channel_type: "chat",
        });
        const { env } = await start({
            mockRPC(route, args) {
                if (args.method === "channel_fetched") {
                    assert.strictEqual(args.args[0][0], channelId);
                    assert.strictEqual(args.model, "mail.channel");
                    assert.step("rpc:channel_fetch");
                } else if (route === "/mail/channel/set_last_seen_message") {
                    assert.strictEqual(args.channel_id, channelId);
                    assert.step("rpc:set_last_seen_message");
                }
            },
        });
        await click(".o_menu_systray i[aria-label='Messages']");
        await afterNextRender(async () =>
            env.services.rpc("/mail/chat_post", {
                context: { mockedUserId: userId },
                message_content: "new message",
                uuid: "uuid-uuid",
            })
        );
        assert.verifySteps(["rpc:channel_fetch"]);

        $(".o-Composer-input")[0].focus();
        assert.verifySteps(["rpc:set_last_seen_message"]);
    }
);

QUnit.test(
    "mark channel as fetched and seen when a new message is loaded if composer is focused [REQUIRE FOCUS]",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({});
        const userId = pyEnv["res.users"].create({ partner_id: partnerId });
        const channelId = pyEnv["mail.channel"].create({
            name: "test",
            uuid: "uuid-uuid",
        });
        const deferred = makeDeferred();
        const { env, openDiscuss } = await start({
            async mockRPC(route, args) {
                if (args.method === "channel_fetched" && args.args[0] === channelId) {
                    throw new Error(
                        "'channel_fetched' RPC must not be called for created channel as message is directly seen"
                    );
                } else if (route === "/mail/channel/set_last_seen_message") {
                    assert.strictEqual(args.channel_id, channelId);
                    assert.step("rpc:set_last_seen_message");
                    await deferred;
                }
            },
        });
        await openDiscuss(channelId);
        $(".o-Composer-input")[0].focus();
        // simulate receiving a message
        await env.services.rpc("/mail/chat_post", {
            context: { mockedUserId: userId },
            message_content: "<p>Some new message</p>",
            uuid: "uuid-uuid",
        });
        await afterNextRender(() => deferred.resolve());
        assert.verifySteps(["rpc:set_last_seen_message"]);
    }
);

QUnit.test(
    "should scroll to bottom on receiving new message if the list is initially scrolled to bottom (asc order)",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Foreigner partner" });
        const userId = pyEnv["res.users"].create({ name: "Foreigner user", partner_id: partnerId });
        const channelId = pyEnv["mail.channel"].create({ uuid: "channel-uuid" });
        for (let i = 0; i <= 10; i++) {
            pyEnv["mail.message"].create({
                body: "not empty",
                model: "mail.channel",
                res_id: channelId,
            });
        }
        const { env } = await start();
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-NotificationItem");
        assert.ok(isScrolledToBottom($(".o-Thread")[0]));

        // simulate receiving a message
        await afterNextRender(() =>
            env.services.rpc("/mail/chat_post", {
                context: { mockedUserId: userId },
                message_content: "hello",
                uuid: "channel-uuid",
            })
        );
        assert.ok(isScrolledToBottom($(".o-Thread")[0]));
    }
);

QUnit.test(
    "should not scroll on receiving new message if the list is initially scrolled anywhere else than bottom (asc order)",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Foreigner partner" });
        const userId = pyEnv["res.users"].create({ name: "Foreigner user", partner_id: partnerId });
        const channelId = pyEnv["mail.channel"].create({ uuid: "channel-uuid" });
        for (let i = 0; i <= 10; i++) {
            pyEnv["mail.message"].create({
                body: "not empty",
                model: "mail.channel",
                res_id: channelId,
            });
        }
        const { env } = await start();
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-NotificationItem");
        assert.ok(isScrolledToBottom($(".o-Thread")[0]));

        $(".o-Thread").scrollTop(0);
        await nextAnimationFrame();
        assert.strictEqual($(".o-Thread")[0].scrollTop, 0);

        // simulate receiving a message
        await afterNextRender(() =>
            env.services.rpc("/mail/chat_post", {
                context: { mockedUserId: userId },
                message_content: "hello",
                uuid: "channel-uuid",
            })
        );
        assert.strictEqual($(".o-Thread")[0].scrollTop, 0);
    }
);

QUnit.test("show empty placeholder when thread contains no message", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "general" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-Thread:contains(There are no messages in this conversation.)");
    assert.containsNone($, ".o-Message");
});

QUnit.test("show empty placeholder when thread contains only empty messages", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({ model: "mail.channel", res_id: channelId });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-Thread:contains(There are no messages in this conversation.)");
    assert.containsNone($, ".o-Message");
});

QUnit.test(
    "message list with a full page of empty messages should load more messages until there are some non-empty",
    async (assert) => {
        // Technical assumptions :
        // - /mail/channel/messages fetching exactly 30 messages,
        // - empty messages not being displayed
        // - auto-load more being triggered on scroll, not automatically when the 30 first messages are empty
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ name: "General" });
        for (let i = 0; i < 50; i++) {
            pyEnv["mail.message"].create({
                body: "not empty",
                model: "mail.channel",
                res_id: channelId,
            });
        }
        for (let i = 0; i < 50; i++) {
            pyEnv["mail.message"].create({ model: "mail.channel", res_id: channelId });
        }
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        // initial load: +30 empty ; (auto) load more: +20 empty +10 non-empty
        assert.containsN($, ".o-Message", 10);
        assert.containsOnce($, "button:contains(Load More)"); // still 40 non-empty
    }
);

QUnit.test(
    "no new messages separator on posting message (some message history)",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({
            channel_member_ids: [
                [0, 0, { message_unread_counter: 0, partner_id: pyEnv.currentPartnerId }],
            ],
            channel_type: "channel",
            name: "General",
        });
        const messageId = pyEnv["mail.message"].create({
            body: "first message",
            model: "mail.channel",
            res_id: channelId,
        });
        const [memberId] = pyEnv["mail.channel.member"].search([
            ["channel_id", "=", channelId],
            ["partner_id", "=", pyEnv.currentPartnerId],
        ]);
        pyEnv["mail.channel.member"].write([memberId], { seen_message_id: messageId });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-Message");
        assert.containsNone($, "hr + span:contains(New messages)");

        await insertText(".o-Composer-input", "hey!");
        await afterNextRender(() => {
            // need to remove focus from text area to avoid set_last_seen_message
            $(".o-Composer-send")[0].focus();
            $(".o-Composer-send")[0].click();
        });
        assert.containsN($, ".o-Message", 2);
        assert.containsNone($, "hr + span:contains(New messages)");
    }
);

QUnit.test("new messages separator on receiving new message [REQUIRE FOCUS]", async (assert) => {
    patchWithCleanup(transitionConfig, { disabled: true });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Foreigner partner" });
    const userId = pyEnv["res.users"].create({
        name: "Foreigner user",
        partner_id: partnerId,
    });
    const channelId = pyEnv["mail.channel"].create({
        channel_member_ids: [
            [0, 0, { message_unread_counter: 0, partner_id: pyEnv.currentPartnerId }],
        ],
        channel_type: "channel",
        name: "General",
        uuid: "randomuuid",
    });
    const messageId = pyEnv["mail.message"].create({
        body: "blah",
        model: "mail.channel",
        res_id: channelId,
    });
    const [memberId] = pyEnv["mail.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", pyEnv.currentPartnerId],
    ]);
    pyEnv["mail.channel.member"].write([memberId], { seen_message_id: messageId });
    const { env, openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-Message", "should have an initial message");
    assert.containsNone($, "hr + span:contains(New messages)");

    $(".o-Composer-input")[0].blur();
    // simulate receiving a message
    await afterNextRender(() =>
        env.services.rpc("/mail/chat_post", {
            context: { mockedUserId: userId },
            message_content: "hu",
            uuid: "randomuuid",
        })
    );
    assert.containsN($, ".o-Message", 2);
    assert.containsOnce($, "hr + span:contains(New messages)");
    assert.containsOnce($, ".o-Thread-newMessage ~ .o-Message:contains(hu)");

    $(".o-Composer-input")[0].focus();
    await nextTick();
    assert.containsNone($, "hr + span:contains(New messages)");
});

QUnit.test("no new messages separator on posting message (no message history)", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        channel_member_ids: [
            [0, 0, { message_unread_counter: 0, partner_id: pyEnv.currentPartnerId }],
        ],
        channel_type: "channel",
        name: "General",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-Message");
    assert.containsNone($, "hr + span:contains(New messages)");

    await insertText(".o-Composer-input", "hey!");
    await click(".o-Composer-send");
    assert.containsOnce($, ".o-Message");
    assert.containsNone($, "hr + span:contains(New messages)");
});

QUnit.test("Mention a partner with special character (e.g. apostrophe ')", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "usatyi@example.com",
        name: "Pynya's spokesman",
    });
    const channelId = pyEnv["mail.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-Composer-input", "@");
    await insertText(".o-Composer-input", "Pyn");
    await click(".o-composer-suggestion");
    await click(".o-Composer-send");
    assert.containsOnce(
        $(".o-Message-body"),
        `.o_mail_redirect[data-oe-id="${partnerId}"][data-oe-model="res.partner"]:contains("@Pynya's spokesman")`
    );
});

QUnit.test("mention 2 different partners that have the same name", async (assert) => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        {
            email: "partner1@example.com",
            name: "TestPartner",
        },
        {
            email: "partner2@example.com",
            name: "TestPartner",
        },
    ]);
    const channelId = pyEnv["mail.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId_1 }],
            [0, 0, { partner_id: partnerId_2 }],
        ],
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-Composer-input", "@");
    await insertText(".o-Composer-input", "Te");
    await click(".o-composer-suggestion:eq(0)");
    await insertText(".o-Composer-input", "@");
    await insertText(".o-Composer-input", "Te");
    await click(".o-composer-suggestion:eq(1)");
    await click(".o-Composer-send");
    assert.containsOnce($, ".o-Message-body");
    assert.containsOnce(
        $(".o-Message-body"),
        `.o_mail_redirect[data-oe-id="${partnerId_1}"][data-oe-model="res.partner"]:contains("@TestPartner")`
    );
    assert.containsOnce(
        $(".o-Message-body"),
        `.o_mail_redirect[data-oe-id="${partnerId_2}"][data-oe-model="res.partner"]:contains("@TestPartner")`
    );
});

QUnit.test("mention a channel on a second line when the first line contains #", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General good" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-Composer-input", "#blabla\n");
    await insertText(".o-Composer-input", "#");
    await click(".o-composer-suggestion");
    await click(".o-Composer-send");
    assert.containsOnce($(".o-Message-body"), ".o_channel_redirect");
    assert.strictEqual($(".o_channel_redirect").text(), "#General good");
});

QUnit.test(
    "mention a channel when replacing the space after the mention by another char",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ name: "General good" });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await insertText(".o-Composer-input", "#");
        await click(".o-composer-suggestion");
        const text = $(".o-Composer-input").val();
        $(".o-Composer-input").val(text.slice(0, -1));
        await insertText(".o-Composer-input", ", test");
        await click(".o-Composer-send");
        assert.containsOnce($(".o-Message-body"), ".o_channel_redirect");
        assert.strictEqual($(".o_channel_redirect").text(), "#General good");
    }
);

QUnit.test("mention 2 different channels that have the same name", async (assert) => {
    const pyEnv = await startServer();
    const [channelId_1, channelId_2] = pyEnv["mail.channel"].create([
        {
            channel_type: "channel",
            group_public_id: false,
            name: "my channel",
        },
        {
            channel_type: "channel",
            name: "my channel",
        },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss(channelId_1);
    await insertText(".o-Composer-input", "#");
    await insertText(".o-Composer-input", "m");
    await click(".o-composer-suggestion:eq(0)");
    await insertText(".o-Composer-input", "#");
    await insertText(".o-Composer-input", "m");
    await click(".o-composer-suggestion:eq(1)");
    await click(".o-Composer-send");
    assert.containsOnce($, ".o-Message-body");
    assert.containsOnce(
        $(".o-Message-body"),
        `.o_channel_redirect[data-oe-id="${channelId_1}"][data-oe-model="mail.channel"]:contains("#my channel")`
    );
    assert.containsOnce(
        $(".o-Message-body"),
        `.o_channel_redirect[data-oe-id="${channelId_2}"][data-oe-model="mail.channel"]:contains("#my channel")`
    );
});

QUnit.test(
    "Post a message containing an email address followed by a mention on another line",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({
            email: "testpartner@odoo.com",
            name: "TestPartner",
        });
        const channelId = pyEnv["mail.channel"].create({
            name: "test",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId }],
            ],
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await insertText(".o-Composer-input", "email@odoo.com\n");
        await insertText(".o-Composer-input", "@");
        await insertText(".o-Composer-input", "Te");
        await click(".o-composer-suggestion");
        await click(".o-Composer-send");
        assert.containsOnce(
            $(".o-Message-body"),
            `.o_mail_redirect[data-oe-id="${partnerId}"][data-oe-model="res.partner"]:contains("@TestPartner")`
        );
    }
);

QUnit.test("basic rendering of canceled notification", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "test" });
    const partnerId = pyEnv["res.partner"].create({ name: "Someone" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "email",
        model: "mail.channel",
        res_id: channelId,
    });
    pyEnv["mail.notification"].create({
        failure_type: "SMTP",
        mail_message_id: messageId,
        notification_status: "canceled",
        notification_type: "email",
        res_partner_id: partnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-Message-notification .fa-envelope-o");

    await click(".o-Message-notification");
    assert.containsOnce($, ".o-MessageNotificationPopover");
    assert.containsOnce($, ".o-MessageNotificationPopover .fa-trash-o");
    assert.containsOnce($, ".o-MessageNotificationPopover:contains(Someone)");
});

QUnit.test(
    "first unseen message should be directly preceded by the new message separator if there is a transient message just before it while composer is not focused [REQUIRE FOCUS]",
    async (assert) => {
        // The goal of removing the focus is to ensure the thread is not marked as seen automatically.
        // Indeed that would trigger set_last_seen_message no matter what, which is already covered by other tests.
        // The goal of this test is to cover the conditions specific to transient messages,
        // and the conditions from focus would otherwise shadow them.
        const pyEnv = await startServer();
        // Needed partner & user to allow simulation of message reception
        const partnerId = pyEnv["res.partner"].create({ name: "Foreigner partner" });
        const userId = pyEnv["res.users"].create({
            name: "Foreigner user",
            partner_id: partnerId,
        });
        const channelId = pyEnv["mail.channel"].create({
            channel_type: "channel",
            name: "General",
            uuid: "channel20uuid",
        });
        pyEnv["mail.message"].create([
            {
                body: "not empty",
                model: "mail.channel",
                res_id: channelId,
            },
        ]);
        const { openDiscuss, env } = await start();
        await openDiscuss(channelId);
        // send a command that leads to receiving a transient message
        await insertText(".o-Composer-input", "/who");
        await click(".o-Composer-send");
        // composer is focused by default, we remove that focus
        $(".o-Composer-input")[0].blur();
        // simulate receiving a message
        await afterNextRender(() =>
            env.services.rpc("/mail/chat_post", {
                context: { mockedUserId: userId },
                message_content: "test",
                uuid: "channel20uuid",
            })
        );
        assert.containsN($, ".o-Message", 3);
        assert.containsOnce($, "hr + span:contains(New messages)");
        assert.containsOnce($, ".o-Message[aria-label='Note'] + .o-Thread-newMessage");
    }
);

QUnit.test(
    "composer should be focused automatically after clicking on the send button",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ name: "test" });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await insertText(".o-Composer-input", "Dummy Message");
        await click(".o-Composer-send");
        assert.strictEqual(document.activeElement, $(".o-Composer-input")[0]);
    }
);

QUnit.test(
    "chat window header should not have unread counter for non-channel thread",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "test" });
        const messageId = pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "not empty",
            model: "res.partner",
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
        await click(".o-NotificationItem-name");
        assert.containsOnce($, ".o-ChatWindow");
        assert.containsNone($, ".o-ChatWindow-header:contains('(1)')");
    }
);

QUnit.test(
    "[technical] opening a non-channel chat window should not call channel_fold",
    async (assert) => {
        // channel_fold should not be called when opening non-channels in chat
        // window, because there is no server sync of fold state for them.
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "test" });
        const messageId = pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "not empty",
            model: "res.partner",
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
        await start({
            async mockRPC(route, args) {
                if (route.includes("channel_fold")) {
                    const message =
                        "should not call channel_fold when opening a non-channel chat window";
                    assert.step(message);
                    console.error(message);
                    throw Error(message);
                }
            },
        });
        await click(".o_menu_systray i[aria-label='Messages']");
        assert.containsOnce($, ".o-NotificationItem");
        assert.containsNone($, ".o-ChatWindow");

        await click(".o-NotificationItem");
        assert.containsOnce($, ".o-ChatWindow");
    }
);
