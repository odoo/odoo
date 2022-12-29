/** @odoo-module **/

import { start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("mail", {}, function () {
    QUnit.module("components", {}, function () {
        QUnit.module("discuss_pinned_tests.js");

        QUnit.skipRefactoring(
            "[technical] sidebar: channel group_based_subscription: mandatorily pinned",
            async function (assert) {
                assert.expect(2);

                // FIXME: The following is admittedly odd.
                // Fixing it should entail a deeper reflexion on the group_based_subscription
                // and is_pinned functionalities, especially in python.
                // task-2284357

                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({
                    channel_member_ids: [
                        [
                            0,
                            0,
                            {
                                is_pinned: false,
                                partner_id: pyEnv.currentPartnerId,
                            },
                        ],
                    ],
                    group_based_subscription: true,
                });
                const { openDiscuss } = await start();
                await openDiscuss();

                assert.containsOnce(
                    document.body,
                    `.o-mail-category-item[data-channel-id="${mailChannelId1}"]`,
                    "The channel #General is in discuss sidebar"
                );
                assert.containsNone(
                    document.body,
                    "o_DiscussSidebarCategoryItem_commandLeave",
                    "The group_based_subscription channel is not unpinnable"
                );
            }
        );
    });
});
