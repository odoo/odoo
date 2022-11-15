/** @odoo-module **/

import { loadEmoji } from "@mail/new/composer/emoji_picker";
import { Discuss } from "@mail/new/discuss/discuss";
import { startServer, start } from "@mail/../tests/helpers/test_utils";

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
        await nextTick();
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
        await loadEmoji(); // wait for emoji being loaded (required for rendering)
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
        server.addMessage("comment", 1, 1, "mail.channel", 3, "Hello world\nGoodbye world");
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

    QUnit.test("Scroll bar to the top when edit starts", async (assert) => {
        const server = new TestServer();
        server.addChannel(1, "general", "General announcements...");
        server.addMessage("comment", 1, 1, "mail.channel", 3, "Hello world ! ".repeat(1000));
        const env = makeTestEnv((route, params) => server.rpc(route, params));
        await env.services["mail.messaging"].isReady;
        env.services["mail.messaging"].setDiscussThread(1);
        await mount(Discuss, target, { env });
        target.querySelector(".o-mail-message-actions").classList.remove("invisible");
        await click(target, "i[aria-label='Edit']");

        const messageTextarea = document.querySelector(
            ".o-mail-message-editable-content .o-mail-composer-textarea"
        );
        assert.ok(
            messageTextarea.scrollHeight > messageTextarea.clientHeight,
            "Composer textarea has a vertical scroll bar"
        );
        assert.strictEqual(
            messageTextarea.scrollTop,
            0,
            "Composer text area is scrolled to the top when edit starts"
        );
    });

    QUnit.test(
        "Other messages are grayed out when replying to another one",
        async function (assert) {
            const pyEnv = await startServer();
            const channelId = pyEnv["mail.channel"].create({
                channel_type: "channel",
                name: "channel1",
            });
            const [firstMessageId, secondMessageId] = pyEnv["mail.message"].create([
                { body: "Hello world", res_id: channelId, model: "mail.channel" },
                { body: "Goodbye world", res_id: channelId, model: "mail.channel" },
            ]);
            const { click, openDiscuss } = await start({
                discuss: {
                    context: {
                        active_id: `mail.channel_${channelId}`,
                    },
                },
            });
            await openDiscuss();
            assert.containsN(document.body, ".o-mail-message", 2, "Should display two messages");
            await click(
                `.o-mail-message[data-message-id='${firstMessageId}'] i[aria-label='Reply']`
            );
            assert.notOk(
                document
                    .querySelector(`.o-mail-message[data-message-id='${firstMessageId}']`)
                    .classList.contains("opacity-50"),
                "First message should not be grayed out"
            );
            assert.ok(
                document
                    .querySelector(`.o-mail-message[data-message-id='${secondMessageId}']`)
                    .classList.contains("opacity-50"),
                "Second message should be grayed out"
            );
        }
    );

    QUnit.test("Parent message body is displayed on replies", async function (assert) {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({
            channel_type: "channel",
            name: "channel1",
        });
        pyEnv["mail.message"].create({
            body: "Hello world",
            res_id: channelId,
            model: "mail.channel",
        });
        const { click, openDiscuss } = await start({
            discuss: {
                context: {
                    active_id: `mail.channel_${channelId}`,
                },
            },
        });
        await openDiscuss();

        await click(`.o-mail-message i[aria-label='Reply']`);
        await editInput(document.body, ".o-mail-composer textarea", "FooBarFoo");
        await click(".o-mail-composer-send-button");
        assert.containsOnce(
            document.body,
            ".o-mail-message-in-reply-body",
            "Origin message should be displayed on reply"
        );
        assert.ok(
            document.querySelector(".o-mail-message-in-reply-body").innerText,
            "Hello world",
            "Origin message should be correct"
        );
    });

    QUnit.test(
        "Updating the parent message of a reply also updates the visual of the reply",
        async function (assert) {
            const pyEnv = await startServer();
            const channelId = pyEnv["mail.channel"].create({
                channel_type: "channel",
                name: "channel1",
            });
            pyEnv["mail.message"].create({
                body: "Hello world",
                res_id: channelId,
                message_type: "comment",
                model: "mail.channel",
            });
            const { click, openDiscuss } = await start({
                discuss: {
                    context: {
                        active_id: `mail.channel_${channelId}`,
                    },
                },
            });
            await openDiscuss();

            await click("i[aria-label='Reply']");
            await editInput(document.body, ".o-mail-composer textarea", "FooBarFoo");
            await triggerHotkey("Enter", false);
            await click("i[aria-label='Edit']");
            await editInput(target, ".o-mail-message textarea", "Goodbye World");
            await triggerHotkey("Enter", false);
            await nextTick();
            assert.strictEqual(
                document.querySelector(".o-mail-message-in-reply-body").innerText,
                "Goodbye World"
            );
        }
    );

    QUnit.test(
        "Deleting parent message of a reply should adapt reply visual",
        async function (assert) {
            const pyEnv = await startServer();
            const channelId = pyEnv["mail.channel"].create({
                channel_type: "channel",
                name: "channel1",
            });
            pyEnv["mail.message"].create({
                body: "Hello world",
                res_id: channelId,
                message_type: "comment",
                model: "mail.channel",
            });
            const { click, openDiscuss } = await start({
                discuss: {
                    context: {
                        active_id: `mail.channel_${channelId}`,
                    },
                },
            });
            await openDiscuss();

            await click("i[aria-label='Reply']");
            await editInput(document.body, ".o-mail-composer textarea", "FooBarFoo");
            await triggerHotkey("Enter", false);
            await click("i[aria-label='Delete']");
            $('button:contains("Delete")').click();
            await nextTick();
            assert.strictEqual(
                document.querySelector(".o-mail-message-in-reply-deleted-message").innerText,
                "Original message was deleted"
            );
        }
    );
});
