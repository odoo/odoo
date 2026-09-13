import {
    SIZES,
    click,
    contains,
    defineMailModels,
    inputFiles,
    onRpcBefore,
    openFormView,
    patchUiSize,
    scroll,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { mockTimeZone } from "@odoo/hoot-mock";
import { onRpc, pagerNext, pagerPrevious } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("base non-empty rendering", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["ir.attachment"].create([
        {
            mimetype: "text/plain",
            name: "Blah.txt",
            res_id: partnerId,
            res_model: "res.partner",
        },
        {
            mimetype: "text/plain",
            name: "Blu.txt",
            res_id: partnerId,
            res_model: "res.partner",
        },
    ]);
    await start();
    await openFormView("res.partner", partnerId, {
        arch: `
            <form>
                <sheet></sheet>
                <chatter open_attachments="True"/>
            </form>`,
    });
    await contains(".o-mail-AttachmentBox");
    await contains("button:text('Attach files')");
    await contains(".o-mail-Chatter input[type='file']");
    await contains(".o-mail-AttachmentList");
});

test("remove attachment should ask for confirmation", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["ir.attachment"].create({
        mimetype: "text/plain",
        name: "Blah.txt",
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", partnerId, {
        arch: `
            <form>
                <sheet></sheet>
                <chatter open_attachments="True"/>
            </form>`,
    });
    await contains(".o-mail-AttachmentCard");
    await click("button[title='Actions']");
    await click(".dropdown-item:text('Remove')");
    await contains(
        ".modal-body:text('Are you sure you want to delete \"Blah.txt\"? This action cannot be undone.')"
    );
    // Confirm the deletion
    await click(".modal-footer .btn-primary");
    await contains(".o-mail-AttachmentImage", { count: 0 });
});

test("view attachments", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["ir.attachment"].create([
        {
            mimetype: "text/plain",
            name: "Blah.txt",
            res_id: partnerId,
            res_model: "res.partner",
        },
        {
            mimetype: "text/plain",
            name: "Blu.txt",
            res_id: partnerId,
            res_model: "res.partner",
        },
    ]);
    await start();
    await openFormView("res.partner", partnerId, {
        arch: `
            <form>
                <sheet></sheet>
                <chatter open_attachments="True"/>
            </form>`,
    });
    await click('.o-mail-AttachmentContainer[aria-label="Blah.txt"] .o-mail-AttachmentCard-image');
    await contains(".o-FileViewer");
    await contains(".o-FileViewer-header:has(:text('Blah.txt'))");
    await contains(".o-FileViewer div[aria-label='Next']");
    await click(".o-FileViewer div[aria-label='Next']");
    await contains(".o-FileViewer-header:has(:text('Blu.txt'))");
    await contains(".o-FileViewer div[aria-label='Next']");
    await click(".o-FileViewer div[aria-label='Next']");
    await contains(".o-FileViewer-header:has(:text('Blah.txt'))");
});

test("scroll to attachment box when toggling on", async () => {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    for (let i = 0; i < 30; i++) {
        pyEnv["mail.message"].create({
            body: "not empty".repeat(50),
            model: "res.partner",
            res_id: partnerId,
        });
    }
    pyEnv["ir.attachment"].create({
        mimetype: "text/plain",
        name: "Blah.txt",
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Message", { count: 30 });
    await scroll(".o-mail-Chatter", "bottom");
    await click("button[aria-label='Attach files']");
    await contains(".o-mail-AttachmentBox");
    await contains(".o-mail-Chatter", { scroll: 0 });
    await contains(".o-mail-AttachmentBox", { visible: true });
});

test("do not auto-scroll to attachment box when initially open", async () => {
    patchUiSize({ size: SIZES.LG });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        res_id: partnerId,
    });
    pyEnv["ir.attachment"].create({
        mimetype: "text/plain",
        name: "Blah.txt",
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", partnerId, {
        arch: `
            <form>
                ${`<sheet><field name="name"/></sheet>`.repeat(100)}
                <chatter open_attachments="True"/>
            </form>`,
    });
    await contains(".o-mail-Message");
    // weak test, no guarantee that we waited long enough for the potential scroll to happen
    await contains(".o_content", { scroll: 0 });
});

