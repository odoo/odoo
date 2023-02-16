/** @odoo-module **/

import { afterNextRender, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("mail", (hooks) => {
    QUnit.module("components", {}, function () {
        QUnit.module("thread_view_tests.js");

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
                const mailChannelId1 = pyEnv["mail.channel"].create({});
                const { click, insertText, openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                });
                await openDiscuss();
                await insertText(".o-mail-composer-textarea", "Dummy Message");
                await click(".o-mail-composer-send-button");
                assert.hasClass(
                    document.querySelector(".o_ComposerView"),
                    "o-focused",
                    "composer should be focused automatically after clicking on the send button"
                );
            }
        );
    });
});
