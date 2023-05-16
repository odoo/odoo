/* @odoo-module */

import { click, insertText, start, startServer } from "@mail/../tests/helpers/test_utils";

import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { Composer } from "@mail/composer/composer";

QUnit.module("composer", {
    async beforeEach() {
        // Simulate real user interactions
        patchWithCleanup(Composer.prototype, {
            isEventTrusted() {
                return true;
            },
        });
    },
});

QUnit.test('do not send typing notification on typing "/" command', async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "channel" });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/discuss/channel/notify_typing") {
                assert.step(`notify_typing:${args.is_typing}`);
            }
        },
    });
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer .odoo-editor-editable", "/");
    assert.verifySteps([], "No rpc done");
});

QUnit.test(
    'do not send typing notification on typing after selecting suggestion from "/" command',
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "channel" });
        const { openDiscuss } = await start({
            async mockRPC(route, args) {
                if (route === "/discuss/channel/notify_typing") {
                    assert.step(`notify_typing:${args.is_typing}`);
                }
            },
        });
        await openDiscuss(channelId);
        await insertText(".o-mail-Composer .odoo-editor-editable", "/");
        await click(".o-mail-Composer-suggestion");
        await insertText(".o-mail-Composer .odoo-editor-editable", " is user?");
        assert.verifySteps([], "No rpc done");
    }
);

QUnit.test("add an emoji after a command", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-mail-Composer-suggestionList .o-open");
    assert.strictEqual($(".o-mail-Composer .odoo-editor-editable")[0].textContent, "");
    await insertText(".o-mail-Composer .odoo-editor-editable", "/");
    await click(".o-mail-Composer-suggestion");
    assert.strictEqual(
        $(".o-mail-Composer .odoo-editor-editable")[0].textContent.replaceAll(/\s/g, " "),
        "/who ",
        "previous content + used command + additional whitespace afterwards"
    );

    await click("button[aria-label='Emojis']");
    await click(".o-mail-Emoji:contains(😊)");
    assert.strictEqual(
        $(".o-mail-Composer .odoo-editor-editable")[0].textContent.replaceAll(/\s/g, " "),
        "/who 😊"
    );
});
