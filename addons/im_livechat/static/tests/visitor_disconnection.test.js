import { Command, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "@im_livechat/../tests/livechat_test_helpers";
import {
    contains,
    setupChatHub,
    start,
    startServer,
    click,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { Store } from "@mail/core/common/store_service";
import { Thread } from "@mail/core/common/thread";

describe.current.tags("desktop");
defineLivechatModels();

test("Visitor going offline shows disconnection banner to operator", async () => {
    patchWithCleanup(Store, { IM_STATUS_DEBOUNCE_DELAY: 0 });
    patchWithCleanup(Thread.prototype, {
        setup() {
            super.setup();
            this.IM_STATUS_DELAY = 0;
        },
    });
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
        livechat_operator_id: serverState.partnerId,
        create_uid: serverState.publicUserId,
    });
    setupChatHub({ opened: [channel_id] });
    await start();
    await contains(".o-mail-ChatWindow");
    mockDate("2025-01-01 12:00:00", +1);
    pyEnv["mail.guest"].write(guestId, { im_status: "offline" });
    pyEnv["bus.bus"]._sendone(guestId, "bus.bus/im_status_updated", {
        partner_id: false,
        guest_id: guestId,
        im_status: "offline",
    });
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
    pyEnv["bus.bus"]._sendone(guestId, "bus.bus/im_status_updated", {
        partner_id: false,
        guest_id: guestId,
        im_status: "online",
    });
    await contains(".o-livechat-VisitorDisconnected", { count: 0 });
});
