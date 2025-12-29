import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
    openFormView,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { queryFirst } from "@odoo/hoot-dom";
import { disableAnimations } from "@odoo/hoot-mock";
import { serverState } from "@web/../tests/web_test_helpers";
import { deserializeDateTime } from "@web/core/l10n/dates";

import { getOrigin } from "@web/core/utils/urls";

describe.current.tags("desktop");
defineMailModels();

test("click on message in reply to highlight the parent message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messageId = pyEnv["mail.message"].create({
        body: "Hey lol",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    pyEnv["mail.message"].create({
        body: "Reply to Hey",
        message_type: "comment",
        model: "discuss.channel",
        parent_id: messageId,
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-MessageInReply-message", {
        parent: [".o-mail-Message", { text: "Reply to Hey" }],
    });
    await contains(".o-mail-Message.o-highlighted .o-mail-Message-content", { text: "Hey lol" });
});

test("click on message in reply to scroll to the parent message", async () => {
    disableAnimations();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const [oldestMessageId] = pyEnv["mail.message"].create(
        Array(20)
            .fill(0)
            .map(() => ({
                body: "Non Empty Body ".repeat(25),
                message_type: "comment",
                model: "discuss.channel",
                res_id: channelId,
            }))
    );
    pyEnv["mail.message"].create({
        body: "Response to first message",
        message_type: "comment",
        model: "discuss.channel",
        parent_id: oldestMessageId,
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-MessageInReply-message", {
        parent: [".o-mail-Message", { text: "Response to first message" }],
    });
    await contains(":nth-child(1 of .o-mail-Message)", { visible: true });
});

test("reply shows correct author avatar", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messageId = pyEnv["mail.message"].create({
        body: "Hey there",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    const partner = pyEnv["res.partner"].search_read([["id", "=", serverState.partnerId]])[0];
    pyEnv["mail.message"].create({
        body: "Howdy",
        message_type: "comment",
        model: "discuss.channel",
        author_id: partnerId,
        parent_id: messageId,
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(
        `.o-mail-MessageInReply-avatar[data-src='${`${getOrigin()}/web/image/res.partner/${
            serverState.partnerId
        }/avatar_128?unique=${deserializeDateTime(partner.write_date).ts}`}`
    );
});

test("click on message in reply highlights original message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messageId = pyEnv["mail.message"].create({
        body: "",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    pyEnv["mail.message"].create({
        body: "Response to deleted message",
        message_type: "comment",
        model: "discuss.channel",
        parent_id: messageId,
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await click(
        ".o-mail-Message:contains('Response to deleted message') .o-mail-MessageInReply:contains('Original message was deleted') .cursor-pointer"
    );
    await contains(".o-mail-Message.o-highlighted:contains('This message has been removed')");
});

test("can reply to logged note in chatter", async () => {
    const pyEnv = await startServer();
    const partnerBId = pyEnv["res.partner"].create({ name: "Partner B" });
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    pyEnv["mail.message"].create([
        {
            author_id: partnerBId,
            body: "Test message from B",
            model: "res.partner",
            res_id: serverState.partnerId,
            subtype_id: pyEnv["mail.message.subtype"].search([
                ["subtype_xmlid", "=", "mail.mt_note"],
            ])[0],
        },
        {
            author_id: serverState.partnerId,
            body: "Another msg",
            model: "discuss.channel",
            message_type: "comment",
            res_id: channelId,
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await contains(".o-dropdown-item:contains('Reply')");
    await openFormView("res.partner", serverState.partnerId);
    await click(".o-mail-Message:contains('Test message from B') [title='Reply']");
    await contains("button.active", { text: "Log note" });
    await contains(".o-mail-Composer.o-focused .o-mail-Composer-input", { value: "@Partner B " });
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message a.o_mail_redirect", { text: "@Partner B" });
    await contains(".o-mail-Message:contains('@Partner B') [title='Edit']");
    await contains(".o-mail-Message:contains('@Partner B') [title='Reply']", { count: 0 });
    await click(".o-mail-Message:contains('@Partner B') [title='Expand']");
    await contains(".o-dropdown-item:contains('Delete')");
    await contains(".o-dropdown-item:contains('Reply')", { count: 0 });
});

test("Replying to a message containing line breaks should be correctly inlined", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messageId = pyEnv["mail.message"].create({
        body: "<p>Message first line.<br>Message second line.<br>Message third line.</p>",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    pyEnv["mail.message"].create({
        body: "Howdy",
        message_type: "comment",
        model: "discuss.channel",
        author_id: partnerId,
        parent_id: messageId,
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-MessageInReply-message", {
        text: "Message first line. Message second line. Message third line.",
    });
});

test("reply with only attachment shows parent message context", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const originalMessageId = pyEnv["mail.message"].create({
        body: "Original message content",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "test_image.png",
        mimetype: "image/png",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "",
        message_type: "comment",
        model: "discuss.channel",
        parent_id: originalMessageId,
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-MessageInReply-message", {
        text: "Original message content",
    });
});

test("replying to a note restores focus on an already open composer", async () => {
    const pyEnv = await startServer();
    const partnerBId = pyEnv["res.partner"].create({ name: "Partner B" });
    pyEnv["mail.message"].create({
        author_id: partnerBId,
        body: "Test message from B",
        model: "res.partner",
        res_id: serverState.partnerId,
        subtype_id: pyEnv["mail.message.subtype"].search([
            ["subtype_xmlid", "=", "mail.mt_note"],
        ])[0],
    });
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click("button:not(.active):text('Log note')");
    await contains(".o-mail-Composer.o-focused");
    queryFirst(".o-mail-Composer-input").blur();
    await contains(".o-mail-Composer.o-focused", { count: 0 });
    await click(".o-mail-Message-actions [title='Reply']");
    await contains(".o-mail-Composer.o-focused");
});
