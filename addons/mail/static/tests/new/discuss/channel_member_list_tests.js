/** @odoo-module **/

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { createLocalId } from "@mail/new/utils/misc";
import { nextTick } from "@web/../tests/helpers/utils";

QUnit.module("channel member list");

QUnit.test(
    "there should be a button to show member list in the thread view topbar initially",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
        const channelId = pyEnv["mail.channel"].create({
            name: "TestChanel",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId }],
            ],
            channel_type: "channel",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, "[title='Show Member List']");
    }
);

QUnit.test(
    "should show member list when clicking on show member list button in thread view topbar",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
        const channelId = pyEnv["mail.channel"].create({
            name: "TestChanel",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId }],
            ],
            channel_type: "channel",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await click("button[title='Show Member List']");
        assert.containsOnce($, ".o-mail-ChannelMemberList");
    }
);

QUnit.test("should have correct members in member list", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["mail.channel"].create({
        name: "TestChanel",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[title='Show Member List']");
    assert.containsN($, ".o-mail-ChannelMember", 2);
    assert.containsOnce($, `.o-mail-ChannelMember:contains("${pyEnv.currentPartner.name}")`);
    assert.containsOnce($, ".o-mail-ChannelMember:contains('Demo')");
});

QUnit.test(
    "there should be a button to hide member list in the thread view topbar when the member list is visible",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
        const channelId = pyEnv["mail.channel"].create({
            name: "TestChanel",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId }],
            ],
            channel_type: "channel",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await click("button[title='Show Member List']");
        assert.containsOnce($, "[title='Hide Member List']");
    }
);

QUnit.test("chat with member should be opened after clicking on channel member", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["mail.channel"].create({
        name: "TestChanel",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[title='Show Member List']");
    await click(".o-mail-ChannelMember.cursor-pointer");
    assert.containsOnce($, ".o-mail-AutoresizeInput[title='Demo']");
});

QUnit.test(
    "should show a button to load more members if they are not all loaded",
    async (assert) => {
        // Test assumes at most 100 members are loaded at once.
        const pyEnv = await startServer();
        const channel_member_ids = [];
        for (let i = 0; i < 101; i++) {
            const partnerId = pyEnv["res.partner"].create({ name: "name" + i });
            channel_member_ids.push([0, 0, { partner_id: partnerId }]);
        }
        const channelId = pyEnv["mail.channel"].create({
            name: "TestChanel",
            channel_type: "channel",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        pyEnv["mail.channel"].write([channelId], { channel_member_ids });
        await click("button[title='Show Member List']");
        assert.containsOnce($, "button:contains(Load more)");
    }
);

QUnit.test("Load more button should load more members", async (assert) => {
    // Test assumes at most 100 members are loaded at once.
    const pyEnv = await startServer();
    const channel_member_ids = [];
    for (let i = 0; i < 101; i++) {
        const partnerId = pyEnv["res.partner"].create({ name: "name" + i });
        channel_member_ids.push([0, 0, { partner_id: partnerId }]);
    }
    const channelId = pyEnv["mail.channel"].create({
        name: "TestChanel",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    pyEnv["mail.channel"].write([channelId], { channel_member_ids });
    await click("button[title='Show Member List']");
    await click("button[title='Load more']");
    assert.containsN($, ".o-mail-ChannelMember", 102);
});

QUnit.test("Channel member count update after user joined", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    const userId = pyEnv["res.users"].create({ name: "Harry" });
    pyEnv["res.partner"].create({ name: "Harry", user_ids: [userId] });
    const { env, openDiscuss } = await start();
    await openDiscuss(channelId);
    const thread = env.services["mail.store"].threads[createLocalId("mail.channel", channelId)];
    assert.strictEqual(thread.memberCount, 1);
    await click("button[title='Show Member List']");
    await click("button[title='Add Users']");
    await click(".o-mail-ChannelInvitation-selectable:contains(Harry)");
    await click("button[title='Invite to Channel']");
    assert.strictEqual(thread.memberCount, 2);
});

QUnit.test("Channel member count update after user left", async (assert) => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Dobby" });
    const partnerId = pyEnv["res.partner"].create({ name: "Dobby", user_ids: [userId] });
    const channelId = pyEnv["mail.channel"].create({
        name: "General",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
    });
    const { env, openDiscuss } = await start();
    await openDiscuss(channelId);
    const thread = env.services["mail.store"].threads[createLocalId("mail.channel", channelId)];
    assert.strictEqual(thread.memberCount, 2);
    await env.services.orm.call("mail.channel", "action_unfollow", [channelId], {
        context: { mockedUserId: userId },
    });
    await nextTick();
    assert.strictEqual(thread.memberCount, 1);
});
