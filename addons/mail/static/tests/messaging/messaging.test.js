import {
    click,
    contains,
    defineMailModels,
    insertText,
    listenStoreFetch,
    openDiscuss,
    openFormView,
    start,
    startServer,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";

import { describe, expect, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";

import { Command, getService, serverState, withUser } from "@web/../tests/web_test_helpers";
import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineMailModels();

test("Receiving a new message out of discuss app should open a chat bubble", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    // send after init_messaging because bus subscription is done after init_messaging
    // simulate receving new message
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Magic!", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatBubble[name='Dumbledore']");
});

test("Show conversations with new message in chat hub (outside of discuss app)", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const [chatId, groupChatId] = pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "group",
            name: "GroupChat",
        },
    ]);
    await start();
    getService("bus_service").subscribe("discuss.channel/new_message", () =>
        expect.step("discuss.channel/new_message")
    );
    // simulate receiving new message (chat, outside discuss app)
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Chat Message 1", message_type: "comment" },
            thread_id: chatId,
            thread_model: "discuss.channel",
        })
    );
    await expect.waitForSteps(["discuss.channel/new_message"]);
    await contains(".o-mail-ChatBubble .badge:contains(1)", { count: 1 });
    await click(".o-mail-ChatBubble[name='Dumbledore']");
    await contains(".o-mail-ChatWindow-header:contains('Dumbledore')");
    await contains(".o-mail-Message:contains('Chat Message 1')");
    await contains(".badge", { count: 0 });
    await click(".o-mail-ChatWindow [title*='Close Chat Window']");
    // simulate receiving new message (group chat, outside discuss app)
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "GroupChat Message", message_type: "comment" },
            thread_id: groupChatId,
            thread_model: "discuss.channel",
        })
    );
    await expect.waitForSteps(["discuss.channel/new_message"]);
    await contains(".o-mail-ChatBubble[name='GroupChat']");
    await openDiscuss();
    await contains(".o-mail-Discuss[data-active]");
    // simulate receiving new message (chat, inside discuss app)
    await contains(".o-mail-DiscussSidebar-item:contains('Dumbledore') .badge", { count: 0 });
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Tricky", message_type: "comment" },
            thread_id: chatId,
            thread_model: "discuss.channel",
        })
    );
    await expect.waitForSteps(["discuss.channel/new_message"]);
    await click(".o-mail-DiscussSidebar-item:contains('Dumbledore'):has(.badge:contains(1))");
    await contains(".o-mail-Message:contains('Tricky')");
    // check no new chat window/bubble while in discuss app
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-ChatBubble[name='GroupChat']");
    await contains(".o-mail-ChatBubble[name='Dumbledore']", { count: 0 });
    await contains(".o-mail-ChatWindow-header:contains('Dumbledore')", { count: 0 });
});

test("Posting a message in discuss app should not open a chat window after leaving discuss app", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "test https://www.odoo.com/");
    await press("Enter");
    // leaving discuss.
    await openFormView("res.partner", partnerId);
    // weak test, no guarantee that we waited long enough for the potential chat window to open
    await contains(".o-mail-ChatWindow", { count: 0, text: "Dumbledore" });
});
