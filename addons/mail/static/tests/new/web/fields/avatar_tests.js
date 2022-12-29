/** @odoo-module **/

import { click, start } from "@mail/../tests/helpers/test_utils";
import { Avatar } from "@mail/new/web/fields/avatar/avatar";
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
    assert.containsOnce($, ".o-mail-Avatar");
    assert.containsOnce($, ".o-mail-Avatar img");
    assert.strictEqual($(".o-mail-Avatar img")[0].dataset.src, "/web/image/res.users/2/avatar_128");
    assert.containsOnce($, ".o-mail-Avatar span");
    assert.strictEqual($(".o-mail-Avatar span")[0].innerText, "User display name");
    assert.containsNone($, ".o-mail-ChatWindow");

    await click(".o-mail-Avatar img");
    assert.containsOnce($, ".o-mail-ChatWindow");
});
