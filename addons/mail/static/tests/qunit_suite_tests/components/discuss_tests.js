/** @odoo-module **/

import { isScrolledToBottom, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("mail", {}, function () {
    QUnit.module("components", {}, function () {
        QUnit.module("discuss_tests.js");

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
    });
});
