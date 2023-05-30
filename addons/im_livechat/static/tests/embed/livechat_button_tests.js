/** @odoo-module */

import { start, loadDefaultConfig } from "@im_livechat/../tests/embed/helper/test_utils";
import { afterNextRender, click, insertText } from "@mail/../tests/helpers/test_utils";
import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { triggerHotkey } from "@web/../tests/helpers/utils";

QUnit.test("open/close temporary channel", async (assert) => {
    await startServer();
    await loadDefaultConfig();
    await start();
    assert.containsOnce($, ".o-livechat-LivechatButton");
    await click(".o-livechat-LivechatButton");
    assert.containsOnce($, ".o-mail-ChatWindow");
    assert.containsNone($, ".o-livechat-LivechatButton");
    await click("[title='Close Chat Window']");
    assert.containsNone($, ".o-mail-ChatWindow");
    assert.containsNone($, ".o-livechat-LivechatButton");
});

QUnit.test("open/close persisted channel", async (assert) => {
    await startServer();
    await loadDefaultConfig();
    await start();
    assert.containsOnce($, ".o-livechat-LivechatButton");
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "Hello");
    await afterNextRender(() => triggerHotkey("Enter"));
    await click("[title='Close Chat Window']");
    await click("[title='Close Chat Window']");
    assert.containsNone($, ".o-mail-ChatWindow");
    assert.containsNone($, ".o-livechat-LivechatButton");
});

QUnit.test("livechat not available", async (assert) => {
    await startServer();
    await loadDefaultConfig();
    await start({
        mockRPC(route) {
            if (route === "/im_livechat/init") {
                return { available_for_me: false };
            }
        },
    });
    assert.containsNone($, ".o-livechat-LivechatButton");
});
