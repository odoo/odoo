/* @odoo-module */

import { Composer } from "@mail/composer/composer";
import {
    afterNextRender,
    click,
    insertText,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("suggestion", {
    async beforeEach() {
        // Simulate real user interactions
        patchWithCleanup(Composer.prototype, {
            isEventTrusted() {
                return true;
            },
        });
    },
});

QUnit.test('display command suggestions on typing "/"', async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-mail-Composer-suggestionList .o-open");
    await insertText(".o-mail-Composer-input", "/");
    assert.containsOnce($, ".o-mail-Composer-suggestionList .o-open");
});

QUnit.test("use a command for a specific channel type", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-mail-Composer-suggestionList .o-open");
    assert.strictEqual($(".o-mail-Composer-input").val(), "");
    await insertText(".o-mail-Composer-input", "/");
    await click(".o-mail-Composer-suggestion");
    assert.strictEqual(
        $(".o-mail-Composer-input").val().replace(/\s/, " "),
        "/who ",
        "command + additional whitespace afterwards"
    );
});

QUnit.test(
    "command suggestion should only open if command is the first character",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            name: "General",
            channel_type: "channel",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsNone($, ".o-mail-Composer-suggestionList .o-open");
        assert.strictEqual($(".o-mail-Composer-input").val(), "");
        await insertText(".o-mail-Composer-input", "bluhbluh ");
        assert.strictEqual($(".o-mail-Composer-input").val(), "bluhbluh ");
        await insertText(".o-mail-Composer-input", "/");
        assert.containsNone($, ".o-mail-Composer-suggestionList .o-open");
    }
);

QUnit.test("suggestion are shown after deleting a character", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/");
    await insertText(".o-mail-Composer-input", "hee");
    assert.containsNone($, ".o-mail-Composer-suggestion:contains(help)");
    // Simulate pressing backspace
    await afterNextRender(() => {
        const textarea = document.querySelector(".o-mail-Composer-input");
        textarea.value = textarea.value.slice(0, -1);
    });
    assert.containsOnce($, ".o-mail-Composer-suggestion:contains(help)");
});
