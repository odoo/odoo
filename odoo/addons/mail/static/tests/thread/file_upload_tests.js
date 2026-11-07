/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains, createFile, inputFiles } from "@web/../tests/utils";

QUnit.module("file upload");

QUnit.test("no conflicts between file uploads", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const channelId = pyEnv["discuss.channel"].create({});
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openView } = await start();
    // Uploading file in the first thread: res.partner chatter.
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await click("button", { text: "Send message" });
    await inputFiles(".o-mail-Chatter .o-mail-Composer input[type=file]", [
        await createFile({
            name: "text1.txt",
            content: "hello, world",
            contentType: "text/plain",
        }),
    ]);
    // Uploading file in the second thread: discuss.channel in chatWindow.
    await click("i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await inputFiles(".o-mail-ChatWindow .o-mail-Composer input[type=file]", [
        await createFile({
            name: "text2.txt",
            content: "hello, world",
            contentType: "text/plain",
        }),
    ]);
    await contains(".o-mail-Chatter .o-mail-AttachmentCard");
    await contains(".o-mail-ChatWindow .o-mail-AttachmentCard");
});

QUnit.test("Attachment shows spinner during upload", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "channel_1" });
    const { openDiscuss } = await start({
        async mockRPC(route) {
            if (route === "/mail/attachment/upload") {
                // never fulfill the attachment upload promise.
                await new Promise(() => {});
            }
        },
    });
    await openDiscuss(channelId);
    await inputFiles(".o-mail-Composer input[type=file]", [
        await createFile({
            name: "text2.txt",
            content: "hello, world",
            contentType: "text/plain",
        }),
    ]);
    await contains(".o-mail-AttachmentCard .fa-spinner");
});