test("attachment box should order attachments from newest to oldest", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const resData = { res_id: partnerId, res_model: "res.partner" };
    pyEnv["ir.attachment"].create([
        { name: "A.txt", mimetype: "text/plain", ...resData },
        { name: "B.txt", mimetype: "text/plain", ...resData },
        { name: "C.txt", mimetype: "text/plain", ...resData },
    ]);
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Chatter [aria-label='Attach files']:text('3')");
    await click(".o-mail-Chatter [aria-label='Attach files']"); // open attachment box
    await contains(".o-mail-AttachmentContainer:eq(0):has(:text('C.txt'))");
    await contains(".o-mail-AttachmentContainer:eq(1):has(:text('B.txt'))");
    await contains(".o-mail-AttachmentContainer:eq(2):has(:text('A.txt'))");
});

test("attachment box groups copies of the same file under a counter", async () => {
    mockTimeZone(0); // UTC, so that the create_date times are stable in the assertions
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const resData = { mimetype: "image/png", res_id: partnerId, res_model: "res.partner" };
    pyEnv["ir.attachment"].create([
        { checksum: "sign", create_date: "2026-07-25 10:00:00", name: "signature.png", ...resData },
        { checksum: "sign", create_date: "2026-07-26 10:00:00", name: "signature.png", ...resData },
        { checksum: "sign", create_date: "2026-07-27 10:00:00", name: "signature.png", ...resData },
        { checksum: "deal", create_date: "2026-07-28 10:00:00", name: "contract.png", ...resData },
    ]);
    await start();
    await openFormView("res.partner", partnerId, {
        arch: `
            <form>
                <sheet></sheet>
                <chatter open_attachments="True"/>
            </form>`,
    });
    await contains(".o-mail-AttachmentContainer", { count: 2 });
    await contains(".o-mail-AttachmentContainer[aria-label='contract.png']");
    await contains(".o-mail-AttachmentContainer[aria-label='signature.png']");
    await contains(".o-mail-Attachment-duplicateCounter", { count: 1 });
    await click(
        ".o-mail-AttachmentContainer[aria-label='signature.png'] .o-mail-Attachment-duplicateCounter",
        { text: "3" }
    );
    await contains(".o-mail-Attachment-duplicate", { count: 3 });
    await contains(
        ".o-mail-Attachment-duplicate:eq(0):text('signature.png – 07/27/2026 10:00:00')"
    );
    await contains(
        ".o-mail-Attachment-duplicate:eq(1):text('signature.png – 07/26/2026 10:00:00')"
    );
    await contains(
        ".o-mail-Attachment-duplicate:eq(2):text('signature.png – 07/25/2026 10:00:00')"
    );
});

test("a group of copies keeps the place of its oldest copy", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const resData = { mimetype: "text/plain", res_id: partnerId, res_model: "res.partner" };
    pyEnv["ir.attachment"].create([
        { checksum: "sign", create_date: "2026-07-25 10:00:00", name: "signature.txt", ...resData },
        { checksum: "deal", create_date: "2026-07-26 10:00:00", name: "contract.txt", ...resData },
        { checksum: "sign", create_date: "2026-07-27 10:00:00", name: "signature.txt", ...resData },
    ]);
    await start();
    await openFormView("res.partner", partnerId, {
        arch: `
            <form>
                <sheet></sheet>
                <chatter open_attachments="True"/>
            </form>`,
    });
    await contains(".o-mail-AttachmentContainer", { count: 2 });
    await contains(".o-mail-AttachmentContainer:eq(0):has(:text('contract.txt'))");
    await contains(".o-mail-AttachmentContainer:eq(1):has(:text('signature.txt'))");
    await contains(".o-mail-Attachment-duplicateCounter:text('2')");
});

