/** @odoo-module **/

import { afterNextRender, start, startServer } from "@mail/../tests/helpers/test_utils";

import { datetime_to_str } from "web.time";

QUnit.module("mail", {}, function () {
    QUnit.module("components", {}, function () {
        QUnit.module("discuss_sidebar_category_item_tests.js");
        QUnit.skipRefactoring(
            "chat - sorting: should be sorted by last activity time",
            async function (assert) {
                assert.expect(6);

                const pyEnv = await startServer();
                const [mailChannelId1, mailChannelId2] = pyEnv["mail.channel"].create([
                    {
                        channel_member_ids: [
                            [
                                0,
                                0,
                                {
                                    last_interest_dt: datetime_to_str(new Date(2021, 0, 1)),
                                    partner_id: pyEnv.currentPartnerId,
                                },
                            ],
                        ],
                        channel_type: "chat",
                    },
                    {
                        channel_member_ids: [
                            [
                                0,
                                0,
                                {
                                    last_interest_dt: datetime_to_str(new Date(2021, 0, 2)),
                                    partner_id: pyEnv.currentPartnerId,
                                },
                            ],
                        ],
                        channel_type: "chat",
                    },
                ]);
                const { click, openDiscuss } = await start();
                await openDiscuss();

                const initialChats = document.querySelectorAll(
                    ".o-mail-category-chat .o_DiscussSidebarCategory_item"
                );
                assert.strictEqual(initialChats.length, 2, "should have 2 livechat items");
                assert.strictEqual(
                    Number(initialChats[0].dataset.channelId),
                    mailChannelId2,
                    "first livechat should be the one with the more recent last activity time"
                );
                assert.strictEqual(
                    Number(initialChats[1].dataset.channelId),
                    mailChannelId1,
                    "second chat should be the one with the less recent last activity time"
                );

                // post a new message on the last channel
                await afterNextRender(() => initialChats[1].click());
                await afterNextRender(() => document.execCommand("insertText", false, "Blabla"));
                await click(".o-mail-composer-send-button");
                const newChats = document.querySelectorAll(
                    ".o-mail-category-chat .o_DiscussSidebarCategory_item"
                );
                assert.strictEqual(newChats.length, 2, "should have 2 chat items");
                assert.strictEqual(
                    Number(newChats[0].dataset.channelId),
                    mailChannelId1,
                    "first chat should be the one with the more recent last activity time"
                );
                assert.strictEqual(
                    Number(newChats[1].dataset.channelId),
                    mailChannelId2,
                    "second chat should be the one with the less recent last activity time"
                );
            }
        );
    });
});
