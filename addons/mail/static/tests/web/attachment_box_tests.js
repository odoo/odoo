/* @odoo-module */

import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { click, nextAnimationFrame, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("attachment box");

QUnit.test("base empty rendering", async (assert) => {
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
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-mail-AttachmentBox");
    assert.containsOnce($, "button:contains('Attach files')");
    assert.containsNone($, ".o-mail-Chatter .o-mail-AttachmentImage");
});

QUnit.test("base non-empty rendering", async (assert) => {
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
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-mail-AttachmentBox");
    assert.containsOnce($, "button:contains('Attach files')");
    assert.containsOnce($, ".o-mail-Chatter input[type='file']");
    assert.containsOnce($, ".o-mail-AttachmentList");
});

QUnit.test("remove attachment should ask for confirmation", async (assert) => {
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
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-mail-AttachmentCard");
    assert.containsOnce($, "button[title='Remove']");

    await click("button[title='Remove']");
    assert.containsOnce($, ".modal-body:contains('Do you really want to delete \"Blah.txt\"?')");

    // Confirm the deletion
    await click(".modal-footer .btn-primary");
    assert.containsNone($, ".o-mail-AttachmentImage");
});

QUnit.test("view attachments", async (assert) => {
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
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await click('.o-mail-AttachmentCard[aria-label="Blah.txt"] .o-mail-AttachmentCard-image');
    assert.containsOnce($, ".o-FileViewer");
    assert.containsOnce($, ".o-FileViewer-header:contains(Blah.txt)");
    assert.containsOnce($, ".o-FileViewer div[aria-label='Next']");

    await click(".o-FileViewer div[aria-label='Next']");
    assert.containsOnce($, ".o-FileViewer-header:contains(Blu.txt)");
    assert.containsOnce($, ".o-FileViewer div[aria-label='Next']");

    await click(".o-FileViewer div[aria-label='Next']");
    assert.containsOnce($, ".o-FileViewer-header:contains(Blah.txt)");
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
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    $(".o-mail-Chatter").scrollTop(10 * 1000); // to bottom
    await click("button[aria-label='Attach files']");
    await nextAnimationFrame();
    assert.isVisible($(".o-mail-AttachmentBox"));
});
