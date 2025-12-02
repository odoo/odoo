import { insertText as htmlInsertText } from "@html_editor/../tests/_helpers/user_actions";

import {
    click,
    contains,
    defineMailModels,
    focus,
    insertText,
    onRpcBefore,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { Composer } from "@mail/core/common/composer";
import { beforeEach, describe, test } from "@odoo/hoot";
import {
    asyncStep,
    getService,
    patchWithCleanup,
    waitForSteps,
} from "@web/../tests/web_test_helpers";

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
    let testEnded = false;
    onRpcBefore("/discuss/channel/notify_typing", () => {
        if (!testEnded) {
            asyncStep("notify_typing");
        }
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/");
    await contains(".o-mail-Composer button[title='Send']:enabled");
    await waitForSteps([]); // No rpc done
    testEnded = true;
});

test('do not send typing notification on typing after selecting suggestion from "/" command', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "channel" });
    let testEnded = false;
    onRpcBefore("/discuss/channel/notify_typing", () => {
        if (!testEnded) {
            asyncStep("notify_typing");
        }
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/");
    await click(":nth-child(1 of .o-mail-Composer-suggestion)");
    await contains(".o-mail-Composer-suggestion strong", { count: 0 });
    await insertText(".o-mail-Composer-input", " is user?");
    await waitForSteps([]); // No rpc done"
    testEnded = true;
});

test("send is_typing on adding emoji", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "channel" });
    let testEnded = false;
    onRpcBefore("/discuss/channel/notify_typing", () => {
        if (!testEnded) {
            asyncStep("notify_typing");
        }
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    await insertText("input[placeholder='Search emoji']", "Santa Claus");
    await click(".o-Emoji", { text: "🎅" });
    await waitForSteps(["notify_typing"]);
    testEnded = true;
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
    await click("button[title='Add Emojis']");
    await click(".o-Emoji", { text: "😊" });
    await contains(".o-mail-Composer-input", { value: "/who 😊" });
});

test.tags("html composer");
test("html composer: send a message in a channel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input", { value: "" });
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await focus(".o-mail-Composer-html.odoo-editor-editable");
    const editor = {
        document,
        editable: document.querySelector(".o-mail-Composer-html.odoo-editor-editable"),
    };
    await htmlInsertText(editor, "Hello");
    await contains(".o-mail-Composer-html.odoo-editor-editable", { text: "Hello" });
    await click(".o-mail-Composer button[title='Send']:enabled");
    await click(".o-mail-Message[data-persistent]:contains(Hello)");
    await contains(".o-mail-Composer-html.odoo-editor-editable", { text: "" });
});
