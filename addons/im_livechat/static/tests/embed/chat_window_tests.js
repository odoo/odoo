/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { loadDefaultConfig, start } from "@im_livechat/../tests/embed/helper/test_utils";
import { click, contains, insertText } from "@web/../tests/utils";
import { patchWithCleanup, triggerHotkey } from "@web/../tests/helpers/utils";
import { LivechatButton } from "@im_livechat/embed/common/livechat_button";

QUnit.module("chat window");

QUnit.test("do not save fold state of temporary live chats", async (assert) => {
    patchWithCleanup(LivechatButton, {
        DEBOUNCE_DELAY: 0,
    });
    await startServer();
    await loadDefaultConfig();
    await start({
        mockRPC(route, args) {
            if (route === "/discuss/channel/fold") {
                assert.step(`fold - ${args.state}`);
            }
        },
    });
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "Hello");
    triggerHotkey("Enter");
    await contains(".o-mail-Message", { text: "Hello" });
    await click(".o-mail-ChatWindow-header");
    assert.verifySteps(["fold - folded"]);
    await click("[title='Close Chat Window']");
    await click("button", { text: "Close conversation" });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Message", { text: "Hello, how may I help you?" });
    assert.verifySteps([]);
});
