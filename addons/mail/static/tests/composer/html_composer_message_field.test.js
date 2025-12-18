import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { FileSelector } from "@html_editor/main/media/media_dialog/file_selector";
import { uploadService } from "@html_editor/main/media/media_dialog/upload_progress_toast/upload_service";
import { HtmlComposerMessageField } from "@mail/views/web/fields/html_composer_message_field/html_composer_message_field";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import {
    manuallyDispatchProgrammaticEvent,
    press,
    queryAll,
    queryAllTexts,
    queryOne,
    waitFor,
    waitForNone,
} from "@odoo/hoot-dom";
import { Deferred, animationFrame } from "@odoo/hoot-mock";
import {
    contains,
    makeMockServer,
    mockService,
    mountView,
    mountViewInDialog,
    onRpc,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import {
    click,
    defineMailModels,
    mailModels,
    openFormView,
    openView,
    registerArchs,
    start,
    startServer,
} from "../mail_test_helpers";

// Need this hack to use the arch in mountView(...)
mailModels.MailComposeMessage._views = {};

defineMailModels([]);

let htmlEditor;
beforeEach(() => {
    patchWithCleanup(HtmlComposerMessageField.prototype, {
        onEditorLoad(editor) {
            htmlEditor = editor;
            return super.onEditorLoad(...arguments);
        },
    });
});

test("media dialog: upload", async function () {
    const isUploaded = new Deferred();
    patchWithCleanup(FileSelector.prototype, {
        async onUploaded() {
            await super.onUploaded(...arguments);
            isUploaded.resolve();
        },
    });

    mockService("upload", uploadService);

    const { env } = await makeMockServer();
    const resId = env["mail.compose.message"].create({
        display_name: "Some Composer",
        body: "Hello",
        attachment_ids: [],
    });

    let newAttachmentId;
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        const createVals = args[1];
        expect(createVals.attachment_ids[0][0]).toBe(4); // link command
        expect(createVals.attachment_ids[0][1]).toBe(newAttachmentId); // on attachment id "5"
    });
    onRpc("/html_editor/attachment/add_data", () => {
        const attachment = {
            name: "test.jpg",
            description: false,
            mimetype: "image/jpeg",
            checksum: "7951a43bbfb08fd742224ada280913d1897b89ab",
            url: false,
            type: "binary",
            res_id: 0,
            res_model: "mail.compose.message",
            public: false,
            access_token: false,
            image_src: "/web/image/1-a0e63e61/test.jpg",
            image_width: 1,
            image_height: 1,
            original_id: false,
        };
        newAttachmentId = env["ir.attachment"].create(attachment);
        attachment.id = newAttachmentId;
        return attachment;
    });

    onRpc("ir.attachment", "generate_access_token", () => ["129a52e1-6bf2-470a-830e-8e368b022e13"]);
    await mountView({
        type: "form",
        resId,
        resModel: "mail.compose.message",
        arch: `
        <form>
            <field name="body" type="html" widget="html_composer_message"/>
            <field name="attachment_ids" widget="many2many_binary"/>
        </form>`,
    });

    const anchorNode = queryOne(".odoo-editor-editable div.o-paragraph");
    setSelection({ anchorNode, anchorOffset: 0 });

    // Open media dialog
    await animationFrame();
    await insertText(htmlEditor, "/image");
    await press("Enter");
    await animationFrame();

    // upload test
    const fileInputs = queryAll(".o_select_media_dialog input.d-none.o_file_input");
    const fileB64 =
        "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD3+iiigD//2Q==";
    const fileBytes = new Uint8Array(
        atob(fileB64)
            .split("")
            .map((char) => char.charCodeAt(0))
    );
    // redefine 'files' so we can put mock data in through js
    fileInputs.forEach((input) =>
        Object.defineProperty(input, "files", {
            value: [new File(fileBytes, "test.jpg", { type: "image/jpeg" })],
        })
    );
    fileInputs.forEach((input) => {
        manuallyDispatchProgrammaticEvent(input, "change");
    });
    expect("[name='attachment_ids'] .o_attachment[title='test.jpg']").toHaveCount(0);

    await isUploaded;
    await animationFrame();
    expect("[name='attachment_ids'] .o_attachment[title='test.jpg']").toHaveCount(1);

    await contains(".o_form_button_save").click();
    await expect.waitForSteps(["web_save"]);
});

test("mention a partner", async () => {
    onRpc("res.partner", "get_mention_suggestions", ({ kwargs }) => {
        expect.step(`get_mention_suggestions: ${kwargs.search}`);
    });
    const pyEnv = await startServer();
    registerArchs({
        "mail.compose.message,false,form": `
        <form>
            <field name="body" type="html" widget="html_composer_message"/>
        </form>`,
    });
    const composerId = pyEnv["mail.compose.message"].create({
        subject: "Greetings",
        body: "<p><br></p>",
        model: "res.partner",
    });
    await start();
    await openView({
        res_model: "mail.compose.message",
        res_id: composerId,
        views: [["mail.compose.message,false,form", "form"]],
    });
    const anchorNode = queryOne(`.odoo-editor-editable p`);
    setSelection({ anchorNode, anchorOffset: 0 });
    await insertText(htmlEditor, "@");
    await animationFrame();
    expect(".overlay .search input[placeholder='Search for a user...']").toBeFocused();
    expect(".overlay .o-mail-NavigableList .o-mail-NavigableList-item").toHaveCount(0);

    await press("a");
    await waitFor(".overlay .o-mail-NavigableList .o-mail-NavigableList-item");
    expect(queryAllTexts(".overlay .o-mail-NavigableList .o-mail-NavigableList-item")).toEqual([
        "Mitchell Admin",
    ]);
    expect.verifySteps(["get_mention_suggestions: a"]);

    await press("enter");
    expect("[name='body'] .odoo-editor-editable").toHaveInnerHTML(`
    <p>
        <a target="_blank" data-oe-protected="true" contenteditable="false" href="https://www.hoot.test/odoo/res.partner/17" class="o_mail_redirect" data-oe-id="17" data-oe-model="res.partner">
            @Mitchell Admin
        </a>
    </p>`);
});

