/* @odoo-module */

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("crosstab");

QUnit.test("Add member to channel", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const userId = pyEnv["res.users"].create({ name: "Harry" });
    pyEnv["res.partner"].create({ name: "Harry", user_ids: [userId] });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[title='Show Member List']");
    assert.containsOnce($, ".o-mail-ChannelMember:contains(Mitchell Admin)");
    await click("button[title='Add Users']");
    await click(".o-discuss-ChannelInvitation-selectable:contains(Harry)");
    await click("button[title='Invite to Channel']");
    assert.containsOnce($, ".o-mail-ChannelMember:contains(Harry)");
});

QUnit.test("Remove member from channel", async (assert) => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Harry" });
    const partnerId = pyEnv["res.partner"].create({
        name: "Harry",
        user_ids: [userId],
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
    });
    const { env, openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[title='Show Member List']");
    assert.containsOnce($, ".o-mail-ChannelMember:contains(Harry)");
    env.services.orm.call("discuss.channel", "action_unfollow", [channelId], {
        context: { mockedUserId: userId },
    });
});
