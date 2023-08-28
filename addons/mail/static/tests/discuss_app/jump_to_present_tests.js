/* @odoo-module */

import { PRESENT_THRESHOLD } from "@mail/core/common/thread";
import { click, contains, scroll, start, startServer } from "@mail/../tests/helpers/test_utils";

import { patchWithCleanup } from "@web/../tests/helpers/utils";

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
    await contains(".o-mail-Message", 20);
    assert.ok(
        (await contains(".o-mail-Thread"))[0].scrollHeight > PRESENT_THRESHOLD,
        "should have enough scroll height to trigger jump to present"
    );
    await contains(".o-mail-Thread", 1, { scroll: "bottom" });
    await scroll(".o-mail-Thread", 0);
    await contains(".o-mail-Thread:contains(You're viewing older messagesJump to Present)");
    await click(".o-mail-Thread-jumpPresent");
    await contains(".o-mail-Thread:contains(You're viewing older messagesJump to Present)", 0);
    await contains(".o-mail-Thread", 1, { scroll: "bottom" });
});

QUnit.test("Jump to old reply should prompt jump to presence", async (assert) => {
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
    await contains(".o-mail-Message", 30);
    await click(".o-mail-MessageInReply .cursor-pointer");
    await contains(".o-mail-Message", 46);
    assert.isVisible((await contains(".o-mail-Message:contains(Hello world!):eq(0)"))[0]);
    assert.strictEqual(
        $(".o-mail-Message-body:contains(Hello world!):eq(0)").text(),
        "Hello world!",
        "should correctly execute HTML tags in parent message when using 'load around' feature"
    );
    await contains(".o-mail-Thread:contains(You're viewing older messagesJump to Present)");
    await click(".o-mail-Thread-jumpPresent");
    await contains(".o-mail-Thread:contains(You're viewing older messagesJump to Present)", 0);
    await contains(".o-mail-Message", 30);
    await contains(".o-mail-Thread", 1, { scroll: "bottom" });
});