test("removing a copy from the dropdown keeps the other copies", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const resData = { mimetype: "image/png", res_id: partnerId, res_model: "res.partner" };
    pyEnv["ir.attachment"].create([
        { checksum: "sign", create_date: "2026-07-25 10:00:00", name: "signature.png", ...resData },
        { checksum: "sign", create_date: "2026-07-26 10:00:00", name: "signature.png", ...resData },
        { checksum: "sign", create_date: "2026-07-27 10:00:00", name: "signature.png", ...resData },
    ]);
    await start();
    await openFormView("res.partner", partnerId, {
        arch: `
            <form>
                <sheet></sheet>
                <chatter open_attachments="True"/>
            </form>`,
    });
    await click(".o-mail-Attachment-duplicateCounter", { text: "3" });
    await click(".o-mail-Attachment-duplicate:eq(0) [title='Remove']");
    await contains(
        ".modal-body:text('Are you sure you want to delete \"signature.png\"? This action cannot be undone.')"
    );
    await click(".modal-footer .btn-primary");
    await contains(".o-mail-AttachmentContainer[aria-label='signature.png']");
    await contains(".o-mail-Attachment-duplicateCounter:text('2')");
    await contains(".o-mail-Chatter [aria-label='Attach files']:text('2')");
});

test("removing a group of copies asks confirmation and removes all of them at once", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const resData = { mimetype: "image/png", res_id: partnerId, res_model: "res.partner" };
    pyEnv["ir.attachment"].create([
        { checksum: "sign", create_date: "2026-07-25 10:00:00", name: "signature.png", ...resData },
        { checksum: "sign", create_date: "2026-07-26 10:00:00", name: "signature.png", ...resData },
        { checksum: "deal", create_date: "2026-07-28 10:00:00", name: "contract.png", ...resData },
    ]);
    onRpcBefore("/mail/attachment/delete", ({ access_token_by_attachment_id }) =>
        expect.step(`delete ${Object.keys(access_token_by_attachment_id).length}`)
    );
    await start();
    await openFormView("res.partner", partnerId, {
        arch: `
            <form>
                <sheet></sheet>
                <chatter open_attachments="True"/>
            </form>`,
    });
    await click(".o-mail-AttachmentContainer[aria-label='signature.png'] button[title='Actions']");
    await click(".dropdown-item:text('Remove')");
    await contains(
        ".modal-body:text('Are you sure you want to delete the 2 copies of \"signature.png\"? This action cannot be undone.')"
    );
    await click(".modal-footer button:text('Delete Attachment & Duplicates')");
    await contains(".o-mail-AttachmentContainer", { count: 1 });
    await contains(".o-mail-AttachmentContainer[aria-label='contract.png']");
    // both copies are removed by a single query
    await expect.waitForSteps(["delete 2"]);
});

test("removing a group of copies can spare the attachment it stands for", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const resData = { mimetype: "image/png", res_id: partnerId, res_model: "res.partner" };
    pyEnv["ir.attachment"].create([
        { checksum: "sign", create_date: "2026-07-25 10:00:00", name: "signature.png", ...resData },
        { checksum: "sign", create_date: "2026-07-26 10:00:00", name: "signature.png", ...resData },
        { checksum: "sign", create_date: "2026-07-27 10:00:00", name: "signature.png", ...resData },
    ]);
    onRpcBefore("/mail/attachment/delete", ({ access_token_by_attachment_id }) =>
        expect.step(`delete ${Object.keys(access_token_by_attachment_id).length}`)
    );
    await start();
    await openFormView("res.partner", partnerId, {
        arch: `
            <form>
                <sheet></sheet>
                <chatter open_attachments="True"/>
            </form>`,
    });
    await click(".o-mail-AttachmentContainer[aria-label='signature.png'] button[title='Actions']");
    await click(".dropdown-item:text('Remove')");
    await click(".modal-footer button:text('Delete only Duplicates')");
    await contains(".o-mail-AttachmentContainer", { count: 1 });
    await contains(".o-mail-AttachmentContainer[aria-label='signature.png']");
    await contains(".o-mail-Chatter [aria-label='Attach files']:text('1')");
    // the 2 redundant copies are removed by a single query
    await expect.waitForSteps(["delete 2"]);
});

