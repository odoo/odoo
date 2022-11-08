/** @odoo-module **/

import { Composer } from "@mail/composer/composer";
import { loadEmojiData } from "@mail/composer/emoji_picker";
import { click, getFixture, mount, nextTick } from "@web/../tests/helpers/utils";
import { makeTestEnv, TestServer } from "../helpers/helpers";
import { registry } from "@web/core/registry";

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

    QUnit.test(
        "click on emoji button, select emoji, then re-click on button should show emoji picker",
        async (assert) => {
            const server = new TestServer();
            server.addChannel(1, "general", "General announcements...");
            const env = makeTestEnv((route, params) => server.rpc(route, params));
            const { Component: PopoverContainer, props } = registry
                .category("main_components")
                .get("PopoverContainer");
            await mount(PopoverContainer, target, { env, props });
            await mount(Composer, target, { env, props: { threadId: 1, placeholder: "owl" } });
            await click(target.querySelector("i[aria-label='Emojis']").closest("button"));
            await loadEmojiData(); // wait for emoji being loaded (required for rendering)
            await nextTick(); // wait for following rendering
            await click(target.querySelector(".o-mail-emoji-picker-content .o-emoji"));
            await click(target.querySelector("i[aria-label='Emojis']").closest("button"));
            assert.containsOnce(target, ".o-mail-emoji-picker");
        }
    );
});
