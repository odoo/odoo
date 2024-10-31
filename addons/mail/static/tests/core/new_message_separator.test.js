import { presenceService } from "@bus/services/presence_service";
import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    insertText,
    onRpcBefore,
    openDiscuss,
    openFormView,
    scroll,
    start,
    startServer,
    step,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { queryFirst } from "@odoo/hoot-dom";
import { mockDate, tick } from "@odoo/hoot-mock";
import { Command, mockService, serverState, withUser } from "@web/../tests/web_test_helpers";

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
    await click(".o-mail-Message-moreMenu [title='Mark as Unread']");
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", { text: "message 0" });
    await click("[title='Expand']", {
        parent: [".o-mail-Message", { text: "message 0" }],
    });
    await click(".o-mail-Message-moreMenu [title='Delete']");
    await click("button", { text: "Confirm" });
    await contains(".o-mail-Message", { text: "message 0", count: 0 });
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", { text: "message 1" });
});

test("separator is not shown if message is not yet loaded", async () => {
    const pyEnv = await startServer();
    const generalId = pyEnv["discuss.channel"].create({ name: "General" });
    for (let i = 0; i < 60; i++) {
        pyEnv["mail.message"].create({
            body: `message ${i}`,
            message_type: "comment",
            model: "discuss.channel",
            author_id: serverState.partnerId,
            res_id: generalId,
        });
    }
    await start();
    await openDiscuss(generalId);
    await contains(".o-mail-Message", { count: 30 });
    await scroll(".o-mail-Thread", 0);
    await contains(".o-mail-Message", { text: "message 0" });
    await tick(); // give enough time for the useVisible hook to register load more as hidden
    await scroll(".o-mail-Thread", 0);
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", { text: "message 0" });
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
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "hello",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread");
    await contains(".o-mail-Message", { text: "hello" });
    await contains(".o-mail-Thread-newMessage hr + span", { text: "New" });
    await click(".o-mail-DiscussSidebar-item", { text: "History" });
    await contains(".o-mail-Discuss-threadName", { value: "History" });
    await click(".o-mail-DiscussSidebar-item", { text: "test" });
    await contains(".o-mail-Discuss-threadName", { value: "test" });
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New" });
});

test("show new message separator on receiving new message when out of odoo focus", async () => {
    mockService("presence", () => ({
        ...presenceService.start(),
        isOdooFocused: () => false,
    }));
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread");
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New" });
    // simulate receiving a message
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hu", message_type: "comment", subtype_xmlid: "mail.mt_comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message", { text: "hu" });
    await contains(".o-mail-Thread-newMessage hr + span", { text: "New" });
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
    await click(".o-mail-Message-moreMenu [title='Mark as Unread']");
    await contains(".o-mail-Thread-newMessage hr + span", { count: 1, text: "New" });
    await insertText(".o-mail-Composer-input", "hey!");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message", { count: 2 });
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New" });
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
    await click(".o-mail-Message-moreMenu [title='Mark as Unread']");
    await contains(".o-mail-Thread-newMessage");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Open in Discuss" });
    await contains(".o-mail-Discuss-threadName", { value: "General" });
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
                fold_state: "open",
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
    await contains(".o-mail-Thread-newMessage hr + span", { text: "New" });
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
            Command.create({ partner_id: serverState.partnerId, fold_state: "open" }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    onRpcBefore("/mail/action", (args) => {
        if (args.init_messaging) {
            step(`/mail/action - ${JSON.stringify(args)}`);
        }
    });
    await start();
    await assertSteps([
        `/mail/action - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: serverState.userId, allowed_company_ids: [1] },
        })}`,
    ]);
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
    await contains(".o-mail-Thread-newMessage hr + span", { text: "New" });
});

test("only show new message separator in its thread", async () => {
    // when a message acts as the reference for displaying new message separator,
    // this should applies only when vieweing the message in its thread.
    const pyEnv = await startServer();
    const demoPartnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        author_id: demoPartnerId,
        body: "@Mitchell Admin",
        attachment_ids: [],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        needaction: true,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", { text: "@Mitchell Admin" });
    await click(".o-mail-DiscussSidebar-item", { text: "Inbox" });
    await contains(".o-mail-Discuss-threadName", { value: "Inbox" });
    await contains(".o-mail-Message", { text: "@Mitchell Admin" });
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", {
        count: 0,
        text: "@Mitchell Admin",
    });
});
