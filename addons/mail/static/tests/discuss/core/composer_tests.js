/* @odoo-module */

import { Composer } from "@mail/core/common/composer";
import { click, insertText, start, startServer } from "@mail/../tests/helpers/test_utils";

import { patchWithCleanup } from "@web/../tests/helpers/utils";

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
    await insertText(".o-mail-Composer-input", "/");
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
        await insertText(".o-mail-Composer-input", "/");
        await click(".o-mail-Composer-suggestion");
        await insertText(".o-mail-Composer-input", " is user?");
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
    assert.strictEqual($(".o-mail-Composer-input").val(), "");
    await insertText(".o-mail-Composer-input", "/");
    await click(".o-mail-Composer-suggestion");
    assert.strictEqual(
        $(".o-mail-Composer-input").val().replace(/\s/, " "),
        "/who ",
        "previous content + used command + additional whitespace afterwards"
    );

    await click("button[aria-label='Emojis']");
    await click(".o-Emoji:contains(😊)");
    assert.strictEqual($(".o-mail-Composer-input").val().replace(/\s/, " "), "/who 😊");
});
