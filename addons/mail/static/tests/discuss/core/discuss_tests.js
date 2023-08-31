/* @odoo-module */

import { click, contains, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("discuss");

QUnit.test("Member list and settings menu are exclusive", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("[title='Show Member List']");
    await contains(".o-discuss-ChannelMemberList");
    await click("[title='Show Call Settings']");
    await contains(".o-discuss-CallSettings");
    await contains(".o-discuss-ChannelMemberList", { count: 0 });
});
