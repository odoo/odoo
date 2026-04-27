import { click, contains, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineWhatsAppModels } from "@whatsapp/../tests/whatsapp_test_helpers";

describe.current.tags("desktop");
defineWhatsAppModels();

test("WhatsApp Channel notification items should have thread icon", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem .o-mail-ThreadIcon");
});

test("Notification items should have unread counter for unread messages", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
    });
    pyEnv["mail.message"].create({
        body: "WhatsApp Message",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "whatsapp_message",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu-counter", { text: "1" });
});
