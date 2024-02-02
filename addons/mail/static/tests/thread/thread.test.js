/** @odoo-module */

import { expect, test } from "@odoo/hoot";

import { rpc } from "@web/core/network/rpc";

import { config as transitionConfig } from "@web/core/transition";
import {
    assertSteps,
    click,
    contains,
    createFile,
    dragenterFiles,
    insertText,
    openDiscuss,
    openFormView,
    start,
    startServer,
    step,
    triggerEvents,
} from "../mail_test_helpers";
import { Command, constants, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Deferred, tick } from "@odoo/hoot-mock";

test.skip("dragover files on thread with composer", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        group_public_id: false,
        name: "General",
    });
    await start();
    await openDiscuss(channelId);
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

test.skip("load more messages from channel (auto-load on scroll)", async () => {
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
    await start();
    await openDiscuss(channelId);
    await contains("button", { text: "Load More", before: [".o-mail-Message", { count: 30 }] });
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await scroll(".o-mail-Thread", 0);
    await contains(".o-mail-Message", { count: 60 });
    await contains(".o-mail-Message", { text: "30", after: [".o-mail-Message", { text: "29" }] });
});

test.skip("show message subject when subject is not the same as the thread name", async () => {
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { text: "Subject: Salutations, voyageurnot empty" });
});

test.skip("do not show message subject when subject is the same as the thread name", async () => {
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { text: "not empty" });
    await contains(".o-mail-Message", {
        count: 0,
        text: "Subject: Salutations, voyageurnot empty",
    });
});

test.skip("auto-scroll to bottom of thread on load", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    for (let i = 1; i <= 25; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 25 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
});

test.skip("display day separator before first message of the day", async () => {
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DateSection");
});

test.skip("do not display day separator if all messages of the day are empty", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    pyEnv["mail.message"].create({
        body: "",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread", { text: "There are no messages in this conversation." });
    await contains(".o-mail-DateSection", { count: 0 });
});

test.skip("scroll position is kept when navigating from one channel to another", async () => {
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
    await start();
    await openDiscuss(channelId_1);
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

test.skip("thread is still scrolling after scrolling up then to bottom", async () => {
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 20 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await scroll(".o-mail-Thread", $(".o-mail-Thread")[0].scrollHeight / 2);
    await scroll(".o-mail-Thread", "bottom");
    await insertText(".o-mail-Composer-input", "123");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message", { count: 21 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
});

test.skip("mention a channel with space in the name", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General good boy" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "#");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "#General good boy " });
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-body .o_channel_redirect", { text: "#General good boy" });
});

test.skip('mention a channel with "&" in the name', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General & good" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "#");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "#General & good " });
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-body .o_channel_redirect", { text: "#General & good" });
});

test.skip("mark channel as fetched when a new message is loaded and as seen when focusing composer [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "fred@example.com",
        name: "Fred",
    });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: constants.PARTNER_ID }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    onRpc((route, args) => {
        if (route === "/mail/action" && args.init_messaging) {
            step(`/mail/action - ${JSON.stringify(args)}`);
        }
        if (route === "/web/dataset/call_kw/discuss.channel/channel_fetched") {
            expect(args.args[0][0]).toBe(channelId);
            expect(args.model).toBe("discuss.channel");
            step("rpc:channel_fetch");
        }
        if (route === "/discuss/channel/set_last_seen_message") {
            expect(args.channel_id).toBe(channelId);
            step("rpc:set_last_seen_message");
        }
    });
    await start();
    await contains(".o_menu_systray i[aria-label='Messages']");
    await assertSteps([
        `/mail/action - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: constants.USER_ID },
        })}`,
    ]);
    // send after init_messaging because bus subscription is done after init_messaging
    pyEnv.withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello!", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message");
    await assertSteps(["rpc:channel_fetch"]);
    await contains(".o-mail-Thread-newMessage hr + span", { text: "New messages" });
    await focus(".o-mail-Composer-input");
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });
    await assertSteps(["rpc:set_last_seen_message"]);
});

