/* @odoo-module */

import { start } from "@mail/../tests/helpers/test_utils";

QUnit.module("attachment model test", {});

QUnit.test("Attachment model properties", async function (assert) {
    const { env } = await start();

    const attachment = env.services["mail.attachment"].insert({
        filename: "test.txt",
        id: 750,
        mimetype: "text/plain",
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(attachment.isText);
    assert.ok(attachment.isViewable);
    assert.strictEqual(attachment.filename, "test.txt");
    assert.strictEqual(attachment.mimetype, "text/plain");
    assert.strictEqual(attachment.name, "test.txt");
    assert.strictEqual(attachment.displayName, "test.txt");
    assert.strictEqual(attachment.extension, "txt");
});
