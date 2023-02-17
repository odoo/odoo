/** @odoo-module **/

import { patchUiSize } from "@mail/../tests/helpers/patch_ui_size";
import {
    afterNextRender,
    isScrolledToBottom,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";

QUnit.module("mail", {}, function () {
    QUnit.module("components", {}, function () {
        QUnit.module("chat_window_manager_tests.js");

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
    });
});
