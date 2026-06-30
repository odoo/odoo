/* @odoo-module */

import { start } from "@mail/../tests/helpers/test_utils";
import { serializeDateTime, deserializeDateTime } from "@web/core/l10n/dates";

QUnit.module("message model test", {});

QUnit.test("Message model properties", async (assert) => {
    const { env } = await start();
    env.services["mail.store"].Thread.insert({
        id: 3,
        model: "res.partner",
        name: "general",
    });
    /** @type {import("models").Message} */
    const message = env.services["mail.store"].Message.insert({
        attachments: [
            {
                filename: "test.txt",
                id: 750,
                mimetype: "text/plain",
                name: "test.txt",
            },
        ],
        author: { id: 5, displayName: "Demo" },
        body: "<p>Test</p>",
        date: deserializeDateTime("2019-05-05 10:00:00"),
        id: 4000,
        needaction_partner_ids: [3],
        starred_partner_ids: [3],
        isStarred: true,
        model: "res.partner",
        res_id: 3,
    });
    assert.ok(message);
    assert.ok(message.isNeedaction);
    assert.strictEqual(message.body, "<p>Test</p>");
    assert.strictEqual(serializeDateTime(message.date), "2019-05-05 10:00:00");
    assert.strictEqual(message.id, 4000);

    assert.ok(message.attachments);
    assert.strictEqual(message.attachments[0].name, "test.txt");

    assert.ok(message.originThread);
    assert.strictEqual(message.originThread.id, 3);
    assert.strictEqual(message.originThread.name, "general");

    assert.ok(message.author);
    assert.strictEqual(message.author.id, 5);
    assert.strictEqual(message.author.displayName, "Demo");
});
