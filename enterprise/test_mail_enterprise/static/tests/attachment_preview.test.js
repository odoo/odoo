import {
    assertSteps,
    click,
    contains,
    dragenterFiles,
    dropFiles,
    inputFiles,
    openFormView,
    patchUiSize,
    registerArchs,
    SIZES,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { defineTestMailModels } from "@test_mail/../tests/test_mail_test_helpers";
import { browser } from "@web/core/browser/browser";
import { onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineTestMailModels();

test("Should not have attachment preview for still uploading attachment", async () => {
    const pyEnv = await startServer();
    const recordId = pyEnv["mail.test.simple.main.attachment"].create({});
    patchUiSize({ size: SIZES.XXL });
    registerArchs({
        "mail.test.simple.main.attachment,false,form": `
            <form string="Test document">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="o_attachment_preview"/>
                <chatter reload_on_attachment="True" open_attachments="True"/>
            </form>`,
    });
    let shouldBlockAttachmentUpload = false;
    onRpc("/mail/attachment/upload", () => {
        if (shouldBlockAttachmentUpload) {
            return new Promise(() => {});
        }
    });
    await start();
    await openFormView("mail.test.simple.main.attachment", recordId);
    const files = [new File([new Uint8Array(1)], "invoice.pdf", { type: "application/pdf" })];
    await dragenterFiles(".o-mail-Chatter", files);
    await dropFiles(".o-Dropzone", files);
    await contains("iframe[data-src*='/web/static/lib/pdfjs/web/viewer.html']");
    await click(
        ".o-mail-AttachmentCard:not(.o-isUploading):contains(invoice.pdf) .o-mail-AttachmentCard-unlink"
    );
    await click(".modal button", { text: "Ok" });
    await contains("iframe[data-src*='/web/static/lib/pdfjs/web/viewer.html']", { count: 0 });
    shouldBlockAttachmentUpload = true;
    await dragenterFiles(".o-mail-Chatter", files);
    await dropFiles(".o-Dropzone", files);
    await contains(".o-Dropzone", { count: 0 });
    await contains(".o-mail-Attachment", { count: 0 });
    await contains("iframe[data-src*='/web/static/lib/pdfjs/web/viewer.html']", { count: 0 });
});

test("Attachment on side", async () => {
    const pyEnv = await startServer();
    const recordId = pyEnv["mail.test.simple.main.attachment"].create({});
    const file = new File([new Uint8Array(1)], "invoice.pdf", { type: "application/pdf" });
    const attachmentId = pyEnv["ir.attachment"].create({
        mimetype: "image/jpeg",
        res_id: recordId,
        res_model: "mail.test.simple.main.attachment",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        model: "mail.test.simple.main.attachment",
        res_id: recordId,
    });
    registerArchs({
        "mail.test.simple.main.attachment,false,form": `
            <form string="Test document">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="o_attachment_preview"/>
                <chatter/>
            </form>`,
    });
    patchUiSize({ size: SIZES.XXL });
    onRpc("/mail/thread/data", () => step("/mail/thread/data"));
    onRpc("ir.attachment", "register_as_main_attachment", () =>
        step("register_as_main_attachment")
    );
    await start();
    await openFormView("mail.test.simple.main.attachment", recordId);
    await contains(".o-mail-Attachment-imgContainer > img");
    await contains(".o_form_sheet_bg > .o-mail-Form-chatter");
    await contains(".o-mail-Form-chatter:not(.o-aside)");
    await contains(".o_form_sheet_bg + .o_attachment_preview");
    // Don't display arrow if there is no previous/next element
    await contains(".arrow", { count: 0 });
    // send a message with attached PDF file
    await click("button", { text: "Send message" });
    await assertSteps(["/mail/thread/data", "register_as_main_attachment"]);
    await inputFiles(".o-mail-Composer-coreMain .o_input_file", [file]);
    await click(".o-mail-Composer-send:enabled");
    await contains(".arrow", { count: 2 });
    await assertSteps(["/mail/thread/data"]);
    await click(".o_move_next");
    await contains(".o-mail-Attachment-imgContainer > img", { count: 0 });
    await contains(".o-mail-Attachment > iframe");
    await assertSteps(["register_as_main_attachment"]);
    await click(".o_move_previous");
    await contains(".o-mail-Attachment-imgContainer > img");
    await assertSteps(["register_as_main_attachment"]);
});

test("After switching record with the form pager, when using the attachment preview navigation, the attachment should be switched", async () => {
    const pyEnv = await startServer();
    const recordId_1 = pyEnv["mail.test.simple.main.attachment"].create({
        display_name: "first partner",
        message_attachment_count: 2,
    });
    const attachmentId_1 = pyEnv["ir.attachment"].create({
        mimetype: "image/jpeg",
        res_id: recordId_1,
        res_model: "mail.test.simple.main.attachment",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId_1],
        model: "mail.test.simple.main.attachment",
        res_id: recordId_1,
    });
    const attachmentId_2 = pyEnv["ir.attachment"].create({
        mimetype: "application/pdf",
        res_id: recordId_1,
        res_model: "mail.test.simple.main.attachment",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId_2],
        model: "mail.test.simple.main.attachment",
        res_id: recordId_1,
    });

    const recordId_2 = pyEnv["mail.test.simple.main.attachment"].create({
        display_name: "second partner",
        message_attachment_count: 0,
    });
    registerArchs({
        "mail.test.simple.main.attachment,false,form": `
                <form string="Test document">
                    <sheet>
                        <field name="name"/>
                    </sheet>
                    <div class="o_attachment_preview"/>
                    <chatter/>
                </form>`,
    });
    patchUiSize({ size: SIZES.XXL });
    await start();
    await openFormView("mail.test.simple.main.attachment", recordId_1, {
        resIds: [recordId_1, recordId_2],
    });
    await contains(".o_pager_counter", { text: "1 / 2" });
    await contains(".arrow", { count: 2 });
    await click(".o_pager_next");
    await contains(".o_pager_counter", { text: "2 / 2" });
    await contains(".arrow", { count: 0 });
    await click(".o_pager_previous");
    await contains(".o_pager_counter", { text: "1 / 2" });
    await contains(".arrow", { count: 2 });
    await contains(".o-mail-Message", { count: 2 });
    await click(".o-mail-Attachment .o_move_next");
    await contains(".o-mail-Attachment-imgContainer img");
    await click(".o-mail-Attachment .o_move_previous");
    await contains(".o-mail-Attachment iframe");
});

