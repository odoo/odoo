/** @odoo-module **/

import { ChatWindow } from "@mail/chat/chat_window";
import { click, getFixture, mount } from "@web/../tests/helpers/utils";
import { makeTestEnv, TestServer } from "../helpers/helpers";

let target;

QUnit.module("mail", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
    });

    QUnit.module("chat window");

    QUnit.test("clicking on chat window header toggle its fold status", async (assert) => {
        const server = new TestServer();
        server.addChannel(43, "abc");
        const env = makeTestEnv((route, params) => server.rpc(route, params));
        await mount(ChatWindow, target, { env, props: { threadId: 43 } });

        assert.containsOnce(target, ".o-mail-chat-window");
        assert.containsOnce(target, ".o-mail-thread");
        assert.containsOnce(target, ".o-mail-composer");

        await click(target, ".o-mail-chat-window-header");
        assert.containsNone(target, ".o-mail-thread");
        assert.containsNone(target, ".o-mail-composer");

        await click(target, ".o-mail-chat-window-header");
        assert.containsOnce(target, ".o-mail-thread");
        assert.containsOnce(target, ".o-mail-composer");
    });
});
