/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { config as transitionConfig } from "@web/core/transition";
import { makeDeferred, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import {
    assertSteps,
    click,
    contains,
    createFile,
    dragenterFiles,
    focus,
    insertText,
    scroll,
    step,
    triggerEvents,
} from "@web/../tests/utils";
import { patchWebsocketWorkerWithCleanup } from "@bus/../tests/helpers/mock_websocket";

QUnit.module("thread");

QUnit.test("dragover files on thread with composer", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        group_public_id: false,
        name: "General",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    const files = [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text3.txt",
        }),
    ];
    await dragenterFiles(".o-mail-Thread", files);
    await contains(".o-mail-Dropzone");
});

QUnit.test("load more messages from channel (auto-load on scroll)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        group_public_id: false,
        name: "General",
    });
    for (let i = 0; i <= 60; i++) {
        pyEnv["mail.message"].create({
            body: i.toString(),
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains("button", { text: "Load More", before: [".o-mail-Message", { count: 30 }] });
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await scroll(".o-mail-Thread", 0);
    await contains(".o-mail-Message", { count: 60 });
    await contains(".o-mail-Message", { text: "30", after: [".o-mail-Message", { text: "29" }] });
});

QUnit.test("show message subject when subject is not the same as the thread name", async () => {
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
    openDiscuss(channelId);
    await contains(".o-mail-Message", { text: "Subject: Salutations, voyageurnot empty" });
});

QUnit.test("do not show message subject when subject is the same as the thread name", async () => {
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
    openDiscuss(channelId);
    await contains(".o-mail-Message", { text: "not empty" });
    await contains(".o-mail-Message", {
        count: 0,
        text: "Subject: Salutations, voyageurnot empty",
    });
});

QUnit.test("auto-scroll to bottom of thread on load", async () => {
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
    openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 25 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
});

QUnit.test("display day separator before first message of the day", async () => {
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
    openDiscuss(channelId);
    await contains(".o-mail-DateSection");
});

QUnit.test("do not display day separator if all messages of the day are empty", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    pyEnv["mail.message"].create({
        body: "",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Thread", { text: "There are no messages in this conversation." });
    await contains(".o-mail-DateSection", { count: 0 });
});

QUnit.test("scroll position is kept when navigating from one channel to another", async () => {
    const pyEnv = await startServer();
    const channelId_1 = pyEnv["discuss.channel"].create({ name: "channel-1" });
    const channelId_2 = pyEnv["discuss.channel"].create({ name: "channel-2" });
    // Fill both channels with random messages in order for the scrollbar to
    // appear.
    pyEnv["mail.message"].create(
        Array(50)
            .fill(0)
            .map((_, index) => ({
                body: "Non Empty Body ".repeat(25),
                message_type: "comment",
                model: "discuss.channel",
                res_id: index < 20 ? channelId_1 : channelId_2,
            }))
    );
    const { openDiscuss } = await start();
    openDiscuss(channelId_1);
    await contains(".o-mail-Message", { count: 20 });
    const scrollValue1 = $(".o-mail-Thread")[0].scrollHeight / 2;
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await scroll(".o-mail-Thread", scrollValue1);
    await click(".o-mail-DiscussSidebarChannel", { text: "channel-2" });
    await contains(".o-mail-Message", { count: 30 });
    const scrollValue2 = $(".o-mail-Thread")[0].scrollHeight / 3;
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await scroll(".o-mail-Thread", scrollValue2);
    await click(".o-mail-DiscussSidebarChannel", { text: "channel-1" });
    await contains(".o-mail-Message", { count: 20 });
    await contains(".o-mail-Thread", { scroll: scrollValue1 });
    await click(".o-mail-DiscussSidebarChannel", { text: "channel-2" });
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-Thread", { scroll: scrollValue2 });
});

QUnit.test("thread is still scrolling after scrolling up then to bottom", async () => {
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
    openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 20 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await scroll(".o-mail-Thread", $(".o-mail-Thread")[0].scrollHeight / 2);
    await scroll(".o-mail-Thread", "bottom");
    await insertText(".o-mail-Composer-input", "123");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message", { count: 21 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
});

QUnit.test("Can mention other channels in a group-restricted channel", async () => {
    const pyEnv = await startServer();
    const groupId = pyEnv["res.groups"].create({
        name: "Mario Group",
    });
    const [channelId1] = pyEnv["discuss.channel"].create([
        {
            channel_type: "channel",
            group_public_id: groupId,
            name: "Marios",
        },
        {
            channel_type: "channel",
            group_public_id: false,
            name: "Link and Zelda",
        },
    ]);
    const { openDiscuss } = await start();
    openDiscuss(channelId1);
    await insertText(".o-mail-Composer-input", "#");
    await contains(".o-mail-Composer-suggestion", { text: "#Marios" });
    await contains(".o-mail-Composer-suggestion", { text: "#Link and Zelda" });
    await click(".o-mail-Composer-suggestion", { text: "#Link and Zelda" });
    await contains(".o-mail-Composer-input", { value: "#Link and Zelda " });
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-body .o_channel_redirect", { text: "#Link and Zelda" });
});

QUnit.test("mention a channel with space in the name", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General good boy" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "#");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "#General good boy " });
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-body .o_channel_redirect", { text: "#General good boy" });
});

QUnit.test('mention a channel with "&" in the name', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General & good" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "#");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "#General & good " });
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-body .o_channel_redirect", { text: "#General & good" });
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
        await contains(".o_menu_systray i[aria-label='Messages']");
        pyEnv.withUser(userId, () =>
            env.services.rpc("/mail/message/post", {
                post_data: { body: "Hello!", message_type: "comment" },
                thread_id: channelId,
                thread_model: "discuss.channel",
            })
        );
        await contains(".o-mail-Message");
        assert.verifySteps(["rpc:channel_fetch"]);
        await contains(".o-mail-Thread-newMessage hr + span", { text: "New messages" });
        await focus(".o-mail-Composer-input");
        await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });

        assert.verifySteps(["rpc:set_last_seen_message"]);
    }
);

