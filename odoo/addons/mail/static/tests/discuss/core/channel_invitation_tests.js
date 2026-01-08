/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("channel invitation form");

QUnit.test(
    "should display the channel invitation form after clicking on the invite button of a chat",
    async () => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({
            email: "testpartner@odoo.com",
            name: "TestPartner",
        });
        pyEnv["res.users"].create({ partner_id: partnerId });
        const channelId = pyEnv["discuss.channel"].create({
            name: "TestChanel",
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "channel",
        });
        const { openDiscuss } = await start({ hasTimeControl: true });
        openDiscuss(channelId);
        await click(".o-mail-Discuss-header button[title='Add Users']");
        await contains(".o-discuss-ChannelInvitation");
    }
);

QUnit.test("can invite users in channel from chat window", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["discuss.channel"].create({
        name: "TestChanel",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId, is_minimized: true }),
        ],
        channel_type: "channel",
    });
    await start();
    await click("[title='Open Actions Menu']");
    await click("[title='Add Users']");
    await contains(".o-discuss-ChannelInvitation");
    await click(".o-discuss-ChannelInvitation-selectable", { text: "TestPartner" });
    await click("[title='Invite to Channel']:enabled");
    await contains(".o-discuss-ChannelInvitation", { count: 0 });
    await contains(".o-mail-Thread .o-mail-NotificationMessage", {
        text: "Mitchell Admin invited TestPartner to the channel",
    });
});

QUnit.test("should be able to search for a new user to invite from an existing chat", async () => {
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
        name: "TestChanel",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId_1 }),
        ],
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Add Users']");
    await insertText(".o-discuss-ChannelInvitation-search", "TestPartner2");
    await contains(".o-discuss-ChannelInvitation-selectable", { text: "TestPartner2" });
});

QUnit.test("Invitation form should display channel group restriction", async () => {
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
        name: "TestChanel",
        channel_member_ids: [Command.create({ partner_id: pyEnv.currentPartnerId })],
        channel_type: "channel",
        group_public_id: groupId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Add Users']");
    await contains(".o-discuss-ChannelInvitation div", {
        text: 'Access restricted to group "testGroup"',
        after: ["button .fa.fa-copy"],
    });
});

QUnit.test("should be able to create a new group chat from an existing chat", async () => {
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
        name: "TestChanel",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId_1 }),
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Add Users']");
    await insertText(".o-discuss-ChannelInvitation-search", "TestPartner2");
    await click(".o-discuss-ChannelInvitation-selectable", { text: "TestPartner2" });
    await click("button[title='Create Group Chat']:enabled");
    await contains(".o-mail-DiscussSidebarChannel", {
        text: "Mitchell Admin, TestPartner, and TestPartner2",
    });
});
