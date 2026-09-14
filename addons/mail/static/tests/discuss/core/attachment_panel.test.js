import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";

describe.current.tags("desktop");
defineMailModels();

test("Empty attachment panel", async () => {
    const pyEnv = await startServer();
    const channelId = await pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-DiscussContent-header button[title='Attachments']");
    await contains(".o-mail-ActionPanel:text('This channel doesn't have any attachments.')");
});

test("Attachment panel sort by date", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["ir.attachment"].create([
        {
            res_id: channelId,
            res_model: "discuss.channel",
            name: "file1.pdf",
            create_date: "2023-08-20 10:00:00",
        },
        {
            res_id: channelId,
            res_model: "discuss.channel",
            name: "file2.pdf",
            create_date: "2023-09-21 10:00:00",
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList"); // wait for auto-open of this panel
    await click(".o-mail-DiscussContent-header button[title='Attachments']");
    await contains(".o-mail-AttachmentCard-info:text('file2.pdf')", {
        after: [".o-mail-DateSection:text('September, 2023')"],
        before: [".o-mail-DateSection:text('August, 2023')"],
    });
    await contains(".o-mail-AttachmentCard-info:text('file1.pdf')", {
        after: [".o-mail-DateSection:text('August, 2023')"],
    });
});

test("show attachment in conversation from attachment panel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const attachmentId = pyEnv["ir.attachment"].create({
        mimetype: "image/png",
        name: "Newton.png",
        res_id: channelId,
        res_model: "discuss.channel",
    });
    const messageId = pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "Here is my cat!",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    pyEnv["ir.attachment"].write([attachmentId], { message_ids: [messageId] });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList"); // wait for auto-open of this panel
    await click(".o-mail-DiscussContent-header button[title='Attachments']");
    await click(
        ".o-mail-ActionPanel .o-mail-AttachmentButtons button[title='Show in Conversation']"
    );
    await contains(".o-mail-Message.o-highlighted:contains('Here is my cat!')");
});
