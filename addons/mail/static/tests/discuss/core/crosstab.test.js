/** @odoo-module */

import { test } from "@odoo/hoot";
import { click, contains, openDiscuss, start, startServer } from "../../mail_test_helpers";
import { Command, constants } from "@web/../tests/web_test_helpers";

test.skip("Add member to channel", async () => {
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

test.skip("Remove member from channel", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Harry" });
    const partnerId = pyEnv["res.partner"].create({
        name: "Harry",
        user_ids: [userId],
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            Command.create({ partner_id: constants.PARTNER_ID }),
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
