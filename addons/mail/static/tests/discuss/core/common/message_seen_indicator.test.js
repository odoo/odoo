import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { describe, test } from "@odoo/hoot";
import { Command, serverState, withUser } from "@web/../tests/web_test_helpers";

import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineMailModels();

test("rendering when just one has received the message", async () => {
    const pyEnv = await startServer();
    const partnerId_1 = pyEnv["res.partner"].create({ name: "Demo User" });
    const partnerId_2 = pyEnv["res.partner"].create({ name: "Other User" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId_1 }),
            Command.create({ partner_id: partnerId_2 }),
        ],
        channel_type: "group",
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    const [memberId_1] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", partnerId_1],
    ]);
    pyEnv["discuss.channel.member"].write([memberId_1], {
        fetched_message_id: messageId,
        seen_message_id: false,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-MessageSeenIndicator");
    await contains(".o-mail-MessageSeenIndicator[title='Sent']");
    await contains(".o-mail-MessageSeenIndicator .fa-check", { count: 1 });
    await contains(".o-mail-MessageSeenIndicator.text-primary", { count: 0 });
});

test("rendering when everyone have received the message", async () => {
    const pyEnv = await startServer();
    const partnerId_1 = pyEnv["res.partner"].create({ name: "Demo User" });
    const partnerId_2 = pyEnv["res.partner"].create({ name: "Other User" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId_1 }),
            Command.create({ partner_id: partnerId_2 }),
        ],
        channel_type: "group",
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    const memberIds = pyEnv["discuss.channel.member"].search([["channel_id", "=", channelId]]);
    pyEnv["discuss.channel.member"].write(memberIds, {
        fetched_message_id: messageId,
        seen_message_id: false,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-MessageSeenIndicator");
    await contains(".o-mail-MessageSeenIndicator[title='Sent']");
    await contains(".o-mail-MessageSeenIndicator .fa-check", { count: 1 });
    await contains(".o-mail-MessageSeenIndicator.text-primary", { count: 0 });
});

test("rendering when just one has seen the message", async () => {
    const pyEnv = await startServer();
    const partnerId_1 = pyEnv["res.partner"].create({ name: "Demo User" });
    const partnerId_2 = pyEnv["res.partner"].create({ name: "Other User" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId_1 }),
            Command.create({ partner_id: partnerId_2 }),
        ],
        channel_type: "group",
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    const memberIds = pyEnv["discuss.channel.member"].search([["channel_id", "=", channelId]]);
    pyEnv["discuss.channel.member"].write(memberIds, {
        fetched_message_id: messageId,
        seen_message_id: false,
    });
    const [memberId_1] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", partnerId_1],
    ]);
    pyEnv["discuss.channel.member"].write([memberId_1], {
        seen_message_id: messageId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-MessageSeenIndicator");
    await contains(".o-mail-MessageSeenIndicator[title='Seen by Demo User']");
    await contains(".o-mail-MessageSeenIndicator .fa-check", { count: 2 });
    await contains(".o-mail-MessageSeenIndicator.text-primary", { count: 0 });
});

test("rendering when just one has seen & received the message", async () => {
    const pyEnv = await startServer();
    const partnerId_1 = pyEnv["res.partner"].create({ name: "Demo User" });
    const partnerId_2 = pyEnv["res.partner"].create({ name: "Other User" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId_1 }),
            Command.create({ partner_id: partnerId_2 }),
        ],
        channel_type: "group",
    });
    const mesageId = pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    const [memberId_1] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", partnerId_1],
    ]);
    pyEnv["discuss.channel.member"].write([memberId_1], {
        seen_message_id: mesageId,
        fetched_message_id: mesageId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-MessageSeenIndicator");
    await contains(".o-mail-MessageSeenIndicator[title='Seen by Demo User']");
    await contains(".o-mail-MessageSeenIndicator .fa-check", { count: 2 });
    await contains(".o-mail-MessageSeenIndicator.text-primary", { count: 0 });
});

