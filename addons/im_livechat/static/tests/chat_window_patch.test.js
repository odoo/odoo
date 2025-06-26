import { click, contains, start, startServer } from "@mail/../tests/mail_test_helpers";
import { test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "./livechat_test_helpers";

defineLivechatModels();

test.tags("desktop");
test("closing a chat window with no message from admin side unpins it", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                unpin_dt: false,
                partner_id: serverState.partnerId,
            }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "livechat",
        uuid: "channel-10-uuid",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await click(".o-mail-ChatWindow-command[title*='Close Chat Window']", {
        parent: [".o-mail-ChatWindow", { text: "Demo" }],
    });
    await contains(".o_notification", { text: "You unpinned your conversation with Demo" });
});
