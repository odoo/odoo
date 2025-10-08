import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
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
