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
    waitUntil,
} from "@mail/../tests/helpers/test_utils";
import { Command } from "@mail/../tests/helpers/command";

import {
    makeDeferred,
    nextTick,
    patchWithCleanup,
    triggerEvents,
} from "@web/../tests/helpers/utils";
import { DEBOUNCE_FETCH_SUGGESTION_TIME } from "@mail/discuss_app/channel_selector";

QUnit.module("thread");

QUnit.test("dragover files on thread with composer", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        group_public_id: false,
        name: "General",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await afterNextRender(() => dragenterFiles($(".o-mail-Thread")[0]));
    assert.containsOnce($, ".o-mail-Dropzone");
});

QUnit.test("load more messages from channel (auto-load on scroll)", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        group_public_id: false,
        name: "General",
    });
    for (let i = 0; i <= 60; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsN($, "button:contains(Load More) ~ .o-mail-Message", 30);

    await afterNextRender(() => ($(".o-mail-Thread")[0].scrollTop = 0));
    assert.containsN($, ".o-mail-Message", 60);
});

QUnit.test(
    "show message subject when subject is not the same as the thread name",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            channel_type: "channel",
            group_public_id: false,
            name: "General",
        });
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
            subject: "Salutations, voyageur",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-mail-Message");
        assert.containsOnce($, ".o-mail-Message:contains(Subject: Salutations, voyageur)");
    }
);

QUnit.test(
    "do not show message subject when subject is the same as the thread name",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            channel_type: "channel",
            group_public_id: false,
            name: "Salutations, voyageur",
        });
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
            subject: "Salutations, voyageur",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsNone($, ".o-mail-Message:contains(Salutations, voyageur)");
    }
);

QUnit.test("auto-scroll to bottom of thread on load", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    for (let i = 1; i <= 25; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsN($, ".o-mail-Message", 25);
    assert.ok(isScrolledToBottom($(".o-mail-Thread")[0]));
});

QUnit.test("display day separator before first message of the day", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    pyEnv["mail.message"].create([
        {
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-Thread-date");
});

QUnit.test("do not display day separator if all messages of the day are empty", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    pyEnv["mail.message"].create({
        body: "",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-mail-Thread-date");
});

QUnit.test(
    "scroll position is kept when navigating from one channel to another",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId_1 = pyEnv["discuss.channel"].create({ name: "channel-1" });
        const channelId_2 = pyEnv["discuss.channel"].create({ name: "channel-2" });
        // Fill both channels with random messages in order for the scrollbar to
        // appear.
        pyEnv["mail.message"].create(
            Array(40)
                .fill(0)
                .map((_, index) => ({
                    body: "Non Empty Body ".repeat(25),
                    message_type: "comment",
                    model: "discuss.channel",
                    res_id: index & 1 ? channelId_1 : channelId_2,
                }))
        );
        const { openDiscuss } = await start();
        await openDiscuss(channelId_1);
        const scrolltop_1 = $(".o-mail-Thread")[0].scrollHeight / 2;
        $(".o-mail-Thread")[0].scrollTo({ top: scrolltop_1 });
        await click(".o-mail-DiscussCategoryItem:contains(channel-2)");
        const scrolltop_2 = $(".o-mail-Thread")[0].scrollHeight / 3;
        $(".o-mail-Thread")[0].scrollTo({ top: scrolltop_2 });
        await click(".o-mail-DiscussCategoryItem:contains(channel-1)");
        assert.ok(isScrolledTo($(".o-mail-Thread")[0], scrolltop_1));
        await click(".o-mail-DiscussCategoryItem:contains(channel-2)");
        assert.ok(isScrolledTo($(".o-mail-Thread")[0], scrolltop_2));
    }
);

QUnit.test("thread is still scrolling after scrolling up then to bottom", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "channel-1" });
    pyEnv["mail.message"].create(
        Array(20)
            .fill(0)
            .map(() => ({
                body: "Non Empty Body ".repeat(25),
                message_type: "comment",
                model: "discuss.channel",
                res_id: channelId,
            }))
    );
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    $(".o-mail-Thread")[0].scrollTo({ top: $(".o-mail-Thread")[0].scrollHeight / 2 });
    $(".o-mail-Thread")[0].scrollTo({ top: $(".o-mail-Thread")[0].scrollHeight });
    await insertText(".o-mail-Composer-input", "123");
    await click(".o-mail-Composer-send");
    assert.ok(isScrolledToBottom($(".o-mail-Thread")[0]));
});

