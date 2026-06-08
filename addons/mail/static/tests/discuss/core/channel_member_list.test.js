import {
    click,
    contains,
    defineMailModels,
    insertText,
    listenStoreFetch,
    openDiscuss,
    start,
    startServer,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";
import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";
import { animationFrame, describe, expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";

import {
    Command,
    getService,
    patchWithCleanup,
    serverState,
    withUser,
} from "@web/../tests/web_test_helpers";

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
    await contains(".o-discuss-ChannelMember:text('" + serverState.partnerName + "')");
    await contains(".o-discuss-ChannelMember:text('Demo')");
});

test("members should be correctly categorised into online/offline/others", async () => {
    const pyEnv = await startServer();
    const [onlinePartnerId, idlePartnerId, offlinePartnerId, noUserPartnerId] = pyEnv[
        "res.partner"
    ].create([
        { name: "Online Partner", user_ids: [Command.create({ im_status: "online" })] },
        { name: "Idle Partner", user_ids: [Command.create({ im_status: "away" })] },
        { name: "Offline Partner", user_ids: [Command.create({ im_status: "offline" })] },
        { name: "No User Partner" },
    ]);
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChanel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: onlinePartnerId }),
            Command.create({ partner_id: idlePartnerId }),
            Command.create({ partner_id: offlinePartnerId }),
            Command.create({ partner_id: noUserPartnerId }),
        ],
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList h6:text('Online - 3')");
    await contains(".o-discuss-ChannelMemberList h6:text('Offline - 1')");
    await contains(".o-discuss-ChannelMemberList h6:text('Others - 1')");
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
    await click(".o-discuss-ChannelMember:has(:text('Demo')).cursor-pointer");
    await contains(".o-mail-avatar-card-name:text('Demo')");
    await click(".o-discuss-ChannelMember:has(:text('Demo')).o-active");
    await click(".o_avatar_card button:text('Send message')");
    await contains(".o-mail-AutoresizeInput[title='Demo']");
});

test("Avatar card shows local timezone", async () => {
    mockDate("2026-01-01 12:00:00");
    const pyEnv = await startServer();
    pyEnv["res.partner"].write([serverState.partnerId], { tz: "Europe/Brussels" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", tz: "Asia/Kolkata" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "channel",
    });
    listenStoreFetch(["avatar_card"]);
    let changeTzResolver = Promise.withResolvers();
    patchWithCleanup(AvatarCard.prototype, {
        /**
         * This assumes this is internal code to compute formatting of tz,
         * and next animation frame implies showing or not of timezone on the card
         */
        onChangeTz(...args) {
            changeTzResolver?.resolve();
            return super.onChangeTz(...args);
        },
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList");
    // Case 1: correspondent tz !== self tz
    await click(".o-discuss-ChannelMember:has(:text('Demo'))");
    await waitStoreFetch(["avatar_card"]);
    await animationFrame();
    await contains(".o-mail-avatar-card-name:text('Demo')");
    await contains(".o-mail-avatar-card-localtime:contains('17:30 local time')");
    await click(".o-mail-Thread");
    await contains(".o-mail-avatar-card-name:text('Demo')", { count: 0 });
    // Case 2: correspondent tz === self tz ('localtime' tz)
    pyEnv["res.partner"].write([partnerId], { tz: "localtime" });
    await click(".o-discuss-ChannelMember:has(:text('Demo'))");
    changeTzResolver = Promise.withResolvers();
    await waitStoreFetch(["avatar_card"]);
    await changeTzResolver.promise;
    await animationFrame();
    await contains(".o-mail-avatar-card-name:text('Demo')");
    await contains(".o-mail-avatar-card-localtime", { count: 0 });
    await click(".o-mail-Thread");
    await contains(".o-mail-avatar-card-name:text('Demo')", { count: 0 });
    // Case 3: correspondent tz === self tz (explicit tz)
    pyEnv["res.partner"].write([partnerId], { tz: "Europe/Brussels" });
    await click(".o-discuss-ChannelMember:has(:text('Demo'))");
    changeTzResolver = Promise.withResolvers();
    await waitStoreFetch(["avatar_card"]);
    await changeTzResolver.promise;
    await animationFrame();
    await contains(".o-mail-avatar-card-name:text('Demo')");
    await contains(".o-mail-avatar-card-localtime", { count: 0 });
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
        ".o-mail-ActionPanel:has(.o-mail-ActionPanel-header:contains('Members')) button:text('Load more')"
    );
});

test("Load more button should load more members", async () => {
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
    pyEnv["discuss.channel"].write([channelId], { channel_member_ids });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMember", { count: 101 });
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
    await contains(".o-discuss-ChannelMemberList"); // wait for auto-open of this panel
    await contains(".o-discuss-ChannelMemberList h6:text('Online - 1')");
    await click("[title='Add People']");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('Harry'))");
    await click(".o-discuss-ChannelInvitation [title='Invite']:enabled");
    await contains(".o-discuss-ChannelInvitation", { count: 0 });
    await contains(".o-discuss-ChannelMemberList h6:text('Online - 2')");
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

test("Can search member", async () => {
    const pyEnv = await startServer();
    const [partnerId1, partnerId2] = pyEnv["res.partner"].create([
        { name: "Alice" },
        { name: "Bob" },
    ]);
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId1 }),
            Command.create({ partner_id: partnerId2 }),
        ],
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList"); // This is from auto-open of member list panel
    await contains(".o-discuss-ChannelMember", { count: 3 });
    await insertText("input[placeholder='Search members']", "Alice");
    await contains(".o-discuss-ChannelMember", { count: 1 });
    await contains(".o-discuss-ChannelMember:text('Alice')");
});

