/** @odoo-module **/

import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { getFixture } from "@web/../tests/helpers/utils";

let target;
QUnit.module("attachment box", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("base empty rendering", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const views = {
        "res.partner,false,form": `
            <form>
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
    assert.containsOnce(target, ".o-mail-attachment-box");
    assert.containsOnce(target, "button:contains('Attach files')");
    assert.containsNone(target, ".o-mail-chatter .o-mail-attachment-image");
});

QUnit.test("base non-empty rendering", async function (assert) {
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
    assert.containsOnce(target, ".o-mail-attachment-box");
    assert.containsOnce(target, "button:contains('Attach files')");
    assert.containsOnce(target, ".o-mail-chatter input[type='file']");
    assert.containsOnce(target, ".o-mail-attachment-list");
});

QUnit.test("remove attachment should ask for confirmation", async function (assert) {
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
    assert.containsOnce(target, ".o-mail-attachment-card");
    assert.containsOnce(target, "button[title='Remove']");

    await click("button[title='Remove']");
    assert.containsOnce(
        target,
        ".modal-body:contains('Do you really want to delete \"Blah.txt\"?')"
    );

    // Confirm the deletion
    await click(".modal-footer .btn-primary");
    assert.containsNone(target, ".o-mail-attachment-images");
});

QUnit.test("view attachments", async function (assert) {
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
    await click('.o-mail-attachment-card[aria-label="Blah.txt"] .o-mail-attachment-card-image');
    assert.containsOnce(target, ".o-mail-attachment-viewer");
    assert.containsOnce(target, ".o-mail-attachment-viewer-header:contains(Blah.txt)");
    assert.containsOnce(target, ".o-mail-attachment-viewer div[aria-label='Next']");

    await click(".o-mail-attachment-viewer div[aria-label='Next']");
    assert.containsOnce(target, ".o-mail-attachment-viewer-header:contains(Blu.txt)");
    assert.containsOnce(target, ".o-mail-attachment-viewer div[aria-label='Next']");

    await click(".o-mail-attachment-viewer div[aria-label='Next']");
    assert.containsOnce(target, ".o-mail-attachment-viewer-header:contains(Blah.txt)");
});

QUnit.test("scroll to attachment box when toggling on", async function (assert) {
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
    $(".o-mail-chatter-scrollable").scrollTop(10 * 1000); // to bottom
    assert.notEqual($(".o-mail-chatter-scrollable").scrollTop(), 0);
    await click("i.fa-paperclip");
    assert.strictEqual($(".o-mail-chatter-scrollable").scrollTop(), 0);
});
