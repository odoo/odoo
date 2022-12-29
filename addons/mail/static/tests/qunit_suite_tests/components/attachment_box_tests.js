/** @odoo-module **/

import { nextAnimationFrame, start, startServer } from "@mail/../tests/helpers/test_utils";
import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";

QUnit.skipRefactoring("scroll to attachment box when toggling on", async function (assert) {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    for (let i = 0; i < 30; i++) {
        pyEnv["mail.message"].create({
            body: "not empty".repeat(50),
            model: "res.partner",
            res_id: partnerId,
        });
    }
    pyEnv["ir.attachment"].create({
        mimetype: "text/plain",
        name: "Blah.txt",
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { click, openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    $(".o_Chatter_scrollPanel").scrollTop(10 * 1000); // to bottom
    await nextAnimationFrame();
    await click(".o_ChatterTopbar_buttonToggleAttachments");
    assert.strictEqual($(".o_Chatter_scrollPanel").scrollTop(), 0);
});
