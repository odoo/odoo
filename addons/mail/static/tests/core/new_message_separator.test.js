import { waitNotifications } from "@bus/../tests/bus_test_helpers";
import {
    click,
    contains,
    defineMailModels,
    insertText,
    listenStoreFetch,
    openDiscuss,
    openFormView,
    setupChatHub,
    start,
    startServer,
    triggerHotkey,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { click as hootClick, press, queryFirst } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { Command, serverState, withUser } from "@web/../tests/web_test_helpers";

import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineMailModels();

test("keep new message separator when message is deleted", async () => {
    const pyEnv = await startServer();
    const generalId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create([
        {
            body: "message 0",
            message_type: "comment",
            model: "discuss.channel",
            author_id: serverState.partnerId,
            res_id: generalId,
        },
        {
            body: "message 1",
            message_type: "comment",
            model: "discuss.channel",
            author_id: serverState.partnerId,
            res_id: generalId,
        },
    ]);
    await start();
    await openDiscuss(generalId);
    await contains(".o-mail-Message", { count: 2 });
    queryFirst(".o-mail-Composer-input").blur();
    await click("[title='Expand']", {
        parent: [".o-mail-Message", { text: "message 0" }],
    });
    await click(".o-dropdown-item:contains('Mark as Unread')");
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", { text: "message 0" });
    await click("[title='Expand']", {
        parent: [".o-mail-Message", { text: "message 0" }],
    });
    await click(".o-dropdown-item:contains('Delete')");
    await click(".modal button", { text: "Delete" });
    await contains(".o-mail-Message", { text: "message 0", count: 0 });
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", { text: "message 1" });
});

test("new message separator is not shown if all messages are new", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const bobPartnerId = pyEnv["res.partner"].create({ name: "Bob" });
    for (let i = 0; i < 5; i++) {
        pyEnv["mail.message"].create({
            author_id: bobPartnerId,
            body: `message ${i}`,
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 5 });
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New" });
});

test("new message separator is shown after first mark as read, on receiving new message", async () => {
    const pyEnv = await startServer();
    const bobPartnerId = pyEnv["res.partner"].create({ name: "Bob" });
    const bobUserId = pyEnv["res.users"].create({ name: "Bob", partner_id: bobPartnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: bobPartnerId }),
        ],
        channel_type: "chat",
    });
    pyEnv["mail.message"].create({
        author_id: bobPartnerId,
        body: `Message 0`,
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { text: "Message 0" });
    await contains(".o-mail-Thread-newMessage", { count: 0, text: "New" });
    await withUser(bobUserId, () =>
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
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", { text: "Message 1" });
    await contains(".o-mail-Thread-newMessage", { text: "New" });
});

test("keep new message separator until user goes back to the thread", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Foreigner partner" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: partnerId }),
            Command.create({ partner_id: serverState.partnerId }),
        ],
    });
    const messageIds = pyEnv["mail.message"].create([
        {
            author_id: partnerId,
            body: "Message body 1",
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            author_id: partnerId,
            body: "Message body 2",
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        },
    ]);
    // simulate that there is at least one read message in the channel
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", serverState.partnerId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], { new_message_separator: messageIds[0] + 1 });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread");
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", { text: "Message body 2" });
    await contains(".o-mail-Thread-newMessage:contains('New')");
    await hootClick(document.body); // Force "focusin" back on the textarea
    await hootClick(".o-mail-Composer-input");
    await waitNotifications([
        "mail.record/insert",
        (n) => n["discuss.channel.member"][0].new_message_separator,
    ]);
    await hootClick(".o-mail-DiscussSidebar-item:contains(History)");
    await contains(".o-mail-DiscussContent-threadName", { value: "History" });
    await hootClick(".o-mail-DiscussSidebar-item:contains(test)");
    await contains(".o-mail-DiscussContent-threadName", { value: "test" });
    await contains(".o-mail-Message", { text: "Message body 2" });
    await contains(".o-mail-Thread-newMessage:contains('New')", { count: 0 });
});