QUnit.test("mention a channel with space in the name", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General good boy" });
    const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "#");
    await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
    await nextTick();
    await nextTick();
    await click(".o-mail-Composer-suggestion");
    await click(".o-mail-Composer-send");
    assert.containsOnce($(".o-mail-Message-body"), ".o_channel_redirect");
    assert.strictEqual($(".o_channel_redirect").text(), "#General good boy");
});

QUnit.test('mention a channel with "&" in the name', async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General & good" });
    const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "#");
    await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
    await nextTick();
    await nextTick();
    await click(".o-mail-Composer-suggestion");
    await click(".o-mail-Composer-send");
    assert.containsOnce($(".o-mail-Message-body"), ".o_channel_redirect");
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
        const channelId = pyEnv["discuss.channel"].create({
            name: "test",
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "chat",
        });
        const { env } = await start({
            mockRPC(route, args) {
                if (args.method === "channel_fetched") {
                    assert.strictEqual(args.args[0][0], channelId);
                    assert.strictEqual(args.model, "discuss.channel");
                    assert.step("rpc:channel_fetch");
                } else if (route === "/discuss/channel/set_last_seen_message") {
                    assert.strictEqual(args.channel_id, channelId);
                    assert.step("rpc:set_last_seen_message");
                }
            },
        });
        await click(".o_menu_systray i[aria-label='Messages']");
        await afterNextRender(async () =>
            env.services.rpc("/mail/message/post", {
                context: { mockedUserId: userId },
                post_data: { body: "new message", message_type: "comment" },
                thread_id: channelId,
                thread_model: "discuss.channel",
            })
        );
        assert.verifySteps(["rpc:channel_fetch"]);

        $(".o-mail-Composer-input")[0].focus();
        await waitUntil(".o-mail-Message");
        assert.verifySteps(["rpc:set_last_seen_message"]);
    }
);

QUnit.test(
    "mark channel as fetched and seen when a new message is loaded if composer is focused [REQUIRE FOCUS]",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({});
        const userId = pyEnv["res.users"].create({ partner_id: partnerId });
        const channelId = pyEnv["discuss.channel"].create({ name: "test" });
        const deferred = makeDeferred();
        const { env, openDiscuss } = await start({
            async mockRPC(route, args) {
                if (args.method === "channel_fetched" && args.args[0] === channelId) {
                    throw new Error(
                        "'channel_fetched' RPC must not be called for created channel as message is directly seen"
                    );
                } else if (route === "/discuss/channel/set_last_seen_message") {
                    assert.strictEqual(args.channel_id, channelId);
                    assert.step("rpc:set_last_seen_message");
                    await deferred;
                }
            },
        });
        await openDiscuss(channelId);
        $(".o-mail-Composer-input")[0].focus();
        // simulate receiving a message
        await env.services.rpc("/mail/message/post", {
            context: { mockedUserId: userId },
            post_data: { body: "<p>Some new message</p>", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
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
        const channelId = pyEnv["discuss.channel"].create({});
        for (let i = 0; i <= 10; i++) {
            pyEnv["mail.message"].create({
                body: "not empty",
                model: "discuss.channel",
                res_id: channelId,
            });
        }
        const { env } = await start();
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-NotificationItem");
        assert.ok(isScrolledToBottom($(".o-mail-Thread")[0]));

        // simulate receiving a message
        await afterNextRender(() =>
            env.services.rpc("/mail/message/post", {
                context: { mockedUserId: userId },
                post_data: { body: "hello", message_type: "comment" },
                thread_id: channelId,
                thread_model: "discuss.channel",
            })
        );
        assert.ok(isScrolledToBottom($(".o-mail-Thread")[0]));
    }
);

QUnit.test(
    "should not scroll on receiving new message if the list is initially scrolled anywhere else than bottom (asc order)",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Foreigner partner" });
        const userId = pyEnv["res.users"].create({ name: "Foreigner user", partner_id: partnerId });
        const channelId = pyEnv["discuss.channel"].create({});
        for (let i = 0; i <= 10; i++) {
            pyEnv["mail.message"].create({
                body: "not empty",
                model: "discuss.channel",
                res_id: channelId,
            });
        }
        const { env } = await start();
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-NotificationItem");
        assert.ok(isScrolledToBottom($(".o-mail-Thread")[0]));

        $(".o-mail-Thread").scrollTop(0);
        await nextAnimationFrame();
        assert.strictEqual($(".o-mail-Thread")[0].scrollTop, 0);

        // simulate receiving a message
        await afterNextRender(() =>
            env.services.rpc("/mail/message/post", {
                context: { mockedUserId: userId },
                post_data: { body: "hello", message_type: "comment" },
                thread_id: channelId,
                thread_model: "discuss.channel",
            })
        );
        assert.strictEqual($(".o-mail-Thread")[0].scrollTop, 0);
    }
);

QUnit.test("show empty placeholder when thread contains no message", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-Thread:contains(There are no messages in this conversation.)");
    assert.containsNone($, ".o-mail-Message");
});

