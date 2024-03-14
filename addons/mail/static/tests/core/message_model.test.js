import { describe, expect, test } from "@odoo/hoot";
import { defineMailModels, start } from "../mail_test_helpers";

import { serializeDateTime, deserializeDateTime } from "@web/core/l10n/dates";
import { serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Message model properties", async () => {
    const env = await start();
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
    expect(message.isNeedaction).toBe(true);
    expect(message.body).toBe("<p>Test</p>");
    expect(serializeDateTime(message.date)).toBe("2019-05-05 10:00:00");
    expect(message.id).toBe(4000);
    expect(message.attachments[0].name).toBe("test.txt");
    expect(message.thread.id).toBe(serverState.partnerId);
    expect(message.thread.name).toBe("general");
    expect(message.author.id).toBe(5);
    expect(message.author.displayName).toBe("Demo");
});
