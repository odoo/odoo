import {
    click,
    contains,
    mockGetMedia,
    setupChatHub,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { defineLivechatModels } from "@im_livechat/../tests/livechat_test_helpers";

import { test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";

import { Command, serverState } from "@web/../tests/web_test_helpers";

defineLivechatModels();

test.tags("desktop");
test("should display started a call message with operator livechat username", async () => {
    mockDate("2025-01-01 12:00:00", +1);
    mockGetMedia();
    const pyEnv = await startServer();
    pyEnv["res.partner"].write(serverState.partnerId, {
        user_livechat_username: "mitchell boss",
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    setupChatHub({ opened: [channelId] });
    await start();
    await contains(".o-mail-ChatWindow", { text: "Visitor" });
    await click("[title='Start Call']");
    await contains(".o-mail-NotificationMessage", { text: "mitchell boss started a call.1:00 PM" });
});
