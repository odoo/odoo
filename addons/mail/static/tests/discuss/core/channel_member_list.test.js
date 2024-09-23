import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, getService, serverState, withUser } from "@web/../tests/web_test_helpers";

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
    await contains("[title='Members']");
});

test("should show member list when clicking on member list button in thread view topbar", async () => {
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
    await contains(".o-discuss-ChannelMemberList"); // open by default
    await click("[title='Members']");
    await contains(".o-discuss-ChannelMemberList", { count: 0 });
    await click("[title='Members']");
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
    await contains(".o-discuss-ChannelMember", { count: 2 });
    await contains(".o-discuss-ChannelMember", { text: serverState.partnerName });
    await contains(".o-discuss-ChannelMember", { text: "Demo" });
});

test("members should be correctly categorised into online/offline", async () => {
    const pyEnv = await startServer();
    const [onlinePartnerId, idlePartnerId] = pyEnv["res.partner"].create([
        { name: "Online Partner", im_status: "online" },
        { name: "Idle Partner", im_status: "away" },
    ]);
    pyEnv["res.partner"].write([serverState.partnerId], { im_status: "im_partner" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChanel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: onlinePartnerId }),
            Command.create({ partner_id: idlePartnerId }),
        ],
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList h6", { text: "Online - 2" });
    await contains(".o-discuss-ChannelMemberList h6", { text: "Offline - 1" });
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
    await click(".o-discuss-ChannelMember.cursor-pointer", { text: "Demo" });
    await contains(".o_avatar_card .o_card_user_infos", { text: "Demo" });
    await click(".o_avatar_card button", { text: "Send message" });
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
    await contains(
        ".o-mail-ActionPanel:has(.o-mail-ActionPanel-header:contains('Members')) button",
        { text: "Load more" }
    );
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
    await click(
        ".o-mail-ActionPanel:has(.o-mail-ActionPanel-header:contains('Members')) [title='Load more']"
    );
    await contains(".o-discuss-ChannelMember", { count: 102 });
});

test("Channel member count update after user joined", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const userId = pyEnv["res.users"].create({ name: "Harry" });
    pyEnv["res.partner"].create({ name: "Harry", user_ids: [userId] });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList h6", { text: "Offline - 1" });
    await click("[title='Invite People']");
    await click(".o-discuss-ChannelInvitation-selectable", { text: "Harry" });
    await click(".o-discuss-ChannelInvitation [title='Invite']:enabled");
    await contains(".o-discuss-ChannelInvitation", { count: 0 });
    await click("[title='Members']");
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMember", { count: 2 });
    await withUser(userId, () =>
        getService("orm").call("discuss.channel", "action_unfollow", [channelId])
    );
    await contains(".o-discuss-ChannelMember", { count: 1 });
});

test("Members are partitioned by online/offline", async () => {
    const pyEnv = await startServer();
    const [userId_1, userId_2] = pyEnv["res.users"].create([{ name: "Dobby" }, { name: "John" }]);
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        {
            name: "Dobby",
            user_ids: [userId_1],
            im_status: "offline",
        },
        {
            name: "John",
            user_ids: [userId_2],
            im_status: "online",
        },
    ]);
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId_1 }),
            Command.create({ partner_id: partnerId_2 }),
        ],
    });
    pyEnv["res.partner"].write([serverState.partnerId], { im_status: "online" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMember", { count: 3 });
    await contains("h6", { text: "Online - 2" });
    await contains("h6", { text: "Offline - 1" });
    await contains(".o-discuss-ChannelMember", {
        text: "John",
        after: ["h6", { text: "Online - 2" }],
        before: ["h6", { text: "Offline - 1" }],
    });
    await contains(".o-discuss-ChannelMember", {
        text: "Mitchell Admin",
        after: ["h6", { text: "Online - 2" }],
        before: ["h6", { text: "Offline - 1" }],
    });
    await contains(".o-discuss-ChannelMember", {
        text: "Dobby",
        after: ["h6", { text: "Offline - 1" }],
    });
});
