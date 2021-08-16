/** @odoo-module **/

import { newMessageService } from "@mail/services/new_message_service/new_message_service";
import { afterEach, afterNextRender, beforeEach, start } from '@mail/utils/test_utils';

import { click, nextTick, patchWithCleanup, triggerHotkey } from "@web/../tests/helpers/utils";
import { browser } from '@web/core/browser/browser';
import { registry } from "@web/core/registry";
import { commandService } from "@web/webclient/commands/command_service";

const serviceRegistry = registry.category("services");

QUnit.module('mail', {}, function () {
QUnit.module('services', {}, function () {
QUnit.module('new_message_service', {}, function () {
QUnit.module('new_message_service_tests.js', {
    beforeEach() {
        serviceRegistry.add("command", commandService);
        serviceRegistry.add("new_message", newMessageService);
        beforeEach(this);
        patchWithCleanup(browser, {
            clearTimeout() {},
            setTimeout(later, wait) {
                later();
            },
        });
        registry.category("command_categories").add("default", { label: ("default") });
    },
    afterEach() {
        afterEach(this);
    },
}, function () {

QUnit.test('Open "New Message" chat window with a command', async function (assert) {
    assert.expect(3);

    const { widget: webClient } = await start({
        data: this.data,
        hasChatWindow: true,
        hasWebClient: true,
    });
    triggerHotkey("control+k");
    await nextTick();

    const search = webClient.el.querySelector(".o_command_palette_search input");
    search.value = "Message a user";
    search.dispatchEvent(new window.InputEvent("input"));
    await nextTick();
    assert.deepEqual(
        webClient.el.querySelector(".o_command_palette .o_command.focused").textContent,
        "Message a userALT + SHIFT + W",
    );

    await afterNextRender(() => click(document.body, ".o_command.focused"));
    assert.containsOnce(document.body, ".o_ChatWindow");
    assert.strictEqual(document.querySelector(".o_ChatWindow .o_ChatWindowHeader_name").textContent, "New message");

    webClient.destroy();
});

QUnit.test('open "New Message" chat window with a hotkey', async function (assert) {
    assert.expect(2);

    const { widget: webClient } = await start({
        data: this.data,
        hasChatWindow: true,
        hasWebClient: true,
    });
    await afterNextRender(() => triggerHotkey("alt+shift+w"));
    assert.containsOnce(document.body, ".o_ChatWindow");
    assert.strictEqual(document.querySelector(".o_ChatWindow .o_ChatWindowHeader_name").textContent, "New message");

    webClient.destroy();
});

QUnit.test('Open "New Message" in discuss with a command', async function (assert) {
    assert.expect(1);

    const { widget: webClient } = await start({
        autoOpenDiscuss: true,
        data: this.data,
        hasDiscuss: true,
        hasWebClient: true,
    });
    triggerHotkey("control+k");
    await nextTick();

    const search = webClient.el.querySelector(".o_command_palette_search input");
    search.value = "Message a user";
    search.dispatchEvent(new window.InputEvent("input"));
    await nextTick();

    await afterNextRender(() => click(document.body, ".o_command.focused"));
    assert.containsOnce(document.body, ".o_DiscussSidebar_itemNewInput");

    webClient.destroy();
});

QUnit.test('Open "New Message" in discuss with a hotkey', async function (assert) {
    assert.expect(1);

    const { widget: webClient } = await start({
        autoOpenDiscuss: true,
        data: this.data,
        hasDiscuss: true,
        hasWebClient: true,
    });
    await afterNextRender(() => triggerHotkey("alt+shift+w"));
    assert.containsOnce(document.body, ".o_DiscussSidebar_itemNewInput");

    webClient.destroy();
});

});
});
});
});
