/** @odoo-module **/

import { afterNextRender, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("mail", {}, function () {
    QUnit.module("components", {}, function () {
        QUnit.module("thread_needaction_preview_tests.js");

        QUnit.skipRefactoring(
            "[technical] opening a non-channel chat window should not call channel_fold",
            async function (assert) {
                // channel_fold should not be called when opening non-channels in chat
                // window, because there is no server sync of fold state for them.
                assert.expect(3);

                const pyEnv = await startServer();
                const resPartnerId1 = pyEnv["res.partner"].create({});
                const mailMessageId1 = pyEnv["mail.message"].create({
                    model: "res.partner",
                    needaction: true,
                    needaction_partner_ids: [pyEnv.currentPartnerId],
                    res_id: resPartnerId1,
                });
                pyEnv["mail.notification"].create({
                    mail_message_id: mailMessageId1,
                    notification_status: "sent",
                    notification_type: "inbox",
                    res_partner_id: pyEnv.currentPartnerId,
                });
                const { afterEvent, click, messaging } = await start({
                    async mockRPC(route, args) {
                        if (route.includes("channel_fold")) {
                            const message =
                                "should not call channel_fold when opening a non-channel chat window";
                            assert.step(message);
                            console.error(message);
                            throw Error(message);
                        }
                    },
                });
                await afterNextRender(() =>
                    afterEvent({
                        eventName: "o-thread-cache-loaded-messages",
                        func: () =>
                            document
                                .querySelector(
                                    ".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])"
                                )
                                .click(),
                        message: "should wait until inbox loaded initial needaction messages",
                        predicate: ({ threadCache }) => {
                            return threadCache.thread === messaging.inbox.thread;
                        },
                    })
                );
                assert.containsOnce(
                    document.body,
                    ".o_ThreadNeedactionPreviewView",
                    "should have a preview initially"
                );
                assert.containsNone(
                    document.body,
                    ".o-mail-chat-window",
                    "should have no chat window initially"
                );

                await click(".o_ThreadNeedactionPreviewView");
                assert.containsOnce(
                    document.body,
                    ".o-mail-chat-window",
                    "should have opened the chat window on clicking on the preview"
                );
            }
        );

        QUnit.skipRefactoring(
            "chat window header should not have unread counter for non-channel thread",
            async function (assert) {
                assert.expect(2);

                const pyEnv = await startServer();
                const resPartnerId1 = pyEnv["res.partner"].create({});
                const mailMessageId1 = pyEnv["mail.message"].create({
                    author_id: resPartnerId1,
                    body: "not empty",
                    model: "res.partner",
                    needaction: true,
                    needaction_partner_ids: [pyEnv.currentPartnerId],
                    res_id: resPartnerId1,
                });
                pyEnv["mail.notification"].create({
                    mail_message_id: mailMessageId1,
                    notification_status: "sent",
                    notification_type: "inbox",
                    res_partner_id: pyEnv.currentPartnerId,
                });
                const { afterEvent, click, messaging } = await start();
                await afterNextRender(() =>
                    afterEvent({
                        eventName: "o-thread-cache-loaded-messages",
                        func: () =>
                            document
                                .querySelector(
                                    ".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])"
                                )
                                .click(),
                        message: "should wait until inbox loaded initial needaction messages",
                        predicate: ({ threadCache }) => {
                            return threadCache.thread === messaging.inbox.thread;
                        },
                    })
                );
                await click(".o_ThreadNeedactionPreviewView");
                assert.containsOnce(
                    document.body,
                    ".o-mail-chat-window",
                    "should have opened the chat window on clicking on the preview"
                );
                assert.containsNone(
                    document.body,
                    ".o_ChatWindowHeaderView_counter",
                    "chat window header should not have unread counter for non-channel thread"
                );
            }
        );
    });
});
