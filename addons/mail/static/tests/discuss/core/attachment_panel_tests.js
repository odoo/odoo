/* @odoo-module */

import { click, contains, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("attachment panel");

QUnit.test("Empty attachment panel", async () => {
    const pyEnv = await startServer();
    const channelId = await pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Show Attachments']");
    await contains(
        ".o-mail-Discuss-inspector:contains(This channel doesn't have any attachments.)"
    );
});

QUnit.test("Attachment panel sort by date", async () => {
    const pyEnv = await startServer();
    const channelId = await pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["ir.attachment"].create([
        {
            res_id: channelId,
            res_model: "discuss.channel",
            name: "file1.pdf",
            create_date: "2023-08-20",
        },
        {
            res_id: channelId,
            res_model: "discuss.channel",
            name: "file2.pdf",
            create_date: "2023-09-21",
        },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Show Attachments']");
    await contains(
        ".o-mail-DateSection:contains(August, 2023) + .o-mail-AttachmentList:contains(file1.pdf)"
    );
    await contains(
        ".o-mail-DateSection:contains(September, 2023) + .o-mail-AttachmentList:contains(file2.pdf)"
    );
});