test("mention a channel", async () => {
    onRpc("discuss.channel", "get_mention_suggestions", ({ kwargs }) => {
        expect.step(`get_mention_suggestions: ${kwargs.search}`);
    });
    await mountViewInDialog({
        type: "form",
        resModel: "mail.compose.message",
        arch: `
        <form>
            <field name="body" type="html" widget="html_composer_message"/>
        </form>`,
    });
    const anchorNode = queryOne(`[name='body'] .odoo-editor-editable div.o-paragraph`);
    setSelection({ anchorNode, anchorOffset: 0 });
    await insertText(htmlEditor, "#");
    await animationFrame();
    expect(".overlay .search input[placeholder='Search for a channel...']").toBeFocused();
    expect(".overlay .o-mail-NavigableList .o-mail-NavigableList-item").toHaveCount(0);

    await press("a");
    await animationFrame();
    expect.verifySteps(["get_mention_suggestions: a"]);
});

describe("Remove attachments", () => {
    beforeEach(() => {
        mailModels.MailComposeMessage._views = {
            "form,false": `
            <form js_class="mail_composer_form">
                <field name="body" type="html" widget="html_composer_message"/>
                <field name="attachment_ids" widget="mail_composer_attachment_list"/>
            </form>`,
        };
    });

    test("should remove file from html editor if removed from attachment list", async () => {
        mockService("uploadLocalFiles", {
            async upload() {
                expect.step("File Uploaded");
                return [{ id: 1, name: "file.txt", public: true, checksum: "123" }];
            },
        });
        await start();
        await openFormView("res.partner", serverState.partnerId);
        await click("button", { text: "Log note" });
        await click("button[title='Open Full Composer']");
        await waitFor(".odoo-editor-editable");
        const anchorNode = queryOne(".odoo-editor-editable div.o-paragraph");
        setSelection({ anchorNode, anchorOffset: 0 });
        await insertText(htmlEditor, "/file");
        await press("Enter");
        await expect.waitForSteps(["File Uploaded"]);
        await waitFor("[name='attachment_ids'] a:contains('file.txt')");
        await waitFor(".odoo-editor-editable .o_file_box:has(a:contains('file.txt'))");
        await click("[name='attachment_ids'] button:has(i.fa-times)");
        await waitForNone("[name='attachment_ids'] a:contains('file.txt')");
        await waitForNone(".odoo-editor-editable .o_file_box:has(a:contains('file.txt'))");
    });

    test("should remove image from html editor if removed from attachment list", async () => {
        patchWithCleanup(FileSelector.prototype, {
            async onUploaded() {
                await super.onUploaded(...arguments);
                expect.step("Image Uploaded");
            },
        });
        onRpc("/html_editor/attachment/add_data", () => ({
            id: 1,
            name: "test.jpg",
            description: false,
            mimetype: "image/jpeg",
            checksum: "7951a43bbfb08fd742224ada280913d1897b89ab",
            url: false,
            type: "binary",
            res_id: 0,
            res_model: "mail.compose.message",
            public: false,
            access_token: false,
            image_src: "/web/image/1-a0e63e61/test.jpg",
            image_width: 1,
            image_height: 1,
            original_id: false,
        }));
        onRpc("ir.attachment", "generate_access_token", () => [
            "129a52e1-6bf2-470a-830e-8e368b022e13",
        ]);

        await start();
        await openFormView("res.partner", serverState.partnerId);
        await click("button", { text: "Log note" });
        await click("button[title='Open Full Composer']");
        await waitFor(".odoo-editor-editable");
        const anchorNode = queryOne(".odoo-editor-editable div.o-paragraph");
        setSelection({ anchorNode, anchorOffset: 0 });
        await insertText(htmlEditor, "/image");
        await press("Enter");
        await animationFrame();
        const fileInput = queryOne(".o_select_media_dialog input.d-none.o_file_input");
        Object.defineProperty(fileInput, "files", {
            value: [new File([], "test.jpg", { type: "image/jpeg" })],
        });
        manuallyDispatchProgrammaticEvent(fileInput, "change");
        await expect.waitForSteps(["Image Uploaded"]);
        await waitFor("[name='attachment_ids'] a:contains('test.jpg')");
        await waitFor(".odoo-editor-editable img[data-attachment-id='1']");
        await click("[name='attachment_ids'] button:has(i.fa-times)");
        await waitForNone("[name='attachment_ids'] a:contains('test.jpg')");
        await waitForNone(".odoo-editor-editable img[data-attachment-id='1']");
    });
});
