/** @odoo-module */

import { beforeEach, expect, test } from "@odoo/hoot";

import { Composer } from "@mail/core/common/composer";
import {
    click,
    contains,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "../../mail_test_helpers";
import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";

beforeEach(() => {
    // Simulate real user interactions
    patchWithCleanup(Composer.prototype, {
        isEventTrusted() {
            return true;
        },
    });
});

test.skip('do not send typing notification on typing "/" command', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "channel" });
    onRpc((route, args) => {
        if (route === "/discuss/channel/notify_typing") {
            expect.step(`notify_typing:${args.is_typing}`);
        }
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/");
    expect([]).toVerifySteps({ message: "No rpc done" });
});

test.skip('do not send typing notification on typing after selecting suggestion from "/" command', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "channel" });
    onRpc((route, args) => {
        if (route === "/discuss/channel/notify_typing") {
            expect.step(`notify_typing:${args.is_typing}`);
        }
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/");
    await click(":nth-child(1 of .o-mail-Composer-suggestion)");
    await contains(".o-mail-Composer-suggestion strong", { count: 0 });
    await insertText(".o-mail-Composer-input", " is user?");
    expect([]).toVerifySteps({ message: "No rpc done" });
});

test.skip("add an emoji after a command", async () => {
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
