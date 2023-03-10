/** @odoo-module **/

import { startServer, start, afterNextRender } from "@mail/../tests/helpers/test_utils";

QUnit.module("message_seen_indicator");

QUnit.test("rendering when just one has received the message", async (assert) => {
    const pyEnv = await startServer();
    const partnerId_1 = pyEnv["res.partner"].create({ name: "Demo User" });
    const partnerId_2 = pyEnv["res.partner"].create({ name: "Other User" });
    const channelId = pyEnv["mail.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId_1 }],
            [0, 0, { partner_id: partnerId_2 }],
        ],
        channel_type: "chat", // only chat channel have seen notification
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: "mail.channel",
        res_id: channelId,
    });
    const [memberId_1] = pyEnv["mail.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", partnerId_1],
    ]);
    pyEnv["mail.channel.member"].write([memberId_1], {
        fetched_message_id: messageId,
        seen_message_id: false,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-MessageSeenIndicator");
    assert.doesNotHaveClass($(".o-MessageSeenIndicator"), "o-all-seen");
    assert.containsOnce($, ".o-MessageSeenIndicator i");
});

QUnit.test("rendering when everyone have received the message", async (assert) => {
    const pyEnv = await startServer();
    const partnerId_1 = pyEnv["res.partner"].create({ name: "Demo User" });
    const partnerId_2 = pyEnv["res.partner"].create({ name: "Other User" });
    const channelId = pyEnv["mail.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId_1 }],
            [0, 0, { partner_id: partnerId_2 }],
        ],
        channel_type: "chat",
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: "mail.channel",
        res_id: channelId,
    });
    const memberIds = pyEnv["mail.channel.member"].search([["channel_id", "=", channelId]]);
    pyEnv["mail.channel.member"].write(memberIds, {
        fetched_message_id: messageId,
        seen_message_id: false,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-MessageSeenIndicator");
    assert.doesNotHaveClass($(".o-MessageSeenIndicator"), "o-all-seen");
    assert.containsOnce($, ".o-MessageSeenIndicator i");
});

QUnit.test("rendering when just one has seen the message", async (assert) => {
    const pyEnv = await startServer();
    const partnerId_1 = pyEnv["res.partner"].create({ name: "Demo User" });
    const partnerId_2 = pyEnv["res.partner"].create({ name: "Other User" });
    const channelId = pyEnv["mail.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId_1 }],
            [0, 0, { partner_id: partnerId_2 }],
        ],
        channel_type: "chat",
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: "mail.channel",
        res_id: channelId,
    });
    const memberIds = pyEnv["mail.channel.member"].search([["channel_id", "=", channelId]]);
    pyEnv["mail.channel.member"].write(memberIds, {
        fetched_message_id: messageId,
        seen_message_id: false,
    });
    const [memberId_1] = pyEnv["mail.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", partnerId_1],
    ]);
    pyEnv["mail.channel.member"].write([memberId_1], {
        seen_message_id: messageId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-MessageSeenIndicator");
    assert.doesNotHaveClass($(".o-MessageSeenIndicator"), "o-all-seen");
    assert.containsN($, ".o-MessageSeenIndicator i", 2);
});

QUnit.test("rendering when just one has seen & received the message", async (assert) => {
    const pyEnv = await startServer();
    const partnerId_1 = pyEnv["res.partner"].create({ name: "Demo User" });
    const partnerId_2 = pyEnv["res.partner"].create({ name: "Other User" });
    const channelId = pyEnv["mail.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId_1 }],
            [0, 0, { partner_id: partnerId_2 }],
        ],
        channel_type: "chat",
    });
    const mesageId = pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: "mail.channel",
        res_id: channelId,
    });
    const [memberId_1] = pyEnv["mail.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", partnerId_1],
    ]);
    pyEnv["mail.channel.member"].write([memberId_1], {
        seen_message_id: mesageId,
        fetched_message_id: mesageId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-MessageSeenIndicator");
    assert.doesNotHaveClass($(".o-MessageSeenIndicator"), "o-all-seen");
    assert.containsN($, ".o-MessageSeenIndicator i", 2);
});

QUnit.test("rendering when just everyone has seen the message", async (assert) => {
    const pyEnv = await startServer();
    const partnerId_1 = pyEnv["res.partner"].create({ name: "Demo User" });
    const partnerId_2 = pyEnv["res.partner"].create({ name: "Other User" });
    const channelId = pyEnv["mail.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId_1 }],
            [0, 0, { partner_id: partnerId_2 }],
        ],
        channel_type: "chat",
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: "mail.channel",
        res_id: channelId,
    });
    const memberIds = pyEnv["mail.channel.member"].search([["channel_id", "=", channelId]]);
    pyEnv["mail.channel.member"].write(memberIds, {
        fetched_message_id: messageId,
        seen_message_id: messageId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-MessageSeenIndicator");
    assert.hasClass($(".o-MessageSeenIndicator"), "o-all-seen");
    assert.containsN($, ".o-MessageSeenIndicator i", 2);
});