QUnit.test(
    "mark channel as fetched and seen when a new message is loaded if composer is focused [REQUIRE FOCUS]",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({});
        const userId = pyEnv["res.users"].create({ partner_id: partnerId });
        const channelId = pyEnv["discuss.channel"].create({
            name: "test",
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId }),
            ],
        });
        const { env, openDiscuss } = await start({
            async mockRPC(route, args) {
                if (args.method === "channel_fetched" && args.args[0] === channelId) {
                    throw new Error(
                        "'channel_fetched' RPC must not be called for created channel as message is directly seen"
                    );
                } else if (route === "/discuss/channel/set_last_seen_message") {
                    assert.strictEqual(args.channel_id, channelId);
                    assert.step("rpc:set_last_seen_message");
                }
            },
        });
        openDiscuss(channelId);
        await focus(".o-mail-Composer-input");
        // simulate receiving a message
        await pyEnv.withUser(userId, () =>
            env.services.rpc("/mail/message/post", {
                post_data: { body: "<p>Some new message</p>", message_type: "comment" },
                thread_id: channelId,
                thread_model: "discuss.channel",
            })
        );
        await contains(".o-mail-Message");
        assert.verifySteps(["rpc:set_last_seen_message"]);
    }
);

QUnit.test(
    "should scroll to bottom on receiving new message if the list is initially scrolled to bottom (asc order)",
    async () => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Foreigner partner" });
        const userId = pyEnv["res.users"].create({ name: "Foreigner user", partner_id: partnerId });
        const channelId = pyEnv["discuss.channel"].create({
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId }),
            ],
        });
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
        await contains(".o-mail-Message", { count: 11 });
        await contains(".o-mail-Thread", { scroll: "bottom" });
        // simulate receiving a message
        pyEnv.withUser(userId, () =>
            env.services.rpc("/mail/message/post", {
                post_data: { body: "hello", message_type: "comment" },
                thread_id: channelId,
                thread_model: "discuss.channel",
            })
        );
        await contains(".o-mail-Message", { count: 12 });
        await contains(".o-mail-Thread", { scroll: "bottom" });
    }
);

