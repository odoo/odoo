/* @odoo-module */

import { Command } from "@mail/../tests/helpers/command";
import {
    click,
    insertText,
    nextAnimationFrame,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";

import { makeDeferred } from "@web/../tests/helpers/utils";

QUnit.module("discuss sidebar");

QUnit.test("sidebar find shows channels matching search term", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        channel_member_ids: [],
        channel_type: "channel",
        group_public_id: false,
        name: "test",
    });
    const def = makeDeferred();
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (args.method === "search_read") {
                def.resolve();
            }
        },
    });
    await openDiscuss();
    await click(".o-mail-DiscussCategory-add");
    await insertText(".o-discuss-ChannelSelector input", "test");
    await def;
    await nextAnimationFrame(); // ensures search_read rpc is rendered.
    // When searching for a single existing channel, the results list will have at least 2 lines:
    // One for the existing channel itself
    // One for creating a channel with the search term
    assert.containsN($, ".o-mail-NavigableList-item", 2);
    assert.containsN($, ".o-mail-NavigableList-item:contains(test)", 2);
});

QUnit.test(
    "sidebar find shows channels matching search term even when user is member",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["discuss.channel"].create({
            channel_member_ids: [Command.create({ partner_id: pyEnv.currentPartnerId })],
            channel_type: "channel",
            group_public_id: false,
            name: "test",
        });
        const def = makeDeferred();
        const { openDiscuss } = await start({
            async mockRPC(route, args) {
                if (args.method === "search_read") {
                    def.resolve();
                }
            },
        });
        await openDiscuss();
        await click(".o-mail-DiscussCategory-add");
        await insertText(".o-discuss-ChannelSelector input", "test");
        await def;
        await nextAnimationFrame(); // ensures search_read rpc is rendered.
        // When searching for a single existing channel, the results list will have at least 2 lines:
        // One for the existing channel itself
        // One for creating a channel with the search term
        assert.containsN($, ".o-mail-NavigableList-item", 2);
        assert.containsN($, ".o-mail-NavigableList-item:contains(test)", 2);
    }
);