QUnit.test("show empty placeholder when thread contains only empty messages", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({ model: "discuss.channel", res_id: channelId });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-Thread:contains(There are no messages in this conversation.)");
    assert.containsNone($, ".o-mail-Message");
});

QUnit.test(
    "message list with a full page of empty messages should load more messages until there are some non-empty",
    async (assert) => {
        // Technical assumptions :
        // - /discuss/channel/messages fetching exactly 30 messages,
        // - empty messages not being displayed
        // - auto-load more being triggered on scroll, not automatically when the 30 first messages are empty
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "General" });
        for (let i = 0; i < 50; i++) {
            pyEnv["mail.message"].create({
                body: "not empty",
                model: "discuss.channel",
                res_id: channelId,
            });
        }
        for (let i = 0; i < 50; i++) {
            pyEnv["mail.message"].create({ model: "discuss.channel", res_id: channelId });
        }
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        // initial load: +30 empty ; (auto) load more: +20 empty +10 non-empty
        assert.containsN($, ".o-mail-Message", 10);
        assert.containsOnce($, "button:contains(Load More)"); // still 40 non-empty
    }
);

QUnit.test(
    "no new messages separator on posting message (some message history)",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            channel_member_ids: [
                Command.create({ message_unread_counter: 0, partner_id: pyEnv.currentPartnerId }),
            ],
            channel_type: "channel",
            name: "General",
        });
        const messageId = pyEnv["mail.message"].create({
            body: "first message",
            model: "discuss.channel",
            res_id: channelId,
        });
        const [memberId] = pyEnv["discuss.channel.member"].search([
            ["channel_id", "=", channelId],
            ["partner_id", "=", pyEnv.currentPartnerId],
        ]);
        pyEnv["discuss.channel.member"].write([memberId], { seen_message_id: messageId });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-mail-Message");
        assert.containsNone($, "hr + span:contains(New messages)");

        await insertText(".o-mail-Composer-input", "hey!");
        await afterNextRender(() => {
            // need to remove focus from text area to avoid set_last_seen_message
            $(".o-mail-Composer-send")[0].focus();
            $(".o-mail-Composer-send")[0].click();
        });
        assert.containsN($, ".o-mail-Message", 2);
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
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 0, partner_id: pyEnv.currentPartnerId }),
        ],
        channel_type: "channel",
        name: "General",
    });
    const messageId = pyEnv["mail.message"].create({
        body: "blah",
        model: "discuss.channel",
        res_id: channelId,
    });
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", pyEnv.currentPartnerId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], { seen_message_id: messageId });
    const { env, openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-Message", "should have an initial message");
    assert.containsNone($, "hr + span:contains(New messages)");

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
    assert.containsN($, ".o-mail-Message", 2);
    assert.containsOnce($, "hr + span:contains(New messages)");
    assert.containsOnce($, ".o-mail-Thread-newMessage ~ .o-mail-Message:contains(hu)");

    $(".o-mail-Composer-input")[0].focus();
    await nextTick();
    assert.containsNone($, "hr + span:contains(New messages)");
});