test("Search does not fetch when term is more specific after empty result", async () => {
    const pyEnv = await startServer();
    const [partnerId1, partnerId2] = pyEnv["res.partner"].create([
        { name: "Alice" },
        { name: "Bob" },
    ]);
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId1 }),
            Command.create({ partner_id: partnerId2 }),
        ],
        channel_type: "channel",
    });
    const memberIds = pyEnv["discuss.channel.member"].search([["channel_id", "=", channelId]]);
    const [selfMemberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", serverState.partnerId],
    ]);
    listenStoreFetch("/discuss/channel/members", { logParams: ["/discuss/channel/members"] });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList"); // wait for auto-open of this panel
    await waitStoreFetch(
        `/discuss/channel/members - ${JSON.stringify({
            channel_id: channelId,
            known_member_ids: [selfMemberId], // members not fetched initially
        })}`
    );
    await contains(".o-discuss-ChannelMember", { count: 3 });
    await contains(".o-discuss-ChannelMember:text('Mitchell Admin')");
    await contains(".o-discuss-ChannelMember:text('Alice')");
    await contains(".o-discuss-ChannelMember:text('Bob')");
    await insertText("input[placeholder='Search members']", "a");
    await waitStoreFetch(
        `/discuss/channel/members - ${JSON.stringify({
            channel_id: channelId,
            known_member_ids: memberIds,
            search_term: "a",
        })}`
    );
    await contains(".o-discuss-ChannelMember", { count: 2 });
    await contains(".o-discuss-ChannelMember:text('Mitchell Admin')");
    await contains(".o-discuss-ChannelMember:text('Alice')");
    await insertText("input[placeholder='Search members']", "z");
    await waitStoreFetch(
        `/discuss/channel/members - ${JSON.stringify({
            channel_id: channelId,
            known_member_ids: memberIds,
            search_term: "az",
        })}`
    );
    await contains(".o-discuss-ChannelMember", { count: 0 });
    await contains(".o-discuss-ChannelMemberList span:text('No members found.')");
    await insertText("input[placeholder='Search members']", "z");
    await animationFrame();
    expect.verifySteps([]); // no search 'azz'
    await insertText("input[placeholder='Search members']", "b", { replace: true });
    await waitStoreFetch(
        `/discuss/channel/members - ${JSON.stringify({
            channel_id: channelId,
            known_member_ids: memberIds,
            search_term: "b",
        })}`
    );
    await contains(".o-discuss-ChannelMember", { count: 1 });
    await contains(".o-discuss-ChannelMember:text('Bob')");
});

test("Shows a hint to narrow member search when there's more than 100 matches", async () => {
    const pyEnv = await startServer();
    const channel_member_ids = [Command.create({ partner_id: serverState.partnerId })];
    for (let i = 0; i < 120; i++) {
        const partnerId = pyEnv["res.partner"].create({ name: `Alice ${i}` });
        channel_member_ids.push(Command.create({ partner_id: partnerId }));
    }
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_member_ids,
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList");
    await contains(
        ".o-mail-ActionPanel:has(.o-mail-ActionPanel-header:contains('Members')) button:text('Load more')"
    );
    await contains(".o-discuss-ChannelMember", { count: 101 });
    await insertText("input[placeholder='Search members']", "Alice");
    await contains(".o-discuss-ChannelMember", { count: 100 });
    await contains(
        ".o-discuss-ChannelMemberList span:text('Showing first 100 members. Narrow your search to see more.')"
    );
    await contains(
        ".o-mail-ActionPanel:has(.o-mail-ActionPanel-header:contains('Members')) button:text('Load more')",
        { count: 0 }
    );
});

