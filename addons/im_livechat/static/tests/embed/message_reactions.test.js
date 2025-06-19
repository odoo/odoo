import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { expirableStorage } from "@im_livechat/core/common/expirable_storage";

import {
    click,
    contains,
    hover,
    setupChatHub,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { describe, test } from "@odoo/hoot";

import { Command, serverState } from "@web/../tests/web_test_helpers";

defineLivechatModels();
describe.current.tags("desktop");

test("user custom live chat user name for message reactions", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultEmbedConfig();
    pyEnv["res.partner"].write([serverState.partnerId], { user_livechat_username: "Michou" });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: serverState.partnerId,
    });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "discuss.channel",
        reaction_ids: [
            pyEnv["mail.message.reaction"].create({
                content: "👍",
                partner_id: serverState.partnerId,
            }),
        ],
    });
    expirableStorage.setItem(
        "im_livechat.saved_state",
        JSON.stringify({
            store: { "discuss.channel": [{ id: channelId }] },
            persisted: true,
            livechatUserId: serverState.publicUserId,
        })
    );
    setupChatHub({ opened: [channelId] });
    await start({
        authenticateAs: { ...pyEnv["mail.guest"].read(guestId)[0], _name: "mail.guest" },
    });
    await hover(".o-mail-MessageReaction");
    await click(".o-mail-MessageReactionList-preview", {
        text: "👍:+1: reacted by Michou",
    });
    await contains(".o-mail-MessageReactionMenu-persona", { text: "Michou" });
});
