import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    dragenterFiles,
    focus,
    insertText,
    isInViewportOf,
    onRpcBefore,
    openDiscuss,
    openFormView,
    scroll,
    start,
    startServer,
    step,
    triggerEvents,
} from "@mail/../tests/mail_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { describe, expect, test } from "@odoo/hoot";
import { queryFirst, queryValue } from "@odoo/hoot-dom";
import { Deferred, mockDate, tick } from "@odoo/hoot-mock";
import { Command, makeKwArgs, onRpc, serverState, withUser } from "@web/../tests/web_test_helpers";

import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineMailModels();

test("dragover files on thread with composer", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        group_public_id: false,
        name: "General",
    });
    const text3 = new File(["hello, world"], "text3.txt", { type: "text/plain" });
    await start();
    await openDiscuss(channelId);
    await dragenterFiles(".o-mail-Thread", [text3]);
    await contains(".o-Dropzone");
});

test("load more messages from channel (auto-load on scroll)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        group_public_id: false,
        name: "General",
    });
    let newestMessageId;
    for (let i = 0; i <= 60; i++) {
        newestMessageId = pyEnv["mail.message"].create({
            body: i.toString(),
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const [selfMember] = pyEnv["discuss.channel.member"].search_read([
        ["partner_id", "=", serverState.partnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.member"].write([selfMember.id], {
        new_message_separator: newestMessageId + 1,
    });
    await start();
    await openDiscuss(channelId);
    await contains("button", { text: "Load More", before: [".o-mail-Message", { count: 30 }] });
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await scroll(".o-mail-Thread", 0);
    await contains(".o-mail-Message", { count: 60 });
    await contains(".o-mail-Message", { text: "30", after: [".o-mail-Message", { text: "29" }] });
});

test("show message subject when subject is not the same as the thread name", async () => {
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

test("do not show message subject when subject is the same as the thread name", async () => {
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

test("auto-scroll to last read message on thread load", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messageIds = [];
    for (let i = 0; i <= 200; i++) {
        messageIds.push(
            pyEnv["mail.message"].create({
                body: `message ${i}`,
                model: "discuss.channel",
                res_id: channelId,
            })
        );
    }
    const [selfMemberId] = pyEnv["discuss.channel.member"].search([
        ["partner_id", "=", serverState.partnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.member"].write([selfMemberId], {
        new_message_separator: messageIds[100],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", { text: "message 100" });
    await isInViewportOf(".o-mail-Message:contains(message 100)", ".o-mail-Thread");
});

test("display day separator before first message of the day", async () => {
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

test("do not display day separator if all messages of the day are empty", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    pyEnv["mail.message"].create({
        body: "",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread", { text: "The conversation is empty." });
    await contains(".o-mail-DateSection", { count: 0 });
});

test("scroll position is kept when navigating from one channel to another [CAN FAIL DUE TO WINDOW SIZE]", async () => {
    mockDate("2023-01-03 12:00:00");
    const pyEnv = await startServer();
    const channelId_1 = pyEnv["discuss.channel"].create({
        name: "channel-1",
        channel_type: "channel",
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_interest_dt: "2021-01-03 10:00:00",
            }),
        ],
    });
    const channelId_2 = pyEnv["discuss.channel"].create({
        name: "channel-2",
        channel_type: "channel",
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_interest_dt: "2021-01-03 10:00:00",
            }),
        ],
    });
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
    const scrollValue1 = queryFirst(".o-mail-Thread").scrollHeight / 2;
    await contains(".o-mail-Thread", { scroll: 0 });
    await tick(); // wait for the scroll to first unread to complete
    await scroll(".o-mail-Thread", scrollValue1);
    await click(".o-mail-DiscussSidebarChannel", { text: "channel-2" });
    await contains(".o-mail-Message", { count: 30 });
    const scrollValue2 = queryFirst(".o-mail-Thread").scrollHeight / 3;
    await contains(".o-mail-Thread", { scroll: 0 });
    await tick(); // wait for the scroll to first unread to complete
    await scroll(".o-mail-Thread", scrollValue2);
    await click(".o-mail-DiscussSidebarChannel", { text: "channel-1" });
    await contains(".o-mail-Message", { count: 20 });
    await contains(".o-mail-Thread", { scroll: scrollValue1 });
    await click(".o-mail-DiscussSidebarChannel", { text: "channel-2" });
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-Thread", { scroll: scrollValue2 });
});

test("thread is still scrolling after scrolling up then to bottom", async () => {
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
    await contains(".o-mail-Thread", { scroll: 0 });
    await tick(); // wait for the scroll to first unread to complete
    await scroll(".o-mail-Thread", queryFirst(".o-mail-Thread").scrollHeight / 2);
    await scroll(".o-mail-Thread", "bottom");
    await insertText(".o-mail-Composer-input", "123");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message", { count: 21 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
});

test("mention a channel with space in the name", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General good boy" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "#");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "#General good boy " });
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-body .o_channel_redirect", { text: "General good boy" });
});

test('mention a channel with "&" in the name', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General & good" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "#");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "#General & good " });
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-body .o_channel_redirect", { text: "General & good" });
});

test("mark channel as fetched when a new message is loaded", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "fred@example.com",
        name: "Fred",
    });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ fold_state: "open", partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    onRpcBefore("/mail/data", (args) => {
        if (args.init_messaging) {
            step(`/mail/data - ${JSON.stringify(args)}`);
        }
    });
    onRpcBefore("/discuss/channel/mark_as_read", (args) => {
        expect(args.channel_id).toBe(channelId);
        step("rpc:mark_as_read");
    });
    onRpc("discuss.channel", "channel_fetched", ({ args }) => {
        expect(args[0][0]).toBe(channelId);
        step("rpc:channel_fetch");
    });
    await start();
    await contains(".o_menu_systray i[aria-label='Messages']");
    await assertSteps([
        `/mail/data - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: serverState.userId, allowed_company_ids: [1] },
        })}`,
    ]);
    // send after init_messaging because bus subscription is done after init_messaging
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello!", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message");
    await assertSteps(["rpc:channel_fetch"]);
    await contains(".o-mail-Thread-newMessage hr + span", { text: "New" });
    await focus(".o-mail-Composer-input");
    await assertSteps(["rpc:mark_as_read"]);
});

