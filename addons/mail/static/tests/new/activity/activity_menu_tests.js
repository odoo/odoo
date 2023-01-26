/** @odoo-module **/

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { getFixture } from "@web/../tests/helpers/utils";

let target;

QUnit.module("activity menu", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("should update activities when opening the activity menu", async (assert) => {
    const pyEnv = await startServer();
    await start();
    assert.strictEqual($(target).find(".o-mail-activity-menu-counter").text(), "");
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        res_id: partnerId,
        res_model: "res.partner",
    });
    await click(".o_menu_systray i[aria-label='Activities']");
    assert.strictEqual($(target).find(".o-mail-activity-menu-counter").text(), "1");
});
