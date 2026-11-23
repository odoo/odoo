/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains } from "@web/../tests/utils";

QUnit.module("Channel invite");

QUnit.test("Can invite a partner to a livechat channel", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "James" });
    pyEnv["res.partner"].create({
        name: "James",
        user_ids: [userId],
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 20" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 20",
        name: "Visitor 20",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("button[title='Add Users']");
    await click("input", {
        parent: [".o-discuss-ChannelInvitation-selectable", { text: "James" }],
    });
    await click("button:enabled", { text: "Invite" });
    await contains(".o-discuss-ChannelInvitation", { count: 0 });
    await click("button[title='Show Member List']");
    await contains(".o-discuss-ChannelMember", { text: "James" });
});

QUnit.test("Available operators come first", async () => {
    const pyEnv = await startServer();
    pyEnv["res.partner"].create({
        name: "Harry",
        im_status: "offline",
        user_ids: [pyEnv["res.users"].create({ name: "Harry" })],
    });
    const ronId = pyEnv["res.partner"].create({
        name: "Ron",
        im_status: "online",
        user_ids: [pyEnv["res.users"].create({ name: "Available operator" })],
    });
    pyEnv["im_livechat.channel"].create({
        available_operator_ids: [Command.create({ partner_id: ronId })],
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor #1" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor #1",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
    });

    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[title='Add Users']");
    await contains(".o-discuss-ChannelInvitation-selectable", { count: 2 });
    await contains(":nth-child(1 of .o-discuss-ChannelInvitation-selectable)", { text: "Ron" });
    await contains(":nth-child(2 of .o-discuss-ChannelInvitation-selectable)", { text: "Harry" });
});

QUnit.test("Partners invited most frequently by the current user come first", async () => {
    const pyEnv = await startServer();
    pyEnv["res.partner"].create({
        name: "John",
        im_status: "offline",
        user_ids: [pyEnv["res.users"].create({ name: "John" })],
    });
    pyEnv["res.partner"].create({
        name: "Albert",
        im_status: "offline",
        user_ids: [pyEnv["res.users"].create({ name: "Albert" })],
    });
    const guestId_1 = pyEnv["mail.guest"].create({ name: "Visitor #1" });
    pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor #1",
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ guest_id: guestId_1 }),
        ],
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const guestId_2 = pyEnv["mail.guest"].create({ name: "Visitor #2" });
    pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor #2",
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ guest_id: guestId_2 }),
        ],
        livechat_operator_id: pyEnv.currentPartnerId,
    });

    const { openDiscuss } = await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebarChannel", { text: "Visitor #1" });
    await click("button[title='Add Users']");
    await click("input", { parent: [".o-discuss-ChannelInvitation-selectable", { text: "John" }] });
    await click("button:enabled", { text: "Invite" });
    await click(".o-mail-DiscussSidebarChannel", { text: "Visitor #2" });
    await click("button[title='Add Users']");
    await contains(".o-discuss-ChannelInvitation-selectable", { count: 2 });
    await contains(":nth-child(1 of .o-discuss-ChannelInvitation-selectable)", { text: "John" });
    await contains(":nth-child(2 of .o-discuss-ChannelInvitation-selectable)", { text: "Albert" });
});