test.skip("mark channel as fetched and seen when a new message is loaded if composer is focused [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: constants.PARTNER_ID }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    onRpc((route, args) => {
        if (route === "/web/dataset/call_kw/discuss.channel/channel_fetched") {
            if (args.args[0] === channelId) {
                throw new Error(
                    "'channel_fetched' RPC must not be called for created channel as message is directly seen"
                );
            }
        }
        if (route === "/discuss/channel/set_last_seen_message") {
            expect(args.channel_id).toBe(channelId);
            expect.step("rpc:set_last_seen_message");
        }
    });
    await start();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-input");
    // simulate receiving a message
    await pyEnv.withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "<p>Some new message</p>", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message");
    expect(["rpc:set_last_seen_message"]).toVerifySteps();
});

test.skip("should scroll to bottom on receiving new message if the list is initially scrolled to bottom (asc order)", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Foreigner partner" });
    const userId = pyEnv["res.users"].create({ name: "Foreigner user", partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: constants.PARTNER_ID }),
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
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-Message", { count: 11 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
    // simulate receiving a message
    pyEnv.withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hello", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message", { count: 12 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
});

test.skip("should not scroll on receiving new message if the list is initially scrolled anywhere else than bottom (asc order)", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Foreigner partner" });
    const userId = pyEnv["res.users"].create({ name: "Foreigner user", partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: constants.PARTNER_ID }),
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
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-Message", { count: 11 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await scroll(".o-mail-Thread", 0);
    // simulate receiving a message
    pyEnv.withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hello", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message", { count: 12 });
    await contains(".o-mail-ChatWindow .o-mail-Thread", { scroll: 0 });
});

test.skip("show empty placeholder when thread contains no message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread", { text: "There are no messages in this conversation." });
    await contains(".o-mail-Message", { count: 0 });
});

test.skip("show empty placeholder when thread contains only empty messages", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({ model: "discuss.channel", res_id: channelId });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread", { text: "There are no messages in this conversation." });
    await contains(".o-mail-Message", { count: 0 });
});

test.skip("message list with a full page of empty messages should load more messages until there are some non-empty", async () => {
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
    await start();
    await openDiscuss(channelId);
    // initial load: +30 empty ; (auto) load more: +20 empty +10 non-empty
    await contains(".o-mail-Message", { count: 10 });
    await contains("button", { text: "Load More" }); // still 40 non-empty
});

test.skip("no new messages separator on posting message (some message history)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 0, partner_id: constants.PARTNER_ID }),
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
        ["partner_id", "=", constants.PARTNER_ID],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], { seen_message_id: messageId });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });
    await insertText(".o-mail-Composer-input", "hey!");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message", { count: 2 });
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });
});

test.skip("new messages separator on receiving new message [REQUIRE FOCUS]", async () => {
    patchWithCleanup(transitionConfig, { disabled: true });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Foreigner partner" });
    const userId = pyEnv["res.users"].create({
        name: "Foreigner user",
        partner_id: partnerId,
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 0, partner_id: constants.PARTNER_ID }),
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
        ["partner_id", "=", constants.PARTNER_ID],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], { seen_message_id: messageId });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });

    $(".o-mail-Composer-input")[0].blur();
    // simulate receiving a message
    pyEnv.withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hu", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message", { count: 2 });
    await contains(".o-mail-Thread-newMessage hr + span", { text: "New messages" });
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", { text: "hu" });
    await focus(".o-mail-Composer-input");
    await tick();
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });
});

test.skip("no new messages separator on posting message (no message history)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 0, partner_id: constants.PARTNER_ID }),
        ],
        channel_type: "channel",
        name: "General",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input");
    await contains(".o-mail-Message", { count: 0 });
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });
    await insertText(".o-mail-Composer-input", "hey!");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message");
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });
});

