/** @odoo-module */

import { expect, test } from "@odoo/hoot";
import { start, startServer } from "../mail_test_helpers";

import { serializeDateTime, deserializeDateTime } from "@web/core/l10n/dates";
import { constants } from "@web/../tests/web_test_helpers";

test.skip("Message model properties", async () => {
    await startServer();
    const { env } = await start();
    env.services["mail.store"].Store.insert({
        self: { id: constants.PARTNER_ID, type: "partner" },
    });
    env.services["mail.store"].Thread.insert({
        id: constants.PARTNER_ID,
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
        needaction_partner_ids: [constants.PARTNER_ID],
        starredPersonas: { id: constants.PARTNER_ID, type: "partner" },
        model: "res.partner",
        thread: { id: constants.PARTNER_ID, model: "res.partner" },
        res_id: constants.PARTNER_ID,
    });
    expect(message).toBeTruthy();
    expect(message.isNeedaction).toBeTruthy();
    expect(message.body).toBe("<p>Test</p>");
    expect(serializeDateTime(message.date)).toBe("2019-05-05 10:00:00");
    expect(message.id).toBe(4000);
    expect(message.attachments).toBeTruthy();
    expect(message.attachments[0].name).toBe("test.txt");
    expect(message.thread).toBeTruthy();
    expect(message.thread.id).toBe(constants.PARTNER_ID);
    expect(message.thread.name).toBe("general");
    expect(message.author).toBeTruthy();
    expect(message.author.id).toBe(5);
    expect(message.author.displayName).toBe("Demo");
});
