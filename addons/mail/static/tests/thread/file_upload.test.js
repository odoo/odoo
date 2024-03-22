import { describe, test } from "@odoo/hoot";
import {
    click,
    contains,
    createFile,
    defineMailModels,
    inputFiles,
    openDiscuss,
    openFormView,
    start,
    startServer,
} from "../mail_test_helpers";
import { onRpc } from "@web/../tests/web_test_helpers";
import { Deferred } from "@odoo/hoot-mock";

describe.current.tags("desktop");
defineMailModels();

test("no conflicts between file uploads", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const channelId = pyEnv["discuss.channel"].create({});
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    // Uploading file in the first thread: res.partner chatter.
    await openFormView("res.partner", partnerId);
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

test("Attachment shows spinner during upload", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "channel_1" });
    onRpc("/mail/attachment/upload", () => new Deferred()); // never fulfill the attachment upload promise.
    await start();
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
