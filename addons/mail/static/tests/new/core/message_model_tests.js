/* @odoo-module */

import { start } from "@mail/../tests/helpers/test_utils";
import { str_to_datetime } from "web.time";

QUnit.module("message model test", {});

QUnit.test("Message model properties", async function (assert) {
    const { env } = await start();
    /** @type {import("@mail/new/core/store_service").Store} */
    const store = env.services["mail.store"];
    env.services["mail.thread"].insert({
        id: 3,
        model: "res.partner",
        name: "general",
    });
    /** @type {import("@mail/new/core/message_model").Message} */
    const message = env.services["mail.message"].insert({
        attachment_ids: [
            {
                filename: "test.txt",
                id: 750,
                mimetype: "text/plain",
                name: "test.txt",
            },
        ],
        author: { id: 5, displayName: "Demo" },
        body: "<p>Test</p>",
        date: moment(str_to_datetime("2019-05-05 10:00:00")),
        id: 4000,
        needaction_partner_ids: [3],
        starred_partner_ids: [3],
        isStarred: true,
        resModel: "res.partner",
        resId: 3,
    });
    assert.ok(message);
    assert.ok(message.isNeedaction);
    assert.strictEqual(message.body, "<p>Test</p>");
    assert.strictEqual(
        moment(message.date).utc().format("YYYY-MM-DD hh:mm:ss"),
        "2019-05-05 10:00:00"
    );
    assert.strictEqual(message.id, 4000);
    assert.ok(store.discuss.inbox.messages.find((m) => m.id === message.id));
    assert.ok(store.discuss.starred.messages.find((m) => m.id === message.id));

    assert.ok(message.attachments);
    assert.strictEqual(message.attachments[0].name, "test.txt");

    assert.ok(message.originThread);
    assert.strictEqual(message.originThread.id, 3);
    assert.strictEqual(message.originThread.name, "general");

    assert.ok(message.author);
    assert.strictEqual(message.author.id, 5);
    assert.strictEqual(message.author.displayName, "Demo");
});