QUnit.test("no new messages separator on posting message (no message history)", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 0, partner_id: pyEnv.currentPartnerId }),
        ],
        channel_type: "channel",
        name: "General",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-mail-Message");
    assert.containsNone($, "hr + span:contains(New messages)");

    await insertText(".o-mail-Composer-input", "hey!");
    await click(".o-mail-Composer-send");
    assert.containsOnce($, ".o-mail-Message");
    assert.containsNone($, "hr + span:contains(New messages)");
});

QUnit.test("Mention a partner with special character (e.g. apostrophe ')", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "usatyi@example.com",
        name: "Pynya's spokesman",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@");
    await insertText(".o-mail-Composer-input", "Pyn");
    await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
    await nextTick();
    await nextTick();
    await click(".o-mail-Composer-suggestion");
    await click(".o-mail-Composer-send");
    assert.containsOnce(
        $(".o-mail-Message-body"),
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
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId_1 }),
            Command.create({ partner_id: partnerId_2 }),
        ],
    });
    const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@");
    await insertText(".o-mail-Composer-input", "Te");
    await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
    await nextTick();
    await nextTick();
    await click(".o-mail-Composer-suggestion:eq(0)");
    await insertText(".o-mail-Composer-input", "@");
    await insertText(".o-mail-Composer-input", "Te");
    await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
    await nextTick();
    await nextTick();
    await click(".o-mail-Composer-suggestion:eq(1)");
    await click(".o-mail-Composer-send");
    assert.containsOnce($, ".o-mail-Message-body");
    assert.containsOnce(
        $(".o-mail-Message-body"),
        `.o_mail_redirect[data-oe-id="${partnerId_1}"][data-oe-model="res.partner"]:contains("@TestPartner")`
    );
    assert.containsOnce(
        $(".o-mail-Message-body"),
        `.o_mail_redirect[data-oe-id="${partnerId_2}"][data-oe-model="res.partner"]:contains("@TestPartner")`
    );
});

QUnit.test("mention a channel on a second line when the first line contains #", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General good" });
    const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "#blabla\n");
    await insertText(".o-mail-Composer-input", "#");
    await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
    await nextTick();
    await nextTick();
    await click(".o-mail-Composer-suggestion");
    await click(".o-mail-Composer-send");
    assert.containsOnce($(".o-mail-Message-body"), ".o_channel_redirect");
    assert.strictEqual($(".o_channel_redirect").text(), "#General good");
});

QUnit.test(
    "mention a channel when replacing the space after the mention by another char",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "General good" });
        const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
        await openDiscuss(channelId);
        await insertText(".o-mail-Composer-input", "#");
        await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
        await nextTick();
        await nextTick();
        await click(".o-mail-Composer-suggestion");
        const text = $(".o-mail-Composer-input").val();
        $(".o-mail-Composer-input").val(text.slice(0, -1));
        await insertText(".o-mail-Composer-input", ", test");
        await click(".o-mail-Composer-send");
        assert.containsOnce($(".o-mail-Message-body"), ".o_channel_redirect");
        assert.strictEqual($(".o_channel_redirect").text(), "#General good");
    }
);

