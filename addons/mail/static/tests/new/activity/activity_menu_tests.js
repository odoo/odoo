/** @odoo-module **/

import { ActivityMenu } from "@mail/new/chatter/components/activity_menu";
import { makeTestEnv, TestServer } from "@mail/new/helpers/helpers";

import { click, getFixture, mount } from "@web/../tests/helpers/utils";

let target;

QUnit.module("mail", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
    });

    QUnit.module("activity menu");

    QUnit.test("activity menu: no activity", async (assert) => {
        const server = new TestServer();
        const env = makeTestEnv((route, params) => server.rpc(route, params));
        await mount(ActivityMenu, target, { env });
        await click(
            document.querySelector("i[aria-label='Activities']").closest(".dropdown-toggle")
        );
        assert.containsOnce(target, ".o-mail-no-activity");
    });
});
