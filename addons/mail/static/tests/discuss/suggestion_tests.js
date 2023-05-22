/* @odoo-module */

import { Composer } from "@mail/composer/composer";
import { click, insertText, start, startServer } from "@mail/../tests/helpers/test_utils";
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
    await insertText(".o-mail-Composer .odoo-editor-editable", "/");
    assert.containsOnce($, ".o-mail-Composer-suggestionList .o-open");
});

QUnit.test("use a command for a specific channel type", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-mail-Composer-suggestionList .o-open");
    assert.strictEqual($(".o-mail-Composer .odoo-editor-editable")[0].textContent, "");
    await insertText(".o-mail-Composer .odoo-editor-editable", "/");
    await click(".o-mail-Composer-suggestion");
    assert.strictEqual(
        $(".o-mail-Composer .odoo-editor-editable")[0].textContent.replaceAll(/\s/g, " "),
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
        assert.strictEqual($(".o-mail-Composer .odoo-editor-editable")[0].textContent, "");
        await insertText(".o-mail-Composer .odoo-editor-editable", "bluhbluh ");
        assert.strictEqual(
            $(".o-mail-Composer .odoo-editor-editable")[0].textContent.replaceAll(/\s/g, " "),
            "bluhbluh "
        );
        await insertText(".o-mail-Composer .odoo-editor-editable", "/");
        assert.containsNone($, ".o-mail-Composer-suggestionList .o-open");
    }
);
