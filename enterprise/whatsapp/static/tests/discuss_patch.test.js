import {
    SIZES,
    click,
    contains,
    insertText,
    openDiscuss,
    patchUiSize,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineWhatsAppModels } from "@whatsapp/../tests/whatsapp_test_helpers";

describe.current.tags("desktop");
defineWhatsAppModels();

test("Basic topbar rendering for whatsapp channels", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Discuss-header .o-mail-ThreadIcon .fa-whatsapp");
    await contains(".o-mail-Discuss-threadName", { value: "WhatsApp 1" });
    await contains(".o-mail-Discuss-header button[title='Invite People']");
    await contains(".o-mail-Discuss-header button[name='member-list']");
    await contains(".o-mail-Discuss-header button[name='call']", { count: 0 });
    await contains(".o-mail-Discuss-header button[name='settings']", { count: 0 });
});

test("Invite users into whatsapp channel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
    });
    const partnerId = pyEnv["res.partner"].create({ name: "WhatsApp User" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Invite People']");
    await click(".o-discuss-ChannelInvitation-selectable");
    await click("button[title='Invite']:enabled");
    await contains(".o_mail_notification", { text: "invited WhatsApp User to the channel" });
});

test("Shows whatsapp user in member list", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "WhatsApp Partner" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        whatsapp_partner_id: partnerId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMember.cursor-pointer", { text: "Mitchell Admin" });
    await contains(".o-discuss-ChannelMemberList h6", { text: "WhatsApp User" });
    await contains(".o-discuss-ChannelMember:not(.cursor-pointer)", {
        text: "WhatsApp Partner",
        contains: [".o-mail-ImStatus [title='WhatsApp User']"],
    });
});

test("Mobile has WhatsApp category", async () => {
    const pyEnv = await startServer();
    patchUiSize({ size: SIZES.SM });
    pyEnv["discuss.channel"].create({ name: "WhatsApp 1", channel_type: "whatsapp" });
    await start();
    await openDiscuss();
    await click(".o-mail-MessagingMenu-navbar button", { text: "WhatsApp" });
    await contains(".o-mail-NotificationItem", { text: "WhatsApp 1" });
});

test('"Search WhatsApp Channel" item selection opens WhatsApp channel', async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "slytherins",
        channel_type: "whatsapp",
    });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss();
    await click("button", { text: "WhatsApp" });
    await click("button", { text: "Search WhatsApp Channel" });
    await insertText("input[placeholder='Search WhatsApp Channel']", "slytherins");
    await click(".o-mail-ChannelSelector-suggestion");
    await contains(".o-mail-ChatWindow-header div[title='slytherins']");
});
