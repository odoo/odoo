/** @odoo-module alias=@mail/../tests/discuss/core/composer_tests default=false */
const test = QUnit.test; // QUnit.test()

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Composer } from "@mail/core/common/composer";
import { openDiscuss, start } from "@mail/../tests/helpers/test_utils";

import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { assertSteps, click, contains, insertText, step } from "@web/../tests/utils";

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

test('do not send typing notification on typing "/" command', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "channel" });
    await start({
        async mockRPC(route, args) {
            if (route === "/discuss/channel/notify_typing") {
                step(`notify_typing:${args.is_typing}`);
            }
        },
    });
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/");
    await assertSteps([], "No rpc done");
});

test('do not send typing notification on typing after selecting suggestion from "/" command', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "channel" });
    await start({
        async mockRPC(route, args) {
            if (route === "/discuss/channel/notify_typing") {
                step(`notify_typing:${args.is_typing}`);
            }
        },
    });
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/");
    await click(":nth-child(1 of .o-mail-Composer-suggestion)");
    await contains(".o-mail-Composer-suggestion strong", { count: 0 });
    await insertText(".o-mail-Composer-input", " is user?");
    await assertSteps([], "No rpc done");
});

test("add an emoji after a command", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", "/");
    await click(":nth-child(1 of .o-mail-Composer-suggestion)");
    await contains(".o-mail-Composer-input", { value: "/who " });
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji", { text: "😊" });
    await contains(".o-mail-Composer-input", { value: "/who 😊" });
});
