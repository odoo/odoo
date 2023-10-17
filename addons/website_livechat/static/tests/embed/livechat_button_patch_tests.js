/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { loadDefaultConfig, start } from "@im_livechat/../tests/embed/helper/test_utils";

import { click, contains } from "@web/../tests/utils";

QUnit.module("live chat button");

QUnit.test("clicking on notification opens the chat", async () => {
    await startServer();
    await loadDefaultConfig();
    await start({
        mockRPC(route) {
            if (route === "/im_livechat/init") {
                return { rule: { action: "display_button_and_text" } };
            }
        },
    });
    await click(".o-livechat-LivechatButton-notification", {
        text: "Have a Question? Chat with us.",
    });
    await contains(".o-mail-ChatWindow");
});
