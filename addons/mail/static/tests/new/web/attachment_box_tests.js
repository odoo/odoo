/** @odoo-module **/

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
    assert.containsOnce(target, ".o-mail-attachment-image");
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
    await click('.o-mail-attachment-card[aria-label="Blah.txt"] .o-mail-attachment-image');
    assert.containsOnce(target, ".o-mail-attachment-viewer");
    assert.strictEqual($(target).find(".o-mail-attachment-viewer-name").text(), "Blah.txt");
    assert.containsOnce(target, ".o-mail-attachment-viewer-buttonNavigationNext");

    await click(".o-mail-attachment-viewer-buttonNavigationNext");
    assert.strictEqual($(target).find(".o-mail-attachment-viewer-name").text(), "Blu.txt");
    assert.containsOnce(target, ".o-mail-attachment-viewer-buttonNavigationNext");

    await click(".o-mail-attachment-viewer-buttonNavigationNext");
    assert.strictEqual($(target).find(".o-mail-attachment-viewer-name").text(), "Blah.txt");
});
