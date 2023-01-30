/** @odoo-module **/

import { afterNextRender, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("mail", (hooks) => {
    QUnit.module("components", {}, function () {
        QUnit.module("thread_view_tests.js");

        QUnit.skipRefactoring("basic rendering of canceled notification", async function (assert) {
            assert.expect(8);

            const pyEnv = await startServer();
            const mailChannelId1 = pyEnv["mail.channel"].create({});
            const resPartnerId1 = pyEnv["res.partner"].create({ name: "Someone" });
            const mailMessageId1 = pyEnv["mail.message"].create({
                body: "not empty",
                message_type: "email",
                model: "mail.channel",
                res_id: mailChannelId1,
            });
            pyEnv["mail.notification"].create({
                failure_type: "SMTP",
                mail_message_id: mailMessageId1,
                notification_status: "canceled",
                notification_type: "email",
                res_partner_id: resPartnerId1,
            });
            const { afterEvent, click, openDiscuss } = await start({
                discuss: {
                    context: { active_id: mailChannelId1 },
                },
            });
            await afterEvent({
                eventName: "o-thread-view-hint-processed",
                func: openDiscuss,
                message: "thread become loaded with messages",
                predicate: ({ hint, threadViewer }) => {
                    return (
                        hint.type === "messages-loaded" &&
                        threadViewer.thread.model === "mail.channel" &&
                        threadViewer.thread.id === mailChannelId1
                    );
                },
            });

            assert.containsOnce(
                document.body,
                ".o-mail-message-notification-icon-clickable",
                "should display the notification icon container on the message"
            );
            assert.containsOnce(
                document.body,
                ".o-mail-message-notification-icon",
                "should display the notification icon on the message"
            );
            assert.hasClass(
                document.querySelector(".o-mail-message-notification-icon"),
                "fa-envelope-o",
                "notification icon shown on the message should represent email"
            );

            await click(".o-mail-message-notification-icon-clickable");
            assert.containsOnce(
                document.body,
                ".o-mail-message-notification-popover",
                "notification popover should be opened after notification has been clicked"
            );
            assert.containsOnce(
                document.body,
                ".o-mail-message-notification-popover-icon",
                "an icon should be shown in notification popover"
            );
            assert.containsOnce(
                document.body,
                ".o-mail-message-notification-popover-icon.fa.fa-trash-o",
                "the icon shown in notification popover should be the canceled icon"
            );
            assert.containsOnce(
                document.body,
                ".o-mail-message-notification-popover-partner-name",
                "partner name should be shown in notification popover"
            );
            assert.strictEqual(
                document
                    .querySelector(".o-mail-message-notification-popover-partner-name")
                    .textContent.trim(),
                "Someone",
                "partner name shown in notification popover should be the one concerned by the notification"
            );
        });

        QUnit.skipRefactoring(
            "first unseen message should be directly preceded by the new message separator if there is a transient message just before it while composer is not focused [REQUIRE FOCUS]",
            async function (assert) {
                // The goal of removing the focus is to ensure the thread is not marked as seen automatically.
                // Indeed that would trigger set_last_seen_message no matter what, which is already covered by other tests.
                // The goal of this test is to cover the conditions specific to transient messages,
                // and the conditions from focus would otherwise shadow them.
                assert.expect(3);

                const pyEnv = await startServer();
                // Needed partner & user to allow simulation of message reception
                const resPartnerId1 = pyEnv["res.partner"].create({
                    name: "Foreigner partner",
                });
                const resUsersId1 = pyEnv["res.users"].create({
                    name: "Foreigner user",
                    partner_id: resPartnerId1,
                });
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    channel_type: "channel",
                    name: "General",
                    uuid: "channel20uuid",
                });
                const { click, insertText, messaging, openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                });
                await openDiscuss();
                // send a command that leads to receiving a transient message
                await insertText(".o-mail-composer-textarea", "/who");
                await click(".o-mail-composer-send-button");
                const transientMessage =
                    messaging.discuss.threadViewer.threadView.messageListView
                        .messageListViewItems[0].message;

                // composer is focused by default, we remove that focus
                document.querySelector(".o-mail-composer-textarea").blur();
                // simulate receiving a message
                await afterNextRender(() =>
                    messaging.rpc({
                        route: "/mail/chat_post",
                        params: {
                            context: {
                                mockedUserId: resUsersId1,
                            },
                            message_content: "test",
                            uuid: "channel20uuid",
                        },
                    })
                );
                assert.containsN(
                    document.body,
                    ".o-mail-message",
                    2,
                    "should display 2 messages (the transient & the received message), after posting a command"
                );
                assert.containsOnce(
                    document.body,
                    ".o_MessageListView_separatorNewMessages",
                    "separator should be shown as a message has been received"
                );
                assert.containsOnce(
                    document.body,
                    `.o-mail-message[data-message-id="${transientMessage.id}"] + .o_MessageListView_separatorNewMessages`,
                    "separator should be shown just after transient message"
                );
            }
        );

        QUnit.skipRefactoring(
            "failure on loading messages should display error",
            async function (assert) {
                assert.expect(1);

                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    channel_type: "channel",
                    name: "General",
                });
                const { openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                    async mockRPC(route, args) {
                        if (route === "/mail/channel/messages") {
                            return Promise.reject();
                        }
                    },
                });
                await openDiscuss(null, { waitUntilMessagesLoaded: false });

                assert.containsOnce(
                    document.body,
                    ".o_ThreadView_loadingFailed",
                    "should show loading error message"
                );
            }
        );

        QUnit.skipRefactoring(
            "failure on loading messages should prompt retry button",
            async function (assert) {
                assert.expect(1);

                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    channel_type: "channel",
                    name: "General",
                });
                const { openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                    async mockRPC(route, args) {
                        if (route === "/mail/channel/messages") {
                            return Promise.reject();
                        }
                    },
                });
                await openDiscuss(null, { waitUntilMessagesLoaded: false });

                assert.containsOnce(
                    document.body,
                    ".o_ThreadView_loadingFailedRetryButton",
                    "should show a button to allow user to retry loading"
                );
            }
        );

        QUnit.skipRefactoring(
            "failure on loading more messages should not alter message list display",
            async function (assert) {
                assert.expect(1);

                // first call needs to be successful as it is the initial loading of messages
                // second call comes from load more and needs to fail in order to show the error alert
                // any later call should work so that retry button and load more clicks would now work
                let messageFetchShouldFail = false;
                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    channel_type: "channel",
                    name: "General",
                });
                pyEnv["mail.message"].create(
                    [...Array(60).keys()].map(() => {
                        return {
                            body: "coucou",
                            model: "mail.channel",
                            res_id: mailChannelId1,
                        };
                    })
                );
                const { click, openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                    async mockRPC(route, args) {
                        if (route === "/mail/channel/messages") {
                            if (messageFetchShouldFail) {
                                throw new Error();
                            }
                        }
                    },
                });
                await openDiscuss();

                messageFetchShouldFail = true;
                await click(".o_MessageListView_loadMore");
                assert.containsN(
                    document.body,
                    ".o-mail-message",
                    30,
                    "should still show 30 messages as load more has failed"
                );
            }
        );

        QUnit.skipRefactoring(
            "failure on loading more messages should display error and prompt retry button",
            async function (assert) {
                assert.expect(3);

                // first call needs to be successful as it is the initial loading of messages
                // second call comes from load more and needs to fail in order to show the error alert
                // any later call should work so that retry button and load more clicks would now work
                let messageFetchShouldFail = false;
                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    channel_type: "channel",
                    name: "General",
                });
                pyEnv["mail.message"].create(
                    [...Array(60).keys()].map(() => {
                        return {
                            body: "coucou",
                            model: "mail.channel",
                            res_id: mailChannelId1,
                        };
                    })
                );
                const { click, openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                    async mockRPC(route, args) {
                        if (route === "/mail/channel/messages") {
                            if (messageFetchShouldFail) {
                                throw new Error();
                            }
                        }
                    },
                });
                await openDiscuss();

                messageFetchShouldFail = true;
                await click(".o_MessageListView_loadMore");
                assert.containsOnce(
                    document.body,
                    ".o_MessageListView_alertLoadingFailed",
                    "should show loading error message"
                );
                assert.containsOnce(
                    document.body,
                    ".o_MessageListView_alertLoadingFailedRetryButton",
                    "should show loading error message button"
                );
                assert.containsNone(
                    document.body,
                    ".o_MessageListView_loadMore",
                    "should not show load more buttton"
                );
            }
        );

        QUnit.skipRefactoring(
            "Retry loading more messages on failed load more messages should load more messages",
            async function (assert) {
                assert.expect(0);

                // first call needs to be successful as it is the initial loading of messages
                // second call comes from load more and needs to fail in order to show the error alert
                // any later call should work so that retry button and load more clicks would now work
                let messageFetchShouldFail = false;
                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    channel_type: "channel",
                    name: "General",
                });
                pyEnv["mail.message"].create(
                    [...Array(90).keys()].map(() => {
                        return {
                            body: "coucou",
                            model: "mail.channel",
                            res_id: mailChannelId1,
                        };
                    })
                );
                const { afterEvent, click, openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                    async mockRPC(route, args) {
                        if (route === "/mail/channel/messages") {
                            if (messageFetchShouldFail) {
                                return Promise.reject();
                            }
                        }
                    },
                });
                await openDiscuss();
                messageFetchShouldFail = true;
                await click(".o_MessageListView_loadMore");

                messageFetchShouldFail = false;
                await afterEvent({
                    eventName: "o-thread-view-hint-processed",
                    func: () =>
                        document
                            .querySelector(".o_MessageListView_alertLoadingFailedRetryButton")
                            .click(),
                    message:
                        "should wait until channel loaded more messages after clicked on load more",
                    predicate: ({ hint, threadViewer }) => {
                        return (
                            hint.type === "more-messages-loaded" &&
                            threadViewer.thread.model === "mail.channel" &&
                            threadViewer.thread.id === mailChannelId1
                        );
                    },
                });
            }
        );
    });
});
