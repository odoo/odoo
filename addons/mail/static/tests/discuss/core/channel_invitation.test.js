import {
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    setupChatHub,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { Command, getService, serverState, withUser } from "@web/../tests/web_test_helpers";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { user } from "@web/core/user";

describe.current.tags("desktop");
defineMailModels();

test("Can invite people from member panel", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
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
    await contains(".o-discuss-ChannelMemberList"); // wait for auto-open of this panel
    await click("button[title='Add People']");
});

test("can invite users in channel from chat window", async () => {
    mockDate("2025-01-01 12:00:00", +1);
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_type: "channel",
    });
    setupChatHub({ opened: [channelId] });
    await start();
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item:text('Invite People')");
    await contains(".o-discuss-ChannelInvitation");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner'))");
    await click(".o-discuss-ChannelInvitation [title='Invite']:enabled");
    await contains(".o-discuss-ChannelInvitation", { count: 0 });
    const [{ date }] = pyEnv["mail.message"].search_read([["res_id", "=", channelId]]);
    const time = deserializeDateTime(date).toLocaleString(luxon.DateTime.TIME_SIMPLE, {
        locale: user.lang,
    });
    await contains(
        `.o-mail-Thread .o-mail-NotificationMessage:text('Mitchell Admin invited TestPartner to the channel${time}')`
    );
});

test("should be able to search for a new user to invite from an existing chat", async () => {
    const pyEnv = await startServer();
    const partnerId_1 = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    const partnerId_2 = pyEnv["res.partner"].create({
        email: "testpartner2@odoo.com",
        name: "TestPartner2",
    });
    pyEnv["res.users"].create({ partner_id: partnerId_1 });
    pyEnv["res.users"].create({ partner_id: partnerId_2 });
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId_1 }),
        ],
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList"); // wait for auto-open of this panel
    await click("button[title='Add People']");
    await insertText(".o-discuss-ChannelInvitation-search", "TestPartner2");
    await contains(".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner2'))");
});

test("Invitation form should display channel group restriction", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const groupId = pyEnv["res.groups"].create({
        name: "testGroup",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_type: "channel",
        group_public_id: groupId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList"); // wait for auto-open of this panel
    await click("button[title='Add People']");
    await contains(
        ".o-discuss-ChannelInvitation div:text('Access restricted to group \"testGroup\"')",
        {
            after: ["button .fa.fa-copy"],
        }
    );
});

test("should be able to create a new group chat from an existing chat", async () => {
    const pyEnv = await startServer();
    const partnerId_1 = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    const partnerId_2 = pyEnv["res.partner"].create({
        email: "testpartner2@odoo.com",
        name: "TestPartner2",
    });
    pyEnv["res.users"].create({ partner_id: partnerId_1 });
    pyEnv["res.users"].create({ partner_id: partnerId_2 });
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId_1 }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-DiscussContent-header button[title='Invite People']");
    await contains(".o-discuss-ChannelInvitation");
    await insertText(".o-discuss-ChannelInvitation-search", "TestPartner2");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner2'))");
    await click("button[title='Create Group Chat']:enabled");
    await contains(".o-discuss-ChannelInvitation", { count: 0 });
    await contains(
        ".o-mail-DiscussSidebarChannel-itemName:text('Mitchell Admin, TestPartner, and TestPartner2')"
    );
});

test("unnamed group chat should display correct name just after being invited", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "jane@example.com",
        name: "Jane",
    });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const [, channelId] = pyEnv["discuss.channel"].create([
        { name: "General" },
        {
            channel_member_ids: [Command.create({ partner_id: partnerId })],
            channel_type: "group",
        },
    ]);
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel-itemName:text('General')");
    await contains(".o-mail-DiscussSidebarChannel-itemName:text('Jane and Mitchell Admin')", {
        count: 0,
    });
    const currentUserId = serverState.userId;
    await withUser(userId, () =>
        getService("mail.store").fetchStoreData("/discuss/channel/add_members", {
            channel_id: channelId,
            user_ids: [currentUserId],
        })
    );
    await contains(".o-mail-DiscussSidebarChannel-itemName:text('Jane and Mitchell Admin')");
});

test("invite user to self chat opens DM chat with user", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "TestGuest" });
    const partnerId_1 = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    pyEnv["res.users"].create({ partner_id: partnerId_1 });
    const [selfChatId] = pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: partnerId_1 }),
                Command.create({ partner_id: serverState.partnerId }),
            ],
            channel_type: "group",
        },
        {
            // group chat with guest as correspondent for coverage of no crash
            channel_member_ids: [
                Command.create({ guest_id: guestId }),
                Command.create({ partner_id: serverState.partnerId }),
            ],
            channel_type: "group",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partnerId_1 }),
            ],
            channel_type: "chat",
        },
    ]);
    await start();
    await openDiscuss(selfChatId);
    await contains(".o-mail-DiscussSidebarChannel-itemName:text('Mitchell Admin')"); // self-chat
    await contains(".o-mail-DiscussSidebarChannel-itemName:text('TestPartner and Mitchell Admin')");
    await contains(".o-mail-DiscussSidebarChannel-itemName:text('TestGuest and Mitchell Admin')");
    await contains(".o-mail-DiscussSidebarChannel-itemName:text('TestPartner')");
    await click(".o-mail-DiscussContent-header button[title='Invite People']");
    await insertText(".o-discuss-ChannelInvitation-search", "TestPartner");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner'))");
    await click("button:contains('Go to Conversation'):enabled");
    await contains(".o-mail-DiscussSidebarChannel.o-active:text('TestPartner')");
});

test("Invite sidebar action has the correct title for group chats", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "group",
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Chat Actions']");
    await click(".o-dropdown-item:text('Invite People')");
    await contains(".modal-title:text('Mitchell Admin and Demo')");
});
