import { defineMailModels, start } from "@mail/../tests/mail_test_helpers";

import { describe, expect, test } from "@odoo/hoot";
import { markup } from "@odoo/owl";

import { deserializeDateTime, serializeDateTime } from "@web/core/l10n/dates";
import { getService, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Message model properties", async () => {
    await start();
    const store = getService("mail.store");
    store.Store.insert({
        self_partner: { id: serverState.partnerId },
    });
    store.Thread.insert({
        id: serverState.partnerId,
        model: "res.partner",
        name: "general",
    });
    store["ir.attachment"].insert({
        id: 750,
        mimetype: "text/plain",
        name: "test.txt",
    });
    const message = store["mail.message"].insert({
        attachment_ids: 750,
        author_id: { id: 5, name: "Demo" },
        body: markup`<p>Test</p>`,
        date: deserializeDateTime("2019-05-05 10:00:00"),
        id: 4000,
        starred: true,
        model: "res.partner",
        thread: { id: serverState.partnerId, model: "res.partner" },
        res_id: serverState.partnerId,
    });
    expect(message.body?.toString()).toBe("<p>Test</p>");
    expect(serializeDateTime(message.date)).toBe("2019-05-05 10:00:00");
    expect(message.id).toBe(4000);
    expect(message.attachment_ids[0].name).toBe("test.txt");
    expect(message.thread.id).toBe(serverState.partnerId);
    expect(message.thread.name).toBe("general");
    expect(message.author_id.id).toBe(5);
    expect(message.author_id.name).toBe("Demo");
});
