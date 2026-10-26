import { expect } from "@odoo/hoot";
import { waitFor, waitForNone } from "@odoo/hoot-dom";
import {
    click,
    setupChatHub,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { Command, onRpc, serverState } from "@web/../tests/web_test_helpers";

export async function livechatLastAgentLeaveFromChatWindow() {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatId]])
            .map(({ id }) => id),
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const livechatChannelId = pyEnv["im_livechat.channel"].create({
        name: "HR",
        user_ids: [serverState.userId],
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        livechat_channel_id: livechatChannelId,
        create_uid: serverState.publicUserId,
    });
    setupChatHub({ opened: [channelId] });
    onRpc("discuss.channel", "action_unfollow", () => {
        expect.step("action_unfollow");
    });
    await start();
    await waitFor(".o-mail-ChatWindow:count(1)");
    await click("button[title*='Close Chat Window']");
    await click("button:contains('Yes, leave conversation')");
    await expect.waitForSteps(["action_unfollow"]);
    await waitForNone(".o-mail-ChatWindow");
}
