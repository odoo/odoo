/** @odoo-module **/

import {
    afterNextRender,
    isScrolledToBottom,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";

QUnit.module("mail", (hooks) => {
    QUnit.module("components", {}, function () {
        QUnit.module("thread_view_tests.js");

        QUnit.skipRefactoring(
            "mark channel as fetched when a new message is loaded and as seen when focusing composer [REQUIRE FOCUS]",
            async function (assert) {
                assert.expect(7);

                const pyEnv = await startServer();
                const resPartnerId1 = pyEnv["res.partner"].create({
                    email: "fred@example.com",
                    name: "Fred",
                });
                const resUsersId1 = pyEnv["res.users"].create({
                    partner_id: resPartnerId1,
                });
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    channel_member_ids: [
                        [0, 0, { partner_id: pyEnv.currentPartnerId }],
                        [0, 0, { partner_id: resPartnerId1 }],
                    ],
                    channel_type: "chat",
                });
                const { afterEvent, click, messaging } = await start({
                    mockRPC(route, args) {
                        if (args.method === "channel_fetched") {
                            assert.strictEqual(
                                args.args[0][0],
                                mailChannelId1,
                                "channel_fetched is called on the right channel id"
                            );
                            assert.strictEqual(
                                args.model,
                                "mail.channel",
                                "channel_fetched is called on the right channel model"
                            );
                            assert.step("rpc:channel_fetch");
                        } else if (route === "/mail/channel/set_last_seen_message") {
                            assert.strictEqual(
                                args.channel_id,
                                mailChannelId1,
                                "set_last_seen_message is called on the right channel id"
                            );
                            assert.step("rpc:set_last_seen_message");
                        }
                    },
                });
                await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
                const thread = messaging.models["Thread"].findFromIdentifyingData({
                    id: mailChannelId1,
                    model: "mail.channel",
                });
                await afterNextRender(async () =>
                    messaging.rpc({
                        route: "/mail/chat_post",
                        params: {
                            context: {
                                mockedUserId: resUsersId1,
                            },
                            message_content: "new message",
                            uuid: thread.uuid,
                        },
                    })
                );
                assert.verifySteps(
                    ["rpc:channel_fetch"],
                    "Channel should have been fetched but not seen yet"
                );

                await afterNextRender(() =>
                    afterEvent({
                        eventName: "o-thread-last-seen-by-current-partner-message-id-changed",
                        func: () => document.querySelector(".o-mail-composer-textarea").focus(),
                        message:
                            "should wait until last seen by current partner message id changed after focusing the thread",
                        predicate: ({ thread }) => {
                            return thread.id === mailChannelId1 && thread.model === "mail.channel";
                        },
                    })
                );
                assert.verifySteps(
                    ["rpc:set_last_seen_message"],
                    "Channel should have been marked as seen after threadView got the focus"
                );
            }
        );

        QUnit.skipRefactoring(
            "mark channel as fetched and seen when a new message is loaded if composer is focused [REQUIRE FOCUS]",
            async function (assert) {
                assert.expect(3);

                const pyEnv = await startServer();
                const resPartnerId1 = pyEnv["res.partner"].create({});
                const resUsersId1 = pyEnv["res.users"].create({
                    partner_id: resPartnerId1,
                });
                const mailChannelId1 = pyEnv["mail.channel"].create({});
                const { afterEvent, messaging, openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                    mockRPC(route, args) {
                        if (args.method === "channel_fetched" && args.args[0] === mailChannelId1) {
                            throw new Error(
                                "'channel_fetched' RPC must not be called for created channel as message is directly seen"
                            );
                        } else if (route === "/mail/channel/set_last_seen_message") {
                            assert.strictEqual(
                                args.channel_id,
                                mailChannelId1,
                                "set_last_seen_message is called on the right channel id"
                            );
                            assert.step("rpc:set_last_seen_message");
                        }
                    },
                });
                await openDiscuss();
                document.querySelector(".o-mail-composer-textarea").focus();
                // simulate receiving a message
                await afterEvent({
                    eventName: "o-thread-last-seen-by-current-partner-message-id-changed",
                    func: () =>
                        messaging.rpc({
                            route: "/mail/chat_post",
                            params: {
                                context: {
                                    mockedUserId: resUsersId1,
                                },
                                message_content: "<p>fdsfsd</p>",
                                uuid: messaging.models["Thread"].findFromIdentifyingData({
                                    model: "mail.channel",
                                    id: mailChannelId1,
                                }).uuid,
                            },
                        }),
                    message:
                        "should wait until last seen by current partner message id changed after receiving a message while thread is focused",
                    predicate: ({ thread }) => {
                        return thread.id === mailChannelId1 && thread.model === "mail.channel";
                    },
                });
                assert.verifySteps(
                    ["rpc:set_last_seen_message"],
                    "Channel should have been mark as seen directly"
                );
            }
        );

        QUnit.skipRefactoring(
            "[technical] new messages separator on posting message",
            async function (assert) {
                // technical as we need to remove focus from text input to avoid `set_last_seen_message` call
                assert.expect(4);

                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    channel_member_ids: [
                        [
                            0,
                            0,
                            {
                                message_unread_counter: 0,
                                partner_id: pyEnv.currentPartnerId,
                            },
                        ],
                    ],
                    channel_type: "channel",
                    name: "General",
                });
                const mailMessageId1 = pyEnv["mail.message"].create({
                    body: "first message",
                    model: "mail.channel",
                    res_id: mailChannelId1,
                });
                const [mailChannelMemberId] = pyEnv["mail.channel.member"].search([
                    ["channel_id", "=", mailChannelId1],
                    ["partner_id", "=", pyEnv.currentPartnerId],
                ]);
                pyEnv["mail.channel.member"].write([mailChannelMemberId], {
                    seen_message_id: mailMessageId1,
                });
                const { insertText, openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                });
                await openDiscuss();

                assert.containsOnce(
                    document.body,
                    ".o-mail-message",
                    "should display one message in thread initially"
                );
                assert.containsNone(
                    document.body,
                    ".o_MessageListView_separatorNewMessages",
                    "should not display 'new messages' separator"
                );

                await insertText(".o-mail-composer-textarea", "hey !");
                await afterNextRender(() => {
                    // need to remove focus from text area to avoid set_last_seen_message
                    document.querySelector(".o-mail-composer-send-button").focus();
                    document.querySelector(".o-mail-composer-send-button").click();
                });
                assert.containsN(
                    document.body,
                    ".o-mail-message",
                    2,
                    "should display 2 messages (initial & newly posted), after posting a message"
                );
                assert.containsNone(
                    document.body,
                    ".o_MessageListView_separatorNewMessages",
                    "still no separator shown when current partner posted a message"
                );
            }
        );

        QUnit.skipRefactoring(
            "new messages separator on receiving new message [REQUIRE FOCUS]",
            async function (assert) {
                assert.expect(6);

                const pyEnv = await startServer();
                const resPartnerId1 = pyEnv["res.partner"].create({
                    name: "Foreigner partner",
                });
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
                                message_unread_counter: 0,
                                partner_id: pyEnv.currentPartnerId,
                            },
                        ],
                    ],
                    channel_type: "channel",
                    name: "General",
                    uuid: "randomuuid",
                });
                const mailMessageId1 = pyEnv["mail.message"].create({
                    body: "blah",
                    model: "mail.channel",
                    res_id: mailChannelId1,
                });
                const [mailChannelMemberId] = pyEnv["mail.channel.member"].search([
                    ["channel_id", "=", mailChannelId1],
                    ["partner_id", "=", pyEnv.currentPartnerId],
                ]);
                pyEnv["mail.channel.member"].write([mailChannelMemberId], {
                    seen_message_id: mailMessageId1,
                });
                const { afterEvent, messaging, openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                });
                await openDiscuss();

                assert.containsOnce(
                    document.body,
                    ".o-mail-message",
                    "should have an initial message"
                );
                assert.containsNone(
                    document.body,
                    ".o_MessageListView_separatorNewMessages",
                    "should not display 'new messages' separator"
                );

                document.querySelector(".o-mail-composer-textarea").blur();
                // simulate receiving a message
                await afterEvent({
                    eventName: "o-thread-view-hint-processed",
                    func: () =>
                        messaging.rpc({
                            route: "/mail/chat_post",
                            params: {
                                context: {
                                    mockedUserId: resUsersId1,
                                },
                                message_content: "hu",
                                uuid: messaging.models["Thread"].findFromIdentifyingData({
                                    model: "mail.channel",
                                    id: mailChannelId1,
                                }).uuid,
                            },
                        }),
                    message: "should wait until new message is received",
                    predicate: ({ hint, threadViewer }) => {
                        return (
                            threadViewer.thread.id === mailChannelId1 &&
                            threadViewer.thread.model === "mail.channel" &&
                            hint.type === "message-received"
                        );
                    },
                });
                assert.containsN(
                    document.body,
                    ".o-mail-message",
                    2,
                    "should now have 2 messages after receiving a new message"
                );
                assert.containsOnce(
                    document.body,
                    ".o_MessageListView_separatorNewMessages",
                    "'new messages' separator should be shown"
                );

                assert.containsOnce(
                    document.body,
                    `.o_MessageListView_separatorNewMessages ~ .o-mail-message[data-message-id="${
                        mailMessageId1 + 1
                    }"]`,
                    "'new messages' separator should be shown above new message received"
                );

                await afterNextRender(() =>
                    afterEvent({
                        eventName: "o-thread-last-seen-by-current-partner-message-id-changed",
                        func: () => document.querySelector(".o-mail-composer-textarea").focus(),
                        message:
                            "should wait until last seen by current partner message id changed after focusing the thread",
                        predicate: ({ thread }) => {
                            return thread.id === mailChannelId1 && thread.model === "mail.channel";
                        },
                    })
                );
                assert.containsNone(
                    document.body,
                    ".o_MessageListView_separatorNewMessages",
                    "'new messages' separator should no longer be shown as last message has been seen"
                );
            }
        );

        QUnit.skipRefactoring("new messages separator on posting message", async function (assert) {
            assert.expect(4);

            const pyEnv = await startServer();
            const mailChannelId1 = pyEnv["mail.channel"].create({
                channel_member_ids: [
                    [
                        0,
                        0,
                        {
                            message_unread_counter: 0,
                            partner_id: pyEnv.currentPartnerId,
                        },
                    ],
                ],
                channel_type: "channel",
                name: "General",
            });
            const { click, insertText, openDiscuss } = await start({
                discuss: {
                    context: { active_id: mailChannelId1 },
                },
            });
            await openDiscuss();

            assert.containsNone(document.body, ".o-mail-message", "should have no messages");
            assert.containsNone(
                document.body,
                ".o_MessageListView_separatorNewMessages",
                "should not display 'new messages' separator"
            );

            await insertText(".o-mail-composer-textarea", "hey !");
            await click(".o-mail-composer-send-button");
            assert.containsOnce(
                document.body,
                ".o-mail-message",
                "should have the message current partner just posted"
            );
            assert.containsNone(
                document.body,
                ".o_MessageListView_separatorNewMessages",
                "still no separator shown when current partner posted a message"
            );
        });

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
            "should scroll to bottom on receiving new message if the list is initially scrolled to bottom (asc order)",
            async function (assert) {
                assert.expect(2);

                const pyEnv = await startServer();
                // Needed partner & user to allow simulation of message reception
                const resPartnerId1 = pyEnv["res.partner"].create({
                    name: "Foreigner partner",
                });
                const resUsersId1 = pyEnv["res.users"].create({
                    name: "Foreigner user",
                    partner_id: resPartnerId1,
                });
                const mailChannelId1 = pyEnv["mail.channel"].create({});
                for (let i = 0; i <= 10; i++) {
                    pyEnv["mail.message"].create({
                        body: "not empty",
                        model: "mail.channel",
                        res_id: mailChannelId1,
                    });
                }
                const { afterEvent, click, messaging } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                });
                await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
                const thread = messaging.models["Thread"].findFromIdentifyingData({
                    model: "mail.channel",
                    id: mailChannelId1,
                });
                await afterEvent({
                    eventName: "o-component-message-list-scrolled",
                    async func() {
                        await click(`.o_NotificationListView_preview`);
                    },
                    message: "should wait until channel scrolled initially",
                    predicate: (data) => thread === data.threadViewer.thread,
                });
                const initialMessageList = document.querySelector(".o-mail-thread");
                assert.ok(
                    isScrolledToBottom(initialMessageList),
                    "should have scrolled to bottom of channel 20 initially"
                );

                // simulate receiving a message
                await afterEvent({
                    eventName: "o-component-message-list-scrolled",
                    func: () =>
                        messaging.rpc({
                            route: "/mail/chat_post",
                            params: {
                                context: {
                                    mockedUserId: resUsersId1,
                                },
                                message_content: "hello",
                                uuid: thread.uuid,
                            },
                        }),
                    message: "should wait until channel scrolled after receiving a message",
                    predicate: (data) => thread === data.threadViewer.thread,
                });
                const messageList = document.querySelector(".o-mail-thread");
                assert.ok(
                    isScrolledToBottom(messageList),
                    "should scroll to bottom on receiving new message because the list is initially scrolled to bottom"
                );
            }
        );

        QUnit.skipRefactoring(
            "should not scroll on receiving new message if the list is initially scrolled anywhere else than bottom (asc order)",
            async function (assert) {
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
                const mailChannelId1 = pyEnv["mail.channel"].create({});
                for (let i = 0; i <= 10; i++) {
                    pyEnv["mail.message"].create({
                        body: "not empty",
                        model: "mail.channel",
                        res_id: mailChannelId1,
                    });
                }
                const { afterEvent, click, messaging } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                });

                const thread = messaging.models["Thread"].findFromIdentifyingData({
                    model: "mail.channel",
                    id: mailChannelId1,
                });
                await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
                await afterEvent({
                    eventName: "o-component-message-list-scrolled",
                    async func() {
                        await click(`.o_NotificationListView_preview`);
                    },
                    message: "should wait until channel scrolled initially",
                    predicate: (data) => thread === data.threadViewer.thread,
                });
                const initialMessageList = document.querySelector(".o-mail-thread");
                assert.ok(
                    isScrolledToBottom(initialMessageList),
                    "should have scrolled to bottom of channel 1 initially"
                );

                await afterEvent({
                    eventName: "o-component-message-list-scrolled",
                    func: () => (initialMessageList.scrollTop = 0),
                    message: "should wait until channel 1 processed manual scroll",
                    predicate: (data) => thread === data.threadViewer.thread,
                });
                assert.strictEqual(
                    initialMessageList.scrollTop,
                    0,
                    "should have scrolled to the top of channel 1 manually"
                );

                // simulate receiving a message
                await afterEvent({
                    eventName: "o-thread-view-hint-processed",
                    func: () =>
                        messaging.rpc({
                            route: "/mail/chat_post",
                            params: {
                                context: {
                                    mockedUserId: resUsersId1,
                                },
                                message_content: "hello",
                                uuid: thread.uuid,
                            },
                        }),
                    message: "should wait until channel processed new message hint",
                    predicate: (data) =>
                        thread === data.threadViewer.thread &&
                        data.hint.type === "message-received",
                });
                assert.strictEqual(
                    document.querySelector(".o-mail-thread").scrollTop,
                    0,
                    "should not scroll on receiving new message because the list is initially scrolled anywhere else than bottom"
                );
            }
        );

        QUnit.skipRefactoring(
            "delete all attachments of message without content should no longer display the message",
            async function (assert) {
                assert.expect(2);

                const pyEnv = await startServer();
                const irAttachmentId1 = pyEnv["ir.attachment"].create({
                    mimetype: "text/plain",
                    name: "Blah.txt",
                });
                const mailChannelId1 = pyEnv["mail.channel"].create({});
                pyEnv["mail.message"].create({
                    attachment_ids: [irAttachmentId1],
                    model: "mail.channel",
                    res_id: mailChannelId1,
                });
                const { afterEvent, click, messaging, openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                });
                // wait for messages of the thread to be loaded
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
                    ".o-mail-message",
                    "there should be 1 message displayed initially"
                );

                await click(
                    `.o_AttachmentCard[data-id="${
                        messaging.models["Attachment"].findFromIdentifyingData({
                            id: irAttachmentId1,
                        }).localId
                    }"] .o_AttachmentCard_asideItemUnlink`
                );
                await click(".o_AttachmentDeleteConfirmView_confirmButton");
                assert.containsNone(
                    document.body,
                    ".o-mail-message",
                    "message should no longer be displayed after removing all its attachments (empty content)"
                );
            }
        );

        QUnit.skipRefactoring(
            "delete all attachments of a message with some text content should still keep it displayed",
            async function (assert) {
                assert.expect(2);

                const pyEnv = await startServer();
                const irAttachmentId1 = pyEnv["ir.attachment"].create({
                    mimetype: "text/plain",
                    name: "Blah.txt",
                });
                const mailChannelId1 = pyEnv["mail.channel"].create({});
                pyEnv["mail.message"].create({
                    attachment_ids: [irAttachmentId1],
                    body: "Some content",
                    model: "mail.channel",
                    res_id: mailChannelId1,
                });
                const { afterEvent, click, messaging, openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                });
                // wait for messages of the thread to be loaded
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
                    ".o-mail-message",
                    "there should be 1 message displayed initially"
                );

                await click(
                    `.o_AttachmentCard[data-id="${
                        messaging.models["Attachment"].findFromIdentifyingData({
                            id: irAttachmentId1,
                        }).localId
                    }"] .o_AttachmentCard_asideItemUnlink`
                );
                await click(".o_AttachmentDeleteConfirmView_confirmButton");
                assert.containsOnce(
                    document.body,
                    ".o-mail-message",
                    "message should still be displayed after removing its attachments (non-empty content)"
                );
            }
        );

        QUnit.skipRefactoring(
            "Post a message containing an email address followed by a mention on another line",
            async function (assert) {
                assert.expect(1);

                const pyEnv = await startServer();
                const resPartnerId1 = pyEnv["res.partner"].create({
                    email: "testpartner@odoo.com",
                    name: "TestPartner",
                });
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    channel_member_ids: [
                        [0, 0, { partner_id: pyEnv.currentPartnerId }],
                        [0, 0, { partner_id: resPartnerId1 }],
                    ],
                });
                const { click, insertText, openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                });
                await openDiscuss();
                await insertText(".o-mail-composer-textarea", "email@odoo.com\n");
                await insertText(".o-mail-composer-textarea", "@Te");
                await click(".o_ComposerSuggestionView");
                await click(".o-mail-composer-send-button");
                assert.containsOnce(
                    document.querySelector(`.o-mail-message-body`),
                    `.o_mail_redirect[data-oe-id="${resPartnerId1}"][data-oe-model="res.partner"]:contains("@TestPartner")`,
                    "Conversation should have a message that has been posted, which contains partner mention"
                );
            }
        );

        QUnit.skipRefactoring(
            `Mention a partner with special character (e.g. apostrophe ')`,
            async function (assert) {
                assert.expect(1);

                const pyEnv = await startServer();
                const resPartnerId1 = pyEnv["res.partner"].create({
                    email: "usatyi@example.com",
                    name: "Pynya's spokesman",
                });
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    channel_member_ids: [
                        [0, 0, { partner_id: pyEnv.currentPartnerId }],
                        [0, 0, { partner_id: resPartnerId1 }],
                    ],
                });
                const { click, insertText, openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                });
                await openDiscuss();
                await insertText(".o-mail-composer-textarea", "@Pyn");
                await click(".o_ComposerSuggestionView");
                await click(".o-mail-composer-send-button");
                assert.containsOnce(
                    document.querySelector(`.o-mail-message-body`),
                    `.o_mail_redirect[data-oe-id="${resPartnerId1}"][data-oe-model="res.partner"]:contains("@Pynya's spokesman")`,
                    "Conversation should have a message that has been posted, which contains partner mention"
                );
            }
        );

        QUnit.skipRefactoring(
            "mention 2 different partners that have the same name",
            async function (assert) {
                assert.expect(3);

                const pyEnv = await startServer();
                const [resPartnerId1, resPartnerId2] = pyEnv["res.partner"].create([
                    {
                        email: "partner1@example.com",
                        name: "TestPartner",
                    },
                    {
                        email: "partner2@example.com",
                        name: "TestPartner",
                    },
                ]);
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    channel_member_ids: [
                        [0, 0, { partner_id: pyEnv.currentPartnerId }],
                        [0, 0, { partner_id: resPartnerId1 }],
                        [0, 0, { partner_id: resPartnerId2 }],
                    ],
                });
                const { click, insertText, openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                });
                await openDiscuss();
                await insertText(".o-mail-composer-textarea", "@Te");
                await afterNextRender(() =>
                    document.querySelectorAll(".o_ComposerSuggestionView")[0].click()
                );
                await insertText(".o-mail-composer-textarea", "@Te");
                await afterNextRender(() =>
                    document.querySelectorAll(".o_ComposerSuggestionView")[1].click()
                );
                await click(".o-mail-composer-send-button");
                assert.containsOnce(
                    document.body,
                    ".o-mail-message-body",
                    "should have one message after posting it"
                );
                assert.containsOnce(
                    document.querySelector(`.o-mail-message-body`),
                    `.o_mail_redirect[data-oe-id="${resPartnerId1}"][data-oe-model="res.partner"]:contains("@TestPartner")`,
                    "message should contain the first partner mention"
                );
                assert.containsOnce(
                    document.querySelector(`.o-mail-message-body`),
                    `.o_mail_redirect[data-oe-id="${resPartnerId2}"][data-oe-model="res.partner"]:contains("@TestPartner")`,
                    "message should also contain the second partner mention"
                );
            }
        );

        QUnit.skipRefactoring(
            "mention a channel on a second line when the first line contains #",
            async function (assert) {
                assert.expect(2);

                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    name: "General good",
                });
                const { click, insertText, openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                });
                await openDiscuss();
                await insertText(".o-mail-composer-textarea", "#blabla\n");
                await insertText(".o-mail-composer-textarea", "#");
                await click(".o_ComposerSuggestionView");
                await click(".o-mail-composer-send-button");
                assert.containsOnce(
                    document.querySelector(".o-mail-message-body"),
                    ".o_channel_redirect",
                    "message should contain a link to the mentioned channel"
                );
                assert.strictEqual(
                    document.querySelector(".o_channel_redirect").textContent,
                    "#General good",
                    "link to the channel must contains # + the channel name"
                );
            }
        );

        QUnit.skipRefactoring(
            "mention a channel when replacing the space after the mention by another char",
            async function (assert) {
                assert.expect(2);

                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    name: "General good",
                });
                const { click, insertText, openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                });
                await openDiscuss();

                await insertText(".o-mail-composer-textarea", "#");
                await click(".o_ComposerSuggestionView");
                const text = document.querySelector(`.o-mail-composer-textarea`).value;
                document.querySelector(`.o-mail-composer-textarea`).value = text.slice(0, -1);
                await insertText(".o-mail-composer-textarea", ", test");
                await click(".o-mail-composer-send-button");
                assert.containsOnce(
                    document.querySelector(".o-mail-message-body"),
                    ".o_channel_redirect",
                    "message should contain a link to the mentioned channel"
                );
                assert.strictEqual(
                    document.querySelector(".o_channel_redirect").textContent,
                    "#General good",
                    "link to the channel must contains # + the channel name"
                );
            }
        );

        QUnit.skipRefactoring(
            "mention 2 different channels that have the same name",
            async function (assert) {
                assert.expect(3);

                const pyEnv = await startServer();
                const [mailChannelId1, mailChannelId2] = pyEnv["mail.channel"].create([
                    {
                        channel_type: "channel",
                        group_public_id: false,
                        name: "my channel",
                    },
                    {
                        channel_type: "channel",
                        name: "my channel",
                    },
                ]);
                const { click, insertText, openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                });
                await openDiscuss();
                document.querySelector(".o-mail-composer-textarea").focus();
                await insertText(".o-mail-composer-textarea", "#my");
                await afterNextRender(() =>
                    document.querySelectorAll(".o_ComposerSuggestionView")[0].click()
                );
                await insertText(".o-mail-composer-textarea", "#my");
                await afterNextRender(() =>
                    document.querySelectorAll(".o_ComposerSuggestionView")[1].click()
                );
                await click(".o-mail-composer-send-button");
                assert.containsOnce(
                    document.body,
                    ".o-mail-message-body",
                    "should have one message after posting it"
                );
                assert.containsOnce(
                    document.querySelector(`.o-mail-message-body`),
                    `.o_channel_redirect[data-oe-id="${mailChannelId1}"][data-oe-model="mail.channel"]:contains("#my channel")`,
                    "message should contain the first channel mention"
                );
                assert.containsOnce(
                    document.querySelector(`.o-mail-message-body`),
                    `.o_channel_redirect[data-oe-id="${mailChannelId2}"][data-oe-model="mail.channel"]:contains("#my channel")`,
                    "message should also contain the second channel mention"
                );
            }
        );

        QUnit.skipRefactoring(
            "show empty placeholder when thread contains no message",
            async function (assert) {
                assert.expect(2);

                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({});
                const { afterEvent, openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                });
                await afterEvent({
                    eventName: "o-thread-view-hint-processed",
                    func: openDiscuss,
                    message: "should wait until thread becomes loaded with messages",
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
                    '[data-empty-thread=""]',
                    "message list empty placeholder should be shown as thread does not contain any messages"
                );
                assert.containsNone(
                    document.body,
                    ".o-mail-message",
                    "no message should be shown as thread does not contain any"
                );
            }
        );

        QUnit.skipRefactoring(
            "show empty placeholder when thread contains only empty messages",
            async function (assert) {
                assert.expect(2);

                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({});
                pyEnv["mail.message"].create({
                    model: "mail.channel",
                    res_id: mailChannelId1,
                });
                const { afterEvent, openDiscuss } = await start({
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
                    '[data-empty-thread=""]',
                    "message list empty placeholder should be shown as thread contain only empty messages"
                );
                assert.containsNone(
                    document.body,
                    ".o-mail-message",
                    "no message should be shown as thread contains only empty ones"
                );
            }
        );

        QUnit.skipRefactoring(
            "message with subtype should be displayed (and not considered as empty)",
            async function (assert) {
                assert.expect(2);

                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({});
                const mailMessageSubtypeId1 = pyEnv["mail.message.subtype"].create({
                    description: "Task created",
                });
                pyEnv["mail.message"].create({
                    model: "mail.channel",
                    res_id: mailChannelId1,
                    subtype_id: mailMessageSubtypeId1,
                });
                const { afterEvent, openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                });
                await afterEvent({
                    eventName: "o-thread-view-hint-processed",
                    func: openDiscuss,
                    message: "should wait until thread becomes loaded with messages",
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
                    ".o-mail-message",
                    "should display 1 message (message with subtype description 'task created')"
                );
                assert.strictEqual(
                    document.body.querySelector(".o-mail-message-body").textContent,
                    "Task created",
                    "message should have 'Task created' (from its subtype description)"
                );
            }
        );

        QUnit.skipRefactoring(
            "[technical] message list with a full page of empty messages should show load more if there are other messages",
            async function (assert) {
                // Technical assumptions :
                // - /mail/channel/messages fetching exactly 30 messages,
                // - empty messages not being displayed
                // - auto-load more being triggered on scroll, not automatically when the 30 first messages are empty
                assert.expect(2);

                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({});
                for (let i = 0; i <= 30; i++) {
                    pyEnv["mail.message"].create({
                        body: "not empty",
                        model: "mail.channel",
                        res_id: mailChannelId1,
                    });
                }
                for (let i = 0; i <= 30; i++) {
                    pyEnv["mail.message"].create({
                        model: "mail.channel",
                        res_id: mailChannelId1,
                    });
                }
                const { afterEvent, openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                });
                await afterEvent({
                    eventName: "o-thread-view-hint-processed",
                    func: openDiscuss,
                    message: "should wait until thread becomes loaded with messages",
                    predicate: ({ hint, threadViewer }) => {
                        return (
                            hint.type === "messages-loaded" &&
                            threadViewer.thread.model === "mail.channel" &&
                            threadViewer.thread.id === mailChannelId1
                        );
                    },
                });
                assert.containsNone(
                    document.body,
                    ".o-mail-message",
                    "No message should be shown as all 30 first messages are empty"
                );
                assert.containsOnce(
                    document.body,
                    ".o_MessageListView_loadMore",
                    "Load more button should be shown as there are more messages to show"
                );
            }
        );

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
            "composer should be focused automatically after clicking on the send button [REQUIRE FOCUS]",
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
