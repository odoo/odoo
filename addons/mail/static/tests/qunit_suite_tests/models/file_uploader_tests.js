/* @odoo-module */

import { start, startServer } from "@mail/../tests/helpers/test_utils";
import {
    click,
    contains,
    createFile,
    dropFiles,
    dragenterFiles,
    triggerEvents,
} from "@web/../tests/utils";

QUnit.module("mail", {}, function () {
QUnit.module("components", {}, function () {
QUnit.module("file_uploader", {}, function () {
QUnit.module("file_uploader_tests.js");

QUnit.test("no conflicts between file uploaders", async function () {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({});
    const channelId = pyEnv["mail.channel"].create({});
    const { openView } = await start();
    // Uploading file in the first thread: res.partner chatter.
    await openView({
        res_id: resPartnerId1,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    const file1 = await createFile({
        name: "text1.txt",
        content: "hello, world",
        contentType: "text/plain",
    });
    await dragenterFiles(".o_Chatter", [file1]);
    await dropFiles(".o_Chatter_dropZone", [file1]);
    // Uploading file in the second thread: mail.channel in chatWindow.
    await click(".o_MessagingMenu_toggler");
    await click(`.o_ChannelPreviewView[data-channel-id="${channelId}"]`);
    const file2 = await createFile({
        name: "text2.txt",
        content: "hello, world",
        contentType: "text/plain",
    });
    await dragenterFiles(".o_ChatWindow", [file2]);
    await dropFiles(".o_ChatWindow .o_DropZone", [file2]);
    await contains(".o_ChatWindow .o_Composer .o_AttachmentCard:not(.o-isUploading)");
    await triggerEvents(".o_ChatWindow .o_ComposerTextInput_textarea", [
        ["keydown", { key: "Enter" }],
    ]);
    await contains(".o_Chatter .o_AttachmentCard");
    await contains(".o_ChatWindow .o_Message .o_AttachmentCard");
});
});
});
});
