/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains } from "@web/../tests/utils";

const { DateTime } = luxon;

QUnit.module("message (patch)");

QUnit.test("WhatsApp channels should not have Edit, Delete and Add Reactions button", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
    });
    pyEnv["mail.message"].create({
        body: "WhatsApp Message",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "whatsapp_message",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message-actions");
    await contains(".o-mail-Message-actions .button[title='Add a Reaction']", { count: 0 });
    await contains(".o-mail-Message-actions .dropdown-item .span[title='Edit']", { count: 0 });
    await contains(".o-mail-Message-actions .dropdown-item .span[title='Delete']", {
        count: 0,
    });
});

QUnit.test(
    "WhatsApp error message should be showed with a message header and a whatsapp failure icon",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            name: "WhatsApp 1",
            channel_type: "whatsapp",
        });
        const messageIds = pyEnv["mail.message"].create([
            {
                body: "WhatsApp Message",
                model: "discuss.channel",
                res_id: channelId,
                message_type: "whatsapp_message",
            },
            {
                body: "WhatsApp Message with error",
                model: "discuss.channel",
                res_id: channelId,
                message_type: "whatsapp_message",
            },
        ]);
        pyEnv["whatsapp.message"].create({
            mail_message_id: messageIds[1],
            failure_reason: "Message Not Sent",
            failure_type: "unknown",
            state: "error",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await contains(".o-mail-Message-header", { count: 2 });
        await contains(".o-mail-Message-header span.fa-whatsapp.text-danger");
    }
);

QUnit.test(
    "Clicking on link to WhatsApp Channel in Related Document opens channel in chatwindow",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            name: "WhatsApp 1",
            channel_type: "whatsapp",
            channel_member_ids: [],
        });
        pyEnv["mail.message"].create({
            body: `<a class="o_whatsapp_channel_redirect" data-oe-id="${channelId}">WhatsApp 1</a>`,
            model: "res.partner",
            res_id: pyEnv.currentPartnerId,
            message_type: "comment",
        });
        const { openFormView } = await start();
        await openFormView("res.partner", pyEnv.currentPartnerId);
        await click(".o_whatsapp_channel_redirect");
        await contains(".o-mail-ChatWindow");
        await contains("div.o_mail_notification", { text: "Mitchell Admin joined the channel" });
    }
);

QUnit.test("Allow SeenIndicators in WhatsApp Channels", async () => {
    const pyEnv = await startServer();
    const partnerId2 = pyEnv["res.partner"].create({ name: "WhatsApp User" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId2 }),
        ],
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "whatsapp_message",
    });
    const memberIds = pyEnv["discuss.channel.member"].search([["channel_id", "=", channelId]]);
    pyEnv["discuss.channel.member"].write(memberIds, {
        fetched_message_id: messageId,
        seen_message_id: false,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains(".o-mail-MessageSeenIndicator:not(.o-all-seen)");
    await contains(".o-mail-MessageSeenIndicator i");

    const [channel] = pyEnv["discuss.channel"].searchRead([["id", "=", channelId]]);
    // Simulate received channel seen notification
    pyEnv["bus.bus"]._sendone(channel, "mail.record/insert", {
        ChannelMember: {
            id: memberIds[1],
            lastSeenMessage: { id: messageId },
        },
    });
    await contains(".o-mail-MessageSeenIndicator i", { count: 2 });
});

QUnit.test("No SeenIndicators if message has whatsapp error", async () => {
    const pyEnv = await startServer();
    const partnerId2 = pyEnv["res.partner"].create({ name: "WhatsApp User" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId2 }),
        ],
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "whatsapp_message",
    });
    pyEnv["whatsapp.message"].create({
        mail_message_id: messageId,
        failure_reason: "Message Not Sent",
        failure_type: "unknown",
        state: "error",
    });
    const memberIds = pyEnv["discuss.channel.member"].search([["channel_id", "=", channelId]]);
    pyEnv["discuss.channel.member"].write(memberIds, {
        fetched_message_id: messageId,
        seen_message_id: false,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message .fa.fa-whatsapp.text-danger");
    await contains(".o-mail-MessageSeenIndicator", { count: 0 });
});

QUnit.test("whatsapp template messages should have whatsapp icon in message header", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
    });
    pyEnv["mail.message"].create({
        body: "WhatsApp Message",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "whatsapp_message",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message-header span.fa-whatsapp");
});

QUnit.test("No Reply button if thread is expired", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
        whatsapp_channel_valid_until: DateTime.utc().minus({ minutes: 1 }).toSQL(),
    });
    pyEnv["mail.message"].create({
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "whatsapp_message",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer");
    await contains(".o-mail-Message-actions button[title='Reply']", { count: 0 });
});