test("rendering when just everyone has seen the message", async () => {
    const pyEnv = await startServer();
    const partnerId_1 = pyEnv["res.partner"].create({ name: "Demo User" });
    const partnerId_2 = pyEnv["res.partner"].create({ name: "Other User" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId_1 }),
            Command.create({ partner_id: partnerId_2 }),
        ],
        channel_type: "group",
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    const memberIds = pyEnv["discuss.channel.member"].search([["channel_id", "=", channelId]]);
    pyEnv["discuss.channel.member"].write(memberIds, {
        fetched_message_id: messageId,
        seen_message_id: messageId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-MessageSeenIndicator");
    await contains(".o-mail-MessageSeenIndicator[title='Seen by everyone']");
    await contains(".o-mail-MessageSeenIndicator .fa-check", { count: 2 });
    await contains(".o-mail-MessageSeenIndicator.text-primary", { count: 1 });
});

test("'channel_fetch' notification received is correctly handled", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "test" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await contains(".o-mail-MessageSeenIndicator .fa-check", { count: 0 });

    const channel = pyEnv["discuss.channel"].search_read([["id", "=", channelId]])[0];
    // Simulate received channel fetched notification
    pyEnv["bus.bus"]._sendone(channel, "discuss.channel.member/fetched", {
        id: pyEnv["discuss.channel.member"].search([
            ["channel_id", "=", channelId],
            ["partner_id", "=", partnerId],
        ])[0],
        channel_id: channelId,
        last_message_id: 100,
        partner_id: partnerId,
    });
    await contains(".o-mail-MessageSeenIndicator .fa-check", { count: 1 });
});

test("mark channel as seen from the bus", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "test" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await contains(".o-mail-MessageSeenIndicator .fa-check", { count: 0 });
    const channel = pyEnv["discuss.channel"].search_read([["id", "=", channelId]])[0];
    // Simulate received channel seen notification
    pyEnv["bus.bus"]._sendone(
        channel,
        "mail.record/insert",
        new mailDataHelpers.Store(
            pyEnv["discuss.channel.member"].search([
                ["channel_id", "=", channelId],
                ["partner_id", "=", partnerId],
            ]),
            { seen_message_id: messageId }
        ).get_result()
    );
    await contains(".o-mail-MessageSeenIndicator[title='Seen by test']");
    await contains(".o-mail-MessageSeenIndicator .fa-check", { count: 2 });
});

test("should display message indicator when message is fetched/seen", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Recipient" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await contains(".o-mail-MessageSeenIndicator .fa-check", { count: 0 });
    const channel = pyEnv["discuss.channel"].search_read([["id", "=", channelId]])[0];
    // Simulate received channel fetched notification
    pyEnv["bus.bus"]._sendone(channel, "discuss.channel.member/fetched", {
        id: pyEnv["discuss.channel.member"].search([
            ["channel_id", "=", channelId],
            ["partner_id", "=", partnerId],
        ])[0],
        channel_id: channelId,
        last_message_id: messageId,
        partner_id: partnerId,
    });
    await contains(".o-mail-MessageSeenIndicator .fa-check", { count: 1 });
    // Simulate received channel seen notification
    pyEnv["bus.bus"]._sendone(
        channel,
        "mail.record/insert",
        new mailDataHelpers.Store(
            pyEnv["discuss.channel.member"].search([
                ["channel_id", "=", channelId],
                ["partner_id", "=", partnerId],
            ]),
            { seen_message_id: messageId }
        ).get_result()
    );
    await contains(".o-mail-MessageSeenIndicator .fa-check", { count: 2 });
});

test("do not show message seen indicator on the last message seen by everyone when the current user is not author of the message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo User" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    const memberIds = pyEnv["discuss.channel.member"].search([["channel_id", "=", channelId]]);
    pyEnv["discuss.channel.member"].write(memberIds, { seen_message_id: messageId });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await contains(".o-mail-MessageSeenIndicator", { count: 0 });
});

test("do not show message seen indicator on all the messages of the current user that are older than the last message seen by everyone", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo User" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const [, messageId_2] = pyEnv["mail.message"].create([
        {
            author_id: serverState.partnerId,
            body: "<p>Message before last seen</p>",
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            author_id: serverState.partnerId,
            body: "<p>Last seen by everyone</p>",
            model: "discuss.channel",
            res_id: channelId,
        },
    ]);
    const memberIds = pyEnv["discuss.channel.member"].search([["channel_id", "=", channelId]]);
    pyEnv["discuss.channel.member"].write(memberIds, { seen_message_id: messageId_2 });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", {
        text: "Message before last seen",
        contains: [".o-mail-MessageSeenIndicator", { contains: [".fa-check", { count: 0 }] }],
    });
});

test("only show messaging seen indicator if authored by me, after last seen by all message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo User" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "<p>Test</p>",
        res_id: channelId,
        model: "discuss.channel",
    });
    const memberIds = pyEnv["discuss.channel.member"].search([["channel_id", "=", channelId]]);
    pyEnv["discuss.channel.member"].write(memberIds, {
        fetched_message_id: messageId,
        seen_message_id: messageId - 1,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await contains(".o-mail-MessageSeenIndicator .fa-check", { count: 1 });
});

