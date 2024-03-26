import { describe, test } from "@odoo/hoot";
import { loadDefaultEmbedConfig } from "@im_livechat/../tests/livechat_test_helpers";
import { contains, start, startServer } from "@mail/../tests/mail_test_helpers";
import { Command, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";
import { session } from "@web/session";
import { defineWebsiteLivechatModels } from "../website_livechat_test_helpers";

describe.current.tags("desktop");
defineWebsiteLivechatModels();

test("chat request opens chat window", async () => {
    const pyEnv = await startServer();
    const livechatId = await loadDefaultEmbedConfig();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId, fold_state: "open" }),
        ],
        channel_type: "livechat",
        livechat_active: true,
        livechat_channel_id: livechatId,
        livechat_operator_id: serverState.partnerId,
    });
    const [channel] = pyEnv["discuss.channel"].search_read([["id", "=", channelId]]);
    patchWithCleanup(session.livechatData, {
        options: {
            ...session.livechatData.options,
            force_thread: { id: channel.id, model: "discuss.channel" },
        },
    });
    await start({
        authenticateAs: { ...pyEnv["mail.guest"].read(guestId)[0], _name: "mail.guest" },
    });
    await contains(".o-mail-ChatWindow");
});
