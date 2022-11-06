/** @odoo-module **/

import { Chatter } from "@mail/form/chatter";
import { click, getFixture, mount } from "@web/../tests/helpers/utils";
import { makeMessagingEnv, MessagingServer } from "../helpers/helpers";

let target;

QUnit.module("mail", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
    });

    QUnit.module("chatter");

    QUnit.test("simple chatter on a record", async (assert) => {
        const server = new MessagingServer();
        const env = makeMessagingEnv((route, params) => {
            assert.step(route);
            return server.rpc(route, params);
        });
        await mount(Chatter, target, { env, props: { resId: 43, resModel: "somemodel" } });

        assert.containsOnce(target, ".o-mail-chatter-topbar");
        assert.containsOnce(target, ".o-mail-thread");
        assert.verifySteps(["/mail/init_messaging", "/mail/thread/data", "/mail/thread/messages"]);
    });
});