test.tags("focus required");
test("mark channel as fetched when a new message is loaded and thread is focused", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    onRpc("/discuss/channel/messages", () => step("/discuss/channel/messages"));
    onRpcBefore("/discuss/channel/mark_as_read", (args) => {
        expect(args.channel_id).toBe(channelId);
        step("rpc:mark_as_read");
    });
    onRpc("discuss.channel", "channel_fetched", ({ args }) => {
        if (args[0] === channelId) {
            throw new Error(
                "'channel_fetched' RPC must not be called for created channel as message is directly seen"
            );
        }
    });
    await start();
    await openDiscuss(channelId);
    await assertSteps(["/discuss/channel/messages"]);
    await click(".o-mail-Composer");
    // simulate receiving a message
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "<p>Some new message</p>", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message");
    await assertSteps(["rpc:mark_as_read"]);
});

test("should scroll to bottom on receiving new message if the list is initially scrolled to bottom (asc order)", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Foreigner partner" });
    const userId = pyEnv["res.users"].create({ name: "Foreigner user", partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
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
    await tick(); // wait for the scroll to first unread to complete
    await scroll(".o-mail-Thread", "bottom");
    await contains(".o-mail-Thread", { scroll: "bottom" });
    // simulate receiving a message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hello", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message", { count: 12 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
});

test("should not scroll on receiving new message if the list is initially scrolled anywhere else than bottom (asc order)", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Foreigner partner" });
    const userId = pyEnv["res.users"].create({ name: "Foreigner user", partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
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
    await contains(".o-mail-Thread", { scroll: 0 });
    // simulate receiving a message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hello", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message", { count: 12 });
    await contains(".o-mail-ChatWindow .o-mail-Thread", { scroll: 0 });
});

test("show empty placeholder when thread contains no message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread", { text: "The conversation is empty." });
    await contains(".o-mail-Message", { count: 0 });
});

test("show empty placeholder when thread contains only empty messages", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({ model: "discuss.channel", res_id: channelId });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread", { text: "The conversation is empty." });
    await contains(".o-mail-Message", { count: 0 });
});

