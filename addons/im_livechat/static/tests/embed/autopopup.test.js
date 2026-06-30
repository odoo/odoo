import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { contains, setupChatHub, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

describe.current.tags("desktop");
defineLivechatModels();

test("persisted session", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultEmbedConfig();
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
    setupChatHub({ opened: [channelId] });
    await start({
        authenticateAs: { ...pyEnv["mail.guest"].read(guestId)[0], _name: "mail.guest" },
    });
    await contains(".o-mail-ChatWindow");
});

test("rule received in init", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    const autopopupRuleId = pyEnv["im_livechat.channel.rule"].create({
        auto_popup_timer: 0,
        action: "auto_popup",
    });
    patchWithCleanup(mailDataHelpers, {
        _process_request_for_all(store) {
            super._process_request_for_all(...arguments);
            store.add(pyEnv["im_livechat.channel.rule"].browse(autopopupRuleId), {
                action: "auto_popup",
                auto_popup_timer: 0,
            });
            store.add({ livechat_rule: autopopupRuleId });
        },
    });
    await start({ authenticateAs: false });
    await contains(".o-mail-ChatWindow");
});
