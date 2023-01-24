/** @odoo-module **/

import { patchUiSize } from "@mail/../tests/helpers/patch_ui_size";
import {
    afterNextRender,
    isScrolledToBottom,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";

import { file } from "web.test_utils";
const { createFile, inputFiles } = file;

QUnit.module("mail", {}, function () {
    QUnit.module("components", {}, function () {
        QUnit.module("chat_window_manager_tests.js");

        QUnit.skipRefactoring(
            "chat window: composer state conservation on toggle discuss",
            async function (assert) {
                assert.expect(6);

                const pyEnv = await startServer();
                const mailChannelId = pyEnv["mail.channel"].create({});
                const { click, insertText, messaging, openDiscuss, openView } = await start();
                await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
                await click(`.o_MessagingMenu_dropdownMenu .o_NotificationListView_preview`);
                // Set content of the composer of the chat window
                await insertText(".o-mail-composer-textarea", "XDU for the win !");
                assert.containsNone(
                    document.body,
                    ".o_ComposerView .o_AttachmentCard",
                    "composer should have no attachment initially"
                );
                // Set attachments of the composer
                const files = [
                    await createFile({
                        name: "text state conservation on toggle home menu.txt",
                        content: "hello, world",
                        contentType: "text/plain",
                    }),
                    await createFile({
                        name: "text2 state conservation on toggle home menu.txt",
                        content: "hello, xdu is da best man",
                        contentType: "text/plain",
                    }),
                ];
                await afterNextRender(() =>
                    inputFiles(
                        messaging.chatWindowManager.chatWindows[0].threadView.composerView
                            .fileUploader.fileInput,
                        files
                    )
                );
                assert.strictEqual(
                    document.querySelector(`.o-mail-composer-textarea`).value,
                    "XDU for the win !",
                    "chat window composer initial text input should contain 'XDU for the win !'"
                );
                assert.containsN(
                    document.body,
                    ".o_ComposerView .o_AttachmentCard",
                    2,
                    "composer should have 2 total attachments after adding 2 attachments"
                );

                await openDiscuss(null, { waitUntilMessagesLoaded: false });
                assert.containsNone(
                    document.body,
                    ".o-mail-chat-window",
                    "should not have any chat window after opening discuss"
                );

                await openView({
                    res_id: mailChannelId,
                    res_model: "mail.channel",
                    views: [[false, "form"]],
                });
                assert.strictEqual(
                    document.querySelector(`.o-mail-composer-textarea`).value,
                    "XDU for the win !",
                    "chat window composer should still have the same input after closing discuss"
                );
                assert.containsN(
                    document.body,
                    ".o_ComposerView .o_AttachmentCard",
                    2,
                    "Chat window composer should have 2 attachments after closing discuss"
                );
            }
        );

        QUnit.skipRefactoring(
            "chat window: scroll conservation on toggle discuss",
            async function (assert) {
                assert.expect(2);

                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({});
                for (let i = 0; i < 100; i++) {
                    pyEnv["mail.message"].create({
                        body: "not empty",
                        model: "mail.channel",
                        res_id: mailChannelId1,
                    });
                }
                const { afterEvent, click, openDiscuss, openView } = await start();
                await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
                await afterEvent({
                    eventName: "o-component-message-list-scrolled",
                    func: () => document.querySelector(".o_NotificationListView_preview").click(),
                    message:
                        "should wait until channel scrolled to its last message after opening it from the messaging menu",
                    predicate: ({ scrollTop, thread }) => {
                        const messageList = document.querySelector(".o-mail-thread");
                        return (
                            thread &&
                            thread.model === "mail.channel" &&
                            thread.id === mailChannelId1 &&
                            isScrolledToBottom(messageList)
                        );
                    },
                });
                // Set a scroll position to chat window
                await afterEvent({
                    eventName: "o-component-message-list-scrolled",
                    func: () => {
                        document.querySelector(`.o-mail-thread`).scrollTop = 142;
                    },
                    message:
                        "should wait until channel scrolled to 142 after setting this value manually",
                    predicate: ({ scrollTop, thread }) => {
                        return (
                            thread &&
                            thread.model === "mail.channel" &&
                            thread.id === mailChannelId1 &&
                            scrollTop === 142
                        );
                    },
                });

                await openDiscuss(null, { waitUntilMessagesLoaded: false });
                assert.containsNone(
                    document.body,
                    ".o-mail-chat-window",
                    "should not have any chat window after opening discuss"
                );

                await afterEvent({
                    eventName: "o-component-message-list-scrolled",
                    func: () =>
                        openView({
                            res_id: mailChannelId1,
                            res_model: "mail.channel",
                            views: [[false, "list"]],
                        }),
                    message:
                        "should wait until channel restored its scroll to 142 after closing discuss",
                    predicate: ({ scrollTop, thread }) => {
                        return (
                            thread &&
                            thread.model === "mail.channel" &&
                            thread.id === mailChannelId1 &&
                            scrollTop === 142
                        );
                    },
                });
                assert.strictEqual(
                    document.querySelector(`.o-mail-thread`).scrollTop,
                    142,
                    "chat window scrollTop should still be the same after closing discuss"
                );
            }
        );

        QUnit.skipRefactoring(
            "chat window with a thread: keep scroll position in message list on folded",
            async function (assert) {
                assert.expect(3);

                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({});
                for (let i = 0; i < 100; i++) {
                    pyEnv["mail.message"].create({
                        body: "not empty",
                        model: "mail.channel",
                        res_id: mailChannelId1,
                    });
                }
                const { afterEvent, click } = await start();
                await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
                await afterEvent({
                    eventName: "o-component-message-list-scrolled",
                    func: () => document.querySelector(".o_NotificationListView_preview").click(),
                    message:
                        "should wait until channel scrolled to its last message after opening it from the messaging menu",
                    predicate: ({ scrollTop, thread }) => {
                        const messageList = document.querySelector(".o-mail-thread");
                        return (
                            thread &&
                            thread.model === "mail.channel" &&
                            thread.id === mailChannelId1 &&
                            isScrolledToBottom(messageList)
                        );
                    },
                });
                // Set a scroll position to chat window
                await afterEvent({
                    eventName: "o-component-message-list-scrolled",
                    func: () => {
                        document.querySelector(`.o-mail-thread`).scrollTop = 142;
                    },
                    message:
                        "should wait until channel scrolled to 142 after setting this value manually",
                    predicate: ({ scrollTop, thread }) => {
                        return (
                            thread &&
                            thread.model === "mail.channel" &&
                            thread.id === mailChannelId1 &&
                            scrollTop === 142
                        );
                    },
                });
                assert.strictEqual(
                    document.querySelector(`.o-mail-thread`).scrollTop,
                    142,
                    "verify chat window initial scrollTop"
                );

                // fold chat window
                await click(".o_ChatWindow_header");
                assert.containsNone(
                    document.body,
                    ".o_ThreadView",
                    "chat window should be folded so no ThreadView should be present"
                );

                // unfold chat window
                await afterNextRender(() =>
                    afterEvent({
                        eventName: "o-component-message-list-scrolled",
                        func: () => document.querySelector(".o_ChatWindow_header").click(),
                        message: "should wait until channel restored its scroll position to 142",
                        predicate: ({ scrollTop, thread }) => {
                            return (
                                thread &&
                                thread.model === "mail.channel" &&
                                thread.id === mailChannelId1 &&
                                scrollTop === 142
                            );
                        },
                    })
                );
                assert.strictEqual(
                    document.querySelector(`.o-mail-thread`).scrollTop,
                    142,
                    "chat window scrollTop should still be the same when chat window is unfolded"
                );
            }
        );

        QUnit.skipRefactoring(
            "chat window with a thread: keep scroll position in message list on toggle discuss when folded",
            async function (assert) {
                assert.expect(2);

                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({});
                for (let i = 0; i < 100; i++) {
                    pyEnv["mail.message"].create({
                        body: "not empty",
                        model: "mail.channel",
                        res_id: mailChannelId1,
                    });
                }
                const { afterEvent, click, openDiscuss, openView } = await start();
                await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
                await afterEvent({
                    eventName: "o-component-message-list-scrolled",
                    func: () => document.querySelector(".o_NotificationListView_preview").click(),
                    message:
                        "should wait until channel scrolled to its last message after opening it from the messaging menu",
                    predicate: ({ scrollTop, thread }) => {
                        const messageList = document.querySelector(".o-mail-thread");
                        return (
                            thread &&
                            thread.model === "mail.channel" &&
                            thread.id === mailChannelId1 &&
                            isScrolledToBottom(messageList)
                        );
                    },
                });
                // Set a scroll position to chat window
                await afterEvent({
                    eventName: "o-component-message-list-scrolled",
                    func: () => (document.querySelector(`.o-mail-thread`).scrollTop = 142),
                    message:
                        "should wait until channel scrolled to 142 after setting this value manually",
                    predicate: ({ scrollTop, thread }) => {
                        return (
                            thread &&
                            thread.model === "mail.channel" &&
                            thread.id === mailChannelId1 &&
                            scrollTop === 142
                        );
                    },
                });
                // fold chat window
                await click(".o_ChatWindow_header");
                await openDiscuss(null, { waitUntilMessagesLoaded: false });
                assert.containsNone(
                    document.body,
                    ".o-mail-chat-window",
                    "should not have any chat window after opening discuss"
                );

                await openView({
                    res_id: mailChannelId1,
                    res_model: "mail.channel",
                    views: [[false, "list"]],
                });
                // unfold chat window
                await afterEvent({
                    eventName: "o-component-message-list-scrolled",
                    func: () => document.querySelector(".o_ChatWindow_header").click(),
                    message:
                        "should wait until channel restored its scroll position to the last saved value (142)",
                    predicate: ({ scrollTop, thread }) => {
                        return (
                            thread &&
                            thread.model === "mail.channel" &&
                            thread.id === mailChannelId1 &&
                            scrollTop === 142
                        );
                    },
                });
                assert.strictEqual(
                    document.querySelector(`.o-mail-thread`).scrollTop,
                    142,
                    "chat window scrollTop should still be the same after closing discuss"
                );
            }
        );

        QUnit.skipRefactoring(
            "chat window does not fetch messages if hidden",
            async function (assert) {
                /**
                 * computation uses following info:
                 * ([mocked] global window width: 900px)
                 * (others: @see `mail/static/src/models/chat_window_manager.js:visual`)
                 *
                 * - chat window width: 340px
                 * - start/end/between gap width: 10px/10px/5px
                 * - hidden menu width: 170px
                 * - global width: 1080px
                 *
                 * Enough space for 2 visible chat windows, and one hidden chat window:
                 * 3 visible chat windows:
                 *  10 + 340 + 5 + 340 + 5 + 340 + 10 = 1050 > 900
                 * 2 visible chat windows + hidden menu:
                 *  10 + 340 + 5 + 340 + 10 + 170 + 5 = 880 < 900
                 */
                assert.expect(11);

                const pyEnv = await startServer();
                const [mailChannelId1, mailChannelId2, mailChannelId3] = pyEnv[
                    "mail.channel"
                ].create([
                    {
                        channel_member_ids: [
                            [
                                0,
                                0,
                                {
                                    fold_state: "open",
                                    is_minimized: true,
                                    partner_id: pyEnv.currentPartnerId,
                                },
                            ],
                        ],
                        name: "Channel #10",
                    },
                    {
                        channel_member_ids: [
                            [
                                0,
                                0,
                                {
                                    fold_state: "open",
                                    is_minimized: true,
                                    partner_id: pyEnv.currentPartnerId,
                                },
                            ],
                        ],
                        name: "Channel #11",
                    },
                    {
                        channel_member_ids: [
                            [
                                0,
                                0,
                                {
                                    fold_state: "open",
                                    is_minimized: true,
                                    partner_id: pyEnv.currentPartnerId,
                                },
                            ],
                        ],
                        name: "Channel #12",
                    },
                ]);
                patchUiSize({ width: 900 });
                const { click } = await start({
                    mockRPC(route, args) {
                        if (route === "/mail/channel/messages") {
                            const { channel_id } = args;
                            assert.step(`rpc:/mail/channel/messages:${channel_id}`);
                        }
                    },
                });

                assert.containsN(
                    document.body,
                    ".o-mail-chat-window",
                    2,
                    "2 chat windows should be visible"
                );
                assert.containsNone(
                    document.body,
                    `.o-mail-chat-window[data-thread-id="${mailChannelId3}"][data-thread-model="mail.channel"]`,
                    "chat window for Channel #12 should be hidden"
                );
                assert.containsOnce(
                    document.body,
                    ".o_ChatWindowHiddenMenuView",
                    "chat window hidden menu should be displayed"
                );
                assert.verifySteps(
                    [
                        `rpc:/mail/channel/messages:${mailChannelId1}`,
                        `rpc:/mail/channel/messages:${mailChannelId2}`,
                    ],
                    "messages should be fetched for the two visible chat windows"
                );

                await click(".o_ChatWindowHiddenMenuView_dropdownToggle");
                assert.containsOnce(
                    document.body,
                    ".o_ChatWindowHiddenMenuItemView",
                    "1 hidden chat window should be listed in hidden menu"
                );

                await click(".o_ChatWindowHiddenMenuItemView_chatWindowHeader");
                assert.containsN(
                    document.body,
                    ".o-mail-chat-window",
                    2,
                    "2 chat windows should still be visible"
                );
                assert.containsOnce(
                    document.body,
                    `.o-mail-chat-window[data-thread-id="${mailChannelId3}"][data-thread-model="mail.channel"]`,
                    "chat window for Channel #12 should now be visible"
                );
                assert.verifySteps(
                    [`rpc:/mail/channel/messages:${mailChannelId3}`],
                    "messages should now be fetched for Channel #12"
                );
            }
        );

        QUnit.skipRefactoring(
            "focusing a chat window of a chat should make new message separator disappear [REQUIRE FOCUS]",
            async function (assert) {
                assert.expect(2);

                const pyEnv = await startServer();
                const resPartnerId1 = pyEnv["res.partner"].create({ name: "Demo" });
                const resUsersId1 = pyEnv["res.users"].create({
                    name: "Foreigner user",
                    partner_id: resPartnerId1,
                });
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    channel_member_ids: [
                        [
                            0,
                            0,
                            {
                                is_minimized: true,
                                is_pinned: false,
                                partner_id: pyEnv.currentPartnerId,
                            },
                        ],
                        [0, 0, { partner_id: resPartnerId1 }],
                    ],
                    channel_type: "chat",
                    uuid: "channel-10-uuid",
                });
                pyEnv["mail.message"].create({
                    body: "not empty",
                    model: "mail.channel",
                    res_id: mailChannelId1,
                });
                const { afterEvent, messaging } = await start();

                // simulate receiving a message
                await afterNextRender(() =>
                    messaging.rpc({
                        route: "/mail/chat_post",
                        params: {
                            context: {
                                mockedUserId: resUsersId1,
                            },
                            message_content: "hu",
                            uuid: "channel-10-uuid",
                        },
                    })
                );
                assert.containsOnce(
                    document.body,
                    ".o_MessageListView_separatorNewMessages",
                    "should display 'new messages' separator in the conversation, from reception of new messages"
                );

                await afterNextRender(() =>
                    afterEvent({
                        eventName: "o-thread-last-seen-by-current-partner-message-id-changed",
                        func: () => document.querySelector(".o-mail-composer-textarea").focus(),
                        message:
                            "should wait until last seen by current partner message id changed",
                        predicate: ({ thread }) => {
                            return thread.id === mailChannelId1 && thread.model === "mail.channel";
                        },
                    })
                );
                assert.containsNone(
                    document.body,
                    ".o_MessageListView_separatorNewMessages",
                    "new message separator should no longer be shown, after focus on composer text input of chat window"
                );
            }
        );
    });
});
