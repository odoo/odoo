/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { loadDefaultConfig, start } from "@im_livechat/../tests/embed/helper/test_utils";

import { triggerHotkey } from "@web/../tests/helpers/utils";
import { click, contains, insertText } from "@web/../tests/utils";

QUnit.test("open/close temporary channel", async () => {
    await startServer();
    await loadDefaultConfig();
    start();
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
    await contains(".o-livechat-LivechatButton", { count: 0 });
    await click("[title='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await contains(".o-livechat-LivechatButton", { count: 1 });
});

QUnit.test("open/close persisted channel", async () => {
    await startServer();
    await loadDefaultConfig();
    start();
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "How can I help?");
    triggerHotkey("Enter");
    await contains(".o-mail-Message-content", { text: "How can I help?" });
    await click("[title='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { text: "Did we correctly answer your question?" });
    await click("[title='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await contains(".o-livechat-LivechatButton", { count: 1 });
});

QUnit.test("livechat not available", async () => {
    await startServer();
    await loadDefaultConfig();
    start({
        mockRPC(route) {
            if (route === "/im_livechat/init") {
                return { available_for_me: false };
            }
        },
    });
    await contains(".o-mail-ChatWindowContainer");
    await contains(".o-livechat-LivechatButton", { count: 0 });
});
