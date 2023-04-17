/** @odoo-module **/

import {
    click,
    insertText,
    start,
    triggerHotkey,
} from "@im_livechat/../tests/helpers/new/test_utils";
import { afterNextRender } from "@mail/../tests/helpers/test_utils";
import { RATING } from "@im_livechat/new/feedback_panel/feedback_panel";
import { RATING_TO_EMOJI } from "@im_livechat/new/core/livechat_service";

QUnit.module("feedback panel");

QUnit.test("Do not ask feedback if empty", async (assert) => {
    const { root } = await start();
    await click(".o-livechat-LivechatButton");
    assert.containsOnce(root, ".o-mail-ChatWindow");
    await click(".o-mail-ChatWindow-command[title*='Close']");
    assert.containsOnce(root, ".o-livechat-LivechatButton");
});

QUnit.test("Close without feedback", async (assert) => {
    const { root } = await start({
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
    assert.containsOnce(root, ".o-mail-ChatWindow");
    await insertText(".o-mail-Composer-input", "Hello World!");
    await afterNextRender(() => triggerHotkey("Enter"));
    await click(".o-mail-ChatWindow-command[title*='Close']");
    await click("button:contains('Close')");
    assert.containsNone(root, ".o-livechat-LivechatButton");
    assert.verifySteps(["/im_livechat/visitor_leave_session"]);
});

QUnit.test("Feedback with rating and comment", async (assert) => {
    let messageCount = 0;
    const { root } = await start({
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
    assert.containsOnce(root, ".o-mail-ChatWindow");
    await insertText(".o-mail-Composer-input", "Hello World!");
    await afterNextRender(() => triggerHotkey("Enter"));
    await click(".o-mail-ChatWindow-command[title*='Close']");
    await click(`img[data-alt="${RATING.GOOD}"]`);
    await insertText("textarea[placeholder='Explain your note']", "Good job!");
    await click("button:contains(Send)");
    assert.containsOnce(root, "p:contains(Thank you for your feedback)");
    assert.verifySteps([
        "/im_livechat/chat_post",
        "/im_livechat/visitor_leave_session",
        "/im_livechat/feedback",
        "/im_livechat/chat_post",
        "/im_livechat/chat_post",
    ]);
});
