/** @odoo-module **/

import { Chatter } from "@mail/form/chatter";
import { click, nextTick, getFixture, mount } from "@web/../tests/helpers/utils";
import { makeMessagingEnv, MessagingServer } from "../helpers/helpers";
import { Component, useState, xml } from "@odoo/owl";

let target;

class ChatterParent extends Component {
    static template = xml`<Chatter resId="state.resId" resModel="props.resModel"/>`;
    static components = { Chatter };
    state = useState({ resId: this.props.resId });
}

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

    QUnit.test("simple chatter, with no record", async (assert) => {
        const server = new MessagingServer();
        const env = makeMessagingEnv((route, params) => {
            assert.step(route);
            return server.rpc(route, params);
        });
        await mount(Chatter, target, { env, props: { resId: false, resModel: "somemodel" } });

        assert.containsOnce(target, ".o-mail-chatter-topbar");
        assert.containsOnce(target, ".o-mail-thread");
        assert.containsOnce(target, ".o-mail-message");
        assert.containsOnce(target, ".o-chatter-disabled");
        assert.containsN(target, "button:disabled", 5);
        assert.verifySteps(["/mail/init_messaging"]);
    });

    QUnit.test("composer is closed when creating record", async (assert) => {
        const server = new MessagingServer();
        const env = makeMessagingEnv((route, params) => server.rpc(route, params));
        const props = { resId: 43, resModel: "somemodel" };
        const parent = await mount(ChatterParent, target, { env, props });
        assert.containsNone(target, ".o-mail-composer");

        await click($(target).find("button:contains(Send message)")[0]);
        assert.containsOnce(target, ".o-mail-composer");

        parent.state.resId = false;
        await nextTick();
        assert.containsNone(target, ".o-mail-composer");
    });
});
