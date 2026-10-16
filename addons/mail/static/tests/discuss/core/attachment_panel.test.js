import {
    actionPanel,
    contains as mailContains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test, waitFor } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Empty attachment panel", async () => {
    const pyEnv = await startServer();
    const channelId = await pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussContent-header button[title='Attachments']:count(1)").click();
    await waitFor(
        `.o-mail-ActionPanel:contains("This channel doesn't have any attachments."):count(1)`
    );
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
    await waitFor(`${actionPanel("Members")}:count(1)`); // wait for auto-open of this panel
    await contains(".o-mail-DiscussContent-header button[title='Attachments']:count(1)").click();
    await mailContains(".o-mail-AttachmentCard-info:text('file2.pdf')", {
        after: [".o-mail-DateSection:text('September, 2023')"],
        before: [".o-mail-DateSection:text('August, 2023')"],
    });
    await mailContains(".o-mail-AttachmentCard-info:text('file1.pdf')", {
        after: [".o-mail-DateSection:text('August, 2023')"],
    });
});

test("can jump to attachment in conversation from attachment panel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const attachmentId = pyEnv["ir.attachment"].create({
        mimetype: "image/png",
        name: "Newton.png",
        res_id: channelId,
        res_model: "discuss.channel",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "Here is my cat!",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(`${actionPanel("Members")}:count(1)`); // wait for auto-open of this panel
    await contains(".o-mail-DiscussContent-header button[title='Attachments']:count(1)").click();
    await contains(
        `${actionPanel("Attachments")}
        .o-mail-AttachmentButtons button[title='Show in Conversation']:count(1)`
    ).click();
    await waitFor(".o-mail-Message.o-highlighted:contains('Here is my cat!'):count(1)");
});
