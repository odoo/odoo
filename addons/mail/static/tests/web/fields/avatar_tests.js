/* @odoo-module */

import { Avatar } from "@mail/views/web/fields/avatar/avatar";
import { start } from "@mail/../tests/helpers/test_utils";

import { getFixture, mount } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";

QUnit.module("avatar field");

QUnit.test("basic rendering", async () => {
    const { env } = await start();
    await mount(Avatar, getFixture(), {
        env,
        props: {
            resId: 2,
            resModel: "res.users",
            displayName: "User display name",
        },
    });
    await contains(".o-mail-Avatar");
    await contains(".o-mail-Avatar img");
    await contains(".o-mail-Avatar img[data-src='/web/image/res.users/2/avatar_128']");
    await contains(".o-mail-Avatar span");
    await contains(".o-mail-Avatar span", { text: "User display name" });
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click(".o-mail-Avatar img");
    await contains(".o-mail-ChatWindow");
});
