/* @odoo-module */

import { Command } from "@mail/../tests/helpers/command";
import { click, insertText, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("channel invitation form");

QUnit.test(
    "should display the channel invitation form after clicking on the invite button of a chat",
    async (assert) => {
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
        await openDiscuss(channelId);
        await click(".o-mail-Discuss-header button[title='Add Users']");
        assert.containsOnce($, ".o-discuss-ChannelInvitation");
    }
);

QUnit.test("can invite users in channel from chat window", async (assert) => {
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
    await click("[title='More actions']");
    await click("[title='Add Users']");
    assert.containsOnce($, ".o-discuss-ChannelInvitation");
    await click("div:contains(TestPartner) input[type='checkbox']");
    await click("[title='Invite to Channel']");
    assert.containsNone($, ".o-discuss-ChannelInvitation");
    assert.containsOnce(
        $,
        ".o-mail-Thread .o-mail-NotificationMessage:contains(Mitchell Admin invited TestPartner to the channel)"
    );
});

QUnit.test(
    "should be able to search for a new user to invite from an existing chat",
    async (assert) => {
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
        await openDiscuss(channelId);
        await click(".o-mail-Discuss-header button[title='Add Users']");
        await insertText(".o-discuss-ChannelInvitation-search", "TestPartner2");
        assert.strictEqual($(".o-discuss-ChannelInvitation-selectable").text(), "TestPartner2");
    }
);

QUnit.test("Invitation form should display channel group restriction", async (assert) => {
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
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Add Users']");
    assert.containsOnce(
        $,
        '.o-discuss-ChannelInvitation:contains(Access restricted to group "testGroup")'
    );
});

QUnit.test("should be able to create a new group chat from an existing chat", async (assert) => {
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
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Add Users']");
    await insertText(".o-discuss-ChannelInvitation-search", "TestPartner2");
    await click(".form-check-input");
    await click("button[title='Create Group Chat']");
    assert.strictEqual(
        $(".o-mail-Discuss-threadName").val(),
        "Mitchell Admin, TestPartner, and TestPartner2"
    );
});
