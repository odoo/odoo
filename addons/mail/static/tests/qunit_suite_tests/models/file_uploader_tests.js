/* @odoo-module */

import { start, startServer } from "@mail/../tests/helpers/test_utils";
import { patchUiSize, SIZES } from '@mail/../tests/helpers/patch_ui_size';
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

QUnit.test('Chatter main attachment: can change from non-viewable to viewable', async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId = pyEnv['res.partner'].create({});
    const irAttachmentId = pyEnv['ir.attachment'].create({
        mimetype: 'text/plain',
        res_id: resPartnerId,
        res_model: 'res.partner',
    });
    pyEnv['mail.message'].create({
        attachment_ids: [irAttachmentId],
        model: 'res.partner',
        res_id: resPartnerId,
    });
    pyEnv['res.partner'].write([resPartnerId], {message_main_attachment_id : irAttachmentId})
    const views = {
        'res.partner,false,form':
            '<form string="Partners">' +
                '<sheet>' +
                    '<field name="name"/>' +
                '</sheet>' +
                '<div class="o_attachment_preview"/>' +
                '<div class="oe_chatter">' +
                    '<field name="message_ids"/>' +
                '</div>' +
            '</form>',
    };
    patchUiSize({ size: SIZES.XXL });
    const { openFormView } = await start({
        mockRPC(route, args) {
            if (_.str.contains(route, '/web/static/lib/pdfjs/web/viewer.html')) {
                var canvas = document.createElement('canvas');
                return canvas.toDataURL();
            }
        },
        serverData: { views },
    });
    await openFormView({
        res_id: resPartnerId,
        res_model: 'res.partner',
    });

    // Add a PDF file
    await click(".o_ChatterTopbar_buttonSendMessage");
    const pdfFile = await createFile({ name: "invoice.pdf", contentType: "application/pdf" });
    await dragenterFiles(".o_Chatter", [pdfFile]);
    await dropFiles(".o_Chatter_dropZone", [pdfFile]);
    await contains(".o_attachment_preview_container > iframe", { count: 0 }); // The viewer tries to display the text file not the PDF

    // Switch to the PDF file in the viewer
    await click(".o_move_next");
    await contains(".o_attachment_preview_container > iframe"); // There should be iframe for PDF viewer
});

});
});
});
