import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, serverState, withUser } from "@web/../tests/web_test_helpers";

import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineMailModels();

test("no seen indicator in 'channel' channels (with is_typing)", async () => {
    // is_typing info contains fetched / seen message so this could mistakenly show seen indicators
    const pyEnv = await startServer();
    const demoId = pyEnv["res.partner"].create({ name: "Demo User" });
    const demoUserId = pyEnv["res.users"].create({ partner_id: demoId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test-channel",
        channel_type: "channel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, last_seen_dt: "2024-06-01 12:00" }),
            Command.create({ partner_id: demoId, last_seen_dt: "2024-06-01 12:00" }),
        ],
    });
    const chatId = pyEnv["discuss.channel"].create({
        name: "test-chat",
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, last_seen_dt: "2024-06-01 12:00" }),
            Command.create({ partner_id: demoId, last_seen_dt: "2024-06-01 12:00" }),
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
        seen_message_id: channelMsgId,
    });
    pyEnv["discuss.channel.member"].write(chatMemberIds, {
        fetched_message_id: chatMsgId,
        seen_message_id: chatMsgId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { text: "channel-msg" });
    await contains(".o_avatar_seen_indicator", { count: 0 }); // none in channel
    await click(".o-mail-DiscussSidebar-item", { text: "Demo User" });
    await contains(".o-mail-Message", { text: "chat-msg" });
    await contains(".o_avatar_seen_indicator", { count: 1 }); // received in chat
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
    await contains(".o_avatar_seen_indicator", { count: 1 }); // seen in chat
    await click(".o-mail-DiscussSidebar-item", { text: "test-channel" });
    await contains(".o-mail-Message", { text: "channel-msg" });
    await contains(".o_avatar_seen_indicator", { count: 0 }); // none in channel
});

test("Show avatars of user that have seen the message", async () => {
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
    await contains(".o_avatar_seen_indicator", { count: 2 });
});

test("Show avatars of user that have seen on multiple messages message", async () => {
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
    const [messageId1, messageId2] = pyEnv["mail.message"].create([
        {
            author_id: serverState.partnerId,
            body: "<p>Test</p>",
            model: "discuss.channel",
            res_id: channelId,
            date: "2024-06-01 12:00",
        },
        {
            author_id: serverState.partnerId,
            body: "<p>Test 2</p>",
            model: "discuss.channel",
            res_id: channelId,
            date: "2024-06-01 13:00",
        },
    ]);
    const [memberId_1, memberId_2] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "in", [partnerId_1, partnerId_2]],
    ]);
    pyEnv["discuss.channel.member"].write([memberId_1], {
        seen_message_id: messageId1,
        fetched_message_id: messageId1,
    });
    pyEnv["discuss.channel.member"].write([memberId_2], {
        seen_message_id: messageId2,
        fetched_message_id: messageId2,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o_avatar_seen_indicator", { count: 2 });
});

test("Show avatars of user that have seen on multiple squashed messages", async () => {
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
    const [messageId1, messageId2] = pyEnv["mail.message"].create([
        {
            author_id: serverState.partnerId,
            body: "<p>Test</p>",
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            author_id: serverState.partnerId,
            body: "Test 2",
            model: "discuss.channel",
            res_id: channelId,
        },
    ]);
    const [memberId_1, memberId_2] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "in", [partnerId_1, partnerId_2]],
    ]);
    pyEnv["discuss.channel.member"].write([memberId_1], {
        seen_message_id: messageId1,
        fetched_message_id: messageId1,
    });
    pyEnv["discuss.channel.member"].write([memberId_2], {
        seen_message_id: messageId2,
        fetched_message_id: messageId2,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o_avatar_seen_indicator", { count: 2 });
});

test("Display the first 5 avatars of members that have seen a message an open a modal to display everyone", async () => {
    const pyEnv = await startServer();
    const partners = [];
    for (let i = 0; i < 12; i++) {
        partners.push({ name: `User ${i}` });
    }
    const partnerIds = pyEnv["res.partner"].create(partners);
    const channelMemberIds = [];
    for (const partner_id of partnerIds) {
        channelMemberIds.push(Command.create({ partner_id, last_seen_dt: "2024-06-01 12:00" }));
    }
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, last_seen_dt: "2024-06-01 12:00" }),
            ...channelMemberIds,
        ],
        channel_type: "group",
    });
    const mesageId = pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "test",
        model: "discuss.channel",
        res_id: channelId,
    });
    const members = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "in", partnerIds],
    ]);
    pyEnv["discuss.channel.member"].write(members, {
        seen_message_id: mesageId,
        fetched_message_id: mesageId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o_avatar_seen_indicator", { count: 5 });
});

test("Display the first 5 avatars of members that have seen in chatwindow", async () => {
    const pyEnv = await startServer();
    const partners = [];
    for (let i = 0; i < 12; i++) {
        partners.push({ name: `User ${i}` });
    }
    const partnerIds = pyEnv["res.partner"].create(partners);
    const channelMemberIds = [];
    for (const partner_id of partnerIds) {
        channelMemberIds.push(Command.create({ partner_id, last_seen_dt: "2024-06-01 12:00" }));
    }
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, last_seen_dt: "2024-06-01 12:00" }),
            ...channelMemberIds,
        ],
        channel_type: "group",
    });
    const mesageId = pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "test",
        model: "discuss.channel",
        res_id: channelId,
    });
    const members = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "in", partnerIds],
    ]);
    pyEnv["discuss.channel.member"].write(members, {
        seen_message_id: mesageId,
        fetched_message_id: mesageId,
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o_avatar_seen_indicator", { count: 5 });
});
