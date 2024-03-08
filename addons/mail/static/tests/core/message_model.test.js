/** @odoo-module alias=@mail/../tests/core/message_model_tests default=false */
const test = QUnit.test; // QUnit.test()

import { serverState, startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";
import { serializeDateTime, deserializeDateTime } from "@web/core/l10n/dates";

QUnit.module("message model test", {});

test("Message model properties", async (assert) => {
    await startServer();
    const { env } = await start();
    env.services["mail.store"].Store.insert({
        self: { id: serverState.partnerId, type: "partner" },
    });
    env.services["mail.store"].Thread.insert({
        id: serverState.partnerId,
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
        needaction_partner_ids: [serverState.partnerId],
        starredPersonas: { id: serverState.partnerId, type: "partner" },
        model: "res.partner",
        thread: { id: serverState.partnerId, model: "res.partner" },
        res_id: serverState.partnerId,
    });
    assert.ok(message);
    assert.ok(message.isNeedaction);
    assert.strictEqual(message.body, "<p>Test</p>");
    assert.strictEqual(serializeDateTime(message.date), "2019-05-05 10:00:00");
    assert.strictEqual(message.id, 4000);

    assert.ok(message.attachments);
    assert.strictEqual(message.attachments[0].name, "test.txt");

    assert.ok(message.thread);
    assert.strictEqual(message.thread.id, serverState.partnerId);
    assert.strictEqual(message.thread.name, "general");

    assert.ok(message.author);
    assert.strictEqual(message.author.id, 5);
    assert.strictEqual(message.author.displayName, "Demo");
});
