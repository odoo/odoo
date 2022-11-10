/** @odoo-module **/

import { loadEmojiData } from "@mail/composer/emoji_picker";
import { Discuss } from "@mail/discuss/discuss";

import {
    click,
    editInput,
    getFixture,
    mount,
    nextTick,
    triggerEvent,
    triggerHotkey,
} from "@web/../tests/helpers/utils";
import { makeTestEnv, TestServer } from "../helpers/helpers";

import { registry } from "@web/core/registry";

let target;

QUnit.module("mail", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
    });

    QUnit.module("message");

    QUnit.test("Start edition on click edit", async (assert) => {
        const server = new TestServer();
        server.addChannel(1, "general", "General announcements...");
        server.addMessage("comment", 1, 1, "mail.channel", 3, "Hello world");
        const env = makeTestEnv((route, params) => server.rpc(route, params));
        await env.services["mail.messaging"].isReady;
        env.services["mail.messaging"].setDiscussThread(1);
        await mount(Discuss, target, { env });
        target.querySelector(".o-mail-message-actions").classList.remove("invisible");
        await click(target, "i[aria-label='Edit']");

        assert.containsOnce(target, ".o-mail-message-editable-content .o-mail-composer");
        assert.strictEqual(
            target.querySelector(".o-mail-message-editable-content .o-mail-composer-textarea")
                .value,
            "Hello world"
        );
    });

    QUnit.test("Stop edition on click cancel", async (assert) => {
        const server = new TestServer();
        server.addChannel(1, "general", "General announcements...");
        server.addMessage("comment", 1, 1, "mail.channel", 3, "Hello world");
        const env = makeTestEnv((route, params) => server.rpc(route, params));
        await env.services["mail.messaging"].isReady;
        env.services["mail.messaging"].setDiscussThread(1);
        await mount(Discuss, target, { env });
        target.querySelector(".o-mail-message-actions").classList.remove("invisible");
        await click(target, "i[aria-label='Edit']");

        await click($("a:contains('cancel')")[0]);
        assert.containsNone(target, ".o-mail-message-editable-content .o-mail-composer");
    });

    QUnit.test("Stop edition on press escape", async (assert) => {
        const server = new TestServer();
        server.addChannel(1, "general", "General announcements...");
        server.addMessage("comment", 1, 1, "mail.channel", 3, "Hello world");
        const env = makeTestEnv((route, params) => server.rpc(route, params));
        await env.services["mail.messaging"].isReady;
        env.services["mail.messaging"].setDiscussThread(1);
        await mount(Discuss, target, { env });
        target.querySelector(".o-mail-message-actions").classList.remove("invisible");
        await click(target, "i[aria-label='Edit']");

        await triggerHotkey("Escape", false);
        await nextTick();
        assert.containsNone(target, ".o-mail-message-editable-content .o-mail-composer");
    });

    QUnit.test("Stop edition on click save", async (assert) => {
        const server = new TestServer();
        server.addChannel(1, "general", "General announcements...");
        server.addMessage("comment", 1, 1, "mail.channel", 3, "Hello world");
        const env = makeTestEnv((route, params) => server.rpc(route, params));
        await env.services["mail.messaging"].isReady;
        env.services["mail.messaging"].setDiscussThread(1);
        await mount(Discuss, target, { env });
        target.querySelector(".o-mail-message-actions").classList.remove("invisible");
        await click(target, "i[aria-label='Edit']");

        await click($("a:contains('save')")[0]);
        assert.containsNone(target, ".o-mail-message-editable-content .o-mail-composer");
    });

    QUnit.test("Stop edition on press enter", async (assert) => {
        const server = new TestServer();
        server.addChannel(1, "general", "General announcements...");
        server.addMessage("comment", 1, 1, "mail.channel", 3, "Hello world");
        const env = makeTestEnv((route, params) => server.rpc(route, params));
        await env.services["mail.messaging"].isReady;
        env.services["mail.messaging"].setDiscussThread(1);
        await mount(Discuss, target, { env });
        target.querySelector(".o-mail-message-actions").classList.remove("invisible");
        await click(target, "i[aria-label='Edit']");

        await triggerHotkey("Enter", false);
        await nextTick();
        assert.containsNone(target, ".o-mail-message-editable-content .o-mail-composer");
    });

    QUnit.test("Stop edition on click away", async (assert) => {
        const server = new TestServer();
        server.addChannel(1, "general", "General announcements...");
        server.addMessage("comment", 1, 1, "mail.channel", 3, "Hello world");
        const env = makeTestEnv((route, params) => server.rpc(route, params));
        await env.services["mail.messaging"].isReady;
        env.services["mail.messaging"].setDiscussThread(1);
        await mount(Discuss, target, { env });
        target.querySelector(".o-mail-message-actions").classList.remove("invisible");
        await click(target, "i[aria-label='Edit']");

        await triggerEvent(target, ".o-mail-discuss-sidebar", "click");
        assert.containsNone(target, ".o-mail-message-editable-content .o-mail-composer");
    });

    QUnit.test("Do not stop edition on click away when clicking on emoji", async (assert) => {
        const server = new TestServer();
        server.addChannel(1, "general", "General announcements...");
        server.addMessage("comment", 1, 1, "mail.channel", 3, "Hello world");
        const env = makeTestEnv((route, params) => server.rpc(route, params));
        await env.services["mail.messaging"].isReady;
        env.services["mail.messaging"].setDiscussThread(1);
        const { Component: PopoverContainer, props } = registry
            .category("main_components")
            .get("PopoverContainer");
        await mount(PopoverContainer, target, { env, props });
        await mount(Discuss, target, { env });
        target.querySelector(".o-mail-message-actions").classList.remove("invisible");
        await click(target, "i[aria-label='Edit']");

        await click(target.querySelector("i[aria-label='Emojis']").closest("button"));
        await loadEmojiData(); // wait for emoji being loaded (required for rendering)
        await nextTick(); // wait for following rendering
        await click(target.querySelector(".o-mail-emoji-picker-content .o-emoji"));
        assert.containsOnce(target, ".o-mail-message-editable-content .o-mail-composer");
    });

    QUnit.test("Save on click", async (assert) => {
        const server = new TestServer();
        server.addChannel(1, "general", "General announcements...");
        server.addMessage("comment", 1, 1, "mail.channel", 3, "Hello world");
        const env = makeTestEnv((route, params) => server.rpc(route, params));
        await env.services["mail.messaging"].isReady;
        env.services["mail.messaging"].setDiscussThread(1);
        await mount(Discuss, target, { env });
        target.querySelector(".o-mail-message-actions").classList.remove("invisible");
        await click(target, "i[aria-label='Edit']");

        await editInput(target, ".o-mail-message textarea", "Goodbye World");
        await click($("a:contains('save')")[0]);
        assert.strictEqual(
            document.querySelector(".o-mail-message-body").innerText,
            "Goodbye World"
        );
    });

    QUnit.test("Do not call server on save if no changes", async (assert) => {
        const server = new TestServer();
        server.addChannel(1, "general", "General announcements...");
        server.addMessage("comment", 1, 1, "mail.channel", 3, "Hello world");
        const env = makeTestEnv((route, params) => {
            if (route === "/mail/message/update_content") {
                assert.step("update_content");
            }
            return server.rpc(route, params);
        });
        await env.services["mail.messaging"].isReady;
        env.services["mail.messaging"].setDiscussThread(1);
        await mount(Discuss, target, { env });
        target.querySelector(".o-mail-message-actions").classList.remove("invisible");
        await click(target, "i[aria-label='Edit']");

        await click($("a:contains('save')")[0]);
        await nextTick();
        assert.verifySteps([]);
    });
});
