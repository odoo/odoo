/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { afterNextRender, click, insertText } from "@mail/../tests/helpers/test_utils";
import { loadDefaultConfig, start } from "@im_livechat/../tests/embed/helper/test_utils";
import { nextTick, triggerHotkey } from "@web/../tests/helpers/utils";

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
    await afterNextRender(() => triggerHotkey("Enter"));
    const thread = env.services["im_livechat.livechat"].thread;
    pyEnv["bus.bus"]._sendone(thread.uuid, "im_livechat.history_command", { id: thread.id });
    await nextTick();
    assert.verifySteps(["/im_livechat/history"]);
});
