import {
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test, waitFor, waitForNone } from "@odoo/hoot";
import {
    Command,
    contains,
    getService,
    serverState,
    withUser,
} from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Add member to channel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const userId = pyEnv["res.users"].create({ name: "Harry" });
    pyEnv["res.partner"].create({ name: "Harry", user_ids: [userId] });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-discuss-ChannelMemberList:count(1)"); // wait for auto-open of this panel
    await waitFor(".o-discuss-ChannelMember:text('Mitchell Admin'):count(1)");
    await contains("[title='Add People']:count(1)").click();
    await contains(".o-discuss-ChannelInvitation-selectable:has(:text('Harry')):count(1)").click();
    await contains(".o-discuss-ChannelInvitation button:text('Invite'):enabled:count(1)").click();
    await waitForNone(".o-discuss-ChannelInvitation");
    await waitFor(".o-discuss-ChannelMember:text('Harry'):count(1)");
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
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-discuss-ChannelMember:text('Harry'):count(1)");
    withUser(userId, () =>
        getService("orm").call("discuss.channel", "action_unfollow", [channelId])
    );
    await waitForNone(".o-discuss-ChannelMember:text('Harry')");
});
