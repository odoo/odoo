/** @odoo-module **/

import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { afterNextRender, click, start, startServer } from "@mail/../tests/helpers/test_utils";

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
    assert.containsOnce($, ".o-AttachmentBox");
    assert.containsOnce($, "button:contains('Attach files')");
    assert.containsNone($, ".o-Chatter .o-AttachmentImage");
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
    assert.containsOnce($, ".o-AttachmentBox");
    assert.containsOnce($, "button:contains('Attach files')");
    assert.containsOnce($, ".o-Chatter input[type='file']");
    assert.containsOnce($, ".o-AttachmentList");
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
    assert.containsOnce($, ".o-AttachmentCard");
    assert.containsOnce($, "button[title='Remove']");

    await click("button[title='Remove']");
    assert.containsOnce($, ".modal-body:contains('Do you really want to delete \"Blah.txt\"?')");

    // Confirm the deletion
    await click(".modal-footer .btn-primary");
    assert.containsNone($, ".o-AttachmentImage");
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
    await click('.o-AttachmentCard[aria-label="Blah.txt"] .o-AttachmentCard-image');
    assert.containsOnce($, ".o-AttachmentViewer");
    assert.containsOnce($, ".o-AttachmentViewer-header:contains(Blah.txt)");
    assert.containsOnce($, ".o-AttachmentViewer div[aria-label='Next']");

    await click(".o-AttachmentViewer div[aria-label='Next']");
    assert.containsOnce($, ".o-AttachmentViewer-header:contains(Blu.txt)");
    assert.containsOnce($, ".o-AttachmentViewer div[aria-label='Next']");

    await click(".o-AttachmentViewer div[aria-label='Next']");
    assert.containsOnce($, ".o-AttachmentViewer-header:contains(Blah.txt)");
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
    $(".o-Chatter-scrollable").scrollTop(10 * 1000); // to bottom
    assert.notEqual($(".o-Chatter-scrollable").scrollTop(), 0);
    await click("i.fa-paperclip");
    assert.strictEqual($(".o-Chatter-scrollable").scrollTop(), 0);
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
    await afterNextRender(() => {
        $(".o-Chatter-scrollable").scrollTop(10 * 1000); // to bottom
    });
    await click("button[aria-label='Attach files']");
    assert.strictEqual($(".o-Chatter-scrollable").scrollTop(), 0);
});