test("removing a copy posted on a message only removes it from the list", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const resData = { mimetype: "image/png", res_id: partnerId, res_model: "res.partner" };
    const [, postedId] = pyEnv["ir.attachment"].create([
        { checksum: "sign", create_date: "2026-07-25 10:00:00", name: "signature.png", ...resData },
        { checksum: "sign", create_date: "2026-07-26 10:00:00", name: "signature.png", ...resData },
    ]);
    pyEnv["mail.message"].create({
        attachment_ids: [postedId],
        body: "<p>Signed</p>",
        message_type: "comment",
        model: "res.partner",
        res_id: partnerId,
    });
    await start();
    await openFormView("res.partner", partnerId, {
        arch: `
            <form>
                <sheet></sheet>
                <chatter open_attachments="True"/>
            </form>`,
    });
    await contains(".o-mail-Message .o-mail-AttachmentContainer[aria-label='signature.png']");
    await click(".o-mail-AttachmentBox .o-mail-AttachmentContainer button[title='Actions']");
    await click(".dropdown-item:text('Remove')");
    await click(".modal-footer button:text('Delete only Duplicates')");
    await contains(".o-mail-AttachmentBox .o-mail-AttachmentContainer", { count: 1 });
    await contains(".o-mail-Chatter [aria-label='Attach files']:text('1')");
    // trimming the list is not meant to edit the message the copy was posted on
    await contains(".o-mail-Message .o-mail-AttachmentContainer[aria-label='signature.png']");
});

test("selecting several files deletes their copies in one go", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const resData = { mimetype: "image/png", res_id: partnerId, res_model: "res.partner" };
    pyEnv["ir.attachment"].create([
        { checksum: "sign", create_date: "2026-07-25 10:00:00", name: "signature.png", ...resData },
        { checksum: "sign", create_date: "2026-07-26 10:00:00", name: "signature.png", ...resData },
        { checksum: "deal", create_date: "2026-07-27 10:00:00", name: "contract.png", ...resData },
        { checksum: "deal", create_date: "2026-07-28 10:00:00", name: "contract.png", ...resData },
        { checksum: "logo", create_date: "2026-07-29 10:00:00", name: "logo.png", ...resData },
    ]);
    onRpcBefore("/mail/attachment/delete", ({ access_token_by_attachment_id }) =>
        expect.step(`delete ${Object.keys(access_token_by_attachment_id).length}`)
    );
    await start();
    await openFormView("res.partner", partnerId, {
        arch: `
            <form>
                <sheet></sheet>
                <chatter open_attachments="True"/>
            </form>`,
    });
    await contains(".o-mail-AttachmentContainer", { count: 3 });
    await click(".o-mail-Chatter-selectFiles");
    await contains(".o-mail-Attachment-selectCheckbox", { count: 3 });
    await contains(".o-mail-Chatter-deleteSelected.btn-secondary:disabled:text('Delete 0 files')");
    await click(".o-mail-AttachmentContainer[aria-label='signature.png']");
    await contains(".o-mail-Chatter-deleteSelected.btn-danger:text('Delete 1 file')");
    await click(".o-mail-AttachmentContainer[aria-label='contract.png']");
    await contains(".o-mail-Attachment-selectCheckbox:checked", { count: 2 });
    await contains(".o-mail-Chatter-deleteSelected.btn-danger:text('Delete 2 files')");
    await click(".o-mail-Chatter-deleteSelected");
    await contains(
        ".modal-body:text('Are you sure you want to delete the 2 selected files and their copies? This action cannot be undone.')"
    );
    await click(".modal-footer button:text('Delete only Duplicates')");
    await contains(".o-mail-AttachmentContainer", { count: 3 });
    await contains(".o-mail-Attachment-duplicateCounter", { count: 0 });
    await contains(".o-mail-Chatter [aria-label='Attach files']:text('3')");
    // the redundant copy of each selected file is removed by a single query
    await expect.waitForSteps(["delete 2"]);
    // deleting ends the selection
    await contains(".o-mail-Chatter-selectFiles");
});

