/* @odoo-module */

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { Command } from "@mail/../tests/helpers/command";

QUnit.module("crosstab");

QUnit.test("Add member to channel", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const userId = pyEnv["res.users"].create({ name: "Harry" });
    pyEnv["res.partner"].create({ name: "Harry", user_ids: [userId] });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("[title='Show Member List']");
    assert.containsOnce($, ".o-discuss-ChannelMember:contains(Mitchell Admin)");
    await click("[title='Add Users']");
    await click(".o-discuss-ChannelInvitation-selectable:contains(Harry)");
    await click("[title='Invite to Channel']");
    assert.containsOnce($, ".o-discuss-ChannelMember:contains(Harry)");
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
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const { env, openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("[title='Show Member List']");
    assert.containsOnce($, ".o-discuss-ChannelMember:contains(Harry)");
    env.services.orm.call("discuss.channel", "action_unfollow", [channelId], {
        context: { mockedUserId: userId },
    });
});
