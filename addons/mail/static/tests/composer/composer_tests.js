/** @odoo-module **/

import { Composer } from "@mail/composer/composer";
import { click, nextTick, getFixture, mount } from "@web/../tests/helpers/utils";
import { makeMessagingEnv, MessagingServer } from "../helpers/helpers";

let target;

QUnit.module("mail", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
    });

    QUnit.module("composer");

    QUnit.test("composer display correct placeholder", async (assert) => {
        const server = new MessagingServer();
        server.addChannel(1, "general", "General announcements...");
        const env = makeMessagingEnv((route, params) => server.rpc(route, params));
        await mount(Composer, target, { env, props: { threadId: 1, placeholder: "owl" } });

        assert.containsOnce(target, "textarea");
        assert.strictEqual(target.querySelector("textarea").getAttribute("placeholder"), "owl")
    });
});
