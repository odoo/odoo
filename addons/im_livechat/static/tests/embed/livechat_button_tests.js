const test = QUnit.test; // QUnit.test()

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { waitUntilSubscribe } from "@bus/../tests/helpers/websocket_event_deferred";

import { loadDefaultConfig, start } from "@im_livechat/../tests/embed/helper/test_utils";

import { triggerHotkey } from "@web/../tests/helpers/utils";
import { click, contains, insertText } from "@web/../tests/utils";
import { assertSteps, step } from "@web/../tests/legacy/utils";

test("open/close temporary channel", async () => {
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

test("open/close persisted channel", async () => {
    await startServer();
    await loadDefaultConfig();
    await start({
        mockRPC(route, args, originalRPC) {
            const res = originalRPC(...arguments);
            if (route === "/im_livechat/get_session" && args.persisted) {
                step("persisted");
            }
            return res;
        },
    });
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "How can I help?");
    await triggerHotkey("Enter");
    await waitUntilSubscribe();
    await assertSteps(["persisted"]);
    await contains(".o-mail-Message-content", { text: "How can I help?" });
    await click("[title='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { text: "Did we correctly answer your question?" });
    await click("[title='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await contains(".o-livechat-LivechatButton", { count: 1 });
});

test("livechat not available", async () => {
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

test("clicking on notification opens the chat", async () => {
    await startServer();
    await loadDefaultConfig();
    await start({
        mockRPC(route) {
            if (route === "/im_livechat/init") {
                return { available_for_me: true, rule: { action: "display_button_and_text" } };
            }
        },
    });
    await click(".o-livechat-LivechatButton-notification", {
        text: "Have a Question? Chat with us.",
    });
    await contains(".o-mail-ChatWindow");
});
