import { expect, test } from "@odoo/hoot";
import { defineMailModels, startClient } from "../mail_test_helpers";

defineMailModels();

test("Attachment model properties", async () => {
    const env = await startClient();
    const attachment = env.services["mail.store"].Attachment.insert({
        filename: "test.txt",
        id: 750,
        mimetype: "text/plain",
        name: "test.txt",
    });
    expect(attachment).toBeTruthy();
    expect(attachment.isText).toBeTruthy();
    expect(attachment.isViewable).toBeTruthy();
    expect(attachment.filename).toBe("test.txt");
    expect(attachment.mimetype).toBe("text/plain");
    expect(attachment.name).toBe("test.txt");
    expect(attachment.displayName).toBe("test.txt");
    expect(attachment.extension).toBe("txt");
});
