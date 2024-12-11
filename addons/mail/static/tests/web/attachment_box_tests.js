/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains, createFile, inputFiles, scroll } from "@web/../tests/utils";

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

QUnit.test(
    "open attachment box should remain open after adding a new attachment",
    async (assert) => {
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
        const views = {
            "mail.test.simple.main.attachment,false,form": `
            <form string="Test document">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="o_attachment_preview"/>
                <div class="oe_chatter">
                    <field name="message_ids"  options="{'post_refresh': 'always'}"/>
                </div>
            </form>`,
        };
        patchUiSize({ size: SIZES.XXL });
        const { openFormView } = await start({
            async mockRPC(route, args) {
                if (String(route).includes("/mail/thread/data")) {
                    await new Promise((resolve) => setTimeout(resolve, 1)); // need extra time for useEffect hook
                }
            },
            serverData: { views },
        });
        await openFormView("mail.test.simple.main.attachment", recordId);
        await contains(".o-mail-Attachment-imgContainer > img");
        await contains(".o_form_sheet_bg > .o-mail-Form-chatter");
        await contains(".o-mail-Form-chatter:not(.o-aside)");
        await contains(".o_form_sheet_bg + .o_attachment_preview");
        await click("button", { text: "Send message" });
        await inputFiles(".o-mail-Composer-coreMain .o_input_file", [
            await createFile({ name: "invoice.pdf", contentType: "application/pdf" }),
        ]);
        await click(".o-mail-Chatter-attachFiles");
        await contains(".o-mail-AttachmentBox");
        await click(".o-mail-Composer-send:enabled");
        await new Promise((resolve) => setTimeout(resolve, 100));
        await contains(".o-mail-AttachmentBox");
    }
);
