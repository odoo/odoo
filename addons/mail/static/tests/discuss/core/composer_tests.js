/* @odoo-module */

import { Composer } from "@mail/core/common/composer";
import { click, contains, insertText, start, startServer } from "@mail/../tests/helpers/test_utils";

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
    openDiscuss(channelId);
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
        openDiscuss(channelId);
        await insertText(".o-mail-Composer-input", "/");
        await click(".o-mail-Composer-suggestion:eq(0)");
        await contains(".o-mail-Composer-suggestion strong", { count: 0 });
        await insertText(".o-mail-Composer-input", " is user?");
        assert.verifySteps([], "No rpc done");
    }
);

QUnit.test("add an emoji after a command", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", "/");
    await click(".o-mail-Composer-suggestion:eq(0)");
    await contains(".o-mail-Composer-input", { value: "/who " });
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji", { text: "😊" });
    await contains(".o-mail-Composer-input", { value: "/who 😊" });
});
