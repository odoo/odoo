import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { contains, setupChatHub, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, makeMockEnv, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("Do not show bot IM status", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    await makeMockEnv({ embedLivechat: true });
    const partnerId1 = pyEnv["res.partner"].create({ name: "Mitchell" });
    pyEnv["res.users"].create({ partner_id: partnerId1, im_status: "online" });
    const channelId1 = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: partnerId1 })],
        channel_type: "chat",
    });
    const partnerId2 = pyEnv["res.partner"].create({ name: "Dummy" });
    const channelId2 = pyEnv["discuss.channel"].create({
        name: "Dummy",
        channel_member_ids: [
            Command.create({ partner_id: partnerId2, livechat_member_type: "bot" }),
        ],
        channel_type: "livechat",
    });
    setupChatHub({ folded: [channelId1, channelId2] });
    // IM status is only sent to internal users, so view as an operator (not a visitor) to
    // assert a member's status is shown while a chatbot's stays hidden.
    const [operator] = pyEnv["res.users"].search_read([["id", "=", serverState.userId]]);
    await start({ authenticateAs: operator });
    await contains(".o-mail-ChatBubble[name='Mitchell'] .o-mail-ImStatus");
    await contains(".o-mail-ChatBubble[name='Dummy']");
    await contains(".o-mail-ChatBubble[name='Dummy'] .o-mail-ImStatus", { count: 0 });
});
