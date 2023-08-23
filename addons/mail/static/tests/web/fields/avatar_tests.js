/* @odoo-module */

import { Avatar } from "@mail/views/web/fields/avatar/avatar";
import { click, start } from "@mail/../tests/helpers/test_utils";

import { getFixture, mount } from "@web/../tests/helpers/utils";

QUnit.module("avatar field");

QUnit.test("basic rendering", async (assert) => {
    const { env } = await start();
    await mount(Avatar, getFixture(), {
        env,
        props: {
            resId: 2,
            resModel: "res.users",
            displayName: "User display name",
        },
    });
    assert.containsOnce(document.body, ".o-mail-Avatar");
    assert.containsOnce(document.body, ".o-mail-Avatar img");
    assert.strictEqual($(".o-mail-Avatar img")[0].dataset.src, "/web/image/res.users/2/avatar_128");
    assert.containsOnce(document.body, ".o-mail-Avatar span");
    assert.strictEqual($(".o-mail-Avatar span")[0].innerText, "User display name");
    assert.containsNone(document.body, ".o-mail-ChatWindow");

    await click(".o-mail-Avatar img");
    assert.containsOnce(document.body, ".o-mail-ChatWindow");
});
