/* @odoo-module */

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("discuss");

QUnit.test("Member list and settings menu are exclusive", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[title='Show Member List']");
    assert.containsOnce($, ".o-discuss-ChannelMemberList");
    await click("button[title='Show Call Settings']");
    assert.containsOnce($, ".o-mail-CallSettings");
    assert.containsNone($, ".o-discuss-ChannelMemberList");
});
