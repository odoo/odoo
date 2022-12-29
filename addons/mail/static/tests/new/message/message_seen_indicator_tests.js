/** @odoo-module **/

import { startServer, start, afterNextRender } from "@mail/../tests/helpers/test_utils";
import { getFixture } from "@web/../tests/helpers/utils";

let target;

QUnit.module("message_seen_indicator", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("rendering when just one has received the message", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({ name: "Demo User" });
    const resPartnerId2 = pyEnv["res.partner"].create({ name: "Other User" });
    const mailChannelId = pyEnv["mail.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
            [0, 0, { partner_id: resPartnerId2 }],
        ],
        channel_type: "chat", // only chat channel have seen notification
    });
    const mailMessageId = pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: "mail.channel",
        res_id: mailChannelId,
    });
    const [mailChannelMemberId1] = pyEnv["mail.channel.member"].search([
        ["channel_id", "=", mailChannelId],
        ["partner_id", "=", resPartnerId1],
    ]);
    pyEnv["mail.channel.member"].write([mailChannelMemberId1], {
        fetched_message_id: mailMessageId,
        seen_message_id: false,
    });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId);
    assert.containsOnce(target, ".o-mail-message-seen-indicator");
    assert.doesNotHaveClass(target.querySelector(".o-mail-message-seen-indicator"), "o-all-seen");
    assert.containsOnce(target, ".o-mail-message-seen-indicator-icon");
});

QUnit.test("rendering when everyone have received the message", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({ name: "Demo User" });
    const resPartnerId2 = pyEnv["res.partner"].create({ name: "Other User" });
    const mailChannelId = pyEnv["mail.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
            [0, 0, { partner_id: resPartnerId2 }],
        ],
        channel_type: "chat",
    });
    const mailMessageId = pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: "mail.channel",
        res_id: mailChannelId,
    });
    const mailChannelMemberIds = pyEnv["mail.channel.member"].search([
        ["channel_id", "=", mailChannelId],
    ]);
    pyEnv["mail.channel.member"].write(mailChannelMemberIds, {
        fetched_message_id: mailMessageId,
        seen_message_id: false,
    });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId);
    assert.containsOnce(target, ".o-mail-message-seen-indicator");
    assert.doesNotHaveClass(target.querySelector(".o-mail-message-seen-indicator"), "o-all-seen");
    assert.containsOnce(target, ".o-mail-message-seen-indicator-icon");
});

QUnit.test("rendering when just one has seen the message", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({ name: "Demo User" });
    const resPartnerId2 = pyEnv["res.partner"].create({ name: "Other User" });
    const mailChannelId = pyEnv["mail.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
            [0, 0, { partner_id: resPartnerId2 }],
        ],
        channel_type: "chat",
    });
    const mailMessageId = pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: "mail.channel",
        res_id: mailChannelId,
    });
    const mailChannelMemberIds = pyEnv["mail.channel.member"].search([
        ["channel_id", "=", mailChannelId],
    ]);
    pyEnv["mail.channel.member"].write(mailChannelMemberIds, {
        fetched_message_id: mailMessageId,
        seen_message_id: false,
    });
    const [mailChannelMemberId1] = pyEnv["mail.channel.member"].search([
        ["channel_id", "=", mailChannelId],
        ["partner_id", "=", resPartnerId1],
    ]);
    pyEnv["mail.channel.member"].write([mailChannelMemberId1], {
        seen_message_id: mailMessageId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId);
    assert.containsOnce(target, ".o-mail-message-seen-indicator");
    assert.doesNotHaveClass(target.querySelector(".o-mail-message-seen-indicator"), "o-all-seen");
    assert.containsN(target, ".o-mail-message-seen-indicator-icon", 2);
});

QUnit.test("rendering when just one has seen & received the message", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({ name: "Demo User" });
    const resPartnerId2 = pyEnv["res.partner"].create({ name: "Other User" });
    const mailChannelId = pyEnv["mail.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
            [0, 0, { partner_id: resPartnerId2 }],
        ],
        channel_type: "chat",
    });
    const mailMessageId = pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: "mail.channel",
        res_id: mailChannelId,
    });
    const [mailChannelMemberId1] = pyEnv["mail.channel.member"].search([
        ["channel_id", "=", mailChannelId],
        ["partner_id", "=", resPartnerId1],
    ]);
    pyEnv["mail.channel.member"].write([mailChannelMemberId1], {
        seen_message_id: mailMessageId,
        fetched_message_id: mailMessageId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId);
    assert.containsOnce(target, ".o-mail-message-seen-indicator");
    assert.doesNotHaveClass(target.querySelector(".o-mail-message-seen-indicator"), "o-all-seen");
    assert.containsN(target, ".o-mail-message-seen-indicator-icon", 2);
});