test("message list with a full page of empty messages should load more messages until there are some non-empty", async () => {
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
    let newestMessageId;
    for (let i = 0; i < 50; i++) {
        newestMessageId = pyEnv["mail.message"].create({
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const [selfMember] = pyEnv["discuss.channel.member"].search_read([
        ["partner_id", "=", serverState.partnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.member"].write([selfMember.id], {
        new_message_separator: newestMessageId + 1,
    });
    await start();
    await openDiscuss(channelId);
    // initial load: +30 empty ; (auto) load more: +20 empty +10 non-empty
    await contains(".o-mail-Message", { count: 10 });
    await contains("button", { text: "Load More" }); // still 40 non-empty
});

test("Mention a partner with special character (e.g. apostrophe ')", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "usatyi@example.com",
        name: "Pynya's spokesman",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
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

test("mention 2 different partners that have the same name", async () => {
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
            Command.create({ partner_id: serverState.partnerId }),
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

test("mention a channel on a second line when the first line contains #", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General good" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "#blabla\n#");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "#blabla\n#General good " });
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-body .o_channel_redirect", { text: "General good" });
});

test("mention a channel when replacing the space after the mention by another char", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General good" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "#");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "#General good " });
    const text = queryValue(".o-mail-Composer-input:first");
    queryFirst(".o-mail-Composer-input").value = text.slice(0, -1);
    await insertText(".o-mail-Composer-input", ", test");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-body .o_channel_redirect", { text: "General good" });
});

test("mention 2 different channels that have the same name", async () => {
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
        { text: "my channel" }
    );
    await contains(
        `.o-mail-Message-body .o_channel_redirect[data-oe-id="${channelId_2}"][data-oe-model="discuss.channel"]`,
        { text: "my channel" }
    );
});

test("Post a message containing an email address followed by a mention on another line", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
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

test("basic rendering of canceled notification", async () => {
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

test("first unseen message should be directly preceded by the new message separator if there is a transient message just before it while composer is not focused", async () => {
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
            Command.create({ partner_id: serverState.partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "not empty");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message", { text: "not empty" });
    // send a command that leads to receiving a transient message
    await insertText(".o-mail-Composer-input", "/who");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message", { count: 2 });
    // composer is focused by default, we remove that focus
    queryFirst(".o-mail-Composer-input").blur();
    // simulate receiving a message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "test", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message", { count: 3 });
    await contains(".o-mail-Thread-newMessage hr + span", { text: "New" });
    await contains(".o-mail-Message[aria-label='Note'] + .o-mail-Thread-newMessage");
});

test.tags("focus required");
test("composer should be focused automatically after clicking on the send button", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Dummy Message");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Composer-input:focus");
});

test("chat window header should not have unread counter for non-channel thread", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "test" });
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "not empty",
        model: "res.partner",
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
    await contains(".o-mail-ChatWindow-counter", { count: 0, text: "1" });
});

test("[technical] opening a non-channel chat window should not call channel_fold", async () => {
    // channel_fold should not be called when opening non-channels in chat
    // window, because there is no server sync of fold state for them.
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "test" });
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "not empty",
        model: "res.partner",
        needaction: true,
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    onRpcBefore("/discuss/channel/fold", () => {
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

test("Thread messages are only loaded once", async () => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create([{ name: "General" }, { name: "Sales" }]);
    onRpcBefore("/discuss/channel/messages", (args) =>
        step(`load messages - ${args["channel_id"]}`)
    );
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
    await click("button", { text: "General" });
    await contains(".o-mail-Message-content", { text: "Message on channel1" });
    await click("button", { text: "Sales" });
    await contains(".o-mail-Message-content", { text: "Message on channel2" });
    await click("button", { text: "General" });
    await contains(".o-mail-Message-content", { text: "Message on channel1" });
    await assertSteps([`load messages - ${channelIds[0]}`, `load messages - ${channelIds[1]}`]);
});

test.tags("focus required");
test("Opening thread with needaction messages should mark all messages of thread as read", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    onRpc("mail.message", "mark_all_as_read", ({ args }) => {
        step("mark-all-messages-as-read");
        expect(args[0]).toEqual([
            ["model", "=", "discuss.channel"],
            ["res_id", "=", channelId],
        ]);
    });
    await start();
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
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    // simulate receiving a new needaction message
    const [partner] = pyEnv["res.partner"].read(serverState.partnerId);
    pyEnv["bus.bus"]._sendone(
        partner,
        "mail.message/inbox",
        new mailDataHelpers.Store(
            pyEnv["mail.message"].browse(messageId),
            makeKwArgs({ for_current_user: true, add_followers: true })
        ).get_result()
    );
    await contains("button", { text: "Inbox", contains: [".badge", { text: "1" }] });
    await click("button", { text: "General" });
    await contains(".o-discuss-badge", { count: 0 });
    await contains("button", { text: "Inbox", contains: [".badge", { count: 0 }] });
    await assertSteps(["mark-all-messages-as-read"]);
});

test("[technical] Opening thread without needaction messages should not mark all messages of thread as read", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    onRpc("mail.message", "mark_all_as_read", () => step("mark-all-messages-as-read"));
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
    await assertSteps([]);
});

test.tags("focus required");
test("can be marked as read while loading", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 1, partner_id: serverState.partnerId }),
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
    onRpc("/discuss/channel/messages", () => loadDeferred);
    await start();
    await openDiscuss(undefined);
    await contains(".o-discuss-badge", { text: "1" });
    await click(".o-mail-DiscussSidebarChannel", { text: "Demo" });
    loadDeferred.resolve();
    await contains(".o-discuss-badge", { count: 0 });
});

test("New message separator not appearing after showing composer on thread", async () => {
    const pyEnv = await startServer();
    pyEnv["mail.message"].create([
        {
            model: "res.partner",
            res_id: serverState.partnerId,
            body: "Message on partner",
        },
        {
            model: "res.partner",
            res_id: serverState.partnerId,
            body: "Message on partner",
        },
    ]);
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await contains("button", { text: "Log note" });
    await contains(".o-mail-Thread-newMessage", { count: 0 });
    await click("button", { text: "Log note" });
    await contains(".o-mail-Thread-newMessage", { count: 0 });
});

test("Transient messages are added at the end of the thread", async () => {
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
