/** @odoo-module **/

import { start, startServer } from "@mail/../tests/helpers/test_utils";

import { editInput } from "@web/../tests/helpers/utils";

QUnit.module("mail", {}, function () {
    QUnit.module("components", {}, function () {
        QUnit.module("follower_tests.js");

        QUnit.test("remove a follower in a dirty form view", async function (assert) {
            const pyEnv = await startServer();
            const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
            pyEnv["mail.followers"].create({
                is_active: true,
                partner_id: partnerId,
                res_id: threadId,
                res_model: "res.partner",
            });
            const { click, openView } = await start({
                async mockRPC(route, args) {
                    if (args.method === "read") {
                        assert.step(`read ${args.args[0][0]}`);
                    }
                },
            });
            await openView({
                res_id: threadId,
                res_model: "res.partner",
                views: [[false, "form"]],
            });
            assert.strictEqual(
                document.body.querySelector(".o-mail-chatter-topbar-followers-count").innerText,
                "1"
            );
            assert.verifySteps([`read ${threadId}`]);

            await editInput(document.body, ".o_field_char[name=name] input", "some value");
            await click(".o-mail-chatter-topbar-follower-list-button");
            assert.containsOnce(document.body, ".o-mail-chatter-topbar-follower-list-follower");

            await click(".o-mail-chatter-topbar-follower-list-follower-remove-button");
            assert.strictEqual(
                document.body.querySelector(".o-mail-chatter-topbar-followers-count").innerText,
                "0"
            );
            assert.strictEqual(
                document.body.querySelector(".o_field_char[name=name] input").value,
                "some value"
            );
            assert.verifySteps([`read ${threadId}`]);
        });
    });
});
