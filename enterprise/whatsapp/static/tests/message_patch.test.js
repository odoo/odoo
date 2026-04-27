import {
    click,
    contains,
    openDiscuss,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { describe, test } from "@odoo/hoot";
import { serializeDateTime } from "@web/core/l10n/dates";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineWhatsAppModels } from "@whatsapp/../tests/whatsapp_test_helpers";

const { DateTime } = luxon;

describe.current.tags("desktop");
defineWhatsAppModels();

test("WhatsApp channels should not have Edit, Delete and Add Reactions button", async () => {
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message-actions");
    await contains(".o-mail-Message-actions .button[title='Add a Reaction']", { count: 0 });
    await contains(".o-mail-Message-actions .dropdown-item .span[title='Edit']", { count: 0 });
    await contains(".o-mail-Message-actions .dropdown-item .span[title='Delete']", {
        count: 0,
    });
});

test("WhatsApp error message should be showed with a message header and a whatsapp failure icon", async () => {
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message-header", { count: 2 });
    await contains(".o-mail-Message-header span.fa-whatsapp.text-danger");
});

test("Clicking on link to WhatsApp Channel in Related Document opens channel in chatwindow", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
        channel_member_ids: [],
    });
    pyEnv["mail.message"].create({
        body: `<a class="o_whatsapp_channel_redirect" data-oe-id="${channelId}">WhatsApp 1</a>`,
        model: "res.partner",
        res_id: serverState.partnerId,
        message_type: "comment",
    });
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click(".o_whatsapp_channel_redirect");
    await contains(".o-mail-ChatWindow");
    await contains("div.o_mail_notification", { text: "Mitchell Admin joined the channel" });
});

test("Allow SeenIndicators in WhatsApp Channels", async () => {
    const pyEnv = await startServer();
    const partnerId2 = pyEnv["res.partner"].create({ name: "WhatsApp User" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId2 }),
        ],
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-MessageSeenIndicator[title='Sent']");
    await contains(".o-mail-MessageSeenIndicator .fa-check", { count: 1 });

    const [channel] = pyEnv["discuss.channel"].search_read([["id", "=", channelId]]);
    // Simulate received channel seen notification
    pyEnv["bus.bus"]._sendone(
        channel,
        "mail.record/insert",
        new mailDataHelpers.Store(pyEnv["discuss.channel.member"].browse(memberIds[1]), {
            seen_message_id: messageId,
        }).get_result()
    );
    await contains(".o-mail-MessageSeenIndicator .fa-check", { count: 2 });
    await contains(".o-mail-MessageSeenIndicator[title='Seen by WhatsApp User']");
});

test("No SeenIndicators if message has whatsapp error", async () => {
    const pyEnv = await startServer();
    const partnerId2 = pyEnv["res.partner"].create({ name: "WhatsApp User" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId2 }),
        ],
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message .fa.fa-whatsapp.text-danger");
    await contains(".o-mail-MessageSeenIndicator", { count: 0 });
});

test("whatsapp template messages should have whatsapp icon in message header", async () => {
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message-header span.fa-whatsapp");
});

test("No Reply button if thread is expired", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
        whatsapp_channel_valid_until: serializeDateTime(DateTime.local().minus({ minutes: 1 })),
    });
    pyEnv["mail.message"].create({
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "whatsapp_message",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer");
    await contains(".o-mail-Message-actions button[title='Reply']", { count: 0 });
});