QUnit.test("rendering when just everyone has seen the message", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({ name: "Demo User" });
    const resPartnerId2 = pyEnv["res.partner"].create({ name: "Other User" });
    const mailChannelId = pyEnv["mail.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
            [0, 0, { partner_id: resPartnerId2 }],
        ],
        channel_type: "chat",
    });
    const mailMessageId = pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: "mail.channel",
        res_id: mailChannelId,
    });
    const mailChannelMemberIds = pyEnv["mail.channel.member"].search([
        ["channel_id", "=", mailChannelId],
    ]);
    pyEnv["mail.channel.member"].write(mailChannelMemberIds, {
        fetched_message_id: mailMessageId,
        seen_message_id: mailMessageId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId);
    assert.containsOnce(target, ".o-mail-message-seen-indicator");
    assert.hasClass(target.querySelector(".o-mail-message-seen-indicator"), "o-all-seen");
    assert.containsN(target, ".o-mail-message-seen-indicator-icon", 2);
});

QUnit.test("'channel_fetch' notification received is correctly handled", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId = pyEnv["res.partner"].create({ name: "test" });
    const mailChannelId = pyEnv["mail.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId }],
        ],
        channel_type: "chat",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: "mail.channel",
        res_id: mailChannelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId);
    assert.containsOnce(target, ".o-mail-message");
    assert.containsNone(target, ".o-mail-message-seen-indicator-icon");

    const mailChannel1 = pyEnv["mail.channel"].searchRead([["id", "=", mailChannelId]])[0];
    // Simulate received channel fetched notification
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendone(mailChannel1, "mail.channel.member/fetched", {
            channel_id: mailChannelId,
            last_message_id: 100,
            partner_id: resPartnerId,
        });
    });
    assert.containsOnce(target, ".o-mail-message-seen-indicator-icon");
});

QUnit.test("'channel_seen' notification received is correctly handled", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId = pyEnv["res.partner"].create({ name: "test" });
    const mailChannelId = pyEnv["mail.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId }],
        ],
        channel_type: "chat",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: "mail.channel",
        res_id: mailChannelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId);
    assert.containsOnce(target, ".o-mail-message");
    assert.containsNone(target, ".o-mail-message-seen-indicator-icon");

    const mailChannel1 = pyEnv["mail.channel"].searchRead([["id", "=", mailChannelId]])[0];
    // Simulate received channel seen notification
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendone(mailChannel1, "mail.channel.member/seen", {
            channel_id: mailChannelId,
            last_message_id: 100,
            partner_id: resPartnerId,
        });
    });
    assert.containsN(target, ".o-mail-message-seen-indicator-icon", 2);
});

QUnit.test(
    "'channel_fetch' notification then 'channel_seen' received are correctly handled",
    async function (assert) {
        const pyEnv = await startServer();
        const resPartnerId = pyEnv["res.partner"].create({ name: "Recipient" });
        const mailChannelId = pyEnv["mail.channel"].create({
            name: "test",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: resPartnerId }],
            ],
            channel_type: "chat",
        });
        pyEnv["mail.message"].create({
            author_id: pyEnv.currentPartnerId,
            body: "<p>Test</p>",
            model: "mail.channel",
            res_id: mailChannelId,
        });
        const { openDiscuss } = await start();
        await openDiscuss(mailChannelId);
        assert.containsOnce(target, ".o-mail-message");
        assert.containsNone(target, ".o-mail-message-seen-indicator-icon");

        const mailChannel1 = pyEnv["mail.channel"].searchRead([["id", "=", mailChannelId]])[0];
        // Simulate received channel fetched notification
        await afterNextRender(() => {
            pyEnv["bus.bus"]._sendone(mailChannel1, "mail.channel.member/fetched", {
                channel_id: mailChannelId,
                last_message_id: 100,
                partner_id: resPartnerId,
            });
        });
        assert.containsOnce(target, ".o-mail-message-seen-indicator-icon");

        // Simulate received channel seen notification
        await afterNextRender(() => {
            pyEnv["bus.bus"]._sendone(mailChannel1, "mail.channel.member/seen", {
                channel_id: mailChannelId,
                last_message_id: 100,
                partner_id: resPartnerId,
            });
        });
        assert.containsN(target, ".o-mail-message-seen-indicator-icon", 2);
    }
);

