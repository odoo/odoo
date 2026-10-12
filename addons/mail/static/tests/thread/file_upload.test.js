import {
    click,
    defineMailModels,
    inputFiles,
    openDiscuss,
    openFormView,
    openMessagingMenu,
    start,
    startServer,
    MENU_ACTIVE_IDS,
} from "@mail/../tests/mail_test_helpers";
import { describe, test, waitFor } from "@odoo/hoot";
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
    await click("button:text('Send message')");
    await inputFiles(".o-mail-Chatter .o-mail-Composer input[type=file]", [text]);
    // Uploading file in the second thread: discuss.channel in chatWindow.
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await click(".o-mail-NotificationItem");
    await inputFiles(".o-mail-ChatWindow .o-mail-Composer input[type=file]", [text2]);
    await waitFor(".o-mail-Chatter .o-mail-AttachmentContainer:count(1)");
    await waitFor(".o-mail-ChatWindow .o-mail-AttachmentContainer:count(1)");
    await waitFor(
        ".o-mail-Chatter .o-mail-AttachmentContainer:not(.o-isUploading):contains(text1.txt):count(1)"
    );
    await waitFor(
        ".o-mail-ChatWindow .o-mail-AttachmentContainer:not(.o-isUploading):contains(text2.txt):count(1)"
    );
});

test("Attachment shows spinner during upload", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "channel_1" });
    const text2 = new File(["hello, world"], "text2.txt", { type: "text/plain" });
    onRpc("/mail/attachment/upload", () => new Promise(() => {})); // never fulfill the attachment upload promise.
    await start();
    await openDiscuss(channelId);
    await inputFiles(".o-mail-Composer input[type=file]", [text2]);
    await waitFor(
        ".o-mail-AttachmentContainer.o-isUploading:contains(text2.txt) [data-icon='autorenew']:count(1)"
    );
});
