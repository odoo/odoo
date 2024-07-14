/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";
import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";

import { contains, click, insertText } from "@web/../tests/utils";

QUnit.module("discuss (patch)");

QUnit.test("Basic topbar rendering for whatsapp channels", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Discuss-header .o-mail-ThreadIcon .fa-whatsapp");
    await contains(".o-mail-Discuss-threadName:disabled", { value: "WhatsApp 1" });
    await contains(".o-mail-Discuss-header button[title='Add Users']");
    await contains(".o-mail-Discuss-header button[name='call']", { count: 0 });
    await contains(".o-mail-Discuss-header button[name='settings']", { count: 0 });
});

QUnit.test("Invite users into whatsapp channel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
    });
    const partnerId = pyEnv["res.partner"].create({ name: "WhatsApp User" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Add Users']");
    await click(".o-discuss-ChannelInvitation-selectable");
    await click("button[title='Invite']:enabled");
    await contains(".o_mail_notification", { text: "invited WhatsApp User to the channel" });
});

QUnit.test("Mobile has WhatsApp category", async () => {
    const pyEnv = await startServer();
    patchUiSize({ size: SIZES.SM });
    pyEnv["discuss.channel"].create({ name: "WhatsApp 1", channel_type: "whatsapp" });
    const { openDiscuss } = await start();
    await openDiscuss();
    await click(".o-mail-MessagingMenu-navbar button", { text: "WhatsApp" });
    await contains(".o-mail-NotificationItem", { text: "WhatsApp 1" });
});

QUnit.test('"Search WhatAapp Channel" item selection opens whatsapp channel', async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "slytherins",
        channel_type: "whatsapp",
    });
    patchUiSize({ height: 360, width: 640 });
    const { openDiscuss } = await start();
    await openDiscuss();
    await click("button", { text: "WhatsApp" });
    await click("button", { text: "Search WhatsApp Channel" });
    await insertText("input[placeholder='Search WhatsApp Channel']", "slytherins");
    await click(".o-mail-ChannelSelector-suggestion");
    await contains(".o-mail-ChatWindow-header div[title='slytherins']");
});