test.skip("Mention a partner with special character (e.g. apostrophe ')", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "usatyi@example.com",
        name: "Pynya's spokesman",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: constants.PARTNER_ID }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
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

test.skip("mention 2 different partners that have the same name", async () => {
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
            Command.create({ partner_id: constants.PARTNER_ID }),
            Command.create({ partner_id: partnerId_1 }),
            Command.create({ partner_id: partnerId_2 }),
        ],
    });
    await start();
    await openDiscuss(channelId);
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

test.skip("mention a channel on a second line when the first line contains #", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General good" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "#blabla\n#");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "#blabla\n#General good " });
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-body .o_channel_redirect", { text: "#General good" });
});

test.skip("mention a channel when replacing the space after the mention by another char", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General good" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "#");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "#General good " });
    const text = $(".o-mail-Composer-input").val();
    $(".o-mail-Composer-input").val(text.slice(0, -1));
    await insertText(".o-mail-Composer-input", ", test");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-body .o_channel_redirect", { text: "#General good" });
});

test.skip("mention 2 different channels that have the same name", async () => {
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
    await start();
    await openDiscuss(channelId_1);
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

test.skip("Post a message containing an email address followed by a mention on another line", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: constants.PARTNER_ID }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "email@odoo.com\n@Te");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "email@odoo.com\n@TestPartner " });
    await click(".o-mail-Composer-send:enabled");
    await contains(
        `.o-mail-Message-body .o_mail_redirect[data-oe-id="${partnerId}"][data-oe-model="res.partner"]`,
        { text: "@TestPartner" }
    );
});

test.skip("basic rendering of canceled notification", async () => {
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message-notification .fa-envelope-o");
    await click(".o-mail-Message-notification");
    await contains(".o-mail-MessageNotificationPopover");
    await contains(".o-mail-MessageNotificationPopover .fa-trash-o");
    await contains(".o-mail-MessageNotificationPopover", { text: "Someone" });
});

test.skip("first unseen message should be directly preceded by the new message separator if there is a transient message just before it while composer is not focused [REQUIRE FOCUS]", async () => {
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
            Command.create({ partner_id: constants.PARTNER_ID }),
        ],
    });
    pyEnv["mail.message"].create([
        {
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        },
    ]);
    await start();
    await openDiscuss(channelId);
    // send a command that leads to receiving a transient message
    await insertText(".o-mail-Composer-input", "/who");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message", { count: 2 });
    // composer is focused by default, we remove that focus
    $(".o-mail-Composer-input")[0].blur();
    // simulate receiving a message
    pyEnv.withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "test", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message", { count: 3 });
    await contains(".o-mail-Thread-newMessage hr + span", { text: "New messages" });
    await contains(".o-mail-Message[aria-label='Note'] + .o-mail-Thread-newMessage");
});

test.skip("composer should be focused automatically after clicking on the send button", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Dummy Message");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Composer-input:focus");
});

test.skip("chat window header should not have unread counter for non-channel thread", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "test" });
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "not empty",
        model: "res.partner",
        needaction: true,
        needaction_partner_ids: [constants.PARTNER_ID],
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: constants.PARTNER_ID,
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow-counter", { count: 0, text: "1" });
});

test.skip("[technical] opening a non-channel chat window should not call channel_fold", async () => {
    // channel_fold should not be called when opening non-channels in chat
    // window, because there is no server sync of fold state for them.
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "test" });
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "not empty",
        model: "res.partner",
        needaction: true,
        needaction_partner_ids: [constants.PARTNER_ID],
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: constants.PARTNER_ID,
    });
    onRpc("/discuss/channel/fold", (route, args) => {
        const message = "should not call channel_fold when opening a non-channel chat window";
        expect.step(message);
        console.error(message);
        throw Error(message);
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
});

