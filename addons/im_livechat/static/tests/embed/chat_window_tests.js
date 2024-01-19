/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { LivechatButton } from "@im_livechat/embed/common/livechat_button";
import { loadDefaultConfig, start } from "@im_livechat/../tests/embed/helper/test_utils";

import { patchWithCleanup, triggerHotkey } from "@web/../tests/helpers/utils";
import { assertSteps, click, contains, insertText, step } from "@web/../tests/utils";

QUnit.module("chat window");

QUnit.test("do not save fold state of temporary live chats", async () => {
    patchWithCleanup(LivechatButton, {
        DEBOUNCE_DELAY: 0,
    });
    await startServer();
    await loadDefaultConfig();
    await start({
        mockRPC(route, args) {
            if (route === "/discuss/channel/fold") {
                step(`fold - ${args.state}`);
            }
        },
    });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Message", { text: "Hello, how may I help you?" });
    await assertSteps([]);
    await insertText(".o-mail-Composer-input", "Hello");
    await triggerHotkey("Enter");
    await contains(".o-mail-Message", { text: "Hello" });
    await assertSteps(["fold - open"]);
    await click(".o-mail-ChatWindow-header");
    await contains(".o-mail-Message", { text: "Hello", count: 0 });
    await assertSteps(["fold - folded"]);
    await click("[title='Close Chat Window']");
    await click("button", { text: "Close conversation" });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Message", { text: "Hello, how may I help you?" });
    await assertSteps([]);
    await click(".o-mail-ChatWindow-header");
    await assertSteps([]);
});