test("show new message separator on receiving new message when out of odoo focus", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Foreigner partner" });
    const userId = pyEnv["res.users"].create({
        name: "Foreigner user",
        partner_id: partnerId,
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 0, partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "channel",
        name: "General",
    });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    // simulate that there is at least one read message in the channel
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", serverState.partnerId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], { new_message_separator: messageId + 1 });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread");
    await contains(".o-mail-Thread-newMessage:contains('New')", { count: 0 });
    // simulate receiving a message
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hu", message_type: "comment", subtype_xmlid: "mail.mt_comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message", { text: "hu" });
    await contains(".o-mail-Thread-newMessage:contains('New')");
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", { text: "hu" });
});

test("keep new message separator until current user sends a message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "hello");
    await triggerHotkey("Enter");
    await contains(".o-mail-Message", { text: "hello" });
    await click(".o-mail-Message [title='Expand']");
    await click(".o-dropdown-item:contains('Mark as Unread')");
    await contains(".o-mail-Thread-newMessage:contains('New')");
    await insertText(".o-mail-Composer-input", "hey!");
    await press("Enter");
    await contains(".o-mail-Message", { count: 2 });
    await contains(".o-mail-Thread-newMessage:contains('New')", { count: 0 });
});

test("keep new message separator when switching between chat window and discuss of same thread", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ channel_type: "channel", name: "General" });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "General" });
    await insertText(".o-mail-Composer-input", "Very important message!");
    await triggerHotkey("Enter");
    await click(".o-mail-Message [title='Expand']");
    await click(".o-dropdown-item:contains('Mark as Unread')");
    await contains(".o-mail-Thread-newMessage");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Open in Discuss" });
    await contains(".o-mail-DiscussContent-threadName", { value: "General" });
    await contains(".o-mail-Thread-newMessage");
    await openFormView("res.partner", serverState.partnerId);
    await contains(".o-mail-ChatWindow-header", { text: "General" });
    await contains(".o-mail-Thread-newMessage");
});

test("show new message separator when message is received in chat window", async () => {
    mockDate("2023-01-03 12:00:00"); // so that it's after last interest (mock server is in 2019 by default!)
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({ name: "Foreigner user", partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                unpin_dt: "2021-01-01 12:00:00",
                last_interest_dt: "2021-01-01 10:00:00",
                partner_id: serverState.partnerId,
            }),
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
        ["partner_id", "=", serverState.partnerId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], { new_message_separator: messageId + 1 });
    setupChatHub({ opened: [channelId] });
    await start();
    // simulate receiving a message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hu", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatWindow");
    await contains(".o-mail-Message", { count: 2 });
    await contains(".o-mail-Thread-newMessage:contains('New'):contains('New')");
    await contains(".o-mail-Thread-newMessage + .o-mail-Message", { text: "hu" });
});

test("show new message separator when message is received while chat window is closed", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({
        name: "Foreigner user",
        partner_id: partnerId,
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    // simulate that there is at least one read message in the channel
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", serverState.partnerId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], { new_message_separator: messageId + 1 });
    setupChatHub({ opened: [channelId] });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    await click(".o-mail-ChatWindow-command[title*='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    // send after init_messaging because bus subscription is done after init_messaging
    // simulate receiving a message
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hu", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatBubble");
    await contains(".o-mail-ChatBubble-counter", { text: "1" });
    await click(".o-mail-ChatBubble");
    await contains(".o-mail-Thread-newMessage:contains('New')");
});

test("only show new message separator in its thread", async () => {
    // when a message acts as the reference for displaying new message separator,
    // this should applies only when vieweing the message in its thread.
    const pyEnv = await startServer();
    const demoPartnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const messageIds = pyEnv["mail.message"].create([
        {
            author_id: demoPartnerId,
            body: "Hello",
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            author_id: demoPartnerId,
            body: "@Mitchell Admin",
            attachment_ids: [],
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
            needaction: true,
        },
    ]);
    // simulate that there is at least one read message in the channel
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", serverState.partnerId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], { new_message_separator: messageIds[0] + 1 });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", { text: "@Mitchell Admin" });
    await click(".o-mail-DiscussSidebar-item", { text: "Inbox" });
    await contains(".o-mail-DiscussContent-threadName", { value: "Inbox" });
    await contains(".o-mail-Message", { text: "@Mitchell Admin" });
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", {
        count: 0,
        text: "@Mitchell Admin",
    });
});
