/** @odoo-module **/

import { afterNextRender, click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { editInput } from "@web/../tests/helpers/utils";
import { file } from "web.test_utils";

const { createFile } = file;

QUnit.module("file upload");

QUnit.test("no conflicts between file uploads", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const channelId = pyEnv["mail.channel"].create({});
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openView } = await start();
    // Uploading file in the first thread: res.partner chatter.
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await click("button:contains(Send message)");
    const file1 = await createFile({
        name: "text1.txt",
        content: "hello, world",
        contentType: "text/plain",
    });
    await afterNextRender(() =>
        editInput(document.body, ".o-mail-chatter .o-mail-composer input[type=file]", file1)
    );
    // Uploading file in the second thread: mail.channel in chatWindow.
    await click("i[aria-label='Messages']");
    await click(".o-mail-notification-item");
    const file2 = await createFile({
        name: "text2.txt",
        content: "hello, world",
        contentType: "text/plain",
    });
    await afterNextRender(() =>
        editInput(document.body, ".o-mail-chat-window input[type=file]", file2)
    );
    assert.containsOnce($, ".o-mail-chatter .o-mail-attachment-card");
    assert.containsOnce($, ".o-mail-chat-window .o-mail-attachment-card");
});

QUnit.test("Attachment shows spinner during upload", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "channel_1" });
    const { openDiscuss } = await start({
        async mockRPC(route) {
            if (route === "/mail/attachment/upload") {
                // never fulfill the attachment upload promise.
                await new Promise(() => {});
            }
        },
    });
    await openDiscuss(channelId);
    const file = await createFile({
        name: "text2.txt",
        content: "hello, world",
        contentType: "text/plain",
    });
    await afterNextRender(() =>
        editInput(document.body, ".o-mail-composer input[type=file]", file)
    );
    assert.containsOnce($, ".o-mail-attachment-card .fa-spinner");
});
