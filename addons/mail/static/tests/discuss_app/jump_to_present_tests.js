/** @odoo-module */

import {
    afterNextRender,
    click,
    nextAnimationFrame,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";
import { PRESENT_THRESHOLD } from "@mail/core_ui/thread";
import { nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("jump to present");

QUnit.test("Basic jump to present when scrolling to outdated messages", async (assert) => {
    // make scroll behavior instantaneous.
    patchWithCleanup(Element.prototype, {
        scrollIntoView() {
            return this._super(true);
        },
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
    });
    for (let i = 0; i < 20; i++) {
        pyEnv["mail.message"].create({
            body: "Non Empty Body ".repeat(100),
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.ok(
        $(".o-mail-Thread")[0].scrollHeight > PRESENT_THRESHOLD,
        "should have enough scroll height to trigger jump to present"
    );
    await afterNextRender(() => $(".o-mail-Thread").scrollTop(0));
    assert.containsOnce($, ".o-mail-Thread:contains(You're viewing older messagesJump to Present)");
    await click(".o-mail-Thread-jumpPresent");
    await nextTick();
    assert.containsNone($, ".o-mail-Thread:contains(You're viewing older messagesJump to Present)");
    assert.ok(
        $(".o-mail-Thread")[0].scrollHeight - $(".o-mail-Thread")[0].scrollTop <=
            $(".o-mail-Thread")[0].clientHeight
    );
});

QUnit.test("Jump to old reply should prompt jump to presence", async (assert) => {
    // make scroll behavior instantaneous.
    patchWithCleanup(Element.prototype, {
        scrollIntoView() {
            return this._super(true);
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
    await openDiscuss(channelId);
    await click(".o-mail-MessageInReply .cursor-pointer");
    assert.isVisible($(".o-mail-Message:contains(Hello world!):eq(0)")[0]);
    assert.strictEqual(
        $(".o-mail-Message-body:contains(Hello world!):eq(0)").text(),
        "Hello world!",
        "should correctly execute HTML tags in parent message when using 'load around' feature"
    );
    assert.containsOnce($, ".o-mail-Thread:contains(You're viewing older messagesJump to Present)");
    await click(".o-mail-Thread-jumpPresent");
    await nextAnimationFrame();
    assert.containsNone($, ".o-mail-Thread:contains(You're viewing older messagesJump to Present)");
    assert.ok(
        $(".o-mail-Thread")[0].scrollHeight - $(".o-mail-Thread")[0].scrollTop <=
            $(".o-mail-Thread")[0].clientHeight
    );
});