QUnit.test(
    "should not scroll on receiving new message if the list is initially scrolled anywhere else than bottom (asc order)",
    async () => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Foreigner partner" });
        const userId = pyEnv["res.users"].create({ name: "Foreigner user", partner_id: partnerId });
        const channelId = pyEnv["discuss.channel"].create({
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId }),
            ],
        });
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
        await contains(".o-mail-Message", { count: 11 });
        await contains(".o-mail-Thread", { scroll: "bottom" });
        await scroll(".o-mail-Thread", 0);
        // simulate receiving a message
        pyEnv.withUser(userId, () =>
            env.services.rpc("/mail/message/post", {
                post_data: { body: "hello", message_type: "comment" },
                thread_id: channelId,
                thread_model: "discuss.channel",
            })
        );
        await contains(".o-mail-Message", { count: 12 });
        await contains(".o-mail-ChatWindow .o-mail-Thread", { scroll: 0 });
    }
);

QUnit.test("can join public channel from channel mention link", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Demo" });
    const partnerId = pyEnv["res.partner"].create({
        name: "Demo",
        user_ids: [userId],
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Channel",
        channel_member_ids: [Command.create({ partner_id: partnerId })],
        channel_type: "channel",
        group_public_id: false,
    });
    pyEnv["mail.message"].create({
        model: "res.partner",
        message_type: "comment",
        body: `<p><a class="o_channel_redirect" href="#" data-oe-model="discuss.channel" data-oe-id="${channelId}">#Channel</a></p>`, // simulated channel mention in message
        author_id: partnerId,
        res_id: partnerId,
    });
    patchWebsocketWorkerWithCleanup({
        _sendToServer({ event_name, data }) {
            if (event_name === "subscribe") {
                const channels = data.channels.filter((subscription) =>
                    subscription.startsWith("discuss.channel_")
                );
                step(`subscribe - [${channels.join(",")}]`);
            }
        },
    });
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Message-body a", { text: "#Channel" });
    await contains(".o-mail-ChatWindow-header", { text: "Channel" });
    await assertSteps([`subscribe - [discuss.channel_${channelId}]`]);
});

QUnit.test("show empty placeholder when thread contains no message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Thread", { text: "There are no messages in this conversation." });
    await contains(".o-mail-Message", { count: 0 });
});

QUnit.test("show empty placeholder when thread contains only empty messages", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({ model: "discuss.channel", res_id: channelId });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Thread", { text: "There are no messages in this conversation." });
    await contains(".o-mail-Message", { count: 0 });
});

QUnit.test(
    "message list with a full page of empty messages should load more messages until there are some non-empty",
    async () => {
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
        openDiscuss(channelId);
        // initial load: +30 empty ; (auto) load more: +20 empty +10 non-empty
        await contains(".o-mail-Message", { count: 10 });
        await contains("button", { text: "Load More" }); // still 40 non-empty
    }
);

QUnit.test("no new messages separator on posting message (some message history)", async () => {
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
    openDiscuss(channelId);
    await contains(".o-mail-Message");
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });
    await insertText(".o-mail-Composer-input", "hey!");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message", { count: 2 });
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });
});

QUnit.test("new messages separator on receiving new message [REQUIRE FOCUS]", async () => {
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
            Command.create({ partner_id: partnerId }),
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
    openDiscuss(channelId);
    await contains(".o-mail-Message");
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });

    $(".o-mail-Composer-input")[0].blur();
    // simulate receiving a message
    pyEnv.withUser(userId, () =>
        env.services.rpc("/mail/message/post", {
            post_data: { body: "hu", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message", { count: 2 });
    await contains(".o-mail-Thread-newMessage hr + span", { text: "New messages" });
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", { text: "hu" });
    await focus(".o-mail-Composer-input");
    await nextTick();
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });
});

QUnit.test("no new messages separator on posting message (no message history)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 0, partner_id: pyEnv.currentPartnerId }),
        ],
        channel_type: "channel",
        name: "General",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Composer-input");
    await contains(".o-mail-Message", { count: 0 });
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });

    await insertText(".o-mail-Composer-input", "hey!");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message");
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });
});

