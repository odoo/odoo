import { defineMailModels, start } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { getService } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Attachment model properties", async () => {
    await start();
    const attachment = getService("mail.store")["ir.attachment"].insert({
        id: 750,
        mimetype: "text/plain",
        name: "test.txt",
    });
    expect(attachment.isText).toBe(true);
    expect(attachment.isViewable).toBe(true);
    expect(attachment.mimetype).toBe("text/plain");
    expect(attachment.name).toBe("test.txt");
    expect(attachment.extension).toBe("txt");
});
