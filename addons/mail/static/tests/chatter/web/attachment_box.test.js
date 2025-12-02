import {
    SIZES,
    click,
    contains,
    defineMailModels,
    openFormView,
    patchUiSize,
    scroll,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";

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
    await contains("button", { text: "Attach files" });
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
    await contains("button[title='Remove']");
    await click("button[title='Remove']");
    await contains(".modal-body", { text: 'Do you really want to delete "Blah.txt"?' });
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
    await contains(".o-FileViewer-header", { text: "Blah.txt" });
    await contains(".o-FileViewer div[aria-label='Next']");
    await click(".o-FileViewer div[aria-label='Next']");
    await contains(".o-FileViewer-header", { text: "Blu.txt" });
    await contains(".o-FileViewer div[aria-label='Next']");
    await click(".o-FileViewer div[aria-label='Next']");
    await contains(".o-FileViewer-header", { text: "Blah.txt" });
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
    await contains(".o-mail-Chatter [aria-label='Attach files']", { text: "3" });
    await click(".o-mail-Chatter [aria-label='Attach files']"); // open attachment box
    await contains(":nth-child(1 of .o-mail-AttachmentContainer)", { text: "C.txt" });
    await contains(":nth-child(2 of .o-mail-AttachmentContainer)", { text: "B.txt" });
    await contains(":nth-child(3 of .o-mail-AttachmentContainer)", { text: "A.txt" });
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
