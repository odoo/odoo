/** @odoo-module **/

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";

import { nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("message reply");

QUnit.test("click on message in reply to highlight the parent message", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "general" });
    const messageId = pyEnv["mail.message"].create({
        body: "Hey lol",
        message_type: "comment",
        model: "mail.channel",
        res_id: channelId,
    });
    pyEnv["mail.message"].create({
        body: "Reply to Hey",
        message_type: "comment",
        model: "mail.channel",
        parent_id: messageId,
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message:contains(Reply to Hey) .o-mail-MessageInReply-message");
    assert.containsOnce($, ".o-mail-Message:contains(Hey lol).o-highlighted");
});

QUnit.test("click on message in reply to scroll to the parent message", async (assert) => {
    // make scroll behavior instantaneous.
    patchWithCleanup(Element.prototype, {
        scrollIntoView() {
            return this._super(true);
        },
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "general" });
    const [oldestMessageId] = pyEnv["mail.message"].create(
        Array(20)
            .fill(0)
            .map(() => ({
                body: "Non Empty Body ".repeat(25),
                message_type: "comment",
                model: "mail.channel",
                res_id: channelId,
            }))
    );
    pyEnv["mail.message"].create({
        body: "Response to first message",
        message_type: "comment",
        model: "mail.channel",
        parent_id: oldestMessageId,
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(
        ".o-mail-Message:contains(Response to first message) .o-mail-MessageInReply-message"
    );
    await nextTick();
    const thread = $(".o-mail-Thread")[0];
    const oldestMsg = $(".o-mail-Message:eq(0)")[0];
    const oldestMsgTop = oldestMsg.offsetTop;
    const oldestMsgBottom = oldestMsgTop + oldestMsg.offsetHeight;
    const threadTop = thread.offsetTop;
    const threadBottom = threadTop + thread.offsetHeight;
    assert.ok(
        oldestMsgBottom <= threadBottom && oldestMsgTop >= threadTop,
        "Should have scrolled to oldest message"
    );
});
