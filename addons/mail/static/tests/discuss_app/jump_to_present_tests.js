/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { PRESENT_THRESHOLD } from "@mail/core/common/thread";
import { start } from "@mail/../tests/helpers/test_utils";

import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains, scroll } from "@web/../tests/utils";

QUnit.module("jump to present");

QUnit.test("Basic jump to present when scrolling to outdated messages", async (assert) => {
    // make scroll behavior instantaneous.
    patchWithCleanup(Element.prototype, {
        scrollIntoView() {
            return super.scrollIntoView(true);
        },
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    for (let i = 0; i < 20; i++) {
        pyEnv["mail.message"].create({
            body: "Non Empty Body ".repeat(100),
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 20 });
    await contains(".o-mail-Thread");
    assert.ok(
        document.querySelector(".o-mail-Thread").scrollHeight > PRESENT_THRESHOLD,
        "should have enough scroll height to trigger jump to present"
    );
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await scroll(".o-mail-Thread", 0);
    await contains(".o-mail-Thread", { text: "You're viewing older messagesJump to Present" });
    await click(".o-mail-Thread-jumpPresent");
    await contains(".o-mail-Thread", {
        count: 0,
        text: "You're viewing older messagesJump to Present",
    });
    await contains(".o-mail-Thread", { scroll: "bottom" });
});

QUnit.test("Jump to old reply should prompt jump to presence", async () => {
    // make scroll behavior instantaneous.
    patchWithCleanup(Element.prototype, {
        scrollIntoView() {
            return super.scrollIntoView(true);
        },
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const oldestMessageId = pyEnv["mail.message"].create({
        body: "<p>Hello world!</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    for (let i = 0; i < 100; i++) {
        pyEnv["mail.message"].create({
            body: "<p>Non Empty Body</p>".repeat(100),
            message_type: "comment",
            model: "discuss.channel",
            /**
             * The first message following the oldest message should have it as its parent message
             * so that the oldest message is inserted through the parent field during "load around"
             * to have the coverage of this part of the code (in particular having parent message
             * body being inserted with markup).
             */
            parent_id: i === 0 ? oldestMessageId : undefined,
            res_id: channelId,
        });
    }
    pyEnv["mail.message"].create({
        body: "Most Recent!",
        model: "discuss.channel",
        res_id: channelId,
        parent_id: oldestMessageId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 30 });
    await click(".o-mail-MessageInReply .cursor-pointer");
    await contains(".o-mail-Message", { count: 46 });
    await contains(":nth-child(1 of .o-mail-Message)", { text: "Hello world!" });
    await contains(".o-mail-Thread", { text: "You're viewing older messagesJump to Present" });
    await click(".o-mail-Thread-jumpPresent");
    await contains(".o-mail-Thread-jumpPresent", { count: 0 });
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
});
