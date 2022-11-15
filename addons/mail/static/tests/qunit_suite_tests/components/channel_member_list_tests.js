/** @odoo-module **/

import { start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("mail", {}, function () {
    QUnit.module("components", {}, function () {
        QUnit.module("channel_member_list_tests.js");

        QUnit.skipRefactoring(
            "there should be a button to show member list in the thread view topbar initially",
            async function (assert) {
                assert.expect(1);

                const pyEnv = await startServer();
                const resPartnerId1 = pyEnv["res.partner"].create({ name: "Demo" });
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    channel_member_ids: [
                        [0, 0, { partner_id: pyEnv.currentPartnerId }],
                        [0, 0, { partner_id: resPartnerId1 }],
                    ],
                    channel_type: "group",
                });
                const { openDiscuss } = await start({
                    discuss: {
                        context: {
                            active_id: `mail.channel_${mailChannelId1}`,
                        },
                    },
                });
                await openDiscuss();
                assert.containsOnce(
                    document.body,
                    ".o_ThreadViewTopbar_showMemberListButton",
                    "there should be a button to show member list in the thread view topbar initially"
                );
            }
        );

        QUnit.skipRefactoring(
            "should show member list when clicking on show member list button in thread view topbar",
            async function (assert) {
                assert.expect(1);

                const pyEnv = await startServer();
                const resPartnerId1 = pyEnv["res.partner"].create({ name: "Demo" });
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    channel_member_ids: [
                        [0, 0, { partner_id: pyEnv.currentPartnerId }],
                        [0, 0, { partner_id: resPartnerId1 }],
                    ],
                    channel_type: "group",
                });
                const { click, openDiscuss } = await start({
                    discuss: {
                        context: {
                            active_id: `mail.channel_${mailChannelId1}`,
                        },
                    },
                });
                await openDiscuss();
                await click(".o_ThreadViewTopbar_showMemberListButton");
                assert.containsOnce(
                    document.body,
                    ".o_ChannelMemberListView",
                    "should show member list when clicking on show member list button in thread view topbar"
                );
            }
        );

        QUnit.skipRefactoring(
            "should have correct members in member list",
            async function (assert) {
                assert.expect(3);

                const pyEnv = await startServer();
                const resPartnerId1 = pyEnv["res.partner"].create({ name: "Demo" });
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    channel_member_ids: [
                        [0, 0, { partner_id: pyEnv.currentPartnerId }],
                        [0, 0, { partner_id: resPartnerId1 }],
                    ],
                    channel_type: "group",
                });
                const { click, openDiscuss } = await start({
                    discuss: {
                        context: {
                            active_id: `mail.channel_${mailChannelId1}`,
                        },
                    },
                });
                await openDiscuss();
                await click(".o_ThreadViewTopbar_showMemberListButton");
                assert.containsN(
                    document.body,
                    ".o_ChannelMemberView",
                    2,
                    "should have 2 members in member list"
                );
                assert.containsOnce(
                    document.body,
                    `.o_ChannelMemberView[data-partner-id="${pyEnv.currentPartnerId}"]`,
                    "should have current partner in member list (current partner is a member)"
                );
                assert.containsOnce(
                    document.body,
                    `.o_ChannelMemberView[data-partner-id="${resPartnerId1}"]`,
                    "should have 'Demo' in member list ('Demo' is a member)"
                );
            }
        );

        QUnit.skipRefactoring(
            "there should be a button to hide member list in the thread view topbar when the member list is visible",
            async function (assert) {
                assert.expect(1);

                const pyEnv = await startServer();
                const resPartnerId1 = pyEnv["res.partner"].create({ name: "Demo" });
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    channel_member_ids: [
                        [0, 0, { partner_id: pyEnv.currentPartnerId }],
                        [0, 0, { partner_id: resPartnerId1 }],
                    ],
                    channel_type: "group",
                });
                const { click, openDiscuss } = await start({
                    discuss: {
                        context: {
                            active_id: `mail.channel_${mailChannelId1}`,
                        },
                    },
                });
                await openDiscuss();
                await click(".o_ThreadViewTopbar_showMemberListButton");
                assert.containsOnce(
                    document.body,
                    ".o_ThreadViewTopbar_hideMemberListButton",
                    "there should be a button to hide member list in the thread view topbar when the member list is visible"
                );
            }
        );

        QUnit.skipRefactoring(
            "should show a button to load more members if they are not all loaded",
            async function (assert) {
                assert.expect(1);

                const pyEnv = await startServer();
                const channel_member_ids = [[0, 0, { partner_id: pyEnv.currentPartnerId }]];
                for (let i = 0; i < 101; i++) {
                    const resPartnerId = pyEnv["res.partner"].create({ name: "name" + i });
                    channel_member_ids.push([0, 0, { partner_id: resPartnerId }]);
                }
                const mailChannelId = pyEnv["mail.channel"].create({
                    channel_member_ids,
                    channel_type: "channel",
                });
                const { click, openDiscuss } = await start({
                    discuss: {
                        context: {
                            active_id: `mail.channel_${mailChannelId}`,
                        },
                    },
                });
                await openDiscuss();
                await click(".o_ThreadViewTopbar_showMemberListButton");
                assert.containsOnce(
                    document.body,
                    ".o_ChannelMemberListView_loadMoreButton",
                    "should have a load more button because 100 members were fetched initially and there are 102 members in total"
                );
            }
        );

        QUnit.skipRefactoring("Load more button should load more members", async function (assert) {
            assert.expect(1);

            const pyEnv = await startServer();
            const channel_member_ids = [[0, 0, { partner_id: pyEnv.currentPartnerId }]];
            for (let i = 0; i < 101; i++) {
                const resPartnerId = pyEnv["res.partner"].create({ name: "name" + i });
                channel_member_ids.push([0, 0, { partner_id: resPartnerId }]);
            }
            const mailChannelId = pyEnv["mail.channel"].create({
                channel_member_ids,
                channel_type: "channel",
            });
            const { click, openDiscuss } = await start({
                discuss: {
                    context: {
                        active_id: `mail.channel_${mailChannelId}`,
                    },
                },
            });
            await openDiscuss();
            await click(".o_ThreadViewTopbar_showMemberListButton");
            await click(".o_ChannelMemberListView_loadMoreButton");
            assert.containsN(
                document.body,
                ".o_ChannelMemberView",
                102,
                "should load all the members because 100 members were fetched initially, and load more fetched the remaining 2 members"
            );
        });

        QUnit.skipRefactoring(
            "chat with member should be opened after clicking on channel member",
            async function (assert) {
                assert.expect(1);

                const pyEnv = await startServer();
                const resPartnerId1 = pyEnv["res.partner"].create({ name: "Demo" });
                pyEnv["res.users"].create({ partner_id: resPartnerId1 });
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    channel_member_ids: [
                        [0, 0, { partner_id: pyEnv.currentPartnerId }],
                        [0, 0, { partner_id: resPartnerId1 }],
                    ],
                    channel_type: "channel",
                });
                const { click, openDiscuss } = await start({
                    discuss: {
                        context: {
                            active_id: `mail.channel_${mailChannelId1}`,
                        },
                    },
                });
                await openDiscuss();

                await click(".o_ThreadViewTopbar_showMemberListButton");
                await click(`.o_ChannelMemberView[data-partner-id="${resPartnerId1}"]`);
                assert.containsOnce(
                    document.body,
                    `.o_ThreadView[data-correspondent-id="${resPartnerId1}"]`,
                    "Chat with member Demo should be opened"
                );
            }
        );
    });
});