QUnit.test("Mention a partner with special character (e.g. apostrophe ')", async () => {
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
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@");
    await insertText(".o-mail-Composer-input", "Pyn");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "@Pynya's spokesman " });
    await click(".o-mail-Composer-send:enabled");
    await contains(
        `.o-mail-Message-body .o_mail_redirect[data-oe-id="${partnerId}"][data-oe-model="res.partner"]`,
        { text: "@Pynya's spokesman" }
    );
});

QUnit.test("mention 2 different partners that have the same name", async () => {
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
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@Te");
    await click(":nth-child(1 of .o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "@TestPartner " });
    await insertText(".o-mail-Composer-input", "@Te");
    await click(":nth-child(2 of .o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "@TestPartner @TestPartner " });
    await click(".o-mail-Composer-send:enabled");
    await contains(
        `.o-mail-Message-body .o_mail_redirect[data-oe-id="${partnerId_1}"][data-oe-model="res.partner"]`,
        { text: "@TestPartner" }
    );
    await contains(
        `.o-mail-Message-body .o_mail_redirect[data-oe-id="${partnerId_2}"][data-oe-model="res.partner"]`,
        { text: "@TestPartner" }
    );
});

QUnit.test("mention a channel on a second line when the first line contains #", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General good" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "#blabla\n#");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "#blabla\n#General good " });
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-body .o_channel_redirect", { text: "#General good" });
});

QUnit.test(
    "mention a channel when replacing the space after the mention by another char",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "General good" });
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await insertText(".o-mail-Composer-input", "#");
        await click(".o-mail-Composer-suggestion");
        await contains(".o-mail-Composer-input", { value: "#General good " });
        const text = $(".o-mail-Composer-input").val();
        $(".o-mail-Composer-input").val(text.slice(0, -1));
        await insertText(".o-mail-Composer-input", ", test");
        await click(".o-mail-Composer-send:enabled");
        await contains(".o-mail-Message-body .o_channel_redirect", { text: "#General good" });
    }
);

QUnit.test("mention 2 different channels that have the same name", async () => {
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
    const { openDiscuss } = await start();
    openDiscuss(channelId_1);
    await insertText(".o-mail-Composer-input", "#m");
    await click(":nth-child(1 of .o-mail-Composer-suggestion)");
    await contains(".o-mail-Composer-input", { value: "#my channel " });
    await insertText(".o-mail-Composer-input", "#m");
    await click(":nth-child(2 of .o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "#my channel #my channel " });
    await click(".o-mail-Composer-send:enabled");
    await contains(
        `.o-mail-Message-body .o_channel_redirect[data-oe-id="${channelId_1}"][data-oe-model="discuss.channel"]`,
        { text: "#my channel" }
    );
    await contains(
        `.o-mail-Message-body .o_channel_redirect[data-oe-id="${channelId_2}"][data-oe-model="discuss.channel"]`,
        { text: "#my channel" }
    );
});

QUnit.test(
    "Post a message containing an email address followed by a mention on another line",
    async () => {
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
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await insertText(".o-mail-Composer-input", "email@odoo.com\n@Te");
        await click(".o-mail-Composer-suggestion");
        await contains(".o-mail-Composer-input", { value: "email@odoo.com\n@TestPartner " });
        await click(".o-mail-Composer-send:enabled");
        await contains(
            `.o-mail-Message-body .o_mail_redirect[data-oe-id="${partnerId}"][data-oe-model="res.partner"]`,
            { text: "@TestPartner" }
        );
    }
);

QUnit.test("basic rendering of canceled notification", async () => {
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
    openDiscuss(channelId);
    await contains(".o-mail-Message-notification .fa-envelope-o");

    await click(".o-mail-Message-notification");
    await contains(".o-mail-MessageNotificationPopover");
    await contains(".o-mail-MessageNotificationPopover .fa-trash-o");
    await contains(".o-mail-MessageNotificationPopover", { text: "Someone" });
});

QUnit.test(
    "first unseen message should be directly preceded by the new message separator if there is a transient message just before it while composer is not focused [REQUIRE FOCUS]",
    async () => {
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
            channel_member_ids: [
                Command.create({ partner_id: partnerId }),
                Command.create({ partner_id: pyEnv.currentPartnerId }),
            ],
        });
        pyEnv["mail.message"].create([
            {
                body: "not empty",
                model: "discuss.channel",
                res_id: channelId,
            },
        ]);
        const { openDiscuss, env } = await start();
        openDiscuss(channelId);
        // send a command that leads to receiving a transient message
        await insertText(".o-mail-Composer-input", "/who");
        await click(".o-mail-Composer-send:enabled");
        await contains(".o-mail-Message", { count: 2 });
        // composer is focused by default, we remove that focus
        $(".o-mail-Composer-input")[0].blur();
        // simulate receiving a message
        pyEnv.withUser(userId, () =>
            env.services.rpc("/mail/message/post", {
                post_data: { body: "test", message_type: "comment" },
                thread_id: channelId,
                thread_model: "discuss.channel",
            })
        );
        await contains(".o-mail-Message", { count: 3 });
        await contains(".o-mail-Thread-newMessage hr + span", { text: "New messages" });
        await contains(".o-mail-Message[aria-label='Note'] + .o-mail-Thread-newMessage");
    }
);

