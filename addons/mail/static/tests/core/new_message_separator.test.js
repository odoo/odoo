import { rpcWithEnv } from "@mail/utils/common/misc";
import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    focus,
    insertText,
    onRpcBefore,
    openDiscuss,
    scroll,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { mockDate, tick } from "@odoo/hoot-mock";
import { config as transitionConfig } from "@web/core/transition";
import { withUser } from "@web/../tests/_framework/mock_server/mock_server";
import { Command, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";

/** @type {ReturnType<import("@mail/utils/common/misc").rpcWithEnv>} */
let rpc;
describe.current.tags("desktop");
defineMailModels();

test("keep separator when message is deleted", async () => {
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
    $(".o-mail-Composer-input").blur();
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

test("focusing a chat window of a chat should make new message separator disappear [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({
        name: "Foreigner user",
        partner_id: partnerId,
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({
                fold_state: "open",
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
    const env = await start();
    rpc = rpcWithEnv(env);
    await contains(".o-mail-Composer-input:not(:focus)");
    // simulate receiving a message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hu", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Thread-newMessage hr + span", { text: "New messages" });
    await focus(".o-mail-Composer-input");
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });
});

test("new messages separator on receiving new message [REQUIRE FOCUS]", async () => {
    patchWithCleanup(transitionConfig, { disabled: true });
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
        body: "blah",
        model: "discuss.channel",
        res_id: channelId,
    });
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", serverState.partnerId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], { new_message_separator: messageId + 1 });
    const env = await start();
    rpc = rpcWithEnv(env);
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });
    $(".o-mail-Composer-input")[0].blur();
    // simulate receiving a message
    withUser(userId, () =>
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

test("no new messages separator on posting message (no message history)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 0, partner_id: serverState.partnerId }),
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

test("no new messages separator on posting message (some message history)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 0, partner_id: serverState.partnerId }),
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
        ["partner_id", "=", serverState.partnerId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], { new_message_separator: messageId + 1 });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });
    await insertText(".o-mail-Composer-input", "hey!");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message", { count: 2 });
    await contains(".o-mail-Thread-newMessage hr + span", { count: 0, text: "New messages" });
});

test("new message separator is shown in a chat window of a chat on receiving new message if there is a history of conversation", async () => {
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
    const env = await start();
    rpc = rpcWithEnv(env);
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
    await contains(".o-mail-Thread-newMessage hr + span", { text: "New messages" });
});

test("new message separator is shown in chat window of chat on receiving new message when there was no history", async () => {
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
    onRpcBefore("/mail/action", (args) => {
        if (args.init_messaging) {
            step(`/mail/action - ${JSON.stringify(args)}`);
        }
    });
    const env = await start();
    rpc = rpcWithEnv(env);
    await assertSteps([
        `/mail/action - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: serverState.userId, allowed_company_ids: [1] },
        })}`,
    ]);
    // send after init_messaging because bus subscription is done after init_messaging
    // simulate receiving a message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "hu", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Thread-newMessage hr + span", { text: "New messages" });
});
