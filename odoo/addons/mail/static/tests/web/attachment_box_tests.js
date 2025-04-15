/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains, scroll, createFile, dragenterFiles, dropFiles } from "@web/../tests/utils";

QUnit.module("attachment box");

QUnit.test("base non-empty rendering", async () => {
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
    const views = {
        "res.partner,false,form": `
            <form>
                <sheet></sheet>
                <div class="oe_chatter">
                    <field name="message_ids"  options="{'open_attachments': True}"/>
                </div>
            </form>
        `,
    };
    const { openView } = await start({ serverData: { views } });
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains(".o-mail-AttachmentBox");
    await contains("button", { text: "Attach files" });
    await contains(".o-mail-Chatter input[type='file']");
    await contains(".o-mail-AttachmentList");
});

QUnit.test("remove attachment should ask for confirmation", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["ir.attachment"].create({
        mimetype: "text/plain",
        name: "Blah.txt",
        res_id: partnerId,
        res_model: "res.partner",
    });
    const views = {
        "res.partner,false,form": `
            <form>
                <sheet></sheet>
                <div class="oe_chatter">
                    <field name="message_ids"  options="{'open_attachments': True}"/>
                </div>
            </form>
        `,
    };
    const { openView } = await start({ serverData: { views } });
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains(".o-mail-AttachmentCard");
    await contains("button[title='Remove']");

    await click("button[title='Remove']");
    await contains(".modal-body", { text: 'Do you really want to delete "Blah.txt"?' });

    // Confirm the deletion
    await click(".modal-footer .btn-primary");
    await contains(".o-mail-AttachmentImage", { count: 0 });
});

QUnit.test("view attachments", async () => {
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
    const views = {
        "res.partner,false,form": `<form>
            <sheet></sheet>
            <div class="oe_chatter">
                <field name="message_ids"  options="{'open_attachments': True}"/>
            </div>
        </form>`,
    };
    const { openView } = await start({ serverData: { views } });
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await click('.o-mail-AttachmentCard[aria-label="Blah.txt"] .o-mail-AttachmentCard-image');
    await contains(".o-FileViewer");
    await contains(".o-FileViewer-header", { text: "Blah.txt" });
    await contains(".o-FileViewer div[aria-label='Next']");

    await click(".o-FileViewer div[aria-label='Next']");
    await contains(".o-FileViewer-header", { text: "Blu.txt" });
    await contains(".o-FileViewer div[aria-label='Next']");

    await click(".o-FileViewer div[aria-label='Next']");
    await contains(".o-FileViewer-header", { text: "Blah.txt" });
});

QUnit.test("scroll to attachment box when toggling on", async () => {
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
    const { openView } = await start();
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains(".o-mail-Message", { count: 30 });
    await scroll(".o-mail-Chatter", "bottom");
    await click("button[aria-label='Attach files']");
    await contains(".o-mail-AttachmentBox");
    await contains(".o-mail-Chatter", { scroll: 0 });
    await contains(".o-mail-AttachmentBox", { visible: true });
});

QUnit.test("do not auto-scroll to attachment box when initially open", async () => {
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
    const views = {
        "res.partner,false,form": `
            <form>
                ${`<sheet><field name="name"/></sheet>`.repeat(100)}
                <div class="oe_chatter">
                    <field name="message_ids"  options="{'open_attachments': True}"/>
                </div>
            </form>
        `,
    };
    const { openFormView } = await start({ serverData: { views } });
    openFormView("res.partner", partnerId);
    await contains(".o-mail-Message");
    // weak test, no guarantee that we waited long enough for the potential scroll to happen
    await contains(".o_content", { scroll: 0 });
});

QUnit.test("attachment box should order attachments from newest to oldest", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const resData = { res_id: partnerId, res_model: "res.partner" };
    pyEnv["ir.attachment"].create([
        { name: "A.txt", mimetype: "text/plain", ...resData },
        { name: "B.txt", mimetype: "text/plain", ...resData },
        { name: "C.txt", mimetype: "text/plain", ...resData },
    ]);
    const { openView } = await start();
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains(".o-mail-Chatter [aria-label='Attach files']", { text: "3" });
    await click(".o-mail-Chatter [aria-label='Attach files']"); // open attachment box
    await contains(":nth-child(1 of .o-mail-AttachmentCard)", { text: "C.txt" });
    await contains(":nth-child(2 of .o-mail-AttachmentCard)", { text: "B.txt" });
    await contains(":nth-child(3 of .o-mail-AttachmentCard)", { text: "A.txt" });
});

QUnit.test("attachment box auto-closed on switch to record wih no attachments", async () => {
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
    const views = {
        "res.partner,false,form": `
            <form>
                <sheet></sheet>
                <div class="oe_chatter">
                    <field name="message_ids"  options="{'open_attachments': True}"/>
                </div>
            </form>
        `,
    };
    const { openFormView } = await start({ serverData: { views } });
    await openFormView("res.partner", partnerId_1, {
        props: { resIds: [partnerId_1, partnerId_2] },
    });
    await contains(".o-mail-AttachmentBox");
    await click(".o_pager_next");
    await contains(".o-mail-AttachmentBox", { count: 0 });
});

QUnit.test('Chatter main attachment: can change from non-viewable to viewable', async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId = pyEnv['res.partner'].create({});
    const irAttachmentId = pyEnv['ir.attachment'].create({
        mimetype: 'text/plain',
        name: "Blah.txt",
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
            if (String(route).includes("/web/static/lib/pdfjs/web/viewer.html")) {
                var canvas = document.createElement('canvas');
                return canvas.toDataURL();
            }
        },
        serverData: { views },
    });
    await openFormView('res.partner', resPartnerId);

    // Add a PDF file
    const pdfFile = await createFile({ name: "invoice.pdf", contentType: "application/pdf" });
    await dragenterFiles(".o-mail-Chatter", [pdfFile]);
    await dropFiles(".o-mail-Dropzone", [pdfFile]);
    await contains(".o-mail-Attachment > iframe", { count: 0 }); // The viewer tries to display the text file not the PDF

    // Switch to the PDF file in the viewer
    await click(".o_move_next");
    await contains(".o-mail-Attachment > iframe"); // There should be iframe for PDF viewer
});
