import { describe, expect, test } from "@odoo/hoot";
import { contains, defineMailModels, openDiscuss, start, startServer } from "../mail_test_helpers";
import { Command, serverState } from "@web/../tests/web_test_helpers";

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
    expect($(".o-mail-MessageSeenIndicator")).not.toHaveClass("o-all-seen");
    await contains(".o-mail-MessageSeenIndicator i");
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
    expect($(".o-mail-MessageSeenIndicator")).not.toHaveClass("o-all-seen");
    await contains(".o-mail-MessageSeenIndicator i");
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
    expect($(".o-mail-MessageSeenIndicator")).not.toHaveClass("o-all-seen");
    await contains(".o-mail-MessageSeenIndicator i", { count: 2 });
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
    expect($(".o-mail-MessageSeenIndicator")).not.toHaveClass("o-all-seen");
    await contains(".o-mail-MessageSeenIndicator i", { count: 2 });
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
    expect($(".o-mail-MessageSeenIndicator")).toHaveClass("o-all-seen");
    await contains(".o-mail-MessageSeenIndicator i", { count: 2 });
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
    await contains(".o-mail-MessageSeenIndicator i", { count: 0 });

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
    await contains(".o-mail-MessageSeenIndicator i");
});

test("'channel_seen' notification received is correctly handled", async () => {
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
    await contains(".o-mail-MessageSeenIndicator i", { count: 0 });
    const channel = pyEnv["discuss.channel"].search_read([["id", "=", channelId]])[0];
    // Simulate received channel seen notification
    pyEnv["bus.bus"]._sendone(channel, "discuss.channel.member/seen", {
        id: pyEnv["discuss.channel.member"].search([
            ["channel_id", "=", channelId],
            ["partner_id", "=", partnerId],
        ])[0],
        channel_id: channelId,
        last_message_id: 100,
        partner_id: partnerId,
    });
    await contains(".o-mail-MessageSeenIndicator i", { count: 2 });
});

test("'channel_fetch' notification then 'channel_seen' received are correctly handled", async () => {
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
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await contains(".o-mail-MessageSeenIndicator i", { count: 0 });
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
    await contains(".o-mail-MessageSeenIndicator i");
    // Simulate received channel seen notification
    pyEnv["bus.bus"]._sendone(channel, "discuss.channel.member/seen", {
        id: pyEnv["discuss.channel.member"].search([
            ["channel_id", "=", channelId],
            ["partner_id", "=", partnerId],
        ])[0],
        channel_id: channelId,
        last_message_id: 100,
        partner_id: partnerId,
    });
    await contains(".o-mail-MessageSeenIndicator i", { count: 2 });
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
        contains: [".o-mail-MessageSeenIndicator", { contains: ["i", { count: 0 }] }],
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
    await contains(".o-mail-MessageSeenIndicator");
    await contains(".o-mail-MessageSeenIndicator i");
});