test("no seen indicator in 'channel' channels (with is_typing)", async () => {
    // is_typing info contains fetched / seen message so this could mistakenly show seen indicators
    const pyEnv = await startServer();
    const demoId = pyEnv["res.partner"].create({ name: "Demo User" });
    const demoUserId = pyEnv["res.users"].create({ partner_id: demoId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test-channel",
        channel_type: "channel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: demoId }),
        ],
    });
    const chatId = pyEnv["discuss.channel"].create({
        name: "test-chat",
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: demoId }),
        ],
    });
    const [channelMsgId, chatMsgId] = pyEnv["mail.message"].create([
        {
            author_id: serverState.partnerId,
            body: "<p>channel-msg</p>",
            res_id: channelId,
            model: "discuss.channel",
        },
        {
            author_id: serverState.partnerId,
            body: "<p>chat-msg</p>",
            res_id: chatId,
            model: "discuss.channel",
        },
    ]);
    const channelMemberIds = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
    ]);
    const chatMemberIds = pyEnv["discuss.channel.member"].search([["channel_id", "=", chatId]]);
    pyEnv["discuss.channel.member"].write(channelMemberIds, {
        fetched_message_id: channelMsgId,
        seen_message_id: 0,
    });
    pyEnv["discuss.channel.member"].write(chatMemberIds, {
        fetched_message_id: chatMsgId,
        seen_message_id: 0,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { text: "channel-msg" });
    await contains(".o-mail-MessageSeenIndicator .fa-check", { count: 0 }); // none in channel
    await click(".o-mail-DiscussSidebar-item", { text: "Demo User" });
    await contains(".o-mail-Message", { text: "chat-msg" });
    await contains(".o-mail-MessageSeenIndicator .fa-check", { count: 1 }); // received in chat
    // simulate channel read by Demo User in both threads
    await withUser(demoUserId, () =>
        rpc("/discuss/channel/mark_as_read", {
            channel_id: channelId,
            last_message_id: channelMsgId,
        })
    );
    await withUser(demoUserId, () =>
        rpc("/discuss/channel/mark_as_read", {
            channel_id: chatId,
            last_message_id: chatMsgId,
        })
    );
    // simulate typing by Demo User in both threads
    await withUser(demoUserId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await withUser(demoUserId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: chatId,
            is_typing: true,
        })
    );
    await contains(".o-mail-MessageSeenIndicator .fa-check", { count: 2 }); // seen in chat
    await click(".o-mail-DiscussSidebar-item", { text: "test-channel" });
    await contains(".o-mail-Message", { text: "channel-msg" });
    await contains(".o-mail-MessageSeenIndicator .fa-check", { count: 0 }); // none in channel
});

test("Show everyone seen title on message seen indicator", async () => {
    const pyEnv = await startServer();
    const partnerId_1 = pyEnv["res.partner"].create({ name: "Demo User" });
    const partnerId_2 = pyEnv["res.partner"].create({ name: "Other User" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, last_seen_dt: "2024-06-01 12:00" }),
            Command.create({ partner_id: partnerId_1, last_seen_dt: "2024-06-01 12:00" }),
            Command.create({ partner_id: partnerId_2, last_seen_dt: "2024-06-01 13:00" }),
        ],
        channel_type: "group",
    });
    const mesageId = pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    const [memberId_1, memberId_2] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "in", [partnerId_1, partnerId_2]],
    ]);
    pyEnv["discuss.channel.member"].write([memberId_1], {
        seen_message_id: mesageId,
        fetched_message_id: mesageId,
    });
    pyEnv["discuss.channel.member"].write([memberId_2], {
        seen_message_id: mesageId,
        fetched_message_id: mesageId,
    });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Seen by everyone']");
});

test("Title show some member seen info (partial seen), click show dialog with full info", async () => {
    // last member flagged as not seen so that it doesn't show "Seen by everyone" but list names instead
    const pyEnv = await startServer();
    const partners = [];
    for (let i = 0; i < 12; i++) {
        partners.push({ name: `User ${i}` });
    }
    const partnerIds = pyEnv["res.partner"].create(partners);
    const channelMemberIds = [];
    for (const partner_id of partnerIds) {
        channelMemberIds.push(
            Command.create({
                partner_id,
                last_seen_dt: partner_id === partnerIds.at(-1) ? false : "2024-06-01 12:00",
            })
        );
    }
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_seen_dt: "2024-06-01 12:00",
            }),
            ...channelMemberIds,
        ],
        channel_type: "group",
    });
    const mesageId = pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    const members = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "in", partnerIds.filter((p) => p !== partnerIds.at(-1))],
    ]);
    pyEnv["discuss.channel.member"].write(members, {
        seen_message_id: mesageId,
        fetched_message_id: mesageId,
    });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Seen by User 0, User 1, User 2 and 8 others']");
    await click(".o-mail-MessageSeenIndicator");
    await contains("li", { count: 11 });
    for (let i = 0; i < 11; i++) {
        await contains("li", { text: `User ${i}` }); // Not checking datetime because HOOT mocking of tz do not work
    }
});