test("Members are partitioned by online/offline", async () => {
    const pyEnv = await startServer();
    const [userId_1, userId_2] = pyEnv["res.users"].create([
        { name: "Dobby", im_status: "offline" },
        { name: "John", im_status: "online" },
    ]);
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Dobby", user_ids: [userId_1] },
        { name: "John", user_ids: [userId_2] },
    ]);
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId_1 }),
            Command.create({ partner_id: partnerId_2 }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMember", { count: 3 });
    await contains("h6:text('Online - 2')");
    await contains("h6:text('Offline - 1')");
    await contains(".o-discuss-ChannelMember:text('John')", {
        after: ["h6:text('Online - 2')"],
        before: ["h6:text('Offline - 1')"],
    });
    await contains(".o-discuss-ChannelMember:text('Mitchell Admin')", {
        after: ["h6:text('Online - 2')"],
        before: ["h6:text('Offline - 1')"],
    });
    await contains(".o-discuss-ChannelMember:text('Dobby')", {
        after: ["h6:text('Offline - 1')"],
    });
});

test("Shows owner / admin in members panel + member actions for channel owner", async () => {
    const pyEnv = await startServer();
    const [ownerPid, demoPid, johnPid] = pyEnv["res.partner"].create([
        { name: "Owner" },
        { name: "Demo" },
        { name: "John" },
    ]);
    pyEnv["res.users"].create([
        { partner_id: ownerPid, login: "batman", password: "alfred", active: true },
        { partner_id: demoPid, active: true },
        { partner_id: johnPid, active: true },
    ]);
    const marioGid = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_member_ids: [
            Command.create({ partner_id: ownerPid, channel_role: "owner" }),
            Command.create({ partner_id: demoPid, channel_role: "admin" }),
            Command.create({ partner_id: johnPid }),
            Command.create({ guest_id: marioGid }),
        ],
        channel_type: "channel",
    });
    await start({ authenticateAs: { login: "batman", password: "alfred" } });
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMember", { count: 4 });
    await contains(".o-discuss-ChannelMember:has(:text(Owner))");
    await contains(".o-discuss-ChannelMember:has(:text(Demo))");
    await contains(".o-discuss-ChannelMember:has(:text(John))");
    await contains(".o-discuss-ChannelMember:has(:text(Mario))");
    await contains(
        ".o-discuss-ChannelMember:text('Owner') .fa-star.text-warning[title='Channel Owner']"
    );
    await contains(
        ".o-discuss-ChannelMember:text('Demo') .fa-star.text-primary[title='Channel Admin']"
    );
    await click(".o-discuss-ChannelMember:text('Owner') [title='Member Actions']");
    await contains(".o-dropdown-item", { count: 2 });
    await contains(".o-dropdown-item:eq(0):has(:text(Set Admin))");
    await contains(".o-dropdown-item:eq(1):has(:text(Remove Owner))");
    await click(".o-mail-Thread");
    await contains(".o-dropdown-item", { count: 0 });
    await click(".o-discuss-ChannelMember:text('Demo') [title='Member Actions']");
    await contains(".o-dropdown-item", { count: 3 });
    await contains(".o-dropdown-item:eq(0):has(:text(Remove Admin))");
    await contains(".o-dropdown-item:eq(1):has(:text(Set Owner))");
    await contains(".o-dropdown-item:eq(2):has(:text(Remove Member))");
    await click(".o-mail-Thread");
    await contains(".o-dropdown-item", { count: 0 });
    await click(".o-discuss-ChannelMember:text('John') [title='Member Actions']");
    await contains(".o-dropdown-item", { count: 3 });
    await contains(".o-dropdown-item:eq(0):has(:text(Set Admin))");
    await contains(".o-dropdown-item:eq(1):has(:text(Set Owner))");
    await contains(".o-dropdown-item:eq(2):has(:text(Remove Member))");
    await click(".o-discuss-ChannelMember:text('Mario') [title='Member Actions']");
    await contains(".o-dropdown-item", { count: 1 });
    await contains(".o-dropdown-item:has(:text(Remove Member))");
});
