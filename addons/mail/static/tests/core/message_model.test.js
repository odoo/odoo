import { defineMailModels, start } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { getService, serverState } from "@web/../tests/web_test_helpers";

import { deserializeDateTime, serializeDateTime } from "@web/core/l10n/dates";

describe.current.tags("desktop");
defineMailModels();

test("Message model properties", async () => {
    await start();
    getService("mail.store").Store.insert({
        self: { id: serverState.partnerId, type: "partner" },
    });
    getService("mail.store").Thread.insert({
        id: serverState.partnerId,
        model: "res.partner",
        name: "general",
    });
    const message = getService("mail.store").Message.insert({
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
        starred: true,
        model: "res.partner",
        thread: { id: serverState.partnerId, model: "res.partner" },
        res_id: serverState.partnerId,
    });
    expect(message.body).toBe("<p>Test</p>");
    expect(serializeDateTime(message.date)).toBe("2019-05-05 10:00:00");
    expect(message.id).toBe(4000);
    expect(message.attachments[0].name).toBe("test.txt");
    expect(message.thread.id).toBe(serverState.partnerId);
    expect(message.thread.name).toBe("general");
    expect(message.author.id).toBe(5);
    expect(message.author.displayName).toBe("Demo");
});
