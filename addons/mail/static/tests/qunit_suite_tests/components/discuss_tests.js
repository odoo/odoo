/** @odoo-module **/

import {
    afterNextRender,
    isScrolledToBottom,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";

import { destroy } from "@web/../tests/helpers/utils";

import { makeTestPromise, file } from "web.test_utils";

const { createFile, inputFiles } = file;

QUnit.module("mail", {}, function () {
    QUnit.module("components", {}, function () {
        QUnit.module("discuss_tests.js");

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
    });
});