test("discarding the selection restores the attach files button", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const resData = { mimetype: "image/png", res_id: partnerId, res_model: "res.partner" };
    pyEnv["ir.attachment"].create([
        { checksum: "sign", create_date: "2026-07-25 10:00:00", name: "signature.png", ...resData },
        { checksum: "deal", create_date: "2026-07-26 10:00:00", name: "contract.png", ...resData },
    ]);
    await start();
    await openFormView("res.partner", partnerId, {
        arch: `
            <form>
                <sheet></sheet>
                <chatter open_attachments="True"/>
            </form>`,
    });
    await click(".o-mail-Chatter-selectFiles");
    await click(".o-mail-AttachmentContainer[aria-label='signature.png']");
    await contains(".o-mail-Attachment-selectCheckbox:checked", { count: 1 });
    await click(".o-mail-Chatter-discardSelection");
    await contains(".o-mail-Chatter-attachmentActions button:text('Attach files')");
    await contains(".o-mail-Attachment-selectCheckbox", { count: 0 });
});

test("attachment box auto-closed on switch to record wih no attachments", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { display_name: "first partner" },
        { display_name: "second partner" },
    ]);
    pyEnv["ir.attachment"].create([
        {
            mimetype: "text/plain",
            name: "Blah.txt",
            res_id: partnerId_1,
            res_model: "res.partner",
        },
    ]);
    await start();
    await openFormView("res.partner", partnerId_1, {
        arch: `
            <form>
                <sheet></sheet>
                <chatter open_attachments="True"/>
            </form>`,
        resIds: [partnerId_1, partnerId_2],
    });
    await contains(".o-mail-AttachmentBox");
    await click(".o_pager_next");
    await contains(".o-mail-AttachmentBox", { count: 0 });
});

test("removing the last attachment should close the attachment box", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["ir.attachment"].create({
        mimetype: "text/plain",
        name: "Blah.txt",
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", partnerId, {
        arch: `
            <form>
                <sheet></sheet>
                <chatter open_attachments="True"/>
            </form>`,
    });
    await contains(".o-mail-AttachmentBox");
    await click("button[title='Actions']");
    await click(".dropdown-item:text('Remove')");
    await contains(
        ".modal-body:text('Are you sure you want to delete \"Blah.txt\"? This action cannot be undone.')"
    );
    // Confirm the deletion
    await click(".modal-footer .btn-primary");
    await contains(".o-mail-AttachmentBox", { count: 0 });
});

test("attachment should be uploaded on the correct record when using the pager navigation", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { display_name: "first partner" },
        { display_name: "second partner" },
    ]);
    await start();
    await openFormView("res.partner", partnerId_1, {
        arch: `
            <form>
                <sheet><field name="display_name"/></sheet>
                <div class="oe_chatter"><chatter/></div>
            </form>`,
        resIds: [partnerId_1, partnerId_2],
    });
    // First upload
    let uploadDeferred = Promise.withResolvers();
    onRpc("/mail/attachment/upload", () => uploadDeferred.promise);
    await click(".o-mail-Chatter-attachFiles");
    let uploadPromise = inputFiles(".o_input_file", [new File(["image"], "A.jpeg")]);
    await pagerNext();
    uploadDeferred.resolve();
    await uploadPromise;
    await contains("button[aria-label='Attach files']:not(:has(sup))");
    await pagerPrevious();
    await click("button[aria-label='Attach files']", { text: "1" });
    await contains(".o-mail-AttachmentCard", { text: "A.jpeg" });
    // Second upload
    uploadDeferred = Promise.withResolvers();
    await click("button[aria-label='Attach files']");
    await click("button", { text: "Attach files" });
    uploadPromise = inputFiles(".o_input_file", [new File(["image"], "B.jpeg")]);
    await pagerNext();
    uploadDeferred.resolve();
    await uploadPromise;
    await contains("button[aria-label='Attach files']:not(:has(sup))");
    await pagerPrevious();
    await click("button[aria-label='Attach files']", { text: "2" });
    await contains(".o-mail-AttachmentCard", { text: "A.jpeg" });
    await contains(".o-mail-AttachmentCard", { text: "B.jpeg" });
});
