import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, serverState, withUser } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("there should be a button to show member list in the thread view topbar initially", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Show Member List']");
});

test("should show member list when clicking on show member list button in thread view topbar", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Show Member List']");
    await contains(".o-discuss-ChannelMemberList");
});

test("should have correct members in member list", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Show Member List']");
    await contains(".o-discuss-ChannelMember", { count: 2 });
    await contains(".o-discuss-ChannelMember", { text: serverState.partnerName });
    await contains(".o-discuss-ChannelMember", { text: "Demo" });
});

test("there should be a button to hide member list in the thread view topbar when the member list is visible", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Show Member List']");
    await contains("[title='Hide Member List']");
});

test("chat with member should be opened after clicking on channel member", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Show Member List']");
    await click(".o-discuss-ChannelMember.cursor-pointer");
    await contains(".o-mail-AutoresizeInput[title='Demo']");
});

test("should show a button to load more members if they are not all loaded", async () => {
    // Test assumes at most 100 members are loaded at once.
    const pyEnv = await startServer();
    const channel_member_ids = [];
    for (let i = 0; i < 101; i++) {
        const partnerId = pyEnv["res.partner"].create({ name: "name" + i });
        channel_member_ids.push(Command.create({ partner_id: partnerId }));
    }
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    pyEnv["discuss.channel"].write([channelId], { channel_member_ids });
    await click("[title='Show Member List']");
    await contains("button", { text: "Load more" });
});

test("Load more button should load more members", async () => {
    // Test assumes at most 100 members are loaded at once.
    const pyEnv = await startServer();
    const channel_member_ids = [];
    for (let i = 0; i < 101; i++) {
        const partnerId = pyEnv["res.partner"].create({ name: "name" + i });
        channel_member_ids.push(Command.create({ partner_id: partnerId }));
    }
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    pyEnv["discuss.channel"].write([channelId], { channel_member_ids });
    await click("[title='Show Member List']");
    await click("[title='Load more']");
    await contains(".o-discuss-ChannelMember", { count: 102 });
});

test("Channel member count update after user joined", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const userId = pyEnv["res.users"].create({ name: "Harry" });
    pyEnv["res.partner"].create({ name: "Harry", user_ids: [userId] });
    await start();
    await openDiscuss(channelId);
    await click("[title='Show Member List']");
    await contains(".o-discuss-ChannelMemberList h6", { text: "Offline - 1" });
    await click("[title='Add Users']");
    await click(".o-discuss-ChannelInvitation-selectable", { text: "Harry" });
    await click("[title='Invite to Channel']:enabled");
    await contains(".o-discuss-ChannelInvitation", { count: 0 });
    await click("[title='Show Member List']");
    await contains(".o-discuss-ChannelMemberList h6", { text: "Offline - 2" });
});

test("Channel member count update after user left", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Dobby" });
    const partnerId = pyEnv["res.partner"].create({ name: "Dobby", user_ids: [userId] });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const env = await start();
    await openDiscuss(channelId);
    await click("[title='Show Member List']");
    await contains(".o-discuss-ChannelMember", { count: 2 });
    await withUser(userId, () =>
        env.services.orm.call("discuss.channel", "action_unfollow", [channelId])
    );
    await contains(".o-discuss-ChannelMember", { count: 1 });
});