QUnit.test("mention 2 different channels that have the same name", async (assert) => {
    const pyEnv = await startServer();
    const [channelId_1, channelId_2] = pyEnv["discuss.channel"].create([
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
    const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
    await openDiscuss(channelId_1);
    await insertText(".o-mail-Composer-input", "#");
    await insertText(".o-mail-Composer-input", "m");
    await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
    await nextTick();
    await nextTick();
    await click(".o-mail-Composer-suggestion:eq(0)");
    await insertText(".o-mail-Composer-input", "#");
    await insertText(".o-mail-Composer-input", "m");
    await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
    await nextTick();
    await nextTick();
    await click(".o-mail-Composer-suggestion:eq(1)");
    await click(".o-mail-Composer-send");
    assert.containsOnce($, ".o-mail-Message-body");
    assert.containsOnce(
        $(".o-mail-Message-body"),
        `.o_channel_redirect[data-oe-id="${channelId_1}"][data-oe-model="discuss.channel"]:contains("#my channel")`
    );
    assert.containsOnce(
        $(".o-mail-Message-body"),
        `.o_channel_redirect[data-oe-id="${channelId_2}"][data-oe-model="discuss.channel"]:contains("#my channel")`
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
        const channelId = pyEnv["discuss.channel"].create({
            name: "test",
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId }),
            ],
        });
        const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
        await openDiscuss(channelId);
        await insertText(".o-mail-Composer-input", "email@odoo.com\n");
        await insertText(".o-mail-Composer-input", "@");
        await insertText(".o-mail-Composer-input", "Te");
        await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
        await nextTick();
        await nextTick();
        await click(".o-mail-Composer-suggestion");
        await click(".o-mail-Composer-send");
        assert.containsOnce(
            $(".o-mail-Message-body"),
            `.o_mail_redirect[data-oe-id="${partnerId}"][data-oe-model="res.partner"]:contains("@TestPartner")`
        );
    }
);

QUnit.test("basic rendering of canceled notification", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    const partnerId = pyEnv["res.partner"].create({ name: "Someone" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "email",
        model: "discuss.channel",
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
    assert.containsOnce($, ".o-mail-Message-notification .fa-envelope-o");

    await click(".o-mail-Message-notification");
    assert.containsOnce($, ".o-mail-MessageNotificationPopover");
    assert.containsOnce($, ".o-mail-MessageNotificationPopover .fa-trash-o");
    assert.containsOnce($, ".o-mail-MessageNotificationPopover:contains(Someone)");
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
        const channelId = pyEnv["discuss.channel"].create({
            channel_type: "channel",
            name: "General",
        });
        pyEnv["mail.message"].create([
            {
                body: "not empty",
                model: "discuss.channel",
                res_id: channelId,
            },
        ]);
        const { openDiscuss, env } = await start();
        await openDiscuss(channelId);
        // send a command that leads to receiving a transient message
        await insertText(".o-mail-Composer-input", "/who");
        await click(".o-mail-Composer-send");
        // composer is focused by default, we remove that focus
        $(".o-mail-Composer-input")[0].blur();
        // simulate receiving a message
        await afterNextRender(() =>
            env.services.rpc("/mail/message/post", {
                context: { mockedUserId: userId },
                post_data: { body: "test", message_type: "comment" },
                thread_id: channelId,
                thread_model: "discuss.channel",
            })
        );
        assert.containsN($, ".o-mail-Message", 3);
        assert.containsOnce($, "hr + span:contains(New messages)");
        assert.containsOnce($, ".o-mail-Message[aria-label='Note'] + .o-mail-Thread-newMessage");
    }
);

QUnit.test(
    "composer should be focused automatically after clicking on the send button",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "test" });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await insertText(".o-mail-Composer-input", "Dummy Message");
        await click(".o-mail-Composer-send");
        assert.strictEqual(document.activeElement, $(".o-mail-Composer-input")[0]);
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
        await click(".o-mail-NotificationItem-name");
        assert.containsOnce($, ".o-mail-ChatWindow");
        assert.containsNone($, ".o-mail-ChatWindow-header:contains('(1)')");
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
        assert.containsOnce($, ".o-mail-NotificationItem");
        assert.containsNone($, ".o-mail-ChatWindow");

        await click(".o-mail-NotificationItem");
        assert.containsOnce($, ".o-mail-ChatWindow");
    }
);

QUnit.test("Thread messages are only loaded once", async (assert) => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create([{ name: "General" }, { name: "Sales" }]);
    const { openDiscuss } = await start({
        mockRPC(route, args, originalRPC) {
            if (route === "/discuss/channel/messages") {
                assert.step(`load messages - ${args["channel_id"]}`);
            }
            return originalRPC(route, args);
        },
    });
    pyEnv["mail.message"].create([
        {
            model: "discuss.channel",
            res_id: channelIds[0],
            body: "Message on channel1",
        },
        {
            model: "discuss.channel",
            res_id: channelIds[1],
            body: "Message on channel2",
        },
    ]);
    await openDiscuss();
    await click(".o-mail-DiscussCategoryItem:eq(0)");
    await waitUntil(".o-mail-Message:contains(channel1)");
    await click(".o-mail-DiscussCategoryItem:eq(1)");
    await waitUntil(".o-mail-Message:contains(channel2)");
    await click(".o-mail-DiscussCategoryItem:eq(0)");
    await waitUntil(".o-mail-Message:contains(channel1)");
    assert.verifySteps([`load messages - ${channelIds[0]}`, `load messages - ${channelIds[1]}`]);
});

