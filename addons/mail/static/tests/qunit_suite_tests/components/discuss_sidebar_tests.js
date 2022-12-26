/** @odoo-module **/

import { makeDeferred } from "@mail/utils/deferred";
import { nextAnimationFrame, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("mail", {}, function () {
    QUnit.module("components", {}, function () {
        QUnit.module("discuss_sidebar_tests.js");

        QUnit.test("sidebar find shows channels matching search term", async function (assert) {
            assert.expect(3);

            const pyEnv = await startServer();
            pyEnv["mail.channel"].create({
                channel_member_ids: [],
                channel_type: "channel",
                group_public_id: false,
                name: "test",
            });
            const searchReadDef = makeDeferred();
            const { click, openDiscuss } = await start({
                async mockRPC(route, args) {
                    if (args.method === "search_read") {
                        searchReadDef.resolve();
                    }
                },
            });
            await openDiscuss();
            await click(`.o_DiscussSidebarCategory_commandAdd`);
            document.querySelector(`.o_DiscussSidebarCategory_addingItem`).focus();
            document.execCommand("insertText", false, "test");
            document
                .querySelector(`.o_DiscussSidebarCategory_addingItem`)
                .dispatchEvent(new window.KeyboardEvent("keydown"));
            document
                .querySelector(`.o_DiscussSidebarCategory_addingItem`)
                .dispatchEvent(new window.KeyboardEvent("keyup"));

            await searchReadDef;
            await nextAnimationFrame(); // ensures search_read rpc is rendered.
            const results = document.querySelectorAll(".ui-autocomplete .ui-menu-item a");
            assert.ok(
                results,
                "should have autocomplete suggestion after typing on 'find or create channel' input"
            );
            assert.strictEqual(
                results.length,
                // When searching for a single existing channel, the results list will have at least 2 lines:
                // One for the existing channel itself
                // One for creating a channel with the search term
                2
            );
            assert.strictEqual(
                results[0].textContent,
                "test",
                "autocomplete suggestion should target the channel matching search term"
            );
        });

        QUnit.test(
            "sidebar find shows channels matching search term even when user is member",
            async function (assert) {
                assert.expect(3);

                const pyEnv = await startServer();
                pyEnv["mail.channel"].create({
                    channel_member_ids: [[0, 0, { partner_id: pyEnv.currentPartnerId }]],
                    channel_type: "channel",
                    group_public_id: false,
                    name: "test",
                });
                const searchReadDef = makeDeferred();
                const { click, openDiscuss } = await start({
                    async mockRPC(route, args) {
                        if (args.method === "search_read") {
                            searchReadDef.resolve();
                        }
                    },
                });
                await openDiscuss();
                await click(`.o_DiscussSidebarCategory_commandAdd`);
                document.querySelector(`.o_DiscussSidebarCategory_addingItem`).focus();
                document.execCommand("insertText", false, "test");
                document
                    .querySelector(`.o_DiscussSidebarCategory_addingItem`)
                    .dispatchEvent(new window.KeyboardEvent("keydown"));
                document
                    .querySelector(`.o_DiscussSidebarCategory_addingItem`)
                    .dispatchEvent(new window.KeyboardEvent("keyup"));

                await searchReadDef;
                await nextAnimationFrame();
                const results = document.querySelectorAll(".ui-autocomplete .ui-menu-item a");
                assert.ok(
                    results,
                    "should have autocomplete suggestion after typing on 'find or create channel' input"
                );
                assert.strictEqual(
                    results.length,
                    // When searching for a single existing channel, the results list will have at least 2 lines:
                    // One for the existing channel itself
                    // One for creating a channel with the search term
                    2
                );
                assert.strictEqual(
                    results[0].textContent,
                    "test",
                    "autocomplete suggestion should target the channel matching search term even if user is member"
                );
            }
        );

        QUnit.test(
            "sidebar channels should be ordered case insensitive alphabetically",
            async function (assert) {
                assert.expect(1);

                const pyEnv = await startServer();
                pyEnv["mail.channel"].create([
                    { name: "Xyz" },
                    { name: "abc" },
                    { name: "Abc" },
                    { name: "Xyz" },
                ]);
                const { openDiscuss } = await start();
                await openDiscuss();
                const results = document.querySelectorAll(
                    ".o_DiscussSidebarView_categoryChannel .o_DiscussSidebarCategoryItem_name"
                );
                assert.deepEqual(
                    [
                        results[0].textContent,
                        results[1].textContent,
                        results[2].textContent,
                        results[3].textContent,
                    ],
                    ["abc", "Abc", "Xyz", "Xyz"],
                    "Channel name should be in case insensitive alphabetical order"
                );
            }
        );

        QUnit.test("create channel from sidebar", async function(assert) {
                assert.expect(1);

                const pyEnv = await startServer();
                const searchReadDef = makeDeferred();
                const { click, insertText, openDiscuss, messaging } = await start({
                     async mockRPC (route, args) {
                        if (args.method === "search_read") {
                            searchReadDef.resolve();
                        }
                        if (args.method === "channel_create") {
                            const channel_id = pyEnv["mail.channel"].create({
                                channel_member_ids: [[0, 0, { partner_id: pyEnv.currentPartnerId }]],
                                channel_type: "channel",
                                group_public_id: false,
                                name: args.args[0],
                            });
                            return (await messaging.rpc({
                                model: "mail.channel",
                                method: "channel_info",
                                args: [channel_id],
                            }))[0];
                        }
                    },
                });
                await openDiscuss();
                await click(".o_DiscussSidebarCategory_commandAdd");
                insertText(".o_DiscussSidebarCategory_addingItemInput", "Test Channel");

                await searchReadDef;
                await nextAnimationFrame();
                await click(".o_DiscussSidebarCategory_newChannelAutocompleteSuggestions li");
                assert.strictEqual(
                    document.querySelector(".o_ThreadViewTopbar_threadName").innerText,
                    "Test Channel",
                    "New channel created from the sidebar should be open in threadview"
                );
            }
        );
    });
});
