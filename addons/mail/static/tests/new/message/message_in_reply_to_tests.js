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
    const mailChannelId1 = pyEnv["mail.channel"].create({ name: "general" });
    const mailMessageId1 = pyEnv["mail.message"].create({
        body: "Hey lol",
        message_type: "comment",
        model: "mail.channel",
        res_id: mailChannelId1,
    });
    const mailMessageId2 = pyEnv["mail.message"].create({
        body: "Response to Hey lol",
        message_type: "comment",
        model: "mail.channel",
        parent_id: mailMessageId1,
        res_id: mailChannelId1,
    });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId1);
    await click(
        `.o-mail-message[data-message-id="${mailMessageId2}"] .o-mail-message-in-reply-body`
    );
    assert.containsOnce(target, `.o-mail-message-highlighted[data-message-id="${mailMessageId1}"]`);
});

QUnit.test("click on message in reply to scroll to the parent message", async function (assert) {
    // make scroll behavior instantaneous.
    patchWithCleanup(Element.prototype, {
        scrollIntoView() {
            return this._super(true);
        },
    });

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv["mail.channel"].create({ name: "general" });
    const [oldestMessageId] = pyEnv["mail.message"].create(
        Array(20)
            .fill(0)
            .map(() => ({
                body: "Non Empty Body ".repeat(25),
                message_type: "comment",
                model: "mail.channel",
                res_id: mailChannelId1,
            }))
    );
    const latestMessageId = pyEnv["mail.message"].create({
        body: "Response to first message",
        message_type: "comment",
        model: "mail.channel",
        parent_id: oldestMessageId,
        res_id: mailChannelId1,
    });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId1);
    await click(
        `.o-mail-message[data-message-id="${latestMessageId}"] .o-mail-message-in-reply-body`
    );
    await nextTick();

    const mailThreadEl = document.querySelector(".o-mail-thread");
    const oldestMessageEl = document.querySelector(
        `.o-mail-message[data-message-id='${oldestMessageId}']`
    );
    const oldestMessageTop = oldestMessageEl.offsetTop;
    const oldestMessageBottom = oldestMessageTop + oldestMessageEl.offsetHeight;
    const mailThreadTop = mailThreadEl.offsetTop;
    const mailThreadBottom = mailThreadTop + mailThreadEl.offsetHeight;
    assert.ok(
        oldestMessageBottom <= mailThreadBottom && oldestMessageTop >= mailThreadTop,
        "Should have scrolled into oldest message"
    );
});
