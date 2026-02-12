import {
    click,
    contains,
    defineMailModels,
    listenStoreFetch,
    openDiscuss,
    start,
    startServer,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";
import { animationFrame, describe, test } from "@odoo/hoot";
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

test("members should be correctly categorised into online/offline", async () => {
    const pyEnv = await startServer();
    const [onlinePartnerId, idlePartnerId, onlyPartnerId] = pyEnv["res.partner"].create([
        { name: "Online Partner" },
        { name: "Idle Partner" },
        { name: "Only Partner" },
    ]);
    pyEnv["res.users"].create([
        { partner_id: onlinePartnerId, im_status: "online" },
        { partner_id: idlePartnerId, im_status: "away" },
    ]);
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChanel",
        channel_member_ids: [
            Command.create({ partner_id: onlyPartnerId }),
            Command.create({ partner_id: onlinePartnerId }),
            Command.create({ partner_id: idlePartnerId }),
        ],
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList h6:text('Online - 2')");
    await contains(".o-discuss-ChannelMemberList h6:text('Offline - 1')");
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
    patchWithCleanup(AvatarCardPopover.prototype, {
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
    changeTzResolver = Promise.withResolvers();
    await waitStoreFetch(["avatar_card"]);
    await changeTzResolver.promise;
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
    await contains(".o-discuss-ChannelMemberList"); // wait for auto-open of this panel
    await contains(".o-discuss-ChannelMemberList h6:text('Offline - 1')");
    await click("[title='Invite People']");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('Harry'))");
    await click(".o-discuss-ChannelInvitation [title='Invite']:enabled");
    await contains(".o-discuss-ChannelInvitation", { count: 0 });
    await contains(".o-discuss-ChannelMemberList h6:text('Offline - 2')");
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
    pyEnv["res.users"].write([serverState.userId], { im_status: "online" });
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

test("Shows owner / admin in members panel + member actions", async () => {
    const pyEnv = await startServer();
    const [demoPid, johnPid] = pyEnv["res.partner"].create([{ name: "Demo" }, { name: "John" }]);
    const marioGid = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, channel_role: "owner" }),
            Command.create({ partner_id: demoPid, channel_role: "admin" }),
            Command.create({ partner_id: johnPid }),
            Command.create({ guest_id: marioGid }),
        ],
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMember", { count: 4 });
    await contains(`.o-discuss-ChannelMember:has(:text(${serverState.partnerName}))`);
    await contains(".o-discuss-ChannelMember:has(:text(Demo))");
    await contains(".o-discuss-ChannelMember:has(:text(John))");
    await contains(".o-discuss-ChannelMember:has(:text(Mario))");
    await contains(
        ".o-discuss-ChannelMember:text('" +
            serverState.partnerName +
            "') .fa-star.text-warning[title='Channel Owner']"
    );
    await contains(
        ".o-discuss-ChannelMember:text('Demo') .fa-star.text-primary[title='Channel Admin']"
    );
    await click(
        ".o-discuss-ChannelMember:text('" + serverState.partnerName + "') [title='Member Actions']"
    );
    await contains(".o-dropdown-item", { count: 3 });
    await contains(".o-dropdown-item:eq(0):has(:text(Set Admin))");
    await contains(".o-dropdown-item:eq(1):has(:text(Remove Owner))");
    await contains(".o-dropdown-item:eq(2):has(:text(Remove Member))");
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
