/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { loadDefaultConfig, start } from "@im_livechat/../tests/embed/helper/test_utils";
import { nextTick, triggerHotkey } from "@web/../tests/helpers/utils";
import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("Livechat history command");

QUnit.test("Handle livechat history command", async (assert) => {
    const pyEnv = await startServer();
    await loadDefaultConfig();
    const env = await start({
        mockRPC(route, args) {
            if (route === "/im_livechat/history") {
                assert.step("/im_livechat/history");
                return true;
            }
        },
    });
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message", { count: 2 });
    const thread = env.services["im_livechat.livechat"].thread;
    pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "im_livechat.history_command", {
        id: thread.id,
    });
    await nextTick();
    assert.verifySteps(["/im_livechat/history"]);
});
