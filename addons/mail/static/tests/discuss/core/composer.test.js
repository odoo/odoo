import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    insertText,
    onRpcBefore,
    openDiscuss,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { Composer } from "@mail/core/common/composer";
import { beforeEach, describe, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

beforeEach(() => {
    // Simulate real user interactions
    patchWithCleanup(Composer.prototype, {
        isEventTrusted() {
            return true;
        },
    });
});

test('do not send typing notification on typing "/" command', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "channel" });
    onRpcBefore("/discuss/channel/notify_typing", () => step("notify_typing"));
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/");
    await assertSteps([]); // No rpc done
});

test('do not send typing notification on typing after selecting suggestion from "/" command', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "channel" });
    onRpcBefore("/discuss/channel/notify_typing", () => step("notify_typing"));
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/");
    await click(":nth-child(1 of .o-mail-Composer-suggestion)");
    await contains(".o-mail-Composer-suggestion strong", { count: 0 });
    await insertText(".o-mail-Composer-input", " is user?");
    await assertSteps([]); // No rpc done"
});

test("send is_typing on adding emoji", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "channel" });
    onRpcBefore("/discuss/channel/notify_typing", () => step("notify_typing"));
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await insertText("input[placeholder='Search for an emoji']", "Santa Claus");
    await click(".o-Emoji", { text: "🎅" });
    await assertSteps(["notify_typing"]);
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
