/** @odoo-module **/

import {
    afterNextRender,
    isScrolledToBottom,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";

import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import { destroy } from "@web/../tests/helpers/utils";

import { makeTestPromise, file } from "web.test_utils";

const { createFile, inputFiles } = file;

QUnit.module("mail", {}, function () {
    QUnit.module("components", {}, function () {
        QUnit.module("discuss_tests.js");

        QUnit.skipRefactoring("messaging not created", async function (assert) {
            assert.expect(1);

            const messagingBeforeCreationDeferred = makeTestPromise();
            const { openDiscuss } = await start({
                messagingBeforeCreationDeferred,
                waitUntilMessagingCondition: "none",
            });
            await openDiscuss(null, { waitUntilMessagesLoaded: false });
            assert.containsOnce(
                document.body,
                ".o_DiscussContainer_spinner",
                "should display messaging not initialized"
            );
            messagingBeforeCreationDeferred.resolve();
        });

        QUnit.skipRefactoring(
            "discuss should be marked as opened if the component is already rendered and messaging becomes created afterwards",
            async function (assert) {
                assert.expect(1);

                const messagingBeforeCreationDeferred = makeTestPromise();
                const { env, openDiscuss } = await start({
                    messagingBeforeCreationDeferred,
                    waitUntilMessagingCondition: "none",
                });
                await openDiscuss(null, { waitUntilMessagesLoaded: false });

                await afterNextRender(() => messagingBeforeCreationDeferred.resolve());
                const { messaging } = env.services.messaging.modelManager;
                assert.ok(
                    messaging.discuss.discussView,
                    "discuss should be marked as opened if the component is already rendered and messaging becomes created afterwards"
                );
            }
        );

        QUnit.skipRefactoring(
            "discuss should be marked as closed when the component is unmounted",
            async function (assert) {
                assert.expect(1);

                const { messaging, openDiscuss, webClient } = await start();
                await openDiscuss();

                await afterNextRender(() => destroy(webClient));
                assert.notOk(
                    messaging.discuss.discussView,
                    "discuss should be marked as closed when the component is unmounted"
                );
            }
        );

        QUnit.skipRefactoring("messaging not initialized", async function (assert) {
            assert.expect(1);

            const messaginginitializedDeferred = makeTestPromise();
            const { openDiscuss } = await start({
                async mockRPC(route) {
                    if (route === "/mail/init_messaging") {
                        await messaginginitializedDeferred; // simulate messaging never initialized
                    }
                },
                waitUntilMessagingCondition: "created",
            });
            await openDiscuss(null, { waitUntilMessagesLoaded: false });
            assert.strictEqual(
                document.querySelectorAll(".o_DiscussContainer_spinner").length,
                1,
                "should display messaging not initialized"
            );
            messaginginitializedDeferred.resolve(); // ensure proper teardown
        });

        QUnit.skipRefactoring("messaging becomes initialized", async function (assert) {
            assert.expect(2);

            const messagingInitializedProm = makeTestPromise();

            const { openDiscuss } = await start({
                async mockRPC(route) {
                    if (route === "/mail/init_messaging") {
                        await messagingInitializedProm;
                    }
                },
                waitUntilMessagingCondition: "created",
            });
            await openDiscuss(null, { waitUntilMessagesLoaded: false });
            assert.strictEqual(
                document.querySelectorAll(".o_DiscussContainer_spinner").length,
                1,
                "should display messaging not initialized"
            );

            await afterNextRender(() => messagingInitializedProm.resolve());
            assert.strictEqual(
                document.querySelectorAll(".o_DiscussContainer_spinner").length,
                0,
                "should no longer display messaging not initialized"
            );
        });

        QUnit.skipRefactoring("sidebar: public channel rendering", async function (assert) {
            assert.expect(3);

            const pyEnv = await startServer();
            const mailChannelId1 = pyEnv["mail.channel"].create([
                { name: "channel1", channel_type: "channel", group_public_id: false },
            ]);
            const { openDiscuss } = await start();
            await openDiscuss();
            assert.strictEqual(
                document.querySelectorAll(`.o-mail-category-channel .o_DiscussSidebarCategory_item`)
                    .length,
                1,
                "should have 1 channel items"
            );
            assert.strictEqual(
                document.querySelectorAll(`
            .o-mail-category-channel
            .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]
        `).length,
                1,
                "should have channel 1"
            );
            const channel1 = document.querySelector(`
        .o-mail-category-channel
        .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]
    `);
            assert.ok(
                channel1.querySelectorAll(`:scope .o_ThreadIconView_publicChannel`).length,
                "channel1 (public) should have globe icon"
            );
        });

        QUnit.skipRefactoring("new messages separator [REQUIRE FOCUS]", async function (assert) {
            // this test requires several messages so that the last message is not
            // visible. This is necessary in order to display 'new messages' and not
            // remove from DOM right away from seeing last message.
            // AKU TODO: thread specific test
            assert.expect(6);

            const pyEnv = await startServer();
            const resPartnerId1 = pyEnv["res.partner"].create({ name: "Foreigner partner" });
            const resUsersId1 = pyEnv["res.users"].create({
                name: "Foreigner user",
                partner_id: resPartnerId1,
            });
            const mailChannelId1 = pyEnv["mail.channel"].create({ uuid: "randomuuid" });
            let lastMessageId;
            for (let i = 1; i <= 25; i++) {
                lastMessageId = pyEnv["mail.message"].create({
                    body: "not empty",
                    model: "mail.channel",
                    res_id: mailChannelId1,
                });
            }
            const [mailChannelMemberId] = pyEnv["mail.channel.member"].search([
                ["channel_id", "=", mailChannelId1],
                ["partner_id", "=", pyEnv.currentPartnerId],
            ]);
            pyEnv["mail.channel.member"].write([mailChannelMemberId], {
                seen_message_id: lastMessageId,
            });
            const { afterEvent, messaging, openDiscuss } = await start({
                discuss: {
                    params: {
                        default_active_id: `mail.channel_${mailChannelId1}`,
                    },
                },
            });
            await afterEvent({
                eventName: "o-component-message-list-scrolled",
                func: openDiscuss,
                message: "should wait until channel scrolled to its last message initially",
                predicate: ({ scrollTop, thread }) => {
                    const messageList = document.querySelector(
                        `.o-mail-discuss-content .o-mail-thread`
                    );
                    return (
                        thread &&
                        thread.model === "mail.channel" &&
                        thread.id === mailChannelId1 &&
                        isScrolledToBottom(messageList)
                    );
                },
            });
            assert.containsN(document.body, ".o-mail-message", 25, "should have 25 messages");
            assert.containsNone(
                document.body,
                ".o_MessageListView_separatorNewMessages",
                "should not display 'new messages' separator"
            );
            // scroll to top
            await afterEvent({
                eventName: "o-component-message-list-scrolled",
                func: () => {
                    document.querySelector(`.o-mail-discuss-content .o-mail-thread`).scrollTop = 0;
                },
                message: "should wait until channel scrolled to top",
                predicate: ({ scrollTop, thread }) => {
                    return (
                        thread &&
                        thread.model === "mail.channel" &&
                        thread.id === mailChannelId1 &&
                        scrollTop === 0
                    );
                },
            });
            // composer is focused by default, we remove that focus
            document.querySelector(".o-mail-composer-textarea").blur();
            // simulate receiving a message
            await afterNextRender(async () =>
                messaging.rpc({
                    route: "/mail/chat_post",
                    params: {
                        context: {
                            mockedUserId: resUsersId1,
                        },
                        message_content: "hu",
                        uuid: "randomuuid",
                    },
                })
            );

            assert.containsN(document.body, ".o-mail-message", 26, "should have 26 messages");
            assert.containsOnce(
                document.body,
                ".o_MessageListView_separatorNewMessages",
                "should display 'new messages' separator"
            );
            await afterEvent({
                eventName: "o-component-message-list-scrolled",
                func: () => {
                    const messageList = document.querySelector(
                        ".o-mail-discuss-content .o-mail-thread"
                    );
                    messageList.scrollTop = messageList.scrollHeight - messageList.clientHeight;
                },
                message: "should wait until channel scrolled to bottom",
                predicate: ({ scrollTop, thread }) => {
                    const messageList = document.querySelector(
                        `.o-mail-discuss-content .o-mail-thread`
                    );
                    return (
                        thread &&
                        thread.model === "mail.channel" &&
                        thread.id === mailChannelId1 &&
                        isScrolledToBottom(messageList)
                    );
                },
            });
            assert.containsOnce(
                document.body,
                ".o_MessageListView_separatorNewMessages",
                "should still display 'new messages' separator as composer is not focused"
            );

            await afterNextRender(() =>
                document.querySelector(".o-mail-composer-textarea").focus()
            );
            assert.containsNone(
                document.body,
                ".o_MessageListView_separatorNewMessages",
                "should no longer display 'new messages' separator (message seen)"
            );
        });

        QUnit.skipRefactoring("restore thread scroll position", async function (assert) {
            assert.expect(6);

            const pyEnv = await startServer();
            const [mailChannelId1, mailChannelId2] = pyEnv["mail.channel"].create([
                { name: "Channel1" },
                { name: "Channel2" },
            ]);
            for (let i = 1; i <= 25; i++) {
                pyEnv["mail.message"].create({
                    body: "not empty",
                    model: "mail.channel",
                    res_id: mailChannelId1,
                });
            }
            for (let i = 1; i <= 24; i++) {
                pyEnv["mail.message"].create({
                    body: "not empty",
                    model: "mail.channel",
                    res_id: mailChannelId2,
                });
            }
            const { afterEvent, openDiscuss } = await start({
                discuss: {
                    params: {
                        default_active_id: `mail.channel_${mailChannelId1}`,
                    },
                },
            });
            await afterEvent({
                eventName: "o-component-message-list-scrolled",
                func: openDiscuss,
                message: "should wait until channel 1 scrolled to its last message",
                predicate: ({ thread }) => {
                    return thread && thread.channel && thread.channel.id === mailChannelId1;
                },
            });
            assert.strictEqual(
                document.querySelectorAll(".o-mail-discuss-content .o-mail-thread .o-mail-message")
                    .length,
                25,
                "should have 25 messages in channel 1"
            );
            const initialMessageList = document.querySelector(
                ".o-mail-discuss-content .o-mail-thread"
            );
            assert.ok(
                isScrolledToBottom(initialMessageList),
                "should have scrolled to bottom of channel 1 initially"
            );

            await afterEvent({
                eventName: "o-component-message-list-scrolled",
                func: () =>
                    (document.querySelector(
                        ".o-mail-discuss-content .o-mail-thread"
                    ).scrollTop = 0),
                message: "should wait until channel 1 changed its scroll position to top",
                predicate: ({ thread }) => {
                    return thread && thread.channel && thread.channel.id === mailChannelId1;
                },
            });
            assert.strictEqual(
                document.querySelector(".o-mail-discuss-content .o-mail-thread").scrollTop,
                0,
                "should have scrolled to top of channel 1"
            );

            // Ensure scrollIntoView of channel 2 has enough time to complete before
            // going back to channel 1. Await is needed to prevent the scrollIntoView
            // initially planned for channel 2 to actually apply on channel 1.
            // task-2333535
            await afterEvent({
                eventName: "o-component-message-list-scrolled",
                func: () => {
                    // select channel 2
                    document
                        .querySelector(
                            `
                .o-mail-category-channel
                .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId2}"]
            `
                        )
                        .click();
                },
                message: "should wait until channel 2 scrolled to its last message",
                predicate: ({ scrollTop, thread }) => {
                    const messageList = document.querySelector(".o-mail-thread");
                    return (
                        thread &&
                        thread.channel &&
                        thread.channel.id === mailChannelId2 &&
                        isScrolledToBottom(messageList)
                    );
                },
            });
            assert.strictEqual(
                document.querySelectorAll(".o-mail-discuss-content .o-mail-thread .o-mail-message")
                    .length,
                24,
                "should have 24 messages in channel 2"
            );

            await afterEvent({
                eventName: "o-component-message-list-scrolled",
                func: () => {
                    // select channel 1
                    document
                        .querySelector(
                            `
                .o-mail-category-channel
                .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]
            `
                        )
                        .click();
                },
                message: "should wait until channel 1 restored its scroll position",
                predicate: ({ scrollTop, thread }) => {
                    return (
                        thread &&
                        thread.channel &&
                        thread.channel.id === mailChannelId1 &&
                        scrollTop === 0
                    );
                },
            });
            assert.strictEqual(
                document.querySelector(".o-mail-discuss-content .o-mail-thread").scrollTop,
                0,
                "should have recovered scroll position of channel 1 (scroll to top)"
            );

            await afterEvent({
                eventName: "o-component-message-list-scrolled",
                func: () => {
                    // select channel 2
                    document
                        .querySelector(
                            `
                .o-mail-category-channel
                .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId2}"]
            `
                        )
                        .click();
                },
                message: "should wait until channel 2 recovered its scroll position (to bottom)",
                predicate: ({ scrollTop, thread }) => {
                    const messageList = document.querySelector(".o-mail-thread");
                    return (
                        thread &&
                        thread.channel &&
                        thread.channel.id === mailChannelId2 &&
                        isScrolledToBottom(messageList)
                    );
                },
            });
            const messageList = document.querySelector(".o-mail-thread");
            assert.ok(
                isScrolledToBottom(messageList),
                "should have recovered scroll position of channel 2 (scroll to bottom)"
            );
        });

        QUnit.skipRefactoring(
            "composer state: attachments save and restore",
            async function (assert) {
                assert.expect(6);

                const pyEnv = await startServer();
                const [mailChannelId1] = pyEnv["mail.channel"].create([
                    { name: "General" },
                    { name: "Special" },
                ]);
                const { messaging, openDiscuss } = await start({
                    discuss: {
                        params: {
                            default_active_id: `mail.channel_${mailChannelId1}`,
                        },
                    },
                });
                await openDiscuss();
                const channels = document.querySelectorAll(`
        .o-mail-category-channel .o_DiscussSidebarCategory_item
    `);
                // Add attachment in a message for #general
                await afterNextRender(async () => {
                    const file = await createFile({
                        content: "hello, world",
                        contentType: "text/plain",
                        name: "text.txt",
                    });
                    inputFiles(messaging.discuss.threadView.composerView.fileUploader.fileInput, [
                        file,
                    ]);
                });
                // Switch to #special
                await afterNextRender(() => channels[1].click());
                // Attach files in a message for #special
                const files = [
                    await createFile({
                        content: "hello2, world",
                        contentType: "text/plain",
                        name: "text2.txt",
                    }),
                    await createFile({
                        content: "hello3, world",
                        contentType: "text/plain",
                        name: "text3.txt",
                    }),
                    await createFile({
                        content: "hello4, world",
                        contentType: "text/plain",
                        name: "text4.txt",
                    }),
                ];
                await afterNextRender(() =>
                    inputFiles(
                        messaging.discuss.threadView.composerView.fileUploader.fileInput,
                        files
                    )
                );
                // Switch back to #general
                await afterNextRender(() => channels[0].click());
                // Check attachment is reloaded
                assert.strictEqual(
                    document.querySelectorAll(`.o_ComposerView .o_AttachmentCard`).length,
                    1,
                    "should have 1 attachment in the composer"
                );
                assert.strictEqual(
                    document.querySelector(`.o_ComposerView .o_AttachmentCard`).dataset.id,
                    messaging.models["Attachment"].findFromIdentifyingData({ id: 1 }).localId,
                    "should have correct 1st attachment in the composer"
                );

                // Switch back to #special
                await afterNextRender(() => channels[1].click());
                // Check attachments are reloaded
                assert.strictEqual(
                    document.querySelectorAll(`.o_ComposerView .o_AttachmentCard`).length,
                    3,
                    "should have 3 attachments in the composer"
                );
                assert.strictEqual(
                    document.querySelectorAll(`.o_ComposerView .o_AttachmentCard`)[0].dataset.id,
                    messaging.models["Attachment"].findFromIdentifyingData({ id: 2 }).localId,
                    "should have attachment with id 2 as 1st attachment"
                );
                assert.strictEqual(
                    document.querySelectorAll(`.o_ComposerView .o_AttachmentCard`)[1].dataset.id,
                    messaging.models["Attachment"].findFromIdentifyingData({ id: 3 }).localId,
                    "should have attachment with id 3 as 2nd attachment"
                );
                assert.strictEqual(
                    document.querySelectorAll(`.o_ComposerView .o_AttachmentCard`)[2].dataset.id,
                    messaging.models["Attachment"].findFromIdentifyingData({ id: 4 }).localId,
                    "should have attachment with id 4 as 3rd attachment"
                );
            }
        );

        QUnit.skipRefactoring(
            "mark channel as seen if last message is visible when switching channels when the previous channel had a more recent last message than the current channel [REQUIRE FOCUS]",
            async function (assert) {
                assert.expect(1);

                const pyEnv = await startServer();
                const [mailChannelId1, mailChannelId2] = pyEnv["mail.channel"].create([
                    {
                        channel_member_ids: [
                            [
                                0,
                                0,
                                {
                                    message_unread_counter: 1,
                                    partner_id: pyEnv.currentPartnerId,
                                },
                            ],
                        ],
                        name: "Bla",
                    },
                    {
                        channel_member_ids: [
                            [
                                0,
                                0,
                                {
                                    message_unread_counter: 1,
                                    partner_id: pyEnv.currentPartnerId,
                                },
                            ],
                        ],
                        name: "Blu",
                    },
                ]);
                const [mailMessageId1] = pyEnv["mail.message"].create([
                    {
                        body: "oldest message",
                        model: "mail.channel",
                        res_id: mailChannelId1,
                    },
                    {
                        body: "newest message",
                        model: "mail.channel",
                        res_id: mailChannelId2,
                    },
                ]);
                const { afterEvent, openDiscuss } = await start({
                    discuss: {
                        context: {
                            active_id: `mail.channel_${mailChannelId2}`,
                        },
                    },
                });
                await afterEvent({
                    eventName: "o-thread-view-hint-processed",
                    func: openDiscuss,
                    message: "should wait until channel 2 loaded its messages initially",
                    predicate: ({ hint, threadViewer }) => {
                        return (
                            threadViewer.thread.channel &&
                            threadViewer.thread.channel.id === mailChannelId2 &&
                            hint.type === "messages-loaded"
                        );
                    },
                });
                await afterNextRender(() =>
                    afterEvent({
                        eventName: "o-thread-last-seen-by-current-partner-message-id-changed",
                        func: () => {
                            document
                                .querySelector(
                                    `
                .o-mail-category-item[data-channel-id="${mailChannelId1}"]
            `
                                )
                                .click();
                        },
                        message:
                            "should wait until last seen by current partner message id changed",
                        predicate: ({ thread }) => {
                            return (
                                thread.channel &&
                                thread.channel.id === mailChannelId1 &&
                                thread.lastSeenByCurrentPartnerMessageId === mailMessageId1
                            );
                        },
                    })
                );
                assert.doesNotHaveClass(
                    document.querySelector(`
            .o-mail-category-item[data-channel-id="${mailChannelId1}"]
        `),
                    "o-unread",
                    "sidebar item of channel 1 should no longer be unread"
                );
            }
        );

        QUnit.skipRefactoring(
            "warning on send with shortcut when attempting to post message with still-uploading attachments",
            async function (assert) {
                assert.expect(7);

                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({});
                const { messaging, openDiscuss } = await start({
                    discuss: {
                        context: {
                            active_id: `mail.channel_${mailChannelId1}`,
                        },
                    },
                    async mockRPC(route) {
                        if (route === "/mail/attachment/upload") {
                            // simulates attachment is never finished uploading
                            await new Promise(() => {});
                        }
                    },
                    services: {
                        notification: makeFakeNotificationService((message, options) => {
                            assert.strictEqual(
                                message,
                                "Please wait while the file is uploading.",
                                "notification content should be about the uploading file"
                            );
                            assert.strictEqual(
                                options.type,
                                "warning",
                                "notification should be a warning"
                            );
                            assert.step("notification");
                        }),
                    },
                });
                await openDiscuss();
                const file = await createFile({
                    content: "hello, world",
                    contentType: "text/plain",
                    name: "text.txt",
                });
                await afterNextRender(() =>
                    inputFiles(messaging.discuss.threadView.composerView.fileUploader.fileInput, [
                        file,
                    ])
                );
                assert.containsOnce(
                    document.body,
                    ".o_AttachmentCard",
                    "should have only one attachment"
                );
                assert.containsOnce(
                    document.body,
                    ".o_AttachmentCard.o-isUploading",
                    "attachment displayed is being uploaded"
                );
                assert.containsOnce(
                    document.body,
                    ".o-mail-composer-send-button",
                    "composer send button should be displayed"
                );

                // Try to send message
                document
                    .querySelector(`.o-mail-composer-textarea`)
                    .dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter" }));
                assert.verifySteps(
                    ["notification"],
                    "should have triggered a notification for inability to post message at the moment (some attachments are still being uploaded)"
                );
            }
        );
    });
});
