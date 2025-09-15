import {
    click,
    contains,
    defineMailModels,
    inputFiles,
    openDiscuss,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Deferred } from "@odoo/hoot-mock";
import { onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("no conflicts between file uploads", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const channelId = pyEnv["discuss.channel"].create({});
    const text = new File(["hello, world"], "text1.txt", { type: "text/plain" });
    const text2 = new File(["hello, world"], "text2.txt", { type: "text/plain" });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    // Uploading file in the first thread: res.partner chatter.
    await openFormView("res.partner", partnerId);
    await click("button", { text: "Send message" });
    await inputFiles(".o-mail-Chatter .o-mail-Composer input[type=file]", [text]);
    // Uploading file in the second thread: discuss.channel in chatWindow.
    await click("i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await inputFiles(".o-mail-ChatWindow .o-mail-Composer input[type=file]", [text2]);
    await contains(".o-mail-Chatter .o-mail-AttachmentCard");
    await contains(".o-mail-ChatWindow .o-mail-AttachmentCard");
    await contains(
        ".o-mail-Chatter .o-mail-AttachmentCard:not(.o-isUploading):contains(text1.txt)"
    );
    await contains(
        ".o-mail-ChatWindow .o-mail-AttachmentCard:not(.o-isUploading):contains(text2.txt)"
    );
});

test("Attachment shows spinner during upload", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "channel_1" });
    const text2 = new File(["hello, world"], "text2.txt", { type: "text/plain" });
    onRpc("/mail/attachment/upload", () => new Deferred()); // never fulfill the attachment upload promise.
    await start();
    await openDiscuss(channelId);
    await inputFiles(".o-mail-Composer input[type=file]", [text2]);
    await contains(".o-mail-AttachmentCard.o-isUploading:contains(text2.txt) .fa-spinner");
});
