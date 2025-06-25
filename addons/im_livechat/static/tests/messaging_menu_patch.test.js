import { click, contains, patchUiSize, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "./livechat_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test('livechats should be in "chat" filter', async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu button.fw-bold", { text: "All" });
    await contains(".o-mail-NotificationItem", { text: "Visitor 11" });
    await click(".o-mail-MessagingMenu button", { text: "Chats" });
    await contains(".o-mail-MessagingMenu button.fw-bold", { text: "Chats" });
    await contains(".o-mail-NotificationItem", { text: "Visitor 11" });
});

test('livechats should be in "livechat" tab in mobile', async () => {
    patchUiSize({ height: 360, width: 640 });
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "Livechat" });
    await contains(".o-mail-NotificationItem", { text: "Visitor 11" });
    await click("button", { text: "Chat" });
    await contains(".o-mail-NotificationItem", { count: 0, text: "Visitor 11" });
});
