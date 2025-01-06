import { click, contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "./livechat_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("closing a chat window with no message from admin side unpins it", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Partner 1" },
        { name: "Partner 2" },
    ]);
    pyEnv["res.users"].create([{ partner_id: partnerId_1 }, { partner_id: partnerId_2 }]);
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                unpin_dt: false,
                partner_id: serverState.partnerId,
            }),
            Command.create({ partner_id: partnerId_1 }),
        ],
        channel_type: "livechat",
    });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                unpin_dt: false,
                partner_id: serverState.partnerId,
            }),
            Command.create({ partner_id: partnerId_2 }),
        ],
        channel_type: "livechat",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "Partner 2" });
    await click(".o-mail-ChatWindow-command[title*='Close Chat Window']", {
        parent: [".o-mail-ChatWindow", { text: "Partner 2" }],
    });
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { text: "Partner 1" });
    await contains(".o-mail-DiscussSidebarChannel", { count: 0, text: "Partner 2" });
});
