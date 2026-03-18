import { defineLivechatModels } from "@im_livechat/../tests/livechat_test_helpers";
import {
    click,
    contains,
    sendPresenceUpdate,
    setupChatHub,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { ImStatusMixin } from "@mail/core/common/im_status_mixin";
import { describe, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { Command, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("Visitor going offline shows disconnection banner to operator", async () => {
    patchWithCleanup(ImStatusMixin, { IM_STATUS_DEBOUNCE_DELAY: 0 });
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatId]])
            .map(({ id }) => id),
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor", im_status: "online" });
    const livechatChannelId = pyEnv["im_livechat.channel"].create({
        name: "HR",
        user_ids: [serverState.userId],
    });
    const channel_id = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        livechat_channel_id: livechatChannelId,
        create_uid: serverState.publicUserId,
    });
    setupChatHub({ opened: [channel_id] });
    await start();
    await contains(".o-mail-ChatWindow");
    mockDate("2025-01-01 12:00:00", +1);
    sendPresenceUpdate("mail.guest", guestId, "offline");
    await contains(".o-livechat-VisitorDisconnected", {
        text: "Visitor is disconnected since 1:00 PM",
    });
    mockDate("2025-01-02 12:00:00", +1);
    await click("button[title*='Fold']");
    await click(".o-mail-ChatBubble");
    await contains(".o-livechat-VisitorDisconnected", {
        text: "Visitor is disconnected since yesterday at 1:00 PM",
    });
    mockDate("2025-01-05 12:00:00", +1);
    await click("button[title*='Fold']");
    await click(".o-mail-ChatBubble");
    await contains(".o-livechat-VisitorDisconnected", { text: `Visitor is disconnected` });
    sendPresenceUpdate("mail.guest", guestId, "online");
    await contains(".o-livechat-VisitorDisconnected", { count: 0 });
});
