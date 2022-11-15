/** @odoo-module **/

import { start, startServer } from "@mail/../tests/helpers/test_utils";

import { nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("mail", {}, function () {
    QUnit.module("components", {}, function () {
        QUnit.module("message_in_reply_to_tests");

        QUnit.test(
            "click on message in reply to highlight the parent message",
            async function (assert) {
                assert.expect(1);

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
                const { click, openDiscuss } = await start({
                    discuss: {
                        params: {
                            default_active_id: `mail.channel_${mailChannelId1}`,
                        },
                    },
                });
                await openDiscuss();
                await click(
                    `.o-mail-message[data-message-id="${mailMessageId2}"] .o-mail-message-in-reply-body`
                );
                assert.containsOnce(
                    document.body,
                    `.o-highlighted[data-message-id="${mailMessageId1}"]`,
                    "click on message in reply to should highlight the parent message"
                );
            }
        );

        QUnit.test(
            "click on message in reply to scroll to the parent message",
            async function (assert) {
                assert.expect(1);

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
                const { click, openDiscuss } = await start({
                    discuss: {
                        params: {
                            default_active_id: `mail.channel_${mailChannelId1}`,
                        },
                    },
                });
                await openDiscuss();
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
            }
        );
    });
});
