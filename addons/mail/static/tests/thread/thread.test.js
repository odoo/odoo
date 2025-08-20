import {
    assertChatHub,
    click,
    contains,
    defineMailModels,
    dragenterFiles,
    focus,
    insertText,
    isInViewportOf,
    listenStoreFetch,
    onRpcBefore,
    openDiscuss,
    openFormView,
    scroll,
    setupChatHub,
    start,
    startServer,
    triggerEvents,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { describe, expect, test } from "@odoo/hoot";
import { press, queryFirst, queryValue } from "@odoo/hoot-dom";
import { Deferred, mockDate, tick } from "@odoo/hoot-mock";
import {
    asyncStep,
    Command,
    makeKwArgs,
    onRpc,
    serverState,
    waitForSteps,
    withUser,
} from "@web/../tests/web_test_helpers";

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
    const scrollTopValue = queryFirst(".o-mail-Thread").scrollTop;
    await contains(".o-mail-Thread", { scroll: scrollTopValue });
    await tick(); // wait for the scroll to first unread to complete
    await scroll(".o-mail-Thread", scrollValue1);
    await click(".o-mail-DiscussSidebarChannel", { text: "channel-2" });
    await contains(".o-mail-Message", { count: 30 });
    const scrollValue2 = queryFirst(".o-mail-Thread").scrollHeight / 3;
    await contains(".o-mail-Thread", { scroll: scrollTopValue });
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
    await contains(".o-mail-Thread");
    await tick(); // wait for the scroll to first unread to complete
    await scroll(".o-mail-Thread", queryFirst(".o-mail-Thread").scrollHeight / 2);
    await scroll(".o-mail-Thread", "bottom");
    await insertText(".o-mail-Composer-input", "123");
    await press("Enter");
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
    await press("Enter");
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
    await press("Enter");
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
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    onRpcBefore("/discuss/channel/mark_as_read", (args) => {
        expect(args.channel_id).toBe(channelId);
        asyncStep("rpc:mark_as_read");
    });
    onRpc("discuss.channel", "channel_fetched", ({ args }) => {
        expect(args[0][0]).toBe(channelId);
        asyncStep("rpc:channel_fetch");
    });
    setupChatHub({ opened: [channelId] });
    listenStoreFetch(["init_messaging", "discuss.channel"]);
    await start();
    await waitStoreFetch(["init_messaging", "discuss.channel"]);
    await contains(".o_menu_systray i[aria-label='Messages']");
    // send after init_messaging because bus subscription is done after init_messaging
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello!", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message");
    await waitForSteps(["rpc:channel_fetch"]);
    await contains(".o-mail-ChatWindow .badge:contains(1)");
    await contains(".o-mail-Message:contains('Hello!')");
    await focus(".o-mail-Composer-input");
    await waitForSteps(["rpc:mark_as_read"]);
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
    let hasMarkAsRead = false;
    onRpc("/discuss/channel/messages", () => asyncStep("/discuss/channel/messages"));
    onRpcBefore("/discuss/channel/mark_as_read", (args) => {
        expect(args.channel_id).toBe(channelId);
        if (!hasMarkAsRead) {
            asyncStep("rpc:mark_as_read");
            hasMarkAsRead = true;
        }
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
    await waitForSteps(["/discuss/channel/messages"]);
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
    await waitForSteps(["rpc:mark_as_read"]);
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
    await contains(".o-mail-Thread", { scroll: 0 });
    // simulate receiving a message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hello", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message", { count: 22 });
    await contains(".o-mail-ChatWindow .o-mail-Thread", { scroll: 0 });
});

test("show empty placeholder when thread contains no message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread", { text: "Welcome to #general!" });
    await contains(".o-mail-Message", { count: 0 });
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
    await click(".o-mail-Composer-suggestion", { text: "Pynya's spokesman" });
    await contains(".o-mail-Composer-input", { value: "@Pynya's spokesman " });
    await press("Enter");
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
    await press("Enter");
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
    await press("Enter");
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
    await press("Enter");
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
    await press("Enter");
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
    await press("Enter");
    await contains(
        `.o-mail-Message-body .o_mail_redirect[data-oe-id="${partnerId}"][data-oe-model="res.partner"]`,
        { text: "@TestPartner" }
    );
});