QUnit.test(
    "do not show message seen indicator on the last message seen by everyone when the current user is not author of the message",
    async function (assert) {
        const pyEnv = await startServer();
        const otherPartnerId = pyEnv["res.partner"].create({ name: "Demo User" });
        const mailChannelId = pyEnv["mail.channel"].create({
            name: "test",
            channel_type: "chat",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: otherPartnerId }],
            ],
        });
        const mailMessageId = pyEnv["mail.message"].create({
            author_id: otherPartnerId,
            body: "<p>Test</p>",
            model: "mail.channel",
            res_id: mailChannelId,
        });
        const memberIds = pyEnv["mail.channel.member"].search([["channel_id", "=", mailChannelId]]);
        pyEnv["mail.channel.member"].write(memberIds, { seen_message_id: mailMessageId });
        const { openDiscuss } = await start();
        await openDiscuss(mailChannelId);
        assert.containsOnce(target, ".o-mail-message");
        assert.containsNone(target, ".o-mail-message-seen-indicator");
    }
);

QUnit.test(
    "do not show message seen indicator on all the messages of the current user that are older than the last message seen by everyone",
    async function (assert) {
        const pyEnv = await startServer();
        const otherPartnerId = pyEnv["res.partner"].create({ name: "Demo User" });
        const mailChannelId = pyEnv["mail.channel"].create({
            name: "test",
            channel_type: "chat",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: otherPartnerId }],
            ],
        });
        const [beforeLastMailMessageId, lastMailMessageId] = pyEnv["mail.message"].create([
            {
                author_id: pyEnv.currentPartnerId,
                body: "<p>Message before last seen</p>",
                model: "mail.channel",
                res_id: mailChannelId,
            },
            {
                author_id: pyEnv.currentPartnerId,
                body: "<p>Last seen by everyone</p>",
                model: "mail.channel",
                res_id: mailChannelId,
            },
        ]);
        const memberIds = pyEnv["mail.channel.member"].search([["channel_id", "=", mailChannelId]]);
        pyEnv["mail.channel.member"].write(memberIds, {
            seen_message_id: lastMailMessageId,
        });
        const { openDiscuss } = await start();
        await openDiscuss(mailChannelId);
        assert.containsOnce(target, `.o-mail-message[data-message-id=${beforeLastMailMessageId}]`);
        assert.containsOnce(
            target,
            `.o-mail-message[data-message-id=${beforeLastMailMessageId}] .o-mail-message-seen-indicator`
        );
        assert.containsNone(
            target,
            `.o-mail-message[data-message-id=${beforeLastMailMessageId}] .o-mail-message-seen-indicator-icon`
        );
    }
);

QUnit.test(
    "only show messaging seen indicator if authored by me, after last seen by all message",
    async function (assert) {
        const pyEnv = await startServer();
        const otherPartnerId = pyEnv["res.partner"].create({ name: "Demo User" });
        const mailChannelId = pyEnv["mail.channel"].create({
            name: "test",
            channel_type: "chat",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: otherPartnerId }],
            ],
        });
        const mailMessageId = pyEnv["mail.message"].create({
            author_id: pyEnv.currentPartnerId,
            body: "<p>Test</p>",
            res_id: mailChannelId,
            model: "mail.channel",
        });
        const memberIds = pyEnv["mail.channel.member"].search([["channel_id", "=", mailChannelId]]);
        pyEnv["mail.channel.member"].write(memberIds, {
            fetched_message_id: mailMessageId,
            seen_message_id: mailMessageId - 1,
        });
        const { openDiscuss } = await start();
        await openDiscuss(mailChannelId);
        assert.containsOnce(target, ".o-mail-message");
        assert.containsOnce(target, ".o-mail-message-seen-indicator");
        assert.containsN(target, ".o-mail-message-seen-indicator-icon", 1);
    }
);
