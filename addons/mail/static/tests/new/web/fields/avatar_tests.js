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
    assert.containsOnce($, ".o_mail_avatar");
    assert.containsOnce($, ".o_mail_avatar img");
    assert.strictEqual($(".o_mail_avatar img")[0].dataset.src, "/web/image/res.users/2/avatar_128");
    assert.containsOnce($, ".o_mail_avatar span");
    assert.strictEqual($(".o_mail_avatar span")[0].innerText, "User display name");
    assert.containsNone($, ".o-mail-chat-window");

    await click(".o_mail_avatar img");
    assert.containsOnce($, ".o-mail-chat-window");
});
