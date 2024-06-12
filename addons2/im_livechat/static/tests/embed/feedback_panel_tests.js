/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { RATING } from "@im_livechat/embed/common/livechat_service";
import { loadDefaultConfig, start } from "@im_livechat/../tests/embed/helper/test_utils";

import { triggerHotkey } from "@web/../tests/helpers/utils";
import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("feedback panel");

QUnit.test("Do not ask feedback if empty", async () => {
    await startServer();
    await loadDefaultConfig();
    start();
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
    await click("[title='Close Chat Window']");
    await contains(".o-livechat-LivechatButton", { count: 0 });
});

QUnit.test("Close without feedback", async (assert) => {
    await startServer();
    await loadDefaultConfig();
    start({
        mockRPC(route) {
            if (route === "/im_livechat/visitor_leave_session") {
                assert.step(route);
            }
            if (route === "/im_livechat/feedback") {
                assert.step(route);
            }
        },
    });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message-content", { text: "Hello World!" });
    await click("[title='Close Chat Window']");
    await click("button", { text: "Close conversation" });
    await contains(".o-livechat-LivechatButton", { count: 0 });
    assert.verifySteps(["/im_livechat/visitor_leave_session"]);
});

QUnit.test("Feedback with rating and comment", async (assert) => {
    await startServer();
    await loadDefaultConfig();
    start({
        mockRPC(route, args) {
            if (route === "/im_livechat/visitor_leave_session") {
                assert.step(route);
            }
            if (route === "/im_livechat/feedback") {
                assert.step(route);
                assert.ok(args.reason.includes("Good job!"));
                assert.strictEqual(args.rate, RATING.GOOD);
            }
        },
    });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message-content", { text: "Hello World!" });
    await click("[title='Close Chat Window']");
    assert.verifySteps(["/im_livechat/visitor_leave_session"]);
    await click(`img[data-alt="${RATING.GOOD}"]`);
    await insertText("textarea[placeholder='Explain your note']", "Good job!");
    await click("button:enabled", { text: "Send" });
    await contains("p", { text: "Thank you for your feedback" });
    assert.verifySteps(["/im_livechat/feedback"]);
});

QUnit.test("Closing folded chat window should open it with feedback", async () => {
    await startServer();
    await loadDefaultConfig();
    await start();
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message-content", { text: "Hello World!" });
    await click("[title='Fold']");
    await contains(".o-mail-ChatWindow.o-folded");
    await click("[title='Close Chat Window']");
    await contains(".o-mail-ChatWindow.o-folded", { count: 0 });
    await contains(".o-mail-ChatWindow p", { text: "Did we correctly answer your question?" });
});
