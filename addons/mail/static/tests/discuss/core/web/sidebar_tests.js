/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("discuss sidebar");

QUnit.test("sidebar find shows channels matching search term", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        channel_member_ids: [],
        channel_type: "channel",
        group_public_id: false,
        name: "test",
    });
    const { openDiscuss } = await start();
    openDiscuss();
    await click(
        ":nth-child(1 of .o-mail-DiscussSidebarCategory) .o-mail-DiscussSidebarCategory-add"
    );
    await insertText(".o-discuss-ChannelSelector input", "test");
    // When searching for a single existing channel, the results list will have at least 2 lines:
    // One for the existing channel itself
    // One for creating a channel with the search term
    await contains(".o-mail-NavigableList-item", { count: 2 });
    await contains(".o-mail-NavigableList-item", { text: "test" });
    await contains(".o-mail-NavigableList-item", { text: "Create: # test" });
});

QUnit.test(
    "sidebar find shows channels matching search term even when user is member",
    async () => {
        const pyEnv = await startServer();
        pyEnv["discuss.channel"].create({
            channel_member_ids: [Command.create({ partner_id: pyEnv.currentPartnerId })],
            channel_type: "channel",
            group_public_id: false,
            name: "test",
        });
        const { openDiscuss } = await start();
        openDiscuss();
        await click(
            ":nth-child(1 of .o-mail-DiscussSidebarCategory) .o-mail-DiscussSidebarCategory-add"
        );
        await insertText(".o-discuss-ChannelSelector input", "test");
        // When searching for a single existing channel, the results list will have at least 2 lines:
        // One for the existing channel itself
        // One for creating a channel with the search term
        await contains(".o-mail-NavigableList-item", { count: 2 });
        await contains(".o-mail-NavigableList-item", { text: "test" });
        await contains(".o-mail-NavigableList-item", { text: "Create: # test" });
    }
);

QUnit.test("unknown channel can be displayed and interacted with", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Jane" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [[0, 0, { partner_id: partnerId }]],
        channel_type: "channel",
        name: "Not So Secret",
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    await contains("button.o-active", { text: "Inbox" });
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
    await openDiscuss(channelId);
    await contains(
        ".o-mail-DiscussSidebarCategory-channel + .o-mail-DiscussSidebarChannel.o-active",
        {
            text: "Not So Secret",
        }
    );
    await insertText(".o-mail-Composer-input", "Hello", { replace: true });
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message", { text: "Hello" });
    await click("button", { text: "Inbox" });
    await contains(".o-mail-DiscussSidebarChannel:not(.o-active)", { text: "Not So Secret" });
    await click("div[title='Leave this channel']", {
        parent: [".o-mail-DiscussSidebarChannel", { text: "Not So Secret" }],
    });
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
});
