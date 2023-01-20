/** @odoo-module **/

import { afterNextRender, start, startServer } from "@mail/../tests/helpers/test_utils";

import { makeTestPromise } from "web.test_utils";

QUnit.module("mail", {}, function () {
    QUnit.module("components", {}, function () {
        QUnit.module("chatter_topbar_tests.js");

        QUnit.skipRefactoring("attachment loading is delayed", async function (assert) {
            assert.expect(4);

            const pyEnv = await startServer();
            const resPartnerId1 = pyEnv["res.partner"].create({});
            const { advanceTime, openView } = await start({
                hasTimeControl: true,
                loadingBaseDelayDuration: 100,
                async mockRPC(route) {
                    if (route.includes("/mail/thread/data")) {
                        await makeTestPromise(); // simulate long loading
                    }
                },
            });
            await openView({
                res_id: resPartnerId1,
                res_model: "res.partner",
                views: [[false, "form"]],
            });

            assert.strictEqual(
                document.querySelectorAll(`.o-mail-chatter-topbar`).length,
                1,
                "should have a chatter topbar"
            );
            assert.containsOnce(
                document.body,
                "button[aria-label='Attach files']",
                "should have an attachments button in chatter menu"
            );
            assert.strictEqual(
                document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCountLoader`).length,
                0,
                "attachments button should not have a loader yet"
            );

            await afterNextRender(async () => advanceTime(100));
            assert.strictEqual(
                document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCountLoader`).length,
                1,
                "attachments button should now have a loader"
            );
        });
    });
});