test("Attachment on side on new record", async () => {
    const pyEnv = await startServer();
    const record = pyEnv["mail.test.simple.main.attachment"].create({});
    pyEnv["ir.attachment"].create({
        mimetype: "image/jpeg",
        res_id: record,
        res_model: "mail.test.simple.main.attachment",
    });
    registerArchs({
        "mail.test.simple.main.attachment,false,form": `
            <form string="Test document">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="o_attachment_preview"/>
                <chatter/>
            </form>`,
    });
    patchUiSize({ size: SIZES.XXL });
    await start();
    await openFormView("mail.test.simple.main.attachment", record);
    await contains(".o_attachment_preview");
    await openFormView("mail.test.simple.main.attachment");
    await contains(".o_form_sheet_bg + .o-mail-Form-chatter");
    await contains(".o_attachment_preview", { count: 0 });
});

test("Attachment on side not displayed on smaller screens", async () => {
    const pyEnv = await startServer();
    const recordId = pyEnv["mail.test.simple.main.attachment"].create({});
    const attachmentId = pyEnv["ir.attachment"].create({
        mimetype: "image/jpeg",
        res_id: recordId,
        res_model: "mail.test.simple.main.attachment",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        model: "mail.test.simple.main.attachment",
        res_id: recordId,
    });
    registerArchs({
        "mail.test.simple.main.attachment,false,form": `
            <form string="Test document">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="o_attachment_preview"/>
                <chatter/>
            </form>`,
    });
    patchUiSize({ size: SIZES.XXL });
    await start();
    await openFormView("mail.test.simple.main.attachment", recordId);
    await contains(".o_form_sheet_bg + .o-mail-Form-chatter");
    await contains(".o_attachment_preview");
    patchUiSize({ size: SIZES.XL });
    browser.dispatchEvent(new Event("resize"));
    await contains(".o_attachment_preview", { count: 0 });
});