test("basic rendering of canceled notification", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    const partnerId = pyEnv["res.partner"].create({ name: "Someone", email: "test@test.be" });
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
    await contains(".o-mail-MessageNotificationPopover", { text: "Someone (test@test.be)" });
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
    await press("Enter");
    await contains(".o-mail-Message", { text: "not empty" });
    // send a command that leads to receiving a transient message
    await insertText(".o-mail-Composer-input", "/who");
    await click(".o-mail-Composer button[title='Send']:enabled");
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
    await contains(".o-mail-Thread-newMessage:contains('New')");
    await contains(".o-mail-Message[aria-label='Note'] + .o-mail-Thread-newMessage");
});

test.tags("focus required");
test("composer should be focused automatically after clicking on the send button", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Dummy Message");
    await press("Enter");
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

test("non-channel chat window are saved", async () => {
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
    await contains(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
    assertChatHub({ opened: [{ id: partnerId, model: "res.partner" }] });
});

test("non-channel chat window are restored", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "test partner" });
    setupChatHub({ opened: [{ id: partnerId, model: "res.partner" }] });
    await start();
    await contains(".o-mail-ChatWindow:contains('test partner')");
});

test("Thread messages are only loaded once", async () => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create([{ name: "General" }, { name: "Sales" }]);
    onRpcBefore("/discuss/channel/messages", (args) =>
        asyncStep(`load messages - ${args["channel_id"]}`)
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
    await waitForSteps([`load messages - ${channelIds[0]}`, `load messages - ${channelIds[1]}`]);
});

test.tags("focus required");
test("Opening thread with needaction messages should mark all messages of thread as read", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    onRpc("mail.message", "mark_all_as_read", ({ args }) => {
        asyncStep("mark-all-messages-as-read");
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
    await waitForSteps(["mark-all-messages-as-read"]);
});

test("[technical] Opening thread without needaction messages should not mark all messages of thread as read", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    onRpc("mail.message", "mark_all_as_read", () => asyncStep("mark-all-messages-as-read"));
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
    await waitForSteps([]);
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
    await press("Enter");
    await contains(".o-mail-Message");
    await insertText(".o-mail-Composer-input", "/help");
    await click(".o-mail-Composer button[title='Send']:enabled");
    await contains(".o-mail-Message", { count: 2 });
    await contains(":nth-child(1 of .o-mail-Message)", { text: "Mitchell Admin" });
    await contains(":nth-child(2 of .o-mail-Message)", { text: "OdooBot" });
});

test("Can scroll to notification", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "notification 0",
        message_type: "notification",
        model: "discuss.channel",
        pinned_at: "2024-03-24 15:00:00",
        res_id: channelId,
    });
    let lastMessageId;
    for (let i = 0; i < 60; ++i) {
        lastMessageId = pyEnv["mail.message"].create({
            author_id: serverState.partnerId,
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const [selfMemberId] = pyEnv["discuss.channel.member"].search([
        ["partner_id", "=", serverState.partnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.member"].write([selfMemberId], {
        new_message_separator: lastMessageId + 1,
    });
    await start();
    await openDiscuss(channelId);
    await tick(); // wait for the scroll to first unread to complete
    await isInViewportOf(".o-mail-Message:contains(message 59)", ".o-mail-Thread");
    await click("[title='Pinned Messages']");
    await click(".o-discuss-PinnedMessagesPanel a[role='button']", { text: "Jump" });
    await isInViewportOf(".o-mail-NotificationMessage:contains(notification 0)", ".o-mail-Thread");
});

test("Update unread counter when receiving new message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({ name: "Demo User", partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                message_unread_counter: 1,
                partner_id: serverState.partnerId,
            }),
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
    await start();
    await openDiscuss(undefined);
    await contains(".o-discuss-badge", { text: "1" });

    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "Message 1",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-discuss-badge", { text: "2" });
});
