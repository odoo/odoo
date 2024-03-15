const test = QUnit.test; // QUnit.test()

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { loadDefaultConfig, start } from "@im_livechat/../tests/embed/helper/test_utils";
import { nextTick, triggerHotkey } from "@web/../tests/helpers/utils";
import { assertSteps, click, contains, insertText, step } from "@web/../tests/utils";

QUnit.module("Livechat history command");

test("Handle livechat history command", async () => {
    const pyEnv = await startServer();
    await loadDefaultConfig();
    const env = await start({
        mockRPC(route, args) {
            if (route === "/im_livechat/history") {
                step("/im_livechat/history");
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
    await assertSteps(["/im_livechat/history"]);
});
