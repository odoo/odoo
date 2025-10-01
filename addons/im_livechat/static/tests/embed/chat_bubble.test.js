import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { contains, setupChatHub, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, makeMockEnv } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("Do not show bot IM status", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    await makeMockEnv({ embedLivechat: true });
    const partnerId1 = pyEnv["res.partner"].create({ name: "Mitchell", im_status: "online" });
    pyEnv["res.users"].create({ partner_id: partnerId1 });
    const channelId1 = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: partnerId1 })],
        channel_type: "chat",
    });
    const partnerId2 = pyEnv["res.partner"].create({ name: "Dummy" });
    const channelId2 = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: partnerId2, livechat_member_type: "bot" }),
        ],
        channel_type: "livechat",
        livechat_operator_id: partnerId2,
    });
    setupChatHub({ folded: [channelId1, channelId2] });
    await start({ authenticateAs: false });
    await contains(".o-mail-ChatBubble[name='Mitchell'] .o-mail-ImStatus");
    await contains(".o-mail-ChatBubble[name='Dummy']");
    await contains(".o-mail-ChatBubble[name='Dummy'] .o-mail-ImStatus", { count: 0 });
});
