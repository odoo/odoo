import { expirableStorage } from "@im_livechat/embed/common/expirable_storage";
import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { describe, test } from "@odoo/hoot";
import { contains, start, startServer } from "@mail/../tests/mail_test_helpers";
import { Command, onRpc, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("persisted session", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultEmbedConfig();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId, fold_state: "open" }),
        ],
        channel_type: "livechat",
        livechat_active: true,
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: serverState.partnerId,
    });
    expirableStorage.setItem(
        "im_livechat.saved_state",
        JSON.stringify({
            store: { "discuss.channel": [{ id: channelId }] },
            persisted: true,
            livechatUserId: serverState.publicUserId,
        })
    );
    await start({
        authenticateAs: { ...pyEnv["mail.guest"].read(guestId)[0], _name: "mail.guest" },
    });
    await contains(".o-mail-ChatWindow");
});

test("rule received in init", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    onRpc("/im_livechat/init", () => {
        return {
            available_for_me: true,
            rule: { action: "auto_popup", auto_popup_delay: 0 },
        };
    });
    await start({ authenticateAs: false });
    await contains(".o-mail-ChatWindow");
});
