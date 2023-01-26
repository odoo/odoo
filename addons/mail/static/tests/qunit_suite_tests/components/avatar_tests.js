/** @odoo-module **/

import { start } from "@mail/../tests/helpers/test_utils";
import { Avatar } from "@mail/components/avatar/avatar";
import { getFixture, mount } from "@web/../tests/helpers/utils";

QUnit.module("mail", {}, function () {
    QUnit.module("components", {}, function () {
        QUnit.module("avatar_tests.js");
        QUnit.test("basic rendering", async function (assert) {
            const { click, env } = await start();
            const target = getFixture();
            await mount(Avatar, target, {
                env,
                props: {
                    resId: 2,
                    resModel: "res.users",
                    displayName: "User display name",
                },
            });
            assert.containsOnce(target, ".o_mail_avatar");
            assert.containsOnce(target, ".o_mail_avatar img");
            assert.strictEqual(
                target.querySelector(".o_mail_avatar img").dataset.src,
                "/web/image/res.users/2/avatar_128"
            );
            assert.containsOnce(target, ".o_mail_avatar span");
            assert.strictEqual(
                target.querySelector(".o_mail_avatar span").innerText,
                "User display name"
            );
            assert.containsNone(target, ".o_ChatWindow");

            await click(target.querySelector(".o_mail_avatar img"));

            assert.containsOnce(target, ".o_ChatWindow");
        });
    });
});