test.skip("Thread messages are only loaded once", async () => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create([{ name: "General" }, { name: "Sales" }]);
    onRpc((route, args) => {
        if (route === "/discuss/channel/messages") {
            expect.step(`load messages - ${args["channel_id"]}`);
        }
    });
    await start();
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
    await click(":nth-child(1 of .o-mail-DiscussSidebarChannel");
    await contains(".o-mail-Message-content", { text: "Message on channel1" });
    await click(":nth-child(2 of .o-mail-DiscussSidebarChannel)");
    await contains(".o-mail-Message-content", { text: "Message on channel2" });
    await click(":nth-child(1 of .o-mail-DiscussSidebarChannel)");
    await contains(".o-mail-Message-content", { text: "Message on channel1" });
    expect([
        `load messages - ${channelIds[0]}`,
        `load messages - ${channelIds[1]}`,
    ]).toVerifySteps();
});

test.skip("Opening thread with needaction messages should mark all messages of thread as read", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    onRpc((route, args) => {
        if (route === "/web/dataset/call_kw/mail.message/mark_all_as_read") {
            expect.step("mark-all-messages-as-read");
            expect(args.args[0]).toEqual([
                ["model", "=", "discuss.channel"],
                ["res_id", "=", channelId],
            ]);
        }
    });
    const { env } = await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input");
    await triggerEvents(".o-mail-Composer-input", ["blur", "focusout"]);
    await click("button", { text: "Inbox" });
    await contains("h4", { text: "Your inbox is empty" });
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "@Mitchel Admin",
        needaction: true,
        model: "discuss.channel",
        res_id: channelId,
        needaction_partner_ids: [constants.PARTNER_ID],
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: constants.PARTNER_ID,
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
    expect(["mark-all-messages-as-read"]).toVerifySteps();
});

test.skip("[technical] Opening thread without needaction messages should not mark all messages of thread as read", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    onRpc((route) => {
        if (route === "/web/dataset/call_kw/mail.message/mark_all_as_read") {
            expect.step("mark-all-messages-as-read");
        }
    });
    await start();
    await openDiscuss(channelId);
    await click("button", { text: "Inbox" });
    await rpc("/mail/message/post", {
        post_data: {
            body: "Hello world!",
            attachment_ids: [],
        },
        thread_id: channelId,
        thread_model: "discuss.channel",
    });
    await click("button", { text: "General" });
    await tick();
    expect([]).toVerifySteps();
});

test.skip("can be marked as read while loading", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 1, partner_id: constants.PARTNER_ID }),
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
    const loadDeferred = new Deferred();
    onRpc(async (route) => {
        if (route === "/discuss/channel/messages") {
            await loadDeferred;
        }
    });
    await start();
    await openDiscuss(undefined);
    await contains(".o-discuss-badge", { text: "1" });
    await click(".o-mail-DiscussSidebarChannel", { text: "Demo" });
    loadDeferred.resolve();
    await contains(".o-discuss-badge", { count: 0 });
});

test.skip("New message separator not appearing after showing composer on thread", async () => {
    const pyEnv = await startServer();
    pyEnv["mail.message"].create([
        {
            model: "res.partner",
            res_id: constants.PARTNER_ID,
            body: "Message on partner",
        },
        {
            model: "res.partner",
            res_id: constants.PARTNER_ID,
            body: "Message on partner",
        },
    ]);
    await start();
    await openFormView("res.partner", constants.PARTNER_ID);
    await contains("button", { text: "Log note" });
    await contains(".o-mail-Thread-newMessage", { count: 0 });
    await click("button", { text: "Log note" });
    await contains(".o-mail-Thread-newMessage", { count: 0 });
});

test.skip("Transient messages are added at the end of the thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Dummy Message");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message");
    await insertText(".o-mail-Composer-input", "/help");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message", { count: 2 });
    await contains(":nth-child(1 of .o-mail-Message)", { text: "Mitchell Admin" });
    await contains(":nth-child(2 of .o-mail-Message)", { text: "OdooBot" });
});
