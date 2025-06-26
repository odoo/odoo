import {
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, getService, serverState, withUser } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("should display the channel invitation form after clicking on the invite button of a chat", async () => {
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
    await click(".o-mail-Discuss-header button[title='Invite People']");
    await contains(".o-discuss-ChannelInvitation");
});

test("can invite users in channel from chat window", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_member_ids: [
            Command.create({ fold_state: "open", partner_id: serverState.partnerId }),
        ],
        channel_type: "channel",
    });
    await start();
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Invite People" });
    await contains(".o-discuss-ChannelInvitation");
    await click(".o-discuss-ChannelInvitation-selectable", { text: "TestPartner" });
    await click("[title='Invite to Channel']:enabled");
    await contains(".o-discuss-ChannelInvitation", { count: 0 });
    await contains(".o-mail-Thread .o-mail-NotificationMessage", {
        text: "Mitchell Admin invited TestPartner to the channel",
    });
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
    await click(".o-mail-Discuss-header button[title='Invite People']");
    await insertText(".o-discuss-ChannelInvitation-search", "TestPartner2");
    await contains(".o-discuss-ChannelInvitation-selectable", { text: "TestPartner2" });
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
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "channel",
        group_public_id: groupId,
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Invite People']");
    await contains(".o-discuss-ChannelInvitation div", {
        text: 'Access restricted to group "testGroup"',
        after: ["button .fa.fa-copy"],
    });
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
    await click(".o-mail-Discuss-header button[title='Invite People']");
    await insertText(".o-discuss-ChannelInvitation-search", "TestPartner2");
    await click(".o-discuss-ChannelInvitation-selectable", { text: "TestPartner2" });
    await click("button[title='Create Group Chat']:enabled");
    await contains(".o-mail-DiscussSidebarChannel", {
        text: "Mitchell Admin, TestPartner, and TestPartner2",
    });
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
    await contains(".o-mail-DiscussSidebarChannel", { text: "General" });
    await contains(".o-mail-DiscussSidebarChannel", { count: 0, text: "Jane and Mitchell Admin" });
    const currentPartnerId = serverState.partnerId;
    await withUser(userId, async () => {
        await getService("orm").call("discuss.channel", "add_members", [[channelId]], {
            partner_ids: [currentPartnerId],
        });
    });
    await contains(".o-mail-DiscussSidebarChannel", { text: "Jane and Mitchell Admin" });
    await contains(".o_notification", {
        text: "You have been invited to #Jane and Mitchell Admin",
    });
});
