/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { RATING, RATING_TO_EMOJI } from "@im_livechat/embed/core/livechat_service";
import { loadDefaultConfig, start } from "@im_livechat/../tests/embed/helper/test_utils";

import { afterNextRender, click, insertText } from "@mail/../tests/helpers/test_utils";

import { triggerHotkey } from "@web/../tests/helpers/utils";

QUnit.module("feedback panel");

QUnit.test("Do not ask feedback if empty", async (assert) => {
    await startServer();
    await loadDefaultConfig();
    await start();
    await click(".o-livechat-LivechatButton");
    assert.containsOnce($, ".o-mail-ChatWindow");
    await click("[title='Close Chat Window']");
    assert.containsNone($, ".o-livechat-LivechatButton");
});

QUnit.test("Close without feedback", async (assert) => {
    await startServer();
    await loadDefaultConfig();
    await start({
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
    assert.containsOnce($, ".o-mail-ChatWindow");
    await insertText(".o-mail-Composer-input", "Hello World!");
    await afterNextRender(() => triggerHotkey("Enter"));
    await click("[title='Close Chat Window']");
    await click("button:contains('Close')");
    assert.containsNone($, ".o-livechat-LivechatButton");
    assert.verifySteps(["/im_livechat/visitor_leave_session"]);
});

QUnit.test("Feedback with rating and comment", async (assert) => {
    await startServer();
    await loadDefaultConfig();
    let messageCount = 0;
    await start({
        mockRPC(route, args) {
            if (route === "/im_livechat/visitor_leave_session") {
                assert.step(route);
            }
            if (route === "/im_livechat/feedback") {
                assert.step(route);
            }
            if (route === "/im_livechat/chat_post") {
                if (messageCount === 1) {
                    assert.strictEqual(
                        args.message_content,
                        `Rating: ${RATING_TO_EMOJI[RATING.GOOD]}`
                    );
                } else if (messageCount === 2) {
                    assert.strictEqual(args.message_content, "Rating reason: Good job!");
                }
                messageCount++;
                assert.step(route);
            }
        },
    });
    await click(".o-livechat-LivechatButton");
    assert.containsOnce($, ".o-mail-ChatWindow");
    await insertText(".o-mail-Composer-input", "Hello World!");
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.verifySteps(["/im_livechat/chat_post"]);
    await click("[title='Close Chat Window']");
    assert.verifySteps(["/im_livechat/visitor_leave_session"]);
    await click(`img[data-alt="${RATING.GOOD}"]`);
    await insertText("textarea[placeholder='Explain your note']", "Good job!");
    await click("button:contains(Send)");
    assert.containsOnce($, "p:contains(Thank you for your feedback)");
    assert.verifySteps([
        "/im_livechat/feedback",
        "/im_livechat/chat_post",
        "/im_livechat/chat_post",
    ]);
});

QUnit.test("Closing folded chat window should open it with feedback", async (assert) => {
    await startServer();
    await loadDefaultConfig();
    await start();
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "Hello World!");
    await afterNextRender(() => triggerHotkey("Enter"));
    await click("[title='Fold']");
    assert.containsOnce($, ".o-mail-ChatWindow.o-folded");
    await click("[title='Close Chat Window']");
    assert.containsNone($, ".o-mail-ChatWindow.o-folded");
    assert.containsOnce($, ".o-mail-ChatWindow:contains(Did we correctly answer your question?)");
});
