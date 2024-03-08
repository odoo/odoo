/** @odoo-module alias=@mail/../tests/discuss/core/crosstab_tests default=false */
const test = QUnit.test; // QUnit.test()

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { openDiscuss, start } from "@mail/../tests/helpers/test_utils";

import { click, contains } from "@web/../tests/utils";

QUnit.module("crosstab");

test("Add member to channel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const userId = pyEnv["res.users"].create({ name: "Harry" });
    pyEnv["res.partner"].create({ name: "Harry", user_ids: [userId] });
    await start();
    await openDiscuss(channelId);
    await click("[title='Show Member List']");
    await contains(".o-discuss-ChannelMember", { text: "Mitchell Admin" });
    await click("[title='Add Users']");
    await click(".o-discuss-ChannelInvitation-selectable", { text: "Harry" });
    await click("[title='Invite to Channel']:enabled");
    await contains(".o-discuss-ChannelInvitation", { count: 0 });
    await click("[title='Show Member List']");
    await contains(".o-discuss-ChannelMember", { text: "Harry" });
});

test("Remove member from channel", async () => {
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
    const { env } = await start();
    await openDiscuss(channelId);
    await click("[title='Show Member List']");
    await contains(".o-discuss-ChannelMember", { text: "Harry" });
    pyEnv.withUser(userId, () =>
        env.services.orm.call("discuss.channel", "action_unfollow", [channelId])
    );
    await contains(".o-discuss-ChannelMember", { count: 0, text: "Harry" });
});
