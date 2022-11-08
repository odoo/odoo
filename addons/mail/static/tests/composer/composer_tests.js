/** @odoo-module **/

import { Composer } from "@mail/composer/composer";
import { getFixture, mount } from "@web/../tests/helpers/utils";
import { makeTestEnv, TestServer } from "../helpers/helpers";

let target;

QUnit.module("mail", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
    });

    QUnit.module("composer");

    QUnit.test("composer display correct placeholder", async (assert) => {
        const server = new TestServer();
        server.addChannel(1, "general", "General announcements...");
        const env = makeTestEnv((route, params) => server.rpc(route, params));
        await mount(Composer, target, { env, props: { threadId: 1, placeholder: "owl" } });

        assert.containsOnce(target, "textarea");
        assert.strictEqual(target.querySelector("textarea").getAttribute("placeholder"), "owl");
    });
});
