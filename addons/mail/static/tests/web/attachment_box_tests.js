/* @odoo-module */

import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { click, contains, scroll, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("attachment box");

QUnit.test("base empty rendering", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
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
    await contains("button:contains('Attach files')");
    await contains(".o-mail-Chatter .o-mail-AttachmentImage", 0);
});

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
    await contains("button:contains('Attach files')");
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
    await contains(".modal-body:contains('Do you really want to delete \"Blah.txt\"?')");

    // Confirm the deletion
    await click(".modal-footer .btn-primary");
    await contains(".o-mail-AttachmentImage", 0);
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
    await contains(".o-FileViewer-header:contains(Blah.txt)");
    await contains(".o-FileViewer div[aria-label='Next']");

    await click(".o-FileViewer div[aria-label='Next']");
    await contains(".o-FileViewer-header:contains(Blu.txt)");
    await contains(".o-FileViewer div[aria-label='Next']");

    await click(".o-FileViewer div[aria-label='Next']");
    await contains(".o-FileViewer-header:contains(Blah.txt)");
});

QUnit.test("scroll to attachment box when toggling on", async (assert) => {
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
    await contains(".o-mail-Message", 30);
    await scroll(".o-mail-Chatter", "bottom");
    await click("button[aria-label='Attach files']");
    await contains(".o-mail-AttachmentBox");
    await contains(".o-mail-Chatter", 1, { scroll: 0 });
    assert.isVisible($(".o-mail-AttachmentBox"));
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
    await contains(".o-mail-Chatter [aria-label='Attach files']:contains(3)");
    await click(".o-mail-Chatter [aria-label='Attach files']"); // open attachment box
    await contains(".o-mail-AttachmentCard:eq(0):contains(C.txt)");
    await contains(".o-mail-AttachmentCard:eq(1):contains(B.txt)");
    await contains(".o-mail-AttachmentCard:eq(2):contains(A.txt)");
});
