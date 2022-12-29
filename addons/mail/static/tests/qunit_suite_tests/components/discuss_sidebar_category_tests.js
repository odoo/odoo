/** @odoo-module **/

import { afterNextRender, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("mail", {}, function () {
    QUnit.module("components", {}, function () {
        QUnit.module("discuss_sidebar_category_tests.js");

        QUnit.skipRefactoring(
            "channel - states: close should update the value on the server",
            async function (assert) {
                assert.expect(2);

                const pyEnv = await startServer();
                pyEnv["mail.channel"].create({});
                pyEnv["res.users.settings"].create({
                    user_id: pyEnv.currentUserId,
                    is_discuss_sidebar_category_channel_open: true,
                });
                const currentUserId = pyEnv.currentUserId;
                const { click, messaging, openDiscuss } = await start();
                await openDiscuss();

                const initalSettings = await messaging.rpc({
                    model: "res.users.settings",
                    method: "_find_or_create_for_user",
                    args: [[currentUserId]],
                });
                assert.strictEqual(
                    initalSettings.is_discuss_sidebar_category_channel_open,
                    true,
                    "the server side value should be true"
                );

                await click(`.o-mail-category-channel .o_DiscussSidebarCategory_title`);
                const newSettings = await messaging.rpc({
                    model: "res.users.settings",
                    method: "_find_or_create_for_user",
                    args: [[currentUserId]],
                });
                assert.strictEqual(
                    newSettings.is_discuss_sidebar_category_channel_open,
                    false,
                    "the server side value should be false"
                );
            }
        );

        QUnit.skipRefactoring(
            "channel - states: open should update the value on the server",
            async function (assert) {
                assert.expect(2);

                const pyEnv = await startServer();
                pyEnv["mail.channel"].create({});
                pyEnv["res.users.settings"].create({
                    user_id: pyEnv.currentUserId,
                    is_discuss_sidebar_category_channel_open: false,
                });
                const currentUserId = pyEnv.currentUserId;
                const { click, messaging, openDiscuss } = await start();
                await openDiscuss();

                const initalSettings = await messaging.rpc({
                    model: "res.users.settings",
                    method: "_find_or_create_for_user",
                    args: [[currentUserId]],
                });
                assert.strictEqual(
                    initalSettings.is_discuss_sidebar_category_channel_open,
                    false,
                    "the server side value should be false"
                );

                await click(`.o-mail-category-channel .o_DiscussSidebarCategory_title`);
                const newSettings = await messaging.rpc({
                    model: "res.users.settings",
                    method: "_find_or_create_for_user",
                    args: [[currentUserId]],
                });
                assert.strictEqual(
                    newSettings.is_discuss_sidebar_category_channel_open,
                    true,
                    "the server side value should be false"
                );
            }
        );

        QUnit.skipRefactoring("channel - states: close from the bus", async function (assert) {
            assert.expect(1);

            const pyEnv = await startServer();
            const mailChannelId1 = pyEnv["mail.channel"].create({});
            const resUsersSettingsId1 = pyEnv["res.users.settings"].create({
                user_id: pyEnv.currentUserId,
                is_discuss_sidebar_category_channel_open: true,
            });
            const { openDiscuss } = await start();
            await openDiscuss();

            await afterNextRender(() => {
                pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.record/insert", {
                    "res.users.settings": {
                        id: resUsersSettingsId1,
                        is_discuss_sidebar_category_channel_open: false,
                    },
                });
            });
            assert.containsNone(
                document.body,
                `.o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]`,
                "Category channel should be closed and the content should be invisible"
            );
        });

        QUnit.skipRefactoring("channel - states: open from the bus", async function (assert) {
            assert.expect(1);

            const pyEnv = await startServer();
            const mailChannelId1 = pyEnv["mail.channel"].create({});
            const resUsersSettingsId1 = pyEnv["res.users.settings"].create({
                user_id: pyEnv.currentUserId,
                is_discuss_sidebar_category_channel_open: false,
            });
            const { openDiscuss } = await start();
            await openDiscuss();

            await afterNextRender(() => {
                pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.record/insert", {
                    "res.users.settings": {
                        id: resUsersSettingsId1,
                        is_discuss_sidebar_category_channel_open: true,
                    },
                });
            });
            assert.containsOnce(
                document.body,
                `.o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]`,
                "Category channel should be open and the content should be visible"
            );
        });

        QUnit.skipRefactoring(
            "channel - states: the active category item should be visible even if the category is closed",
            async function (assert) {
                assert.expect(4);

                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({});
                const { click, openDiscuss } = await start();
                await openDiscuss();

                assert.containsOnce(
                    document.body,
                    `.o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]`
                );

                const channel = document.querySelector(
                    `.o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]`
                );
                await afterNextRender(() => {
                    channel.click();
                });
                assert.ok(channel.classList.contains("o-active"));

                await click(`.o-mail-category-channel .o_DiscussSidebarCategory_title`);
                assert.containsOnce(
                    document.body,
                    `.o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]`,
                    "the active channel item should remain even if the category is folded"
                );

                await click(`button[data-mailbox="inbox"]`);
                assert.containsNone(
                    document.body,
                    `.o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]`,
                    "inactive item should be invisible if the category is folded"
                );
            }
        );

        QUnit.skipRefactoring(
            "chat - command: should have add command when category is unfolded",
            async function (assert) {
                assert.expect(1);

                const { openDiscuss } = await start();
                await openDiscuss();
                assert.strictEqual(
                    document.querySelectorAll(
                        `.o-mail-category-chat .o_DiscussSidebarCategory_header .o-mail-category-add-button`
                    ).length,
                    1,
                    "should have add command when chat category is open"
                );
            }
        );

        QUnit.skipRefactoring(
            "chat - command: should not have add command when category is folded",
            async function (assert) {
                assert.expect(1);

                const pyEnv = await startServer();
                pyEnv["res.users.settings"].create({
                    user_id: pyEnv.currentUserId,
                    is_discuss_sidebar_category_chat_open: false,
                });
                const { openDiscuss } = await start();
                await openDiscuss();

                assert.strictEqual(
                    document.querySelectorAll(
                        `.o-mail-category-chat .o_DiscussSidebarCategory_header .o-mail-category-add-button`
                    ).length,
                    0,
                    "should not have add command when chat category is closed"
                );
            }
        );

        QUnit.skipRefactoring(
            "chat - states: close manually by clicking the title",
            async function (assert) {
                assert.expect(1);

                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    channel_type: "chat",
                });
                pyEnv["res.users.settings"].create({
                    user_id: pyEnv.currentUserId,
                    is_discuss_sidebar_category_chat_open: true,
                });
                const { click, openDiscuss } = await start();
                await openDiscuss();
                await click(`.o-mail-category-chat .o_DiscussSidebarCategory_title`);
                assert.containsNone(
                    document.body,
                    `.o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]`,
                    "Category chat should be closed and the content should be invisible"
                );
            }
        );

        QUnit.skipRefactoring(
            "chat - states: open manually by clicking the title",
            async function (assert) {
                assert.expect(1);

                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    channel_type: "chat",
                });
                pyEnv["res.users.settings"].create({
                    user_id: pyEnv.currentUserId,
                    is_discuss_sidebar_category_chat_open: false,
                });
                const { click, openDiscuss } = await start();
                await openDiscuss();
                await click(`.o-mail-category-chat .o_DiscussSidebarCategory_title`);
                assert.containsOnce(
                    document.body,
                    `.o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]`,
                    "Category chat should be open and the content should be visible"
                );
            }
        );

        QUnit.skipRefactoring(
            "chat - states: close should call update server data",
            async function (assert) {
                assert.expect(2);

                const pyEnv = await startServer();
                pyEnv["mail.channel"].create({});
                pyEnv["res.users.settings"].create({
                    user_id: pyEnv.currentUserId,
                    is_discuss_sidebar_category_chat_open: true,
                });
                const currentUserId = pyEnv.currentUserId;
                const { click, messaging, openDiscuss } = await start();
                await openDiscuss();

                const initalSettings = await messaging.rpc({
                    model: "res.users.settings",
                    method: "_find_or_create_for_user",
                    args: [[currentUserId]],
                });
                assert.strictEqual(
                    initalSettings.is_discuss_sidebar_category_chat_open,
                    true,
                    "the value in server side should be true"
                );

                await click(`.o-mail-category-chat .o_DiscussSidebarCategory_title`);
                const newSettings = await messaging.rpc({
                    model: "res.users.settings",
                    method: "_find_or_create_for_user",
                    args: [[currentUserId]],
                });
                assert.strictEqual(
                    newSettings.is_discuss_sidebar_category_chat_open,
                    false,
                    "the value in server side should be false"
                );
            }
        );

        QUnit.skipRefactoring(
            "chat - states: open should call update server data",
            async function (assert) {
                assert.expect(2);

                const pyEnv = await startServer();
                pyEnv["mail.channel"].create({});
                pyEnv["res.users.settings"].create({
                    user_id: pyEnv.currentUserId,
                    is_discuss_sidebar_category_chat_open: false,
                });
                const { click, messaging, openDiscuss } = await start();
                await openDiscuss();

                const initalSettings = await messaging.rpc({
                    model: "res.users.settings",
                    method: "_find_or_create_for_user",
                    args: [[pyEnv.currentUserId]],
                });
                assert.strictEqual(
                    initalSettings.is_discuss_sidebar_category_chat_open,
                    false,
                    "the value in server side should be false"
                );

                await click(`.o-mail-category-chat .o_DiscussSidebarCategory_title`);
                const newSettings = await messaging.rpc({
                    model: "res.users.settings",
                    method: "_find_or_create_for_user",
                    args: [[pyEnv.currentUserId]],
                });
                assert.strictEqual(
                    newSettings.is_discuss_sidebar_category_chat_open,
                    true,
                    "the value in server side should be true"
                );
            }
        );

        QUnit.skipRefactoring("chat - states: close from the bus", async function (assert) {
            assert.expect(1);

            const pyEnv = await startServer();
            const mailChannelId1 = pyEnv["mail.channel"].create({
                channel_type: "chat",
            });
            const resUsersSettingsId1 = pyEnv["res.users.settings"].create({
                user_id: pyEnv.currentUserId,
                is_discuss_sidebar_category_chat_open: true,
            });
            const { openDiscuss } = await start();
            await openDiscuss();

            await afterNextRender(() => {
                pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.record/insert", {
                    "res.users.settings": {
                        id: resUsersSettingsId1,
                        is_discuss_sidebar_category_chat_open: false,
                    },
                });
            });
            assert.containsNone(
                document.body,
                `.o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]`,
                "Category chat should be close and the content should be invisible"
            );
        });

        QUnit.skipRefactoring("chat - states: open from the bus", async function (assert) {
            assert.expect(1);

            const pyEnv = await startServer();
            const mailChannelId1 = pyEnv["mail.channel"].create({
                channel_type: "chat",
            });
            const resUsersSettingsId1 = pyEnv["res.users.settings"].create({
                user_id: pyEnv.currentUserId,
                is_discuss_sidebar_category_chat_open: false,
            });
            const { openDiscuss } = await start();
            await openDiscuss();

            await afterNextRender(() => {
                pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.record/insert", {
                    "res.users.settings": {
                        id: resUsersSettingsId1,
                        is_discuss_sidebar_category_chat_open: true,
                    },
                });
            });
            assert.containsOnce(
                document.body,
                `.o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]`,
                "Category chat should be open and the content should be visible"
            );
        });

        QUnit.skipRefactoring(
            "chat - states: the active category item should be visible even if the category is closed",
            async function (assert) {
                assert.expect(4);

                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    channel_type: "chat",
                });
                const { click, openDiscuss } = await start();
                await openDiscuss();

                assert.containsOnce(
                    document.body,
                    `.o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]`
                );

                const chat = document.querySelector(
                    `.o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]`
                );
                await afterNextRender(() => {
                    chat.click();
                });
                assert.ok(chat.classList.contains("o-active"));

                await click(`.o-mail-category-chat .o_DiscussSidebarCategory_title`);
                assert.containsOnce(
                    document.body,
                    `.o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]`,
                    "the active chat item should remain even if the category is folded"
                );

                await click(`button[data-mailbox="inbox"]`);
                assert.containsNone(
                    document.body,
                    `.o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]`,
                    "inactive item should be invisible if the category is folded"
                );
            }
        );
    });
});
