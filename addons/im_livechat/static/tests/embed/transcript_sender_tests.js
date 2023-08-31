/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { loadDefaultConfig, start } from "@im_livechat/../tests/embed/helper/test_utils";

import { click, contains, insertText } from "@mail/../tests/helpers/test_utils";

import { triggerHotkey } from "@web/../tests/helpers/utils";

QUnit.module("transcript sender");

QUnit.test("send", async (assert) => {
    await startServer();
    await loadDefaultConfig();
    start({
        mockRPC(route, args) {
            if (route === "/im_livechat/email_livechat_transcript") {
                assert.step(`send_transcript - ${args.email}`);
            }
        },
    });
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message-content", 1, { text: "Hello World!" });
    await click(".o-mail-ChatWindow-command[title*='Close']");
    await contains(".form-text", 1, { text: "Receive a copy of this conversation." });
    await contains("button[data-action='sendTranscript']:disabled");
    await insertText("input[placeholder='mail@example.com']", "odoobot@odoo.com");
    await click("button[data-action='sendTranscript']:not(:disabled)");
    await contains(".form-text", 1, { text: "The conversation was sent." });
    assert.verifySteps(["send_transcript - odoobot@odoo.com"]);
});

QUnit.test("send failed", async () => {
    await startServer();
    await loadDefaultConfig();
    start({
        mockRPC(route) {
            if (route === "/im_livechat/email_livechat_transcript") {
                throw new Error();
            }
        },
    });
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message-content", 1, { text: "Hello World!" });
    await click(".o-mail-ChatWindow-command[title*='Close']");
    await insertText("input[placeholder='mail@example.com']", "odoobot@odoo.com");
    await click("button[data-action='sendTranscript']:not(:disabled)");
    await contains(".form-text", 1, { text: "An error occurred. Please try again." });
});
