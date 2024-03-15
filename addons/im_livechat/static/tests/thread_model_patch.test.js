import { describe, test } from "@odoo/hoot";
import { click, contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "./livechat_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("Thread name unchanged when inviting new users", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "James" });
    pyEnv["res.partner"].create({
        name: "James",
        user_ids: [userId],
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor #20" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor #20",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Discuss-threadName[title='Visitor #20']");
    await click("button[title='Add Users']");
    await click("input", {
        parent: [".o-discuss-ChannelInvitation-selectable", { text: "James" }],
    });
    await click("button:enabled", { text: "Invite" });
    await contains(".o-discuss-ChannelInvitation", { count: 0 });
    await click("button[title='Show Member List']");
    await contains(".o-discuss-ChannelMember", { text: "James" });
    await contains(".o-mail-Discuss-threadName[title='Visitor #20']");
});
