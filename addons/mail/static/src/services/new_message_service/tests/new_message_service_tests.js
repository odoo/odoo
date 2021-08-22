/** @odoo-module **/

import { afterNextRender, beforeEach } from '@mail/utils/test_utils';

import { click, nextTick, patchWithCleanup, triggerHotkey } from "@web/../tests/helpers/utils";
import { browser } from '@web/core/browser/browser';

QUnit.module('mail', {}, function () {
QUnit.module('services', {}, function () {
QUnit.module('new_message_service', {}, function () {
QUnit.module('new_message_service_tests.js', {
    beforeEach() {
        beforeEach.call(this);
        patchWithCleanup(browser, {
            clearTimeout() {},
            setTimeout(later, wait) {
                later();
            },
        });
    },
}, function () {

QUnit.test('Open "New Message" chat window with a command', async function (assert) {
    assert.expect(3);

    await this.start();
    triggerHotkey("control+k");
    await nextTick();

    const search = document.body.querySelector(".o_command_palette_search input");
    search.value = "Message a user";
    search.dispatchEvent(new window.InputEvent("input"));
    await nextTick();
    assert.deepEqual(
        document.body.querySelector(".o_command_palette .o_command.focused").textContent,
        "Message a userALT + SHIFT + W",
    );

    await afterNextRender(() => click(document.body, ".o_command.focused"));
    assert.containsOnce(document.body, ".o_ChatWindow");
    assert.strictEqual(document.querySelector(".o_ChatWindow .o_ChatWindowHeader_name").textContent, "New message");
});

QUnit.test('open "New Message" chat window with a hotkey', async function (assert) {
    assert.expect(2);

    await this.start();
    await afterNextRender(() => triggerHotkey("alt+shift+w"));
    assert.containsOnce(document.body, ".o_ChatWindow");
    assert.strictEqual(document.querySelector(".o_ChatWindow .o_ChatWindowHeader_name").textContent, "New message");
});

QUnit.test('Open "New Message" in discuss with a command', async function (assert) {
    assert.expect(1);

    const { openDiscuss } = await this.start();
    await openDiscuss();

    triggerHotkey("control+k");
    await nextTick();

    const search = document.body.querySelector(".o_command_palette_search input");
    search.value = "Message a user";
    search.dispatchEvent(new window.InputEvent("input"));
    await nextTick();

    await afterNextRender(() => click(document.body, ".o_command.focused"));
    assert.containsOnce(document.body, ".o_DiscussSidebar_itemNewInput");
});

QUnit.test('Open "New Message" in discuss with a hotkey', async function (assert) {
    assert.expect(1);

    const { openDiscuss } = await this.start();
    await openDiscuss();

    await afterNextRender(() => triggerHotkey("alt+shift+w"));
    assert.containsOnce(document.body, ".o_DiscussSidebar_itemNewInput");
});

});
});
});
});
