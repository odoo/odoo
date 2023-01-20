/** @odoo-module **/

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";

import { getFixture, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";

let target;
QUnit.module("message reply", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("click on message in reply to highlight the parent message", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "general" });
    const messageId_1 = pyEnv["mail.message"].create({
        body: "Hey lol",
        message_type: "comment",
        model: "mail.channel",
        res_id: channelId,
    });
    const messageId_2 = pyEnv["mail.message"].create({
        body: "Response to Hey lol",
        message_type: "comment",
        model: "mail.channel",
        parent_id: messageId_1,
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(`.o-mail-message[data-message-id="${messageId_2}"] .o-mail-message-in-reply-body`);
    assert.containsOnce(target, `.o-mail-message.o-highlighted[data-message-id="${messageId_1}"]`);
});

QUnit.test("click on message in reply to scroll to the parent message", async function (assert) {
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
    const latestMessageId = pyEnv["mail.message"].create({
        body: "Response to first message",
        message_type: "comment",
        model: "mail.channel",
        parent_id: oldestMessageId,
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(
        `.o-mail-message[data-message-id="${latestMessageId}"] .o-mail-message-in-reply-body`
    );
    await nextTick();

    const thread = document.querySelector(".o-mail-thread");
    const oldestMessage = document.querySelector(
        `.o-mail-message[data-message-id='${oldestMessageId}']`
    );
    const oldestMsgTop = oldestMessage.offsetTop;
    const oldestMsgBottom = oldestMsgTop + oldestMessage.offsetHeight;
    const threadTop = thread.offsetTop;
    const threadBottom = threadTop + thread.offsetHeight;
    assert.ok(
        oldestMsgBottom <= threadBottom && oldestMsgTop >= threadTop,
        "Should have scrolled into oldest message"
    );
});
