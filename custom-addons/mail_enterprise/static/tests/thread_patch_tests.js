/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { start } from "@mail/../tests/helpers/test_utils";

import { contains, scroll } from "@web/../tests/utils";

QUnit.module("thread (patch)");

QUnit.test("message list desc order", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "partner 1" });
    for (let i = 0; i <= 60; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "res.partner",
            res_id: partnerId,
        });
    }
    patchUiSize({ size: SIZES.XXL });
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    assert.notOk(
        $(".o-mail-Message").prevAll("button:contains(Load More)")[0],
        "load more link should NOT be before messages"
    );
    assert.notOk(
        $("button:contains(Load More)").nextAll(".o-mail-Message")[0],
        "load more link should be after messages"
    );
    await contains(".o-mail-Message", { count: 30 });
    await scroll(".o-mail-Chatter", "bottom");
    await contains(".o-mail-Message", { count: 60 });
    await scroll(".o-mail-Chatter", 0);
    // weak test, no guaranteed that we waited long enough for potential extra messages to be loaded
    await contains(".o-mail-Message", { count: 60 });
});
