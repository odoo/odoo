/* @odoo-module */

import { click, contains, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("activity menu");

QUnit.test("should update activities when opening the activity menu", async (assert) => {
    const pyEnv = await startServer();
    await start();
    assert.strictEqual($(".o-mail-ActivityMenu-counter").text(), "");
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        res_id: partnerId,
        res_model: "res.partner",
    });
    await click(".o_menu_systray i[aria-label='Activities']");
    await contains(".o-mail-ActivityMenu-counter:contains(1)");
    assert.strictEqual($(".o-mail-ActivityMenu-counter").text(), "1");
});
