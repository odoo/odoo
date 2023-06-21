/* @odoo-module */

import { start } from "@mail/../tests/helpers/test_utils";
import { insertAttachment } from "@mail/core/common/attachment_service";

QUnit.module("attachment model test", {});

QUnit.test("Attachment model properties", async (assert) => {
    await start();
    const attachment = insertAttachment({
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
