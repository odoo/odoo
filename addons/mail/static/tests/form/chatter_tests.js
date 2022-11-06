/** @odoo-module **/

import { Chatter } from "@mail/form/chatter";
import { click, nextTick, getFixture, mount } from "@web/../tests/helpers/utils";
import { makeMessagingEnv, MessagingServer } from "../helpers/helpers";
import { Component, useState, xml } from "@odoo/owl";

let target;

class ChatterParent extends Component {
    static template = xml`<Chatter resId="state.resId" resModel="props.resModel" displayName="props.displayName"/>`;
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
        await mount(Chatter, target, { env, props: { resId: 43, resModel: "somemodel", displayName: "" } });

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
        await mount(Chatter, target, { env, props: { resId: false, resModel: "somemodel" , displayName: ""} });

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
        const props = { resId: 43, resModel: "somemodel", displayName: "" };
        const parent = await mount(ChatterParent, target, { env, props });
        assert.containsNone(target, ".o-mail-composer");

        await click($(target).find("button:contains(Send message)")[0]);
        assert.containsOnce(target, ".o-mail-composer");

        parent.state.resId = false;
        await nextTick();
        assert.containsNone(target, ".o-mail-composer");
    });

    QUnit.test("composer has proper placeholder when sending message", async (assert) => {
        const server = new MessagingServer();
        const env = makeMessagingEnv((route, params) => server.rpc(route, params));
        await mount(Chatter, target, { env, props: { resId: 43, resModel: "somemodel", displayName: "" } });
        assert.containsNone(target, ".o-mail-composer");

        await click($(target).find("button:contains(Send message)")[0]);
        assert.containsOnce(target, ".o-mail-composer");
        assert.strictEqual(target.querySelector("textarea").getAttribute("placeholder"), "Send a message to followers...")
    });

    QUnit.test("composer has proper placeholder when logging note", async (assert) => {
        const server = new MessagingServer();
        const env = makeMessagingEnv((route, params) => server.rpc(route, params));
        await mount(Chatter, target, { env, props: { resId: 43, resModel: "somemodel", displayName: "" } });
        assert.containsNone(target, ".o-mail-composer");

        await click($(target).find("button:contains(Log note)")[0]);
        assert.containsOnce(target, ".o-mail-composer");
        assert.strictEqual(target.querySelector("textarea").getAttribute("placeholder"), "Log an internal note...")
    });

    QUnit.test("send/log buttons are properly styled", async (assert) => {
        const server = new MessagingServer();
        const env = makeMessagingEnv((route, params) => server.rpc(route, params));
        await mount(Chatter, target, { env, props: { resId: 43, resModel: "somemodel", displayName: "" } });
        assert.containsNone(target, ".o-mail-composer");

        const sendMsgBtn = $(target).find("button:contains(Send message)")[0];
        const sendNoteBtn = $(target).find("button:contains(Log note)")[0];
        assert.ok(sendMsgBtn.classList.contains('btn-odoo'));
        assert.notOk(sendNoteBtn.classList.contains('btn-odoo'));

        await click(sendNoteBtn);
        assert.notOk(sendMsgBtn.classList.contains('btn-odoo'));
        assert.ok(sendNoteBtn.classList.contains('btn-odoo'));

        await click(sendMsgBtn);
        assert.ok(sendMsgBtn.classList.contains('btn-odoo'));
        assert.notOk(sendNoteBtn.classList.contains('btn-odoo'));
    });

    QUnit.test("displayname is used when sending a message", async (assert) => {
        const server = new MessagingServer();
        const env = makeMessagingEnv((route, params) => server.rpc(route, params));
        await mount(Chatter, target, { env, props: { resId: 43, resModel: "somemodel", displayName: "Gnargl" } });
        await click($(target).find("button:contains(Send message)")[0]);
        const msg = $(target).find("span:contains(Gnargl)")[0];
        assert.ok(msg);
    });

});