QUnit.test(
    "Opening thread with needaction messages should mark all messages of thread as read",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "General" });
        const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
        const { env, openDiscuss } = await start({
            mockRPC(route, args) {
                if (args.model === "mail.message" && args.method === "mark_all_as_read") {
                    assert.step("mark-all-messages-as-read");
                    assert.deepEqual(args.args[0], [
                        ["model", "=", "discuss.channel"],
                        ["res_id", "=", channelId],
                    ]);
                }
            },
        });
        await openDiscuss(channelId);
        // ensure focusout is triggered on composers' textarea
        await triggerEvents($(".o-mail-Composer-input")[0], null, ["blur", "focusout"]);
        await click("button:contains(Inbox)");
        const messageId = pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "@Mitchel Admin",
            needaction: true,
            model: "discuss.channel",
            res_id: channelId,
            needaction_partner_ids: [pyEnv.currentPartnerId],
        });
        pyEnv["mail.notification"].create({
            mail_message_id: messageId,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        });
        // simulate receiving a new needaction message
        const [formattedMessage] = await env.services.orm.call("mail.message", "message_format", [
            [messageId],
        ]);
        pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "discuss.channel/new_message", {
            id: channelId,
            message: formattedMessage,
        });
        await waitUntil(".o-mail-DiscussCategoryItem-counter:contains(1)");
        await waitUntil("button:contains(Inbox) .badge:contains(1)");
        await click("button:contains(General)");
        await waitUntil(".o-mail-DiscussCategoryItem-counter", 0);
        await waitUntil("button:contains(Inbox) .badge", 0);
        assert.verifySteps(["mark-all-messages-as-read"]);
    }
);

QUnit.test(
    "[technical] Opening thread without needaction messages should not mark all messages of thread as read",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "General" });
        const { env, openDiscuss } = await start({
            mockRPC(route, args) {
                if (args.model === "mail.message" && args.method === "mark_all_as_read") {
                    assert.step("mark-all-messages-as-read");
                }
            },
        });
        await openDiscuss(channelId);
        await click("button:contains(Inbox)");
        await env.services.rpc("/mail/message/post", {
            post_data: {
                body: "Hello world!",
                attachment_ids: [],
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        });
        await click("button:contains(General)");
        await nextTick();
        assert.verifySteps([]);
    }
);

QUnit.test("can be marked as read while loading", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
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
    const loadDeferred = makeDeferred();
    const { openDiscuss } = await start({
        async mockRPC(route) {
            if (route === "/discuss/channel/messages") {
                await loadDeferred;
            }
        },
    });
    await openDiscuss(undefined, { waitUntilMessagesLoaded: false });
    assert.containsOnce($, ".o-mail-DiscussCategoryItem-counter:contains(1)");
    await click(".o-mail-DiscussCategoryItem:contains(Demo)");
    await afterNextRender(loadDeferred.resolve);
    assert.containsNone($, ".o-mail-DiscussCategoryItem-counter");
});

QUnit.test(
    "New message separator not appearing after showing composer on thread",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["mail.message"].create([
            {
                model: "res.partner",
                res_id: pyEnv.currentPartnerId,
                body: "Message on partner",
            },
            {
                model: "res.partner",
                res_id: pyEnv.currentPartnerId,
                body: "Message on partner",
            },
        ]);
        const { openFormView } = await start();
        await openFormView("res.partner", pyEnv.currentPartnerId);
        assert.containsNone($, ".o-mail-Thread-newMessage");
        await click("button:contains(Log note)");
        assert.containsNone($, ".o-mail-Thread-newMessage");
    }
);
