import { describe, expect, test } from "@odoo/hoot";
import { mockUserAgent } from "@odoo/hoot-mock";
import { defineMailModels, start } from "@mail/../tests/mail_test_helpers";
import { getService } from "@web/../tests/web_test_helpers";

describe.current.tags("mobile");
defineMailModels();

test("Settings:usePushToTalk is removed on mobile", async () => {
    mockUserAgent("android");
    localStorage.setItem("discuss.upgrade.version", "saas~19.3");
    localStorage.setItem("Settings:usePushToTalk", '{"value": "true"}');
    await start();
    expect(localStorage.getItem("Settings:usePushToTalk")).toBe(null);
    expect(getService("mail.store").settings.usePushToTalk).toBe(false);
});
