/** @odoo-module **/

import { afterNextRender, click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { editInput, getFixture } from "@web/../tests/helpers/utils";
import { file } from "web.test_utils";

const { createFile } = file;

let target;
QUnit.module("file upload", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("no conflicts between file uploads", async function (assert) {
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
        editInput(target, ".o-mail-chatter .o-mail-composer input[type=file]", file1)
    );
    // Uploading file in the second thread: mail.channel in chatWindow.
    await click("i[aria-label='Messages']");
    await click(".o-mail-notification-item");
    const file2 = await createFile({
        name: "text2.txt",
        content: "hello, world",
        contentType: "text/plain",
    });
    await afterNextRender(() => editInput(target, ".o-mail-chat-window input[type=file]", file2));
    assert.containsOnce(target, ".o-mail-chatter .o-mail-attachment-image");
    assert.containsOnce(target, ".o-mail-chat-window .o-mail-attachment-image");
});