QUnit.test("'channel_fetch' notification received is correctly handled", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "test" });
    const channelId = pyEnv["mail.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
        channel_type: "chat",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-Message");
    assert.containsNone($, ".o-MessageSeenIndicator i");

    const channel = pyEnv["mail.channel"].searchRead([["id", "=", channelId]])[0];
    // Simulate received channel fetched notification
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendone(channel, "mail.channel.member/fetched", {
            channel_id: channelId,
            last_message_id: 100,
            partner_id: partnerId,
        });
    });
    assert.containsOnce($, ".o-MessageSeenIndicator i");
});

QUnit.test("'channel_seen' notification received is correctly handled", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "test" });
    const channelId = pyEnv["mail.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
        channel_type: "chat",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-Message");
    assert.containsNone($, ".o-MessageSeenIndicator i");

    const channel = pyEnv["mail.channel"].searchRead([["id", "=", channelId]])[0];
    // Simulate received channel seen notification
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendone(channel, "mail.channel.member/seen", {
            channel_id: channelId,
            last_message_id: 100,
            partner_id: partnerId,
        });
    });
    assert.containsN($, ".o-MessageSeenIndicator i", 2);
});

QUnit.test(
    "'channel_fetch' notification then 'channel_seen' received are correctly handled",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Recipient" });
        const channelId = pyEnv["mail.channel"].create({
            name: "test",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId }],
            ],
            channel_type: "chat",
        });
        pyEnv["mail.message"].create({
            author_id: pyEnv.currentPartnerId,
            body: "<p>Test</p>",
            model: "mail.channel",
            res_id: channelId,
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-Message");
        assert.containsNone($, ".o-MessageSeenIndicator i");

        const channel = pyEnv["mail.channel"].searchRead([["id", "=", channelId]])[0];
        // Simulate received channel fetched notification
        await afterNextRender(() => {
            pyEnv["bus.bus"]._sendone(channel, "mail.channel.member/fetched", {
                channel_id: channelId,
                last_message_id: 100,
                partner_id: partnerId,
            });
        });
        assert.containsOnce($, ".o-MessageSeenIndicator i");

        // Simulate received channel seen notification
        await afterNextRender(() => {
            pyEnv["bus.bus"]._sendone(channel, "mail.channel.member/seen", {
                channel_id: channelId,
                last_message_id: 100,
                partner_id: partnerId,
            });
        });
        assert.containsN($, ".o-MessageSeenIndicator i", 2);
    }
);

QUnit.test(
    "do not show message seen indicator on the last message seen by everyone when the current user is not author of the message",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Demo User" });
        const channelId = pyEnv["mail.channel"].create({
            name: "test",
            channel_type: "chat",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId }],
            ],
        });
        const messageId = pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "<p>Test</p>",
            model: "mail.channel",
            res_id: channelId,
        });
        const memberIds = pyEnv["mail.channel.member"].search([["channel_id", "=", channelId]]);
        pyEnv["mail.channel.member"].write(memberIds, { seen_message_id: messageId });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-Message");
        assert.containsNone($, ".o-MessageSeenIndicator");
    }
);

QUnit.test(
    "do not show message seen indicator on all the messages of the current user that are older than the last message seen by everyone",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Demo User" });
        const channelId = pyEnv["mail.channel"].create({
            name: "test",
            channel_type: "chat",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId }],
            ],
        });
        const [, messageId_2] = pyEnv["mail.message"].create([
            {
                author_id: pyEnv.currentPartnerId,
                body: "<p>Message before last seen</p>",
                model: "mail.channel",
                res_id: channelId,
            },
            {
                author_id: pyEnv.currentPartnerId,
                body: "<p>Last seen by everyone</p>",
                model: "mail.channel",
                res_id: channelId,
            },
        ]);
        const memberIds = pyEnv["mail.channel.member"].search([["channel_id", "=", channelId]]);
        pyEnv["mail.channel.member"].write(memberIds, { seen_message_id: messageId_2 });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-Message:contains(Message before last seen)");
        assert.containsOnce(
            $,
            ".o-Message:contains(Message before last seen) .o-MessageSeenIndicator"
        );
        assert.containsNone(
            $,
            ".o-Message:contains(Message before last seen) .o-MessageSeenIndicator i"
        );
    }
);

QUnit.test(
    "only show messaging seen indicator if authored by me, after last seen by all message",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Demo User" });
        const channelId = pyEnv["mail.channel"].create({
            name: "test",
            channel_type: "chat",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId }],
            ],
        });
        const messageId = pyEnv["mail.message"].create({
            author_id: pyEnv.currentPartnerId,
            body: "<p>Test</p>",
            res_id: channelId,
            model: "mail.channel",
        });
        const memberIds = pyEnv["mail.channel.member"].search([["channel_id", "=", channelId]]);
        pyEnv["mail.channel.member"].write(memberIds, {
            fetched_message_id: messageId,
            seen_message_id: messageId - 1,
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-Message");
        assert.containsOnce($, ".o-MessageSeenIndicator");
        assert.containsN($, ".o-MessageSeenIndicator i", 1);
    }
);
