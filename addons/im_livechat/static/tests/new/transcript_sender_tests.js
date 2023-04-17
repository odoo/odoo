/** @odoo-module **/

import {
    click,
    insertText,
    start,
    triggerHotkey,
} from "@im_livechat/../tests/helpers/new/test_utils";
import { afterNextRender } from "@mail/../tests/helpers/test_utils";

QUnit.module("transcript sender");

QUnit.test("send", async (assert) => {
    const { root } = await start({
        mockRPC(route, args) {
            if (route === "/im_livechat/email_livechat_transcript") {
                assert.step(`send_transcript - ${args.email}`);
            }
        },
    });
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "Hello World!");
    await afterNextRender(() => triggerHotkey("Enter"));
    await click(".o-mail-ChatWindow-command[title*='Close']");
    assert.containsOnce(root, ".form-text:contains(Receive a copy of this conversation)");
    assert.containsOnce(root, "button[data-action='sendTranscript']:disabled");
    await insertText("input[placeholder='mail@example.com']", "odoobot@odoo.com");
    await click("button[data-action='sendTranscript']");
    assert.verifySteps(["send_transcript - odoobot@odoo.com"]);
    assert.containsOnce(root, ".form-text:contains(The conversation was sent)");
});

QUnit.test("send failed", async (assert) => {
    const { root } = await start({
        mockRPC(route) {
            if (route === "/im_livechat/email_livechat_transcript") {
                throw new Error();
            }
        },
    });
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "Hello World!");
    await afterNextRender(() => triggerHotkey("Enter"));
    await click(".o-mail-ChatWindow-command[title*='Close']");
    await insertText("input[placeholder='mail@example.com']", "odoobot@odoo.com");
    await click("button[data-action='sendTranscript']");
    assert.containsOnce(root, ".form-text:contains(An error occurred. Please try again.)");
});