QUnit.test(
    "composer should be focused automatically after clicking on the send button",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "test" });
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await insertText(".o-mail-Composer-input", "Dummy Message");
        await click(".o-mail-Composer-send:enabled");
        await contains(".o-mail-Composer-input:focus");
    }
);

QUnit.test("chat window header should not have unread counter for non-channel thread", async () => {
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
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow-counter", { count: 0, text: "1" });
});

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
        await contains(".o-mail-NotificationItem");
        await contains(".o-mail-ChatWindow", { count: 0 });

        await click(".o-mail-NotificationItem");
        await contains(".o-mail-ChatWindow");
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
    openDiscuss();
    await click(":nth-child(1 of .o-mail-DiscussSidebarChannel");
    await contains(".o-mail-Message-content", { text: "Message on channel1" });
    await click(":nth-child(2 of .o-mail-DiscussSidebarChannel)");
    await contains(".o-mail-Message-content", { text: "Message on channel2" });
    await click(":nth-child(1 of .o-mail-DiscussSidebarChannel)");
    await contains(".o-mail-Message-content", { text: "Message on channel1" });
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
        openDiscuss(channelId);
        await contains(".o-mail-Composer-input");
        await triggerEvents(".o-mail-Composer-input", ["blur", "focusout"]);
        await click("button", { text: "Inbox" });
        await contains("h4", { text: "Congratulations, your inbox is empty" });
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
        pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.message/inbox", formattedMessage);
        await contains("button", { text: "Inbox", contains: [".badge", { text: "1" }] });
        await click("button", { text: "General" });
        await contains(".o-discuss-badge", { count: 0 });
        await contains("button", { text: "Inbox", contains: [".badge", { count: 0 }] });
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
        openDiscuss(channelId);
        await click("button", { text: "Inbox" });
        await env.services.rpc("/mail/message/post", {
            post_data: {
                body: "Hello world!",
                attachment_ids: [],
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        });
        await click("button", { text: "General" });
        await nextTick();
        assert.verifySteps([]);
    }
);

QUnit.test("can be marked as read while loading", async function () {
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
    openDiscuss(undefined);
    await contains(".o-discuss-badge", { text: "1" });
    await click(".o-mail-DiscussSidebarChannel", { text: "Demo" });
    loadDeferred.resolve();
    await contains(".o-discuss-badge", { count: 0 });
});

QUnit.test("New message separator not appearing after showing composer on thread", async () => {
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
    openFormView("res.partner", pyEnv.currentPartnerId);
    await contains("button", { text: "Log note" });
    await contains(".o-mail-Thread-newMessage", { count: 0 });
    await click("button", { text: "Log note" });
    await contains(".o-mail-Thread-newMessage", { count: 0 });
});

QUnit.test("Transient messages are added at the end of the thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Dummy Message");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message");
    await insertText(".o-mail-Composer-input", "/help");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message", { count: 2 });
    await contains(":nth-child(1 of .o-mail-Message)", { text: "Mitchell Admin" });
    await contains(":nth-child(2 of .o-mail-Message)", { text: "OdooBot" });
});
