/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains } from "@web/../tests/utils";

QUnit.module("attachment panel");

QUnit.test("Empty attachment panel", async () => {
    const pyEnv = await startServer();
    const channelId = await pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Show Attachments']");
    await contains(".o-mail-Discuss-inspector", {
        text: "This channel doesn't have any attachments.",
    });
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
    await contains(".o-mail-AttachmentList", {
        text: "file2.pdf",
        after: [".o-mail-DateSection", { text: "September, 2023" }],
        before: [".o-mail-DateSection", { text: "August, 2023" }],
    });
    await contains(".o-mail-AttachmentList", {
        text: "file1.pdf",
        after: [".o-mail-DateSection", { text: "August, 2023" }],
    });
});

QUnit.test("Can toggle allow public upload", async () => {
    const pyEnv = await startServer();
    const channelId = await pyEnv["discuss.channel"].create({ name: "General" });
    const tab1 = await start({ asTab: true });
    await tab1.openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Show Attachments']", { target: tab1.target });
    const tab2 = await start({ asTab: true });
    await tab2.openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Show Attachments']", { target: tab2.target });
    await contains(".o-mail-ActionPanel", {
        contains: ["label", { text: "File upload is disabled for external users" }],
        target: tab2.target,
    });
    await click(".o-mail-ActionPanel input[type='checkbox']", { target: tab1.target });
    await contains(".o-mail-ActionPanel", {
        contains: ["label", { text: "File upload is enabled for external users" }],
        target: tab2.target,
    });
});
